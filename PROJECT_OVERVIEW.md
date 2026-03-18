# Project Overview

## Goal

SUPERCAPFREEZER provides headless runtime control and data logging for a supercapacitor freezer platform using a Raspberry Pi plus microcontrollers.

## Runtime Topology

- Raspberry Pi process (main.py)
  - Owns orchestration and data logging.
  - Sends setpoint and measured temperature to peltier Arduino.
  - Receives peltier status and measurement MCU telemetry.

- Peltier Controller (arduino/supercapfreezer_firmware.ino)
  - Receives SET and TEMP over serial.
  - Executes control loop.
  - Outputs TEMP ... PWM ... status.

- Measurement Controller (external firmware)
  - Streams voltage/current/state data.

## Main Modules

- main.py
  - Parses CLI args.
  - Loads config.
  - Starts serial devices.
  - Starts periodic CSV flush.
  - Runs headless until interrupted.

- serial_handler.py
  - PeltierController and MeasurementController abstractions.
  - Serial auto-detection fallback.
  - Optional simulation mode.

- data_logger.py
  - Keeps in-memory rolling buffers.
  - Writes merged rows to CSV.
  - Exposes basic stats and retrieval helpers.

- config_loader.py
  - Provides defaults.
  - Deep-merges YAML overrides.

## Data Path Summary

1. Serial packets arrive from controllers.
2. Callback handlers convert packets into logger entries.
3. Background flush writes latest merged snapshot row to CSV every second.
4. Service mode keeps process persistent with systemd restart policy.

## Operational Mode

This branch is intentionally no-GUI:

- No pygame dependency.
- No UI loop or display assumptions.
- Suitable for SSH-only or service-first deployments.
