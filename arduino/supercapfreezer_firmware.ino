/**
 * SUPERCAPFREEZER Arduino UNO R4 WiFi Firmware
 * =============================================
 * 
 * Reads PT1000 temperature sensor (via ADC + Callendar-Van Dusen conversion)
 * Sends temperature data via USB Serial in binary protocol format
 * 10 Hz sampling rate
 * 
 * HARDWARE REQUIREMENTS:
 * - Arduino UNO R4 WiFi
 * - PT1000 RTD sensor with signal conditioning
 * - Connected to ADC pin A0 (0-5V reading from PT1000 circuit)
 * 
 * CONNECTIONS:
 * - PT1000 Circuit Output → Arduino A0 (analog input)
 * - USB → Raspberry Pi
 * 
 * NOTES:
 * - PT1000 requires conditioning circuit (e.g., current source + amplifier)
 *   to convert resistance to 0-5V signal
 * - Calibration values (R0, A, B, C) set below for PT1000
 * - Temperature range: -30°C to +30°C
 */

#include <stdint.h>

// ===== PROTOCOL HEADER =====
// (Same as protocol.h - embedded for Arduino compilation)

#define PROTO_SYNC_0         0xAA
#define PROTO_SYNC_1         0x55
#define PROTO_TYPE_TEMP      0x01
#define PROTO_HEADER_SIZE    10
#define PROTO_CRC_SIZE       2
#define PROTO_SAMPLE_SIZE    2

typedef struct {
    uint8_t sync[2];
    uint8_t type;
    uint8_t samples;
    uint32_t timestamp_ms;
    uint16_t seq_num;
} PacketHeader;

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

// Sampling
#define SAMPLE_RATE_HZ     10             // 10 Hz
#define SAMPLE_INTERVAL_MS (1000 / SAMPLE_RATE_HZ)

// Serial
#define SERIAL_BAUD        115200

// ===== GLOBAL STATE =====
static uint32_t g_seq_num = 0;           // Packet sequence counter
static uint32_t g_last_sample_ms = 0;    // Last sampling timestamp

// ===== FUNCTION PROTOTYPES =====
static float read_temperature(void);
static uint16_t crc16_ccitt(const uint8_t* data, uint16_t length);
static void send_temperature_packet(float temp);
static void write_uint32_le(uint8_t* buf, uint32_t value);
static void write_uint16_le(uint8_t* buf, uint16_t value);
static int16_t temp_to_int16(float temp);

// ===== SETUP =====
void setup() {
    Serial.begin(SERIAL_BAUD);
    
    // Wait for serial connection (USB enumeration)
    while (!Serial) {
        delay(100);
    }
    
    Serial.println("# SUPERCAPFREEZER started");
    Serial.println("# PT1000 Temperature Sensor (10 Hz)");
    delay(500);
    
    g_last_sample_ms = millis();
}

// ===== MAIN LOOP =====
void loop() {
    uint32_t now_ms = millis();
    
    // Check if it's time to sample (10 Hz = every 100 ms)
    if (now_ms - g_last_sample_ms >= SAMPLE_INTERVAL_MS) {
        g_last_sample_ms = now_ms;
        
        // Read temperature
        float temp = read_temperature();
        
        // Send packet
        send_temperature_packet(temp);
    }
    
    delay(10);  // Small delay to prevent busy-loop
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

// ===== PACKET TRANSMISSION =====
/**
 * Sends one temperature value in binary protocol format
 */
static void send_temperature_packet(float temp) {
    // Allocate packet buffer (header + 1 sample + crc)
    // Total: 10 + 2 + 2 = 14 bytes
    uint8_t packet[14];
    uint8_t idx = 0;
    
    // Header: SYNC
    packet[idx++] = PROTO_SYNC_0;     // 0xAA
    packet[idx++] = PROTO_SYNC_1;     // 0x55
    
    // Type: Temperature
    packet[idx++] = PROTO_TYPE_TEMP;  // 0x01
    
    // Samples: 1
    packet[idx++] = 1;
    
    // Timestamp (4 bytes, little-endian)
    uint32_t ts = millis();
    write_uint32_le(&packet[idx], ts);
    idx += 4;
    
    // Sequence number (2 bytes, little-endian)
    write_uint16_le(&packet[idx], g_seq_num);
    idx += 2;
    g_seq_num++;
    
    // Payload: Temperature as int16 (2 bytes)
    int16_t temp_int16 = temp_to_int16(temp);
    write_uint16_le(&packet[idx], (uint16_t)temp_int16);
    idx += 2;
    
    // CRC16 over header + payload (excluding CRC itself)
    uint16_t crc = crc16_ccitt(packet, 12);
    write_uint16_le(&packet[idx], crc);
    idx += 2;
    
    // Send packet
    Serial.write(packet, 14);
}

// ===== HELPER FUNCTIONS =====

/**
 * CRC16-CCITT calculation
 * Polynomial: 0x1021, Init: 0xFFFF
 */
static uint16_t crc16_ccitt(const uint8_t* data, uint16_t length) {
    uint16_t crc = 0xFFFF;
    for (uint16_t i = 0; i < length; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (uint8_t j = 0; j < 8; j++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc = crc << 1;
            }
            crc &= 0xFFFF;
        }
    }
    return crc;
}

/**
 * Write uint32 in little-endian format
 */
static void write_uint32_le(uint8_t* buf, uint32_t value) {
    buf[0] = (uint8_t)(value & 0xFF);
    buf[1] = (uint8_t)((value >> 8) & 0xFF);
    buf[2] = (uint8_t)((value >> 16) & 0xFF);
    buf[3] = (uint8_t)((value >> 24) & 0xFF);
}

/**
 * Write uint16 in little-endian format
 */
static void write_uint16_le(uint8_t* buf, uint16_t value) {
    buf[0] = (uint8_t)(value & 0xFF);
    buf[1] = (uint8_t)((value >> 8) & 0xFF);
}

/**
 * Convert float temperature to int16 (temp × 100)
 */
static int16_t temp_to_int16(float temp) {
    return (int16_t)(temp * 100.0f);
}
