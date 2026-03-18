# Implementation Status

Date: 2026-03-18
Branch intent: headless runtime, no GUI.

## Completed

- Removed GUI application module and pygame dependency.
- Converted main.py to headless service loop.
- Updated systemd service command to headless CLI arguments.
- Updated install script service template to headless CLI arguments.
- Updated Arduino firmware to receive measured temperature from Pi (TEMP: command) instead of reading local sensor input.
- Kept dual-controller architecture (peltier + measurement MCU).
- CSV logging pipeline operational in headless mode.

## Current Runtime Contract

- Pi sends setpoint and measured temperature to Arduino.
- Arduino sends back control status with PWM.
- Measurement MCU streams V/I/state telemetry.
- Python process logs merged data to CSV.

## Known Limitations

- Some config sections still contain legacy keys for removed GUI or sensor paths.
- protocol.h binary format is not the active runtime path in this branch.
- No integrated automated test suite is included yet.

## Recommended Next Steps

1. Clean legacy config keys that no longer affect runtime.
2. Add a dedicated Pi temperature source module and wire it into main.py.
3. Add smoke tests for serial parser and logger output schema.
4. Add deployment verification script that checks ports, service state, and log writes.
