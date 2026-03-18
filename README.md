# SUPERCAPFREEZER

Headless Raspberry Pi control and logging stack for a dual-controller supercapacitor freezer setup.

## What This Project Does

- Runs on Raspberry Pi without a GUI.
- Talks to two serial devices:
  - Peltier controller (Arduino UNO R4 WiFi).
  - Measurement controller (voltage/current state machine MCU).
- Logs merged telemetry to CSV files.
- Supports simulation mode for software-only testing.

## Current Control Architecture

The control loop is split between Pi and Arduino:

1. Pi computes or reads measured temperature.
2. Pi sends measured temperature to Arduino using TEMP:<value>.
3. Pi sends target setpoint to Arduino using SET:<value>.
4. Arduino computes PWM and returns status line TEMP:<value> PWM:<value>.

Important: Arduino firmware no longer reads PT1000 directly in this branch.

## Repository Layout

- main.py: headless runtime entrypoint.
- serial_handler.py: threaded serial handlers for peltier and measurement controllers.
- data_logger.py: in-memory buffers plus periodic CSV write.
- config_loader.py: YAML config merge with defaults.
- config.yaml: project configuration.
- arduino/supercapfreezer_firmware.ino: Arduino controller firmware.
- supercapfreezer.service: systemd service template.
- install.sh: Raspberry Pi install helper.

## Requirements

- Linux (Raspberry Pi OS recommended).
- Python 3.9+.
- Two serial links if running full hardware mode.
- Dependencies from requirements.txt.

## Installation

### Option A: Manual

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Option B: Scripted on Raspberry Pi

```bash
chmod +x install.sh
./install.sh
```

## Running

### Simulation Mode

```bash
source venv/bin/activate
python main.py --simulate
```

### Hardware Mode

```bash
source venv/bin/activate
python main.py --port1 /dev/ttyACM0 --port2 /dev/ttyACM1
```

If ports are omitted, auto-detection is attempted.

## Configuration

Default config file is config.yaml.

Main keys used by runtime:

- serial.port
- serial.baud
- measurement.port
- logging.directory
- logging.retention_hours
- control.default_setpoint

Run with custom config path:

```bash
python main.py --config /path/to/config.yaml
```

## Logging

CSV files are written to ./logs (configurable).

Columns:

- timestamp_utc
- time_elapsed_s
- temperature_celsius
- pwm
- setpoint_celsius
- v1_volts
- v2_volts
- i1_amps
- i2_amps
- meas_state

## Service Deployment

Install service file:

```bash
sudo cp supercapfreezer.service /etc/systemd/system/supercapfreezer.service
sudo systemctl daemon-reload
sudo systemctl enable --now supercapfreezer.service
```

View service logs:

```bash
sudo journalctl -u supercapfreezer -f
```

## Documentation Map

- QUICKSTART.md: fastest path to run.
- PROTOCOL.md: serial ASCII protocol details.
- PROJECT_OVERVIEW.md: architecture and module responsibilities.
- FAQ.md: troubleshooting.
- IMPLEMENTATION_COMPLETE.md: implementation status notes.
- README_NEW.md: deployment-oriented runbook.
