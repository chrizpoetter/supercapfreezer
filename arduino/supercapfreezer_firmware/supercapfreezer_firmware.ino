/**
 * SUPERCAPFREEZER Arduino Peltier Controller
 * ==========================================
 * 
 * Raspberry Pi Temperature Input + Peltier Feedback Control
 * 
 * FEATURES:
 * - Receives measured temperature from Raspberry Pi over Serial
 * - Peltier PWM control (heater/cooler on/off or PID feedback)
 * - Simple ASCII serial communication with Raspberry Pi
 * 
 * HARDWARE:
 * - Arduino UNO R4 WiFi
 * - Peltier controller PWM input on D3
 * - USB serial to Raspberry Pi
 * 
 * COMMUNICATION:
 * - Pi → Controller: "CMD: CHARGE" (start test)
 * - Controller → Pi: "ACK: CMD: CHARGE" (command acknowledge)
 * - Controller → Pi: "T:43440, V:0, I:6 mA, STATE:1, Temp: -1.2 C"
 */

#include <stdint.h>
#include <stdlib.h>

// ===== CONTROL MODE SELECTION =====
// Set to 0 for simple On/Off with hysteresis
// Set to 1 for full PID controller
#define CONTROL_MODE 0  // Change this to switch between modes

// ===== PIN CONFIGURATION =====
#define PELTIER_PWM_PIN_ONE    5              // D5: Peltier controller PWM output
#define PELTIER_PWM_PIN_TWO    6              // D6: Peltier controller PWM output


// Sampling & Control
#define SAMPLE_RATE_HZ     10             // 10 Hz control update
#define SAMPLE_INTERVAL_MS (1000 / SAMPLE_RATE_HZ)
#define REPORT_INTERVAL_MS 1000           // Send status to Pi every 1 second
#define TEMP_TIMEOUT_MS    2000           // Disable output if Pi temp updates stop
#define TIMEOUT_ENABLED    false          // Enables timeout 

// Serial
#define SERIAL_BAUD        9600

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
static float g_current_temp = 25.0f;      // Last temperature received from Pi
static uint8_t g_pwm_value = 0;         // Current PWM output (0-255)
static uint8_t g_test_state = 0;           // 0=IDLE, 1=CHARGE
static uint32_t g_last_sample_ms = 0;     // Last sampling timestamp
static uint32_t g_last_report_ms = 0;     // Last report to Pi
static uint32_t g_last_temp_rx_ms = 0;    // Last time TEMP was received from Pi
static float g_pid_integral = 0.0f;       // PID integral accumulator
static float g_pid_last_error = 0.0f;     // PID last error for derivative

// ===== FUNCTION PROTOTYPES =====
static void handle_serial_command(void);
static uint8_t control_onoff(float temp, float setpoint);
static uint8_t control_pid(float temp, float setpoint, float dt);
static void send_status_to_pi(float temp, uint8_t pwm);

// ===== SETUP =====
void setup() {
    // Initialize PWM output pins
    pinMode(PELTIER_PWM_PIN_ONE, OUTPUT);
    pinMode(PELTIER_PWM_PIN_TWO, OUTPUT);

    analogWrite(PELTIER_PWM_PIN_ONE, 0);    // Initialize to off
    analogWrite(PELTIER_PWM_PIN_TWO, 0);    // Initialize to off

    
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
    Serial.println("# Send: CMD: CHARGE or CMD: IDLE");
    delay(500);
    
    g_last_sample_ms = millis();
    g_last_report_ms = millis();
    g_last_temp_rx_ms = millis();
}

// ===== MAIN LOOP =====
void loop() {
    uint32_t now_ms = millis();
    
    // Check for incoming commands from Pi
    if (Serial.available()) {
        handle_serial_command();
    }
    
    // Control update at fixed interval
    if (now_ms - g_last_sample_ms >= SAMPLE_INTERVAL_MS) {
        g_last_sample_ms = now_ms;
        if (now_ms - g_last_temp_rx_ms > TEMP_TIMEOUT_MS && TIMEOUT_ENABLED) {
            g_pwm_value = ONOFF_PWM_OFF;
        } else {
            // Calculate control output using temperature received from Pi
            #if CONTROL_MODE == 0
            // On/Off Mode
            g_pwm_value = control_onoff(g_current_temp, g_setpoint_temp);
            #else
            // PID Mode
            float dt = (float)SAMPLE_INTERVAL_MS / 1000.0f;
            g_pwm_value = control_pid(g_current_temp, g_setpoint_temp, dt);
            #endif
        }
        
        // Apply PWM to both Peltier Elements
        analogWrite(PELTIER_PWM_PIN_ONE, g_pwm_value);
        analogWrite(PELTIER_PWM_PIN_TWO, g_pwm_value);
    }
    
    // Send status to Pi periodically
    if (now_ms - g_last_report_ms >= REPORT_INTERVAL_MS) {
        g_last_report_ms = now_ms;
        send_status_to_pi(g_current_temp, g_pwm_value);
    }
    
    delay(5);  // Small delay to prevent busy-loop
}

// ===== CONTROL FUNCTIONS =====

/**
 * Simple On/Off control with hysteresis
 * Returns PWM value (0-255)
 */
static uint8_t control_onoff(float temp, float setpoint) {
    // Merkt sich den letzten Schaltzustand für echte Hysterese
    static bool cooling_on = false;

    // Untere Schwelle: sicher aus
    if (temp < setpoint - ONOFF_HYSTERESIS) {
        cooling_on = false;
    }
    // Obere Schwelle: sicher an
    else if (temp > setpoint + ONOFF_HYSTERESIS) {
        cooling_on = true;
    }
    // Dazwischen: Zustand beibehalten

    return cooling_on ? ONOFF_PWM_COLD : ONOFF_PWM_OFF;
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
 * Expected formats:
 * - "CMD: CHARGE" (start test)
 * - "CMD: IDLE"   (stop test)
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
                
                // Parse "CMD: CHARGE" / "CMD: IDLE"
                if (
                    cmd_buffer[0] == 'C' && cmd_buffer[1] == 'M' && cmd_buffer[2] == 'D' &&
                    cmd_buffer[3] == ':'
                ) {
                    char* cmd = &cmd_buffer[4];
                    while (*cmd == ' ') {
                        cmd++;
                    }

                    if (cmd[0] == 'C' && cmd[1] == 'H' && cmd[2] == 'A' && cmd[3] == 'R' && cmd[4] == 'G' && cmd[5] == 'E') {
                        g_test_state = 1;
                        Serial.println("ACK: CMD: CHARGE");
                    } else if (cmd[0] == 'I' && cmd[1] == 'D' && cmd[2] == 'L' && cmd[3] == 'E') {
                        g_test_state = 0;
                        Serial.println("ACK: CMD: IDLE");
                    } else {
                        Serial.print("ACK: CMD: UNKNOWN (");
                        Serial.print(cmd);
                        Serial.println(")");
                    }
                } else {
                    Serial.print("ACK: UNKNOWN INPUT (");
                    Serial.print(cmd_buffer);
                    Serial.println(")");
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
 * Format: "T:43440, V:0, I:6 mA, STATE:1, Temp: -1.2 C"
 */
static void send_status_to_pi(float temp, uint8_t pwm) {
    float current_ma = ((float)pwm / 255.0f) * 20.0f;
    Serial.print("T:");
    Serial.print(millis());
    Serial.print(", V:0, I:");
    Serial.print(current_ma, 1);
    Serial.print(" mA, STATE:");
    Serial.print(g_test_state);
    Serial.print(", Temp: ");
    Serial.print(temp, 2);
    Serial.println(" C");
}
