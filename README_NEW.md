# Deployment Runbook (Headless)

This runbook focuses on running SUPERCAPFREEZER as a headless service on Raspberry Pi.

## 1. System Preparation

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

## 3. Firmware

Upload Arduino firmware from:

- arduino/supercapfreezer_firmware.ino

Firmware expects:

- SET:<value>
- TEMP:<value>

and publishes:

- TEMP:<value> PWM:<value>

## 4. Configure Ports

Edit config.yaml or pass CLI args.

Typical:

- Peltier on /dev/ttyACM0
- Measurement MCU on /dev/ttyACM1

Test manually first:

```bash
source venv/bin/activate
python main.py --port1 /dev/ttyACM0 --port2 /dev/ttyACM1
```

## 5. Install systemd Service

```bash
sudo cp supercapfreezer.service /etc/systemd/system/supercapfreezer.service
sudo systemctl daemon-reload
sudo systemctl enable supercapfreezer.service
sudo systemctl start supercapfreezer.service
```

Check status:

```bash
sudo systemctl status supercapfreezer.service
```

Tail logs:

```bash
sudo journalctl -u supercapfreezer -f
```

## 6. Update Workflow

```bash
cd /home/pi/supercapfreezer
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart supercapfreezer.service
```

## 7. Rollback Quick Method

If a deployment fails:

1. Checkout previous known-good commit.
2. Restart service.
3. Confirm serial connectivity and CSV output.

## 8. Health Checks

- Service active and auto-restarting on failure.
- New CSV files in logs/.
- Serial logs show packets from both controllers.
- PWM values update over time in peltier status lines.
