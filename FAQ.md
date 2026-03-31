# FAQ

## What serial format is supported?

Telemetry format:

T:43440, V:0, I:6 mA, STATE:1, Temp: -1.2 C

ACK format:

ACK: ...

## How do I start a test from Pi?

Send:

CMD: CHARGE

Use runtime option:

```bash
python main.py --start-test --port /dev/ttyACM0
```

## How do I auto-trigger a test at a temperature?

```bash
python main.py --port /dev/ttyACM0 --trigger-temp -1.0 --trigger-direction below --command CHARGE
```

## Where are logs stored?

Default is logs/. Change via logging.directory in config.yaml.

## How do I run without hardware?

```bash
python main.py --simulate
```

## Why were protocol.h and PROTOCOL.md removed?

This project now uses direct text line parsing for runtime communication, so the old protocol artifacts are not part of the active code path.
