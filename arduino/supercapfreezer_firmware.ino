/**
 * SUPERCAPFREEZER Arduino Peltier Controller
 * ==========================================
 * 
 * PT1000 Temperature Sensor + Peltier Feedback Control
 * 
 * FEATURES:
 * - Reads PT1000 RTD via ADC (A0)
 * - Peltier PWM control (heater/cooler on/off or PID feedback)
 * - Simple ASCII serial communication with Raspberry Pi
 * 
 * HARDWARE:
 * - Arduino UNO R4 WiFi
 * - PT1000 sensor with conditioning circuit on A0
 * - Peltier controller PWM input on D3
 * - USB serial to Raspberry Pi
 * 
 * COMMUNICATION:
 * - Pi → Arduino: "SET:25.5" (set target temperature in °C)
 * - Arduino → Pi: "TEMP:23.45 PWM:128" (every 1 second)
 */

#include <stdint.h>

// ===== CONTROL MODE SELECTION =====
// Set to 0 for simple On/Off with hysteresis
// Set to 1 for full PID controller
#define CONTROL_MODE 0  // Change this to switch between modes

// ===== PIN CONFIGURATION =====
#define PELTIER_PWM_PIN    3              // D3: Peltier controller PWM output

// ===== TEMPERATURE SENSOR CALIBRATION (PT1000) =====
// PT1000: R(T) = R0 * [1 + A*T + B*T² + C*(T-100)*T³]
// Standard PT1000 coefficients (DIN 43760):

#define PT1000_R0          1000.0f        // Resistance at 0°C [Ohm]
#define PT1000_A           3.9083e-3f     // Coefficient A [1/°C]
#define PT1000_B          -5.775e-7f      // Coefficient B [1/°C²]
#define PT1000_C          -4.183e-12f     // Coefficient C [1/°C⁴]

// ADC Configuration
#define PT1000_ADC_PIN     A0             // Analog input A0
#define ADC_REF_VOLTAGE    5.0f           // Reference voltage [V]
#define ADC_RESOLUTION     1024           // 10-bit ADC (0-1023)

// PT1000 Conditioning Circuit:
// - Assumes a transimpedance amplifier with 0-5V output range
// - Voltage divider calibration: map [0V, 5V] to [Rmin, Rmax]
// - For example: 0V → 500 Ohm, 5V → 1500 Ohm
// - Adjust calibration values below based on your circuit!

#define PT1000_V_MIN       0.5f           // Voltage at Rmin [V] (e.g., -30°C)
#define PT1000_V_MAX       4.5f           // Voltage at Rmax [V] (e.g., +30°C)
#define PT1000_R_MIN       500.0f         // Resistance at V_MIN [Ohm]
#define PT1000_R_MAX       1500.0f        // Resistance at V_MAX [Ohm]

// Sampling & Control
#define SAMPLE_RATE_HZ     10             // 10 Hz temperature sampling
#define SAMPLE_INTERVAL_MS (1000 / SAMPLE_RATE_HZ)
#define REPORT_INTERVAL_MS 1000           // Send status to Pi every 1 second

// Serial
#define SERIAL_BAUD        115200

// ===== CONTROL PARAMETERS =====

// On/Off Mode (CONTROL_MODE = 0)
#define ONOFF_HYSTERESIS   0.5f           // Hysteresis band [°C]
#define ONOFF_PWM_COLD     255            // PWM for cooling (0-255)
#define ONOFF_PWM_OFF      0              // PWM neutral/off

// PID Mode (CONTROL_MODE = 1)
#define PID_KP             50.0f          // Proportional gain
#define PID_KI             5.0f           // Integral gain
#define PID_KD             10.0f          // Derivative gain
#define PID_INTEGRAL_MAX   50.0f          // Anti-windup limit

