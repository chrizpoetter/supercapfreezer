# FAQ

## Why does the service start but no control happens?

Common causes:

- Wrong serial port assignment.
- Arduino firmware not flashed.
- Pi is not sending TEMP: updates to Arduino.

Check:

```bash
python main.py --port1 /dev/ttyACM0 --port2 /dev/ttyACM1
```

and observe startup logs.

## How do I run without hardware?

Use simulation mode:

```bash
python main.py --simulate
```

## Why is PWM always zero?

The Arduino firmware has a temperature input timeout.
If no TEMP: update is received for the timeout period, PWM is forced to off.

## Where are logs stored?

Default location is ./logs.
Path can be changed in config.yaml under logging.directory.

## How do I change the default setpoint?

Edit config.yaml:

- control.default_setpoint

You can also send setpoint updates over serial with SET:<value>.

## How do I inspect service logs?

```bash
sudo journalctl -u supercapfreezer -f
```

## Is there still a GUI?

No. This branch is headless only.

## Why does protocol.h mention binary packets?

protocol.h documents a legacy or alternate binary protocol.
Current runtime path in Python uses ASCII line protocol as described in PROTOCOL.md.

## How do I stop the service?

```bash
sudo systemctl stop supercapfreezer.service
```

Disable autostart:

```bash
sudo systemctl disable supercapfreezer.service
```
