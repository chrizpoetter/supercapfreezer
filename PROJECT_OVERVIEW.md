# SUPERCAPFREEZER - Projektstruktur & Übersicht

## 📁 Verzeichnisstruktur

```
supercapfreezer/
├── README_NEW.md                      ← Start hier!
├── QUICKSTART.md                      ← Schnellanleitung
├── PROTOCOL.md                        ← Kommunikations-Protokoll (BA-Doku)
├── config.yaml                        ← Konfigurationsdatei
├── requirements.txt                   ← Python-Abhängigkeiten
├── install.sh                         ← Automatische Installation
│
├── arduino/                           ← Arduino-Firmware
│   └── supercapfreezer_firmware.ino  ← UNO R4 WiFi Code (PT1000)
│
├── protocol.h                         ← Header mit Protokoll-Konstanten
│
├── main.py                           ← 🚀 Entry Point (Startet alles)
├── serial_handler.py                 ← Binär-Parser (Arduino Kommunikation)
├── data_logger.py                    ← CSV-Logger (24h Ring-Buffer)
├── ui_app.py                         ← Pygame UI (Dashboard, Graph, Settings)
│
├── supercapfreezer.service           ← Systemd Service (Autostart)
├── logs/                             ← 📊 CSV-Daten Verzeichnis
│
└── .gitignore                        ← (automatisch erstellen)
```

---

## 🎯 Komponenten Übersicht

### 1. **Arduino Firmware** (`arduino/supercapfreezer_firmware.ino`)

**Aufgabe:** PT1000 Sensor auslesen und Daten senden

```cpp
┌─────────────────────────────┐
│   ADC (A0) ← PT1000 Signal  │
│      ↓                      │
│  Callendar-Van Dusen        │
│  Temperatur-Berechnung      │
│      ↓                      │
│  Binary Packet packen       │
│  CRC16-CCITT berechnen      │
│      ↓                      │
│  Serial.write() 115200 Baud │
└─────────────────────────────┘
```

**Eigenschaften:**
- 10 Hz Abtastrate
- 4× ADC-Mittelwertbildung
- PT1000 Callendar-Van Dusen Kalibrierung
- Robustes Paketformat mit Checksumme
- ~140 Bytes/Sekunde Durchsatz

**Wichtig:** PT1000-Kalibrierungswerte müssen angepasst werden!

---

### 2. **Serial Parser** (`serial_handler.py`)

**Aufgabe:** Binäre Pakete vom Arduino empfangen, validieren, parsen

```python
┌──────────────────────────────────────┐
│  USB Serial (115200 baud)            │
│  Byte-by-Byte Empfang                │
│      ↓                               │
│  Zustandsautomat:                    │
│  - SYNC_0: Warte auf 0xAA            │
│  - SYNC_1: Warte auf 0x55            │
│  - HEADER: Lese 8 weitere Bytes      │
│  - PAYLOAD: Lese N×2 Payload-Bytes   │
│  - CRC: Lese CRC16                   │
│      ↓                               │
│  CRC-Validierung                     │
│  ✗ Fehler → Reset                    │
│  ✓ Gültig → Packet-Struktur          │
│      ↓                               │
│  Callback mit Temperature-Wert       │
└──────────────────────────────────────┘
```

**Features:**
- Byte-für-Byte Synchronisation
- CRC16-CCITT Validierung
- Fehlerbehandlung & Recovery
- Statistiken (Paket-Zähler, CRC-Fehler)

---

### 3. **Data Logger** (`data_logger.py`)

**Aufgabe:** Daten speichern (RAM + CSV-Datei)

```python
┌────────────────────────────────────┐
│  Ring-Buffer (24h, 864k Samples)   │
│  - Älteste Daten überschreiben     │
│  - Immer aktuelle Daten verfügbar  │
│      ↓                             │
│  CSV-Datei (kontinuierlich)        │
│  - timestamp_utc                   │
│  - temperature_celsius             │
│  - seq_num                         │
│                                    │
│  get_stats():                      │
│  - min/max/avg Temperature         │
│  - Sample Count                    │
│  - Laufzeit                        │
└────────────────────────────────────┘
```

**Format:**
```csv
timestamp_utc,time_elapsed_s,temperature_celsius,seq_num
2025-12-18T15:30:45.123456,0.000,23.45,0
2025-12-18T15:30:45.223456,0.100,23.46,1
```

