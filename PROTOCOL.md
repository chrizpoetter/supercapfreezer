# SUPERCAPFREEZER - Binary Communication Protocol
## Specification & Implementation Guide

---

## 1. Overview

**SUPERCAPFREEZER** uses a **binary protocol** for communication between:
- **Sender:** Arduino UNO R4 WiFi (with PT1000 temperature sensor)
- **Receiver:** Raspberry Pi 3 (via USB Serial)
- **Baudrate:** 115200 bps
- **Sampling Rate:** 10 Hz (temperature), extensible to 1 kHz (voltage)

### Why Binary Protocol?

| Aspect | ASCII | Binary |
|--------|-------|--------|
| Overhead | ~7 bytes per value | ~2 bytes per value |
| Throughput @ 115200 | ~1650 val/s | ~5760 val/s |
| Parsing | Complex (string handling) | Fast (memcpy) |
| Reliability | Low (no checksums) | High (CRC16) |
| Extensibility | Limited | Excellent |

---

## 2. Packet Format

### General Structure (Little Endian)

```
┌─────────────────────────────────────────────────────────┐
│ PACKET LAYOUT                                           │
├─────────────────────────────────────────────────────────┤
│ Offset  │ Size  │ Field         │ Type      │ Purpose   │
├─────────┼───────┼───────────────┼───────────┼───────────┤
│ 0-1     │ 2     │ SYNC          │ uint8[2]  │ Frame start
│ 2       │ 1     │ TYPE          │ uint8     │ Data type
│ 3       │ 1     │ SAMPLES       │ uint8     │ Count N
│ 4-7     │ 4     │ TIMESTAMP_MS  │ uint32_le │ Time (ms)
│ 8-9     │ 2     │ SEQ_NUM       │ uint16_le │ Sequence
│ 10..    │ N×2   │ PAYLOAD       │ int16_le[]│ Data
│ -2,-1   │ 2     │ CRC16         │ uint16_le │ Checksum
└─────────┴───────┴───────────────┴───────────┴───────────┘

MINIMUM SIZE: 14 bytes (1 sample)
MAXIMUM SIZE: 14 + 255×2 = 524 bytes (255 samples)
```

### Synchronization

- **SYNC[0] = 0xAA** (first byte)
- **SYNC[1] = 0x55** (second byte)
- Parser searches for this pattern byte-by-byte
- Allows recovery from transmission errors

### Type Field

| Value | Name | Description |
|-------|------|-------------|
| 0x01 | TEMP | Temperature samples (PT1000) |
| 0x02 | VOLT | Voltage samples (future: ADC, battery, etc.) |

### Payload Encoding

#### Temperature (Type 0x01)
- **Encoding:** int16 = actual_temp × 100
- **Range:** -30,000 to +30,000 → -30.00°C to +30.00°C
- **Resolution:** 0.01°C
- **Example:** 23.45°C → 2345 (0xD9 0x09 in little-endian)

#### Voltage (Type 0x02, Future)
- **Encoding:** int16 = voltage × 100
- **Range:** 0 to 655.35V (limited to 0-5V practical)
- **Resolution:** 0.01V

### CRC16-CCITT Checksum

**Algorithm:** CRC-16-CCITT
- **Polynomial:** 0x1021
- **Initial Value:** 0xFFFF
- **Input Reflection:** No
- **Output Reflection:** No
- **Final XOR:** 0x0000
- **Calculated over:** SYNC + TYPE + SAMPLES + TIMESTAMP_MS + SEQ_NUM + PAYLOAD
- **Appended as:** 2 bytes (little-endian)

**C/C++ Implementation:**
```c
uint16_t crc16_ccitt(const uint8_t* data, uint16_t length) {
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
```

---

## 3. Example Packets

### Example 1: Single Temperature Value

**Temperature:** 23.45°C

**Packet breakdown:**
```
AA 55          SYNC bytes
01             TYPE = 0x01 (Temperature)
01             SAMPLES = 1
12 34 56 78    TIMESTAMP_MS = 0x78563412 (2018915346 ms in big-endian)
AB CD          SEQ_NUM = 0xCDAB (52651)
D9 09          PAYLOAD: int16_le(2345) = 23.45°C
XX YY          CRC16-CCITT (2 bytes)

Total: 14 bytes
```

### Example 2: Multiple Temperature Samples

**Samples:** 3 values (batch mode)

```
AA 55          SYNC
01             TYPE = Temperature
03             SAMPLES = 3
12 34 56 78    TIMESTAMP_MS
AB CD          SEQ_NUM
D9 09          Sample 1: 23.45°C (2345)
DA 09          Sample 2: 23.46°C (2346)
D8 09          Sample 3: 23.44°C (2344)
XX YY          CRC16-CCITT

Total: 18 bytes
```

---

## 4. Arduino Implementation

See: `arduino/supercapfreezer_firmware.ino`

### Key Steps:
1. Read PT1000 via ADC (A0)
2. Apply Callendar-Van Dusen equation
3. Pack temperature as int16 × 100
4. Build packet with header + payload
5. Calculate CRC16-CCITT
6. Send 14 bytes via Serial.write()

