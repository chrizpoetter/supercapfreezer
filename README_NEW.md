# SUPERCAPFREEZER - Temperature Monitor für Raspberry Pi

**Bachelorarbeit Projekt:** Embedded-System zur Echtzeiterfassung von Temperaturdaten mit Arduino UNO R4 WiFi und Raspberry Pi 3.

---

## 🎯 Features

- ✅ **Robustes binäres Protokoll** mit CRC16-CCITT Checksummen
- ✅ **PT1000 RTD Sensor** mit Callendar-Van Dusen Gleichung
- ✅ **Multi-Screen UI** mit pygame (Dashboard, Graph, Settings)
- ✅ **24h Daten-Puffer** mit CSV-Logging
- ✅ **Touchscreen-Support** (Swipe-Navigation)
- ✅ **Autostart via Systemd**
- ✅ **Simulation-Modus** zum Testen ohne Hardware
- ✅ **Erweiterbar** für mehrere Sensoren (Spannung, etc.)

---

## 📋 Komponenten

### Hardware
- **Arduino:** Arduino UNO R4 WiFi
- **Sensor:** PT1000 RTD mit Signalaufbereitung
- **Display:** 3.5" SPI-TFT (320×480)
- **Verbindung:** USB Serial (115200 baud)

### Software
- **Arduino-Firmware:** `arduino/supercapfreezer_firmware.ino`
- **RPi Python App:** `main.py`
  - Serial Parser: `serial_handler.py`
  - Daten-Logger: `data_logger.py`
  - UI/pygame: `ui_app.py`
- **Konfiguration:** `config.yaml`

---

## 🚀 Installation

### Raspberry Pi Setup

#### 1. System vorbereiten
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libfreetype6-dev
```

#### 2. Repository klonen & venv erstellen
```bash
cd /home/pi
git clone <repo-url> supercapfreezer
cd supercapfreezer
python3 -m venv venv
source venv/bin/activate
```

#### 3. Dependencies installieren
```bash
pip install -r requirements.txt
```

#### 4. (Optional) Display-Treiber installieren
Für 3.5" SPI-TFT Displays:
```bash
# Beispiel für ILI9486 (FBTFT):
sudo bash -c 'echo "dtoverlay=waveshare35a" >> /boot/config.txt'
sudo reboot
```

### Arduino Setup

#### 1. Arduino IDE öffnen & Sketch laden
- File → Open → `arduino/supercapfreezer_firmware.ino`

#### 2. Board & Port wählen
- Board: Arduino UNO R4 WiFi
- Port: `/dev/ttyACM0` (oder erkannt auf Raspberry Pi)

#### 3. PT1000-Kalibrierung anpassen
Im Sketch folgende Werte nach Ihrem Signalaufbereiter-Circuit anpassen:
```cpp
#define PT1000_V_MIN       0.5f   // Spannung bei -30°C
#define PT1000_V_MAX       4.5f   // Spannung bei +30°C
#define PT1000_R_MIN       500.0f // Widerstand bei V_MIN
#define PT1000_R_MAX       1500.0f // Widerstand bei V_MAX
```

#### 4. Hochladen
- Sketch → Upload

---

## 💻 Verwendung

### Manueller Start (Test-Modus)

```bash
# Mit Hardware
python main.py --port /dev/ttyACM0 --baud 115200 --fullscreen

# Simulationsmodus (ohne Arduino)
python main.py --simulate

# Debug-Modus
python main.py --port /dev/ttyACM0 --baud 115200
```

### Autostart mit Systemd

```bash
# Service-Datei installieren
sudo cp supercapfreezer.service /etc/systemd/system/

# Service aktivieren
sudo systemctl enable supercapfreezer.service

# Service starten
sudo systemctl start supercapfreezer.service

# Status prüfen
sudo systemctl status supercapfreezer.service

