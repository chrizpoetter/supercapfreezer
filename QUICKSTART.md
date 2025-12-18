# SUPERCAPFREEZER Quick Start Guide

## 📌 Was ist SUPERCAPFREEZER?

Ein vollständiges Echtzeitüberwachungssystem für Temperaturmessungen:
- **Arduino UNO R4 WiFi** → Liest PT1000 Sensor
- **Raspberry Pi 3** → Empfängt Daten, plottet & speichert
- **3.5" TFT Display** → Zeigt Live-Daten, Graph, Statistiken
- **24h Logging** → CSV-Datei mit allen Messwerten

---

## 🔧 Schnelle Inbetriebnahme

### Option A: Automatische Installation (Empfohlen)

```bash
# 1. Auf Raspberry Pi anmelden
ssh pi@raspberrypi.local

# 2. Repository klonen
git clone <repo-url> ~/supercapfreezer
cd ~/supercapfreezer

# 3. Installation starten
chmod +x install.sh
./install.sh
```

### Option B: Manuelle Installation

```bash
# System-Packages
sudo apt update
sudo apt install -y python3-pip python3-venv libsdl2-dev libfreetype6-dev

# Virtual environment
python3 -m venv venv
source venv/bin/activate

# Python-Abhängigkeiten
pip install -r requirements.txt

# Log-Verzeichnis
mkdir -p logs
```

---

## 🎯 Arduino Setup

### Hardware

1. **PT1000 Sensor mit Signalaufbereiter**
   - Sensor an ADC Pin A0 anschließen (0-5V)
   - Beispiel: Transimpedanz-Verstärker mit PT1000

2. **USB-Verbindung zur RPi**
   - Arduino UNO R4 WiFi via USB-C an Raspberry Pi

### Firmware einspielen

1. Arduino IDE öffnen
2. `File` → `Open` → `arduino/supercapfreezer_firmware.ino`
3. Board: "Arduino UNO R4 WiFi" wählen
4. **WICHTIG: Kalibrierungswerte anpassen!**

```cpp
// Im Sketch anpassen nach eigenem Circuit:
#define PT1000_V_MIN    0.5    // Spannung bei -30°C
#define PT1000_V_MAX    4.5    // Spannung bei +30°C
#define PT1000_R_MIN    500.0  // Widerstand bei V_MIN
#define PT1000_R_MAX    1500.0 // Widerstand bei V_MAX
```

5. `Sketch` → `Upload`

---

## ▶️ Erste Schritte

### 1. Test im Simulationsmodus (kein Arduino nötig)

```bash
cd ~/supercapfreezer
source venv/bin/activate
python main.py --simulate
```

**Was sehen Sie:**
- Dashboard mit simulierten Temperatur-Daten (sinusförmig ~25°C ± 3°C)
- Graph mit rollendem Plot
- System-Informationen

**Navigation:**
- Pfeiltasten oder Wischen für Screen-Wechsel
- ESC zum Beenden

### 2. Mit Arduino (Hardware)

```bash
python main.py --port /dev/ttyACM0 --baud 115200
```

Wenn erfolgreich:
```
[LOG] Opened logfile: ./logs/supercapfreezer_YYYYMMDD_HHMMSS.csv
[APP] Dashboard Screen
[PARSER] Valid packets: 5/5 ✓
```

---

## ⚙️ Autostart konfigurieren

### Systemd Service starten

```bash
# Service aktivieren
sudo systemctl enable supercapfreezer.service

# Service starten
sudo systemctl start supercapfreezer.service

# Status prüfen
sudo systemctl status supercapfreezer.service

# Logs live ansehen
sudo journalctl -u supercapfreezer -f
```

### Nach Neustart automatisch starten
Der Service startet jetzt automatisch beim Raspberry Pi Boot!

---

## 📊 Daten ansehen

### CSV-Dateien

```bash
# Letzte Log-Datei öffnen
cd logs/
ls -lt
tail -20 supercapfreezer_*.csv
```

Format:
```csv
timestamp_utc,time_elapsed_s,temperature_celsius,seq_num
2025-12-18T15:30:45.123,0.000,23.45,0
2025-12-18T15:30:45.223,0.100,23.46,1
2025-12-18T15:30:45.323,0.200,23.44,2
```

