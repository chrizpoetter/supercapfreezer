/**
 * SUPERCAPFREEZER Binary Protocol Specification
 * ===============================================
 * 
 * This protocol defines communication between Arduino UNO R4 WiFi and Raspberry Pi
 * over USB Serial (115200 baud).
 * 
 * PACKET STRUCTURE (Little Endian):
 * ┌─────────────────────────────────────────────────────────┐
 * │ Byte 0-1:   SYNC           = 0xAA 0x55                 │
 * │ Byte 2:     TYPE           = 0x01 (Temperature)        │
 * │ Byte 3:     SAMPLES        = N (1..255, number of vals)│
 * │ Byte 4-7:   TIMESTAMP_MS   = uint32 (system time ms)   │
 * │ Byte 8-9:   SEQ_NUM        = uint16 (packet sequence)  │
 * │ Byte 10..:  PAYLOAD        = N × int16 (little-endian)│
 * │ Byte -2,-1: CRC16_CCITT    = Checksum                 │
 * └─────────────────────────────────────────────────────────┘
 * 
 * TOTAL PACKET SIZE: 12 + (N × 2) + 2 = 14 + (N × 2) bytes
 * 
 * PAYLOAD ENCODING:
 * - Temperature: int16 = actual_temp × 100
 *   Example: 23.45°C → int16 = 2345
 *   Range: -3000 to +3000 (covers -30.00 to +30.00°C)
 * 
 * - Voltage (future): int16 = voltage × 100
 *   Example: 5.12V → int16 = 512
 * 
 * CRC16-CCITT:
 * - Polynomial: 0x1021
 * - Init: 0xFFFF
 * - Calculated over: SYNC + TYPE + SAMPLES + TIMESTAMP_MS + SEQ_NUM + PAYLOAD
 * - Appended as 2 bytes (little-endian)
 * 
 * EXAMPLE PACKET (1 Temperature sample: 23.45°C):
 * AA 55 | 01 | 01 | [4 bytes TS] | [2 bytes SEQ] | D9 09 | [2 bytes CRC]
 * = 14 bytes total
 * 
 * TIMING:
 * - Temperature: 10 Hz → ~140 bytes/sec
 * - Voltage (future, 1kHz batched): ~2-4 kBytes/sec
 * - Total throughput << 115200 bps ✓
 */

#ifndef SUPERCAPFREEZER_PROTOCOL_H
#define SUPERCAPFREEZER_PROTOCOL_H

#include <stdint.h>

// Protocol Constants
#define PROTO_SYNC_0         0xAA
#define PROTO_SYNC_1         0x55
#define PROTO_TYPE_TEMP      0x01
#define PROTO_TYPE_VOLT      0x02
#define PROTO_HEADER_SIZE    10  // SYNC(2) + TYPE(1) + SAMPLES(1) + TIMESTAMP(4) + SEQ(2)
#define PROTO_CRC_SIZE       2
#define PROTO_SAMPLE_SIZE    2   // int16

// Packet structure (C/C++)
typedef struct {
    uint8_t sync[2];           // 0xAA 0x55
    uint8_t type;              // 0x01=Temp, 0x02=Volt
    uint8_t samples;           // Number of samples N
    uint32_t timestamp_ms;     // Timestamp in milliseconds
    uint16_t seq_num;          // Packet sequence number
    // Followed by: samples × int16_t (payload)
    // Followed by: uint16_t crc16 (checksum)
} PacketHeader;

// Helper: CRC16-CCITT calculation
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

// Helper: Convert float temp to int16
static int16_t temp_to_int16(float temp) {
    return (int16_t)(temp * 100.0f);
}

// Helper: Convert int16 to float temp
static float int16_to_temp(int16_t raw) {
    return raw / 100.0f;
}

#endif // SUPERCAPFREEZER_PROTOCOL_H
