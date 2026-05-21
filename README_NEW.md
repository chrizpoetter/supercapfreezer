# Deployment Runbook (Headless)

## 1. System Setup

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git
```

## 2. Project Setup

```bash
git clone <your-repo-url> supercapfreezer
cd supercapfreezer
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Configure Runtime

Edit config.yaml:

- serial.port
- serial.baud
- trigger.temperature_celsius
- trigger.direction
- trigger.command

## 4. Manual Test

```bash
source venv/bin/activate
python main.py
```

Common serial options on Raspberry Pi:

- GPIO UART (Pi 3/4/5): `/dev/serial0`
- USB serial adapters/devices: `/dev/ttyACM0` or `/dev/ttyUSB0`

Override only when needed:

```bash
python main.py --port /dev/serial0
```

Or simulation:

```bash
python main.py --simulate
```

## 5. Service Install

```bash
sudo cp supercapfreezer.service /etc/systemd/system/supercapfreezer.service
sudo systemctl daemon-reload
sudo systemctl enable supercapfreezer.service
sudo systemctl start supercapfreezer.service
```

Check logs:

```bash
sudo journalctl -u supercapfreezer -f
```

## 6. Runtime Expectations

- STM32 sends telemetry lines in this format:
  - T:43440, V:0, I:6 mA, STATE:1, Temp: -1.2 C
- Pi can send test start command:
  - CMD: CHARGE
- STM32 can respond with ACK line.

## 7. Update Workflow

```bash
cd /home/<your-user>/supercapfreezer
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart supercapfreezer.service
```