### Timing:
- **Sampling rate:** 10 Hz (every 100 ms)
- **Packet generation:** 10 packets/second
- **Throughput:** 140 bytes/second (well under 115200 bps limit)

---

## 5. Raspberry Pi Parser Implementation

See: `serial_handler.py` (PacketParser class)

### State Machine:

```
┌──────────────┐
│ STATE_SYNC_0 │ ← Waiting for 0xAA
└──────┬───────┘
       │ [byte == 0xAA]
       ▼
┌──────────────┐
│ STATE_SYNC_1 │ ← Waiting for 0x55
└──────┬───────┘
       │ [byte == 0x55]
       ▼
┌──────────────┐
│ STATE_HEADER │ ← Reading 8 more bytes
└──────┬───────┘
       │ [got 10 bytes total]
       ▼
┌──────────────┐
│ STATE_PAYLOAD│ ← Reading N×2 payload bytes
└──────┬───────┘
       │ [got all payload]
       ▼
┌──────────────┐
│ STATE_CRC    │ ← Reading 2 CRC bytes
└──────┬───────┘
       │ [got 2 bytes]
       ▼
   [VALIDATE & PARSE]
       │
       ├─→ CRC Error? → Reset to STATE_SYNC_0
       │
       └─→ Valid → [Emit Packet] → Reset to STATE_SYNC_0
```

### Error Recovery:
- **CRC Mismatch:** Entire packet discarded, parser resets
- **Frame Error:** Invalid sample count → skip to next sync
- **Timeout:** No action (asynchronous protocol)

---

## 6. Performance Analysis

### Theoretical Maximum Throughput

**At 115200 baud (10 bits per byte):**
- Net rate: 115200 / 10 = 11,520 bytes/second
- Temperature packet: 14 bytes
- Maximum: 11,520 / 14 ≈ **820 packets/second**
- At 10 Hz sampling: Only using **1.2% of bandwidth** ✓

### Future: Voltage at 1 kHz

**Batched voltage packets (100 samples per packet):**
- Packet size: 10 + (100 × 2) + 2 = 212 bytes
- Packets needed: 10 / sec (1000 Hz / 100)
- Throughput: 10 × 212 = 2,120 bytes/second
- Still under 11,520 bytes/sec **9.8% bandwidth** ✓

---

## 7. Extensibility

### Adding New Data Types

1. Define new TYPE constant (e.g., 0x03)
2. Document payload encoding
3. Add case to Arduino packet builder
4. Add case to RPi parser
5. Update UI to display new type

**Example: Humidity (future)**
```c
#define PROTO_TYPE_HUMIDITY  0x03
// Encoding: int16 = humidity_percent × 100
// Range: 0-10000 (0-100%)
// Resolution: 0.01%
```

### Batching Strategy

For high-frequency data (≥100 Hz):
- Batch multiple samples per packet
- Reduces framing overhead
- Trade-off: Latency vs. efficiency

**Example batching configurations:**
```
10 Hz:   1 sample/packet  (14 bytes/packet) → Low latency
100 Hz:  10 samples/packet (34 bytes/packet) → Balanced
1 kHz:   100 samples/packet (212 bytes/packet) → High efficiency
```

---

## 8. Testing & Validation

### Arduino Test Mode

Upload firmware with `#define DEBUG_MODE 1` to print packets to Serial Monitor:
```
AA 55 01 01 [TS] [SEQ] D9 09 [CRC]
AA 55 01 01 [TS] [SEQ] DA 09 [CRC]
...
```

### Raspberry Pi Test

Run parser in test mode:
```bash
python -m serial_handler /dev/ttyACM0 115200 --verbose
```

Expected output:
```
[PARSER] Packet 1: type=0x01 samples=1 seq=0 temp=23.45°C ✓
[PARSER] Packet 2: type=0x01 samples=1 seq=1 temp=23.46°C ✓
...
```

### Data Validation Checklist

- [ ] Sync bytes always 0xAA 0x55
- [ ] Type field valid (0x01 or 0x02)
- [ ] Sample count matches payload size
- [ ] CRC16 checksum passes
- [ ] Temperature in valid range (-30 to +30°C)
- [ ] Sequence numbers monotonic (gaps indicate lost packets)
- [ ] No missing bytes (frame size = 14 + N×2)

---

## 9. Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| No packets received | Serial not opened | Check `/dev/ttyACM0` exists |
| CRC errors | Noise, baud rate mismatch | Use 115200, add shielding |
| Garbled data | Buffer overflow | Reduce sample rate or batch |
| Packet sync loss | Start-of-line noise | Wait 1s after serial open |

---

## 10. References

- CRC-16-CCITT calculator: https://crccalc.com/
- Callendar-Van Dusen equation: IEC 60751
- PT1000 datasheet: https://www.analog.com/
- Arduino Serial library: https://www.arduino.cc/

---

**Document Version:** 1.0  
**Date:** 2025-12-18  
**Author:** SUPERCAPFREEZER Project