# Logs ansehen
sudo journalctl -u supercapfreezer -f
```

---

## 🖥️ UI Navigation

### Screens

1. **Dashboard** - Aktuelle Temperatur & Statistiken
2. **Graph** - Rollendes 60-Sekunden-Plot
3. **Settings** - System-Info & Export

### Bedienung

- **Wischen nach Links/Rechts:** Zwischen Screens navigieren
- **ESC-Taste:** App beenden
- **S-Taste:** CSV exportieren (nur Tastatur)

---

## 📊 Daten & Logging

### CSV-Format

```csv
timestamp_utc,time_elapsed_s,temperature_celsius,seq_num
2025-12-18T15:30:45.123456,0.000,23.45,0
2025-12-18T15:30:45.223456,0.100,23.46,1
2025-12-18T15:30:45.323456,0.200,23.44,2
...
```

### Puffer & Retention

- **Ring-Buffer:** 24h Daten im RAM
- **CSV-Logging:** Kontinuierliche Datei
- **Max. Buffer-Size:** ~864k Samples (24h @ 10Hz)

---

## 🔧 Konfiguration

Siehe `config.yaml` für:
- PT1000-Kalibrierungswerte
- Abtastrate & Averaging
- Display-Einstellungen
- Logging-Parameter
- Zukünftige Alarm-Schwellen

---

## 📡 Protokoll

Das binäre Kommunikationsprotokoll ist in [PROTOCOL.md](PROTOCOL.md) vollständig dokumentiert.

### Schnellübersicht

- **Sync:** 0xAA 0x55
- **Paketgröße:** 14 + N×2 Bytes (14 min.)
- **CRC:** CRC-16-CCITT (0x1021)
- **Payload-Encoding:** Temperature = int16 × 100
- **Durchsatz:** 140 bytes/sec @ 10Hz

Mehr: [PROTOCOL.md](PROTOCOL.md)

---

## 🧪 Troubleshooting

### Keine Pakete empfangen
```bash
# Serial-Port testen
ls -la /dev/ttyACM*
cat /dev/ttyACM0  # Sollte Rohdaten zeigen
```

### CRC-Fehler häufig
- Baudrate prüfen (sollte 115200 sein)
- USB-Kabel austauschen (Störungen)
- Signalaufbereiter-Circuit prüfen

### Display zeigt nichts
```bash
# Framebuffer testen
ls -la /dev/fb*
fbset -i  # Info anzeigen
```

### Service startet nicht
```bash
sudo journalctl -u supercapfreezer.service -n 50
```

---

## 📚 Dokumentation

- **PROTOCOL.md** - Binäres Protokoll (Arduino ↔ RPi)
- **config.yaml** - Konfigurationsoptionen
- **Arduino Code** - Kommentiert für PT1000 Integration
- **Python Code** - Docstrings für alle Klassen

---

## 🎓 Für die Bachelorarbeit

### Schwerpunkte

- ✅ **Sensorik:** PT1000 RTD mit Callendar-Van Dusen Kalibrierung
- ✅ **Elektronik:** Signalaufbereiter-Circuit (ADC-Interface)
- ✅ **Embedded:** Arduino UNO R4 Firmware mit Interrupt-basierter Abtastung
- ✅ **Systemintegration:** RPi mit pygame UI & CSV-Logging
- ✅ **Protokoll:** Robustes binäres Format mit CRC16 & Fehlerbehandlung

### Erweiterungspotenzial

- [ ] Mehrere Temperatur-Sensoren (Multiplex)
- [ ] Spannungsmessungen (1 kHz Abtastrate)
- [ ] Datenbank-Backend (SQLite)
- [ ] Web-Dashboard (Flask)
- [ ] Anomalieerkennung (ML)
- [ ] Cloud-Upload

---

## 📄 Lizenz

MIT License - Siehe LICENSE.txt

---

## 👤 Kontakt & Support

Bei Fragen oder Problemen: [contact details hier eintragen]

---

**Letztes Update:** 2025-12-18  
**Version:** 1.0  
**Status:** Produktionsreif für Bachelor-Projekt
