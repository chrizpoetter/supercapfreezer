# SUPERCAPFREEZER

Headless Raspberry Pi runtime for STM32 telemetry logging and test triggering.

## Runtime Message Format

Incoming STM32 telemetry (example):

T:43440, V:0, I:6 mA, STATE:1, Temp: -1.2 C

Incoming ACK after command (example):

ACK: CMD: CHARGE

Outgoing Pi command:

CMD: CHARGE

## Features

- Reads and parses STM32 telemetry line-by-line.
- Handles ACK messages for sent commands.
- Writes telemetry, ACK, and events to CSV logs.
- Can auto-trigger a test command when a configured temperature threshold is reached.
- Supports simulation mode for local testing.

## Run

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py --port /dev/ttyACM0
```

Simulation:

```bash
python main.py --simulate
```

## Auto Trigger

Trigger when temperature drops below -1.0 C:

```bash
python main.py --port /dev/ttyACM0 --trigger-temp -1.0 --trigger-direction below --command CHARGE
```

Start test directly on startup:

```bash
python main.py --port /dev/ttyACM0 --start-test
```

## Configuration

Main config file: config.yaml

Relevant sections:

- serial.port
- serial.baud
- trigger.temperature_celsius
- trigger.direction
- trigger.command
- trigger.once
- logging.directory
- logging.retention_hours
- logging.flush_interval_s

## Repository Layout

- main.py: runtime orchestration and trigger logic.
- serial_handler.py: serial thread, parser, and command sending.
- data_logger.py: CSV logger for telemetry/ACK/events.
- config_loader.py: YAML loading with defaults.
- config.yaml: runtime settings.
- arduino/supercapfreezer_firmware/supercapfreezer_firmware.ino: firmware-side configuration and behavior.
- supercapfreezer.service: systemd service template.
- install.sh: Raspberry Pi setup helper.