---

### 4. **Pygame UI** (`ui_app.py`)

**Aufgabe:** Daten visualisieren auf 3.5" TFT Display

```
┌─────────────────────────────────┐
│  SCREEN 1: DASHBOARD            │
│  ┌─────────────────────────────┐│
│  │ SUPERCAPFREEZER             ││
│  │ Temp: 23.45°C (groß)        ││
│  │                             ││
│  │ Samples: 850                ││
│  │ Min: 20.12°C                ││
│  │ Max: 26.78°C                ││
│  │ Avg: 23.51°C                ││
│  │ Runtime: 1825s              ││
│  │                             ││
│  │ Swipe for more >>           ││
│  └─────────────────────────────┘│
└─────────────────────────────────┘

┌─────────────────────────────────┐
│  SCREEN 2: GRAPH                │
│  ┌─────────────────────────────┐│
│  │ Temperature Graph (60s)      ││
│  │                             ││
│  │  26 ┌─────────────────────  ││
│  │  25 │  ╱╲    ╱╲              ││
│  │  24 │ ╱  ╲  ╱  ╲             ││
│  │  23 │╱    ╲╱    ╲            ││
│  │  22 ────────────────         ││
│  │     0s  15s  30s  45s  60s   ││
│  │                             ││
│  │ << Swipe for more >>        ││
│  └─────────────────────────────┘│
└─────────────────────────────────┘

┌─────────────────────────────────┐
│  SCREEN 3: SETTINGS             │
│  ┌─────────────────────────────┐│
│  │ System Info                 ││
│  │ CPU: 45.2%                  ││
│  │ RAM: 32.1% (487 MB)         ││
│  │ Port: /dev/ttyACM0          ││
│  │ Baud: 115200                ││
│  │                             ││
│  │ ┌──────────────────────────┐││
│  │ │  EXPORT CSV              │││
│  │ └──────────────────────────┘││
│  └─────────────────────────────┘│
└─────────────────────────────────┘
```

**Screens:**
1. **Dashboard** - Aktuelle Daten + Statistiken
2. **Graph** - 60-Sekunden Rollendes Plot
3. **Settings** - System-Info + Export

**Navigation:**
- Wischen links/rechts = Screen wechseln
- ESC = App beenden
- S = CSV exportieren

---

### 5. **Main Application** (`main.py`)

**Aufgabe:** Alles koordinieren

```python
┌───────────────────────────────────┐
│  main.py                          │
│                                   │
│  1. DataLogger initialisieren     │
│  2. SerialReader starten          │
│     ├─ USB öffnen                 │
│     ├─ PacketParser starten       │
│     └─ Callback registrieren      │
│  3. PyGameApp starten             │
│     ├─ Display initialisieren     │
│     ├─ 3 Screens laden            │
│     └─ Event-Loop (30 FPS)        │
│  4. Cleanup bei Beendigung        │
│     ├─ CSV speichern              │
│     ├─ Serial schließen           │
│     └─ pygame beenden             │
└───────────────────────────────────┘
```

---

## 🔄 Datenfluss