### Daten exportieren

Während App läuft: `S` drücken (nur Tastatur) oder über Settings-Screen

---

## 🐛 Troubleshooting

### "Kein serieller Port gefunden"

```bash
# Arduino erkannt?
ls -la /dev/ttyACM*

# Berechtigungen prüfen
groups $USER  # sollte "dialout" enthalten

# Falls nicht:
sudo usermod -a -G dialout pi
# Neu anmelden erforderlich
```

### "CRC-Fehler häufig"

- USB-Kabel überprüfen (hochwertig, kurz)
- Arduino-Board neu flashen
- Baudrate in Arduino überprüfen (sollte 115200)
- Screenshotspannungsversorgung des Arduino

### "Display zeigt nichts"

```bash
# Framebuffer testen
ls -la /dev/fb*

# FBTFT Treiber installieren (für SPI-TFT)
sudo bash -c 'echo "dtoverlay=waveshare35a" >> /boot/config.txt'
sudo reboot
```

### "App startet nicht"

```bash
# Manuelle Debug-Ausgabe
python main.py --port /dev/ttyACM0 --simulate

# Service-Logs ansehen
sudo journalctl -u supercapfreezer -n 50 --no-pager
```

---

## 📚 Dokumentation

| Datei | Inhalt |
|-------|--------|
| `README_NEW.md` | Ausführliche Features & Installation |
| `PROTOCOL.md` | Binäres Protokoll (für Bachelor!) |
| `config.yaml` | Konfigurationsoptionen |
| `arduino/supercapfreezer_firmware.ino` | Arduino Code (PT1000) |
| `main.py` | Main Entry Point |
| `serial_handler.py` | Binary Parser |
| `data_logger.py` | CSV Logging |
| `ui_app.py` | Pygame UI |

---

## 🎓 Bachelor-Arbeit

Wichtige Aspekte für die Dokumentation:

### Protokoll-Analyse
- Siehe `PROTOCOL.md` für komplette Spezifikation
- Binäres Format (nicht ASCII) mit CRC16-CCITT
- Extensibel für Spannungsmessungen

### PT1000-Sensorik
- Callendar-Van Dusen Kalibrierung
- ADC-Konditionierung (0-5V Mapping)
- Arduino-Firmware: `arduino/supercapfreezer_firmware.ino`

### Systemintegration
- Raspberry Pi Linux (Systemd Service)
- Pygame UI für TFT-Display
- CSV-Logging (24h Ring-Buffer)

### Performance
- 10 Hz Abtastrate = 140 bytes/s
- Baudrate 115200 = nur 1.2% genutzt
- Beliebig auf 1 kHz erweiterbar

---

## ✅ Checkliste für erfolgreichen Start

- [ ] Raspberry Pi mit Betriebssystem bereit
- [ ] Python 3.7+ installiert
- [ ] `install.sh` erfolgreich durchgelaufen
- [ ] Arduino UNO R4 mit Firmware geflasht
- [ ] PT1000 an Arduino A0 angeschlossen
- [ ] USB-Verbindung Arduino ↔ RPi hergestellt
- [ ] App im Simulationsmodus getestet
- [ ] App mit Arduino getestet
- [ ] CSV-Dateien in `logs/` vorhanden
- [ ] Systemd Service aktiviert

---

## 🚀 Nächste Schritte

1. **Daten sammeln:** App laufen lassen, Messdaten in CSV speichern
2. **Kalibrierung:** PT1000-Werte mit bekannten Temperaturen verifizieren
3. **Optimierung:** Performance-Messungen, Fehlerrate dokumentieren
4. **Erweiterung:** Spannungsmessungen hinzufügen (1 kHz)
5. **Dokumentation:** Alles für Bachelor-Arbeit zusammenfassen

---

## 📞 Support

Für Probleme:
1. Logs ansehen: `sudo journalctl -u supercapfreezer -f`
2. Dokumentation lesen: `PROTOCOL.md`, `README_NEW.md`
3. Kalibrierungswerte überprüfen
4. Arduino-Firmware Debug-Modus aktivieren

---

**Viel Erfolg! 🎉**

Version: 1.0 | Datum: 2025-12-18
