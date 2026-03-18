# Protocol Specification

This project currently uses a line-based ASCII protocol over USB serial.

## Transport

- Serial baud: 115200 by default.
- Newline-terminated text lines (\n or \r\n).
- Key/value segments separated by spaces.

## Peltier Controller Protocol (Arduino)

### Pi to Arduino Commands

- SET:<float>
  - Set control target in degC.
  - Example: SET:25.5

- TEMP:<float>
  - Provide the latest measured temperature from Pi-side sensing logic.
  - Example: TEMP:23.42

### Arduino to Pi Status

- TEMP:<float> PWM:<int>
  - Example: TEMP:23.45 PWM:128

### Notes

- Arduino computes PWM internally (OnOff or PID by firmware mode).
- Arduino disables PWM if no TEMP: update is received for timeout window.

## Measurement Controller Protocol

### MCU to Pi Measurement Line

Typical format:

MEAS:V1:<float> V2:<float> I1:<float> I2:<float> STATE:<name>

Example:

MEAS:V1:12.341 V2:5.012 I1:0.123 I2:0.045 STATE:CHARGE

### Pi to MCU Commands

- START
- STOP
- RESET
- STATE:<IDLE|CHARGE|DISCHARGE>

## Parser Rules

Implemented in serial_handler.py:

- Lines beginning with # are treated as comments.
- Each key:value segment is parsed into dictionary entries.
- Numeric values are parsed as float when possible.

## Legacy Binary Protocol

The file protocol.h describes an older or alternate binary framing approach.
Current Python runtime in this branch uses ASCII protocol only.