// ===== GLOBAL STATE =====
static float g_setpoint_temp = 25.0f;     // Target temperature [°C]
static float g_current_temp = 25.0f;      // Last measured temperature
static uint8_t g_pwm_value = 0;         // Current PWM output (0-255)
static uint32_t g_last_sample_ms = 0;     // Last sampling timestamp
static uint32_t g_last_report_ms = 0;     // Last report to Pi
static float g_pid_integral = 0.0f;       // PID integral accumulator
static float g_pid_last_error = 0.0f;     // PID last error for derivative

// ===== FUNCTION PROTOTYPES =====
static float read_temperature(void);
static void handle_serial_command(void);
static uint8_t control_onoff(float temp, float setpoint);
static uint8_t control_pid(float temp, float setpoint, float dt);
static void send_status_to_pi(float temp, uint8_t pwm);

// ===== SETUP =====
void setup() {
    // Initialize PWM output pin
    pinMode(PELTIER_PWM_PIN, OUTPUT);
    analogWrite(PELTIER_PWM_PIN, 0);    // Initialize to off
    
    // Initialize serial
    Serial.begin(SERIAL_BAUD);
    while (!Serial) {
        delay(100);
    }
    
    Serial.println("# SUPERCAPFREEZER Peltier Controller Started");
    #if CONTROL_MODE == 0
    Serial.println("# Mode: On/Off with Hysteresis");
    #else
    Serial.println("# Mode: PID Feedback Control");
    #endif
    Serial.println("# Send: SET:25.5 (to set target temp)");
    delay(500);
    
    g_last_sample_ms = millis();
    g_last_report_ms = millis();
}

// ===== MAIN LOOP =====
void loop() {
    uint32_t now_ms = millis();
    
    // Check for incoming commands from Pi
    if (Serial.available()) {
        handle_serial_command();
    }
    
    // Sample temperature at fixed interval
    if (now_ms - g_last_sample_ms >= SAMPLE_INTERVAL_MS) {
        g_last_sample_ms = now_ms;
        
        // Read temperature
        g_current_temp = read_temperature();
        
        // Calculate control output
        #if CONTROL_MODE == 0
        // On/Off Mode
        g_pwm_value = control_onoff(g_current_temp, g_setpoint_temp);
        #else
        // PID Mode
        float dt = (float)SAMPLE_INTERVAL_MS / 1000.0f;
        g_pwm_value = control_pid(g_current_temp, g_setpoint_temp, dt);
        #endif
        
        // Apply PWM
        analogWrite(PELTIER_PWM_PIN, g_pwm_value);
    }
    
    // Send status to Pi periodically
    if (now_ms - g_last_report_ms >= REPORT_INTERVAL_MS) {
        g_last_report_ms = now_ms;
        send_status_to_pi(g_current_temp, g_pwm_value);
    }
    
    delay(5);  // Small delay to prevent busy-loop
}

// ===== TEMPERATURE READING =====
/**
 * Reads PT1000 temperature from ADC pin
 * 
 * Process:
 * 1. Read ADC value (0-1023)
 * 2. Convert to voltage (0-5V)
 * 3. Map voltage to PT1000 resistance
 * 4. Use Callendar-Van Dusen equation to get temperature
 * 
 * Returns: Temperature in °C
 */