```
┌──────────────────────────────────────────────────────────────┐
│  ARDUINO                                                     │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ PT1000 Sensor (A0)                                     │  │
│  │    ↓                                                   │  │
│  │ ADC lesen + Mittelwertbildung                          │  │
│  │    ↓                                                   │  │
│  │ Temperatur berechnen (Callendar-Van Dusen)            │  │
│  │    ↓                                                   │  │
│  │ Paket konstruieren (14 Bytes + CRC)                   │  │
│  │    ↓                                                   │  │
│  │ Serial.write() (10×/Sekunde)                          │  │
│  └────────────────────────────────────────────────────────┘  │
│                          ↓ USB Serial ↓                      │
├──────────────────────────────────────────────────────────────┤
│  RASPBERRY PI                                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ serial_handler.py: PacketParser                        │  │
│  │    ↓                                                   │  │
│  │ Bytes empfangen & parsen                              │  │
│  │ CRC validieren                                        │  │
│  │    ↓                                                   │  │
│  │ main.py: on_packet_received()                         │  │
│  │    ↓                                                   │  │
│  │ data_logger.py: push()                                │  │
│  │    ├─ Ring-Buffer (RAM)                               │  │
│  │    └─ CSV-Datei (Disk)                                │  │
│  │    ↓                                                   │  │
│  │ ui_app.py: Daten visualisieren                        │  │
│  │    ├─ Dashboard (aktuelle Werte)                      │  │
│  │    ├─ Graph (60s Trend)                               │  │
│  │    └─ Settings (System-Info)                          │  │
│  │    ↓                                                   │  │
│  │ TFT-Display (3.5")                                    │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Technologie Stack

| Komponente | Technologie | Version |
|-----------|------------|---------|
| **Arduino** | UNO R4 WiFi | - |
| **Sensor** | PT1000 RTD | - |
| **Übertragung** | USB Serial | 115200 baud |
| **Protokoll** | Binary + CRC16 | v1.0 |
| **RPi OS** | Raspberry Pi OS | Bullseye/Bookworm |
| **Python** | Python | 3.9+ |
| **UI Framework** | pygame | 2.5.2 |
| **Parser** | Custom | - |
| **Logging** | CSV | - |
| **Init System** | systemd | - |

---

## 📊 Performance & Kapazität

| Metrik | Wert |
|--------|-----|
| Abtastrate (Temperatur) | 10 Hz |
| Zukünftige Abtastrate (Spannung) | 1 kHz |
| Baudrate | 115200 bps |
| Aktueller Durchsatz | 140 bytes/sec |
| Baudrate-Auslastung | 1.2% |
| Puffer-Kapazität | 24 Stunden |
| Samples @ 10Hz/24h | 864,000 |
| RAM benötigt | ~30 MB (Ring-Buffer) |
| Display | 480×320 @30 FPS |

---

## 🚀 Installation & Start

### Schnell
```bash
./install.sh      # Automatisch (empfohlen)
```

### Manuell
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py --simulate
```

### Mit Hardware
```bash
python main.py --port /dev/ttyACM0 --fullscreen
```

### Autostart
```bash
sudo systemctl enable supercapfreezer.service
sudo systemctl start supercapfreezer.service
```

---

## 📚 Dokumentation für Bachelor

### Für die Arbeit relevant:

1. **PROTOCOL.md** (10 Seiten)
   - Binäres Protokoll
   - CRC-Berechnung
   - Extensibilität für zukünftige Sensoren
   - Performance-Analyse

2. **Arduino-Firmware** (`arduino/supercapfreezer_firmware.ino`)
   - PT1000 Kalibrierung
   - Callendar-Van Dusen Gleichung
   - Timer-basierte Abtastung
   - Paket-Struktur

3. **Parser & Fehlerbehandlung** (`serial_handler.py`)
   - Zustandsautomat
   - CRC-Validierung
   - Synchronisation & Recovery

4. **Systemintegration**
   - Raspberry Pi Linux (Systemd)
   - Multi-Screen UI
   - 24h Daten-Persistierung

---

## ✅ Implementierungs-Checkliste

- [x] Binäres Kommunikationsprotokoll spezifiziert
- [x] Arduino-Firmware (PT1000 RTD)
- [x] RPi Serial-Parser mit CRC16
- [x] Data Logger (CSV + Ring-Buffer)
- [x] Multi-Screen UI (pygame)
- [x] Konfigurationsdatei (YAML)
- [x] Systemd Service (Autostart)
- [x] Installation Script
- [x] Dokumentation (PROTOCOL.md)
- [x] Quick Start Guide

---

## 🔮 Zukünftige Erweiterungen

### Kurzfristig
- [ ] Mehrere Temperatur-Sensoren (Multiplex)
- [ ] Web-Dashboard (Flask optional)
- [ ] Datenbank-Backend (SQLite)

### Mittelfristig
- [ ] Spannungsmessungen (1 kHz)
- [ ] Anomalieerkennung
- [ ] Kalibrierungsprogramm

### Langfristig
- [ ] Cloud-Upload
- [ ] Machine Learning
- [ ] Mobile App

---

## 📄 Lizenzen & Referenzen

- **Eigener Code:** MIT License
- **Bibliotheken:** Siehe `requirements.txt`
- **Arduino:** CC0 / Public Domain
- **Referenzen:**
  - IEC 60751: PT1000 Standard
  - CRC-16-CCITT: https://crccalc.com/
  - pygame: https://www.pygame.org/

---

**Projektversion:** 1.0  
**Datum:** 2025-12-18  
**Status:** ✅ Produktionsreif für Bachelor-Arbeit
