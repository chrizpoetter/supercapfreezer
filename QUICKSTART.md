# QUICKSTART

Fast path for getting SUPERCAPFREEZER running in headless mode.

## 1. Create Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Run in Simulation

```bash
python main.py --simulate
```

Expected behavior:

- Process starts and prints headless status.
- CSV logs appear in logs/.

## 3. Run with Hardware

```bash
python main.py --port1 /dev/ttyACM0 --port2 /dev/ttyACM1
```

Where:

- port1 is Arduino peltier controller.
- port2 is measurement controller.

## 4. Verify Serial Traffic

Peltier controller should receive:

- SET:<setpoint>
- TEMP:<measured_temp> from the Pi-side logic that supplies temperature.

Arduino should return:

- TEMP:<temp> PWM:<pwm>

Measurement controller should return lines containing:

- V1, V2, I1, I2, STATE

## 5. Stop

Press Ctrl+C.

The app will stop serial threads and close logger files cleanly.