static float read_temperature(void) {
    // Step 1: Read ADC (average 4 samples for noise reduction)
    uint16_t adc_sum = 0;
    for (int i = 0; i < 4; i++) {
        adc_sum += analogRead(PT1000_ADC_PIN);
        delayMicroseconds(100);
    }
    uint16_t adc_val = adc_sum / 4;
    
    // Step 2: Convert ADC to voltage [0, 5V]
    float voltage = (float)adc_val / ADC_RESOLUTION * ADC_REF_VOLTAGE;
    
    // Step 3: Map voltage to PT1000 resistance
    // Linear interpolation based on calibration points
    float resistance = PT1000_R_MIN + 
                       (voltage - PT1000_V_MIN) / (PT1000_V_MAX - PT1000_V_MIN) * 
                       (PT1000_R_MAX - PT1000_R_MIN);
    
    // Clamp to valid range
    if (resistance < 500.0f)   resistance = 500.0f;
    if (resistance > 1500.0f)  resistance = 1500.0f;
    
    // Step 4: Callendar-Van Dusen inverse: R → T
    // Simplified: for small temperature ranges, linear approximation works
    // R(T) ≈ R0 * (1 + A*T)  →  T ≈ (R - R0) / (R0 * A)
    
    float temp_celsius = (resistance - PT1000_R0) / (PT1000_R0 * PT1000_A);
    
    // Better: Use iterative Newton-Raphson for higher accuracy (optional)
    // For now, the linear approximation is sufficient for -30..+30°C
    
    return temp_celsius;
}

// ===== CONTROL FUNCTIONS =====

/**
 * Simple On/Off control with hysteresis
 * Returns PWM value (0-255)
 */
static uint8_t control_onoff(float temp, float setpoint) {
    float error = setpoint - temp;
    
    // Cooling: turn on if above setpoint + hysteresis
    if (error > -ONOFF_HYSTERESIS) {
        return ONOFF_PWM_COLD;  // Full power cooling
    }
    // Dead zone: maintain current
    else {
        return ONOFF_PWM_OFF;  // Neutral
    }
}

/**
 * PID feedback control
 * Returns PWM value (0-255)
 */
static uint8_t control_pid(float temp, float setpoint, float dt) {
    float error = setpoint - temp;
    
    // Proportional term
    float p_term = PID_KP * error;
    
    // Integral term with anti-windup
    g_pid_integral += error * dt;
    if (g_pid_integral > PID_INTEGRAL_MAX) g_pid_integral = PID_INTEGRAL_MAX;
    if (g_pid_integral < -PID_INTEGRAL_MAX) g_pid_integral = -PID_INTEGRAL_MAX;
    float i_term = PID_KI * g_pid_integral;
    
    // Derivative term
    float d_term = PID_KD * (error - g_pid_last_error) / dt;
    g_pid_last_error = error;
    
    // Combined output
    float output = p_term + i_term + d_term;
    
    // Clamp to PWM range (0-255)
    if (output > 255.0f) output = 255.0f;
    if (output < 0.0f) output = 0.0f;
    
    return (uint8_t)output;
}

/**
 * Handle serial commands from Raspberry Pi
 * Expected format: "SET:25.5" (set target to 25.5°C)
 */
static void handle_serial_command(void) {
    static char cmd_buffer[20];
    static uint8_t cmd_idx = 0;
    
    while (Serial.available()) {
        char c = Serial.read();
        
        // Newline: process command
        if (c == '\n' || c == '\r') {
            if (cmd_idx > 0) {
                cmd_buffer[cmd_idx] = '\0';
                
                // Parse "SET:XX.X" format
                if (cmd_buffer[0] == 'S' && cmd_buffer[1] == 'E' && cmd_buffer[2] == 'T' && cmd_buffer[3] == ':') {
                    float new_setpoint = atof(&cmd_buffer[4]);
                    g_setpoint_temp = new_setpoint;
                    g_pid_integral = 0.0f;  // Reset PID state on new setpoint
                    Serial.print("# Setpoint changed to: ");
                    Serial.println(g_setpoint_temp);
                }
            }
            cmd_idx = 0;
        }
        // Build command buffer
        else if (cmd_idx < sizeof(cmd_buffer) - 1) {
            cmd_buffer[cmd_idx++] = c;
        }
    }
}

/**
 * Send status to Raspberry Pi
 * Format: "TEMP:23.45 PWM:128"
 */
static void send_status_to_pi(float temp, uint8_t pwm) {
    Serial.print("TEMP:");
    Serial.print(temp, 2);
    Serial.print(" PWM:");
    Serial.println(pwm);
}
