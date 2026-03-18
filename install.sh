#!/bin/bash

# SUPERCAPFREEZER Installation Script for Raspberry Pi 3
# ======================================================
# This script automates the setup of the SUPERCAPFREEZER application

set -e  # Exit on error

echo "=========================================="
echo "SUPERCAPFREEZER Installation"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo -e "${YELLOW}[WARNING] Not running on Raspberry Pi${NC}"
    echo "This script is optimized for Raspberry Pi OS"
    echo ""
fi

# Step 1: Update system
echo -e "${GREEN}[1/6] Updating system packages...${NC}"
sudo apt update
sudo apt upgrade -y

# Step 2: Install dependencies
echo -e "${GREEN}[2/6] Installing dependencies...${NC}"
sudo apt install -y \
    python3-pip \
    python3-venv \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libfreetype6-dev \
    git

# Step 3: Create virtual environment
echo -e "${GREEN}[3/6] Creating Python virtual environment...${NC}"
if [ -d "venv" ]; then
    echo "    venv already exists, skipping creation"
else
    python3 -m venv venv
    echo "    venv created"
fi

# Step 4: Activate venv and install Python packages
echo -e "${GREEN}[4/6] Installing Python packages...${NC}"
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Step 5: Configure systemd service
echo -e "${GREEN}[5/6] Configuring systemd service...${NC}"

# Update service file with current directory
CURRENT_DIR=$(pwd)
SERVICE_FILE="supercapfreezer_install.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=SUPERCAPFREEZER Temperature Monitor
After=network.target
StartLimitInterval=60
StartLimitBurst=3

[Service]
Type=simple
User=pi
WorkingDirectory=${CURRENT_DIR}
ExecStart=${CURRENT_DIR}/venv/bin/python main.py --port1 /dev/ttyACM0
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

PrivateTmp=yes
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

echo "    Service file: $SERVICE_FILE"
echo "    Installing service..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/supercapfreezer.service
sudo systemctl daemon-reload
sudo systemctl enable supercapfreezer.service

# Step 6: Create log directory
echo -e "${GREEN}[6/6] Creating log directory...${NC}"
mkdir -p logs
chmod 755 logs

echo ""
echo -e "${GREEN}=========================================="
echo "Installation complete!"
echo "==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Upload Arduino firmware to UNO R4 WiFi"
echo "   - File: arduino/supercapfreezer_firmware.ino"
echo "   - Adjust PT1000 calibration values in firmware"
echo ""
echo "2. Test the application:"
echo "   $ source venv/bin/activate"
echo "   $ python main.py --simulate          # Simulation mode"
echo "   $ python main.py --port /dev/ttyACM0 # With Arduino"
echo ""
echo "3. Enable autostart:"
echo "   $ sudo systemctl start supercapfreezer"
echo "   $ sudo systemctl status supercapfreezer"
echo ""
echo "4. View logs:"
echo "   $ sudo journalctl -u supercapfreezer -f"
echo ""
echo "Documentation:"
echo "   - README_NEW.md (installation & usage)"
echo "   - PROTOCOL.md (binary protocol specification)"
echo "   - config.yaml (configuration options)"
echo ""
