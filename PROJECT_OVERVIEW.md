# Project Overview

## Goal

SUPERCAPFREEZER runs on Raspberry Pi and handles:

- Serial ingestion of STM32 telemetry.
- Test-command dispatch (CMD: CHARGE).
- Automatic trigger when a temperature threshold is reached.
- CSV logging for telemetry, ACK messages, and events.

## Runtime Topology

- Raspberry Pi process (main.py)
  - Owns serial connection and trigger decisions.
  - Sends command lines to STM32.
  - Logs incoming telemetry and ACK lines.

- STM32 firmware (external)
  - Streams telemetry like:
    - T:43440, V:0, I:6 mA, STATE:1, Temp: -1.2 C
  - Responds with ACK lines after commands.

## Main Modules

- main.py
  - Loads config.
  - Starts serial connection.
  - Applies auto-trigger logic.

- serial_handler.py
  - Parses telemetry and ACK messages.
  - Sends CMD lines.
  - Supports simulation mode.

- data_logger.py
  - Buffers records in memory.
  - Periodically flushes to CSV.

- config_loader.py
  - Provides defaults and merges config.yaml.

## Notes

- Legacy binary protocol artifacts were removed.
- Arduino-specific configuration should live in firmware code only.
