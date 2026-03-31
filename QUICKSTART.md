# QUICKSTART

## 1. Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Run Simulation

```bash
python main.py --simulate
```

## 3. Run Hardware

```bash
python main.py --port /dev/ttyACM0
```

## 4. Enable Temperature Trigger

```bash
python main.py --port /dev/ttyACM0 --trigger-temp -1.0 --trigger-direction below --command CHARGE
```

## 5. Verify Input and ACK

Incoming telemetry example:

T:43440, V:0, I:6 mA, STATE:1, Temp: -1.2 C

Outgoing command example:

CMD: CHARGE

Incoming ACK example:

ACK: CMD: CHARGE
