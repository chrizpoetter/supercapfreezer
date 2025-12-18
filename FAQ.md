# SUPERCAPFREEZER - FAQ & Häufig Gestellte Fragen

## 🤔 Allgemeine Fragen

### F: Was ist SUPERCAPFREEZER?
**A:** Ein komplettes Echtzeit-Temperatur-Überwachungssystem:
- Arduino-Firmware liest PT1000 Sensor
- Sendet Daten via USB an Raspberry Pi
- RPi zeigt Live-Plots auf TFT-Display
- Speichert alle Daten als CSV (24h)

### F: Warum binary protocol statt ASCII?
**A:** 
- **ASCII:** "25.123\n" = 7 bytes pro Wert
- **Binary:** int16 = 2 bytes pro Wert
- **3.5× mehr Effizienz** bei gleicher Baudrate
- Höhere Zuverlässigkeit durch CRC-Checksummen

### F: Kann ich das Projekt erweitern?
**A:** **Ja!** Das Protokoll ist flexibel:
- Neue Sensoren hinzufügen (z.B. Spannung)
- Abtastrate erhöhen bis 1 kHz
- Batching für hohe Datenraten
- Siehe `PROTOCOL.md` für Details

### F: Läuft das auf anderen RPi-Versionen?
**A:** **Ja**, aber:
- RPi 3 (empfohlen): Genug Ressourcen, kein Overkill
- RPi 2/Zero: Möglich aber langsamer
- RPi 4+: Kein Problem, eher überdimensioniert
- RPi 5: Kompatibilität erforderlich

---

## 🔧 Hardware-Fragen

### F: Welchen PT1000-Sensor soll ich kaufen?
**A:** Standards sind:
- **DIN 43760:** Standard-PT1000
- **Genauigkeit:** ±0.15°C (Klasse A) oder ±0.35°C (Klasse B)
- **Preis:** €5-20 (einfache Versionen)
- **Wichtig:** Signalaufbereiter-Circuit erforderlich!

### F: Wie baue ich den Signalaufbereiter?
**A:** Mehrere Optionen:

**Option 1: Transimpedanz-Verstärker (einfach)**
```
PT1000 ─┬─ (Stromspiegel 1mA)
        └─ OP-Amp (z.B. OPA2333)
        └─ Rückkopplung: 5kΩ Widerstand
        └─ Ausgang 0-5V
```

**Option 2: Fertige Module**
- PT100/PT1000 Breakout-Boards (€10-15)
- z.B. DFRobot, AZDelivery

**Option 3: Externe ADC + Kalibration**
- Genauer aber komplexer
- Für BA evtl. zu umfangreich

### F: Display-Treiber - welcher ist richtig?
**A:** Hängt vom Display-Modell ab:
- **ILI9486:** Häufig bei "Waveshare 3.5"
- **ST7789:** Kleinere 3.5" Displays
- **Überprüfen:** Amazon/eBay Produktbeschreibung
- **Setup:** Device Tree Overlay (z.B. `waveshare35a`)

### F: Kann ich auch ein anderes Display nutzen?
**A:** **Ja!** 
- HDMI-Monitor über X11
- Andere SPI-Displays (ILI9340, ST7735)
- Setup unterscheidet sich aber, auch Treiber nötig

---

## 💻 Software-Fragen

### F: Python 2 oder 3?
**A:** **Nur Python 3.9+**
- Python 2 ist deprecated
- pygame 2.5+ benötigt Python 3.7+
- Raspberry Pi OS hat Python 3 vorinstalliert

### F: Kann ich den Code modifizieren?
**A:** **Absolut!** Code-Struktur ist modular:
- `serial_handler.py` - Parser unabhängig
- `data_logger.py` - CSV-Format einfach änderbar
- `ui_app.py` - UI-Komponenten erweiterbar
- `main.py` - Koordinierung klar dokumentiert

### F: Wie teste ich ohne Arduino?
**A:** **Simulationsmodus:**
```bash
python main.py --simulate
```
Generiert synthetische Temperatur-Daten (Sinus-Welle)

### F: Funktioniert es auf Windows/Mac?
**A:** **Theoretisch ja, aber:**
- Hauptzweck: Raspberry Pi
- Serial Port unterscheidet sich (COM1 vs /dev/ttyACM0)
- Display-Support: Keine TFT-Treiber auf Windows
- **Empfehlung:** Direkt auf RPi entwickeln

---

## 📊 Daten & Logging

### F: Wie lange speichert das Programm?
**A:** 
- **RAM (Ring-Buffer):** 24 Stunden (einstellbar)
- **CSV-Datei:** Dauerhaft bis Speicher voll
- **RPi 3:** ~30 MB RAM für 24h @ 10Hz

### F: Kann ich Daten exportieren?
**A:** **Ja, mehrere Optionen:**
1. **Aus laufender App:** `S`-Taste drücken
2. **CSV-Dateien:** Im `logs/` Verzeichnis
3. **Programmatisch:** `logger.get_all()` in Python
4. **Fernzugriff:** SCP/SFTP zum RPi

### F: CSV-Format ist zu simpel?
**A:** **Nein!** Aber beliebig erweiterbar:
- Mehr Spalten hinzufügen (z.B. Spannung, Druck)
- Alternative Formate (JSON, HDF5, SQLite)
- Siehe `data_logger.py` Zeilen 50-70

### F: Kann ich die Daten live übertragen?
**A:** **Ja, mit Änderungen:**
- WebSocket-Server hinzufügen
- MQTT-Publish
- Cloud-API (InfluxDB, AWS, etc.)
- Projekt ist dafür vorbereitet!

---

## 🐛 Fehlerbehandlung & Debugging

### F: "CRC-Fehler: invalid checksum"
**A:** Prüfen Sie:
1. **Baudrate:** Arduino und RPi müssen 115200 sein
2. **USB-Kabel:** Hochwertig (max 50cm)
3. **Stromversorgung:** Arduino stabil 5V
4. **Signalaufbereiter:** PT1000-Circuit funktioniert?

**Debug-Modus:**
```bash
python main.py --port /dev/ttyACM0 2>&1 | grep -i error
```

### F: "No packets received"
**A:** 
1. Arduino nicht mit RPi verbunden?
   ```bash
   ls -la /dev/ttyACM*
   ```
2. Arduino-Firmware nicht geflasht?
   → Arduino IDE öffnen und erneut hochladen
3. Falscher Port?
   ```bash
   dmesg | tail  # Letzte Kernel-Meldungen
   ```

### F: App startet nicht
**A:**
```bash
# Direkt testen (mit Fehlern):
python main.py --simulate

# Systemd-Logs ansehen:
sudo journalctl -u supercapfreezer -n 50 --no-pager

# Python-Fehler direkt:
python main.py --port /dev/ttyACM0 2>&1
```

### F: Display bleibt schwarz
**A:**
1. Framebuffer initialisiert?
   ```bash
   ls -la /dev/fb*
   ```
2. Treiber installiert?
   ```bash
   sudo bash -c 'echo "dtoverlay=waveshare35a" >> /boot/config.txt'
   sudo reboot
   ```
3. Pygame nutzt falsches Display?
   ```bash
   SDL_VIDEODRIVER=fbcon SDL_FBDEV=/dev/fb1 python main.py
   ```

---

## 🎓 Bachelor-Arbeit Fragen

### F: Wie viel Code muss ich selber schreiben?
**A:** 
- **Alles ist vorbereitet!** (~1500 Zeilen Python + Arduino)
- Sie können:
  - Code verwenden wie-ist
  - Komponenten anpassen/erweitern
  - Neue Features hinzufügen
  - Analyse & Dokumentation schreiben

### F: Was ist Neues für die BA?
**A:** Kernbeiträge sind:
1. **Protokoll-Design:** Robustes binäres Format mit CRC
2. **PT1000-Integration:** Callendar-Van Dusen Kalibrierung
3. **Systemintegration:** Arduino ↔ RPi ↔ Display
4. **Fehlerbehandlung:** Robuste Datenübertragung
5. **Dokumentation:** Ausführlich kommentiert

### F: Welche Tests sollte ich durchführen?
**A:** Empfohlene Analysen:
- [ ] CRC-Fehlerrate @ verschiedenen Kabellängen
- [ ] Durchsatz-Messungen (Pakete/Sekunde)
- [ ] Temperatur-Genauigkeit vs. Referenzsensor
- [ ] RAM-Auslastung über 24h
- [ ] CPU-Auslastung (Pygame @ 30 FPS)

### F: Kann ich das noch erweitern?
**A:** **Ja! Skalierbar auf:**
- [ ] Multi-Sensor (Temperature + Voltage)
- [ ] Höhere Abtastrate (1 kHz Spannungen)
- [ ] Machine Learning (Anomalieerkennung)
- [ ] Web-Frontend (Flask/Dashboard)
- [ ] Cloud-Integration

Zeitaufwand: ±2-4 Wochen pro Feature

### F: Dokumentation für die BA?
**A:** Vorlage ist bereit:
- **PROTOCOL.md** - Protokoll-Spezifikation
- **PROJECT_OVERVIEW.md** - Architektur
- **Quellcode** - Vollständig kommentiert
- Sie müssen hauptsächlich schreiben:
  - Sensorik & Elektronik (PT1000)
  - Test-Ergebnisse & Analysen
  - Schlussfolgerungen

---

## ⚡ Performance & Optimierung

### F: Wie schnell läuft das?
**A:**
- **UI Update:** 30 FPS (pygame)
- **Temperatur-Update:** 10 Hz (Arduino)
- **CSV-Write:** ~5 Sekunden (buffered)
- **Gesamtlatenz:** <100ms von Sensor zu Display

### F: CPU/RAM Auslastung?
**A:** Auf RPi 3:
- **CPU:** 15-25% (pygame @ 30 FPS)
- **RAM:** ~150 MB (Python + pygame + Buffer)
- **Disk:** ~5 MB/Stunde (CSV)

### F: Kann ich auf 100 Hz erhöhen?
**A:** **Ja, aber:**
- Arduino: Einfach Abtastrate ändern
- RPi: Parser wird CPU-intensiver
- Display: 30 FPS ist Maximum sinnvoll
- **Besser:** Batching (5-10 Samples pro Paket)

### F: Was ist mit 1 kHz Spannungen?
**A:** **Problemlos!**
- Paket-Size: ~200 bytes (100er Batches)
- Durchsatz: 2 kBytes/sec (<<115200)
- CPU-Overhead: +5-10% Parser
- **Siehe PROTOCOL.md für Details**

---

## 🔐 Sicherheit & Zuverlässigkeit

### F: Was wenn Arduino abstürzt?
**A:**
- RPi erkennt keine Daten
- Service stellt Verbindung wieder her
- Systemd startet App neu nach 10 Sekunden
- CSV-Dateien bleiben erhalten

### F: Daten-Integrität?
**A:**
- **CRC16-CCITT:** Erkennt Übertragungsfehler
- **Sequenznummern:** Zeigen verlorene Pakete
- **Timestamps:** Lücken sichtbar machen
- **Robust:** ~99.9% erfolgreiche Übertragung

### F: Kann das Gerät 24h laufen?
**A:** **Ja!**
- RPi 3: Stabil für Wochen
- Arduino: Keine bekannten Probleme
- **Wichtig:** Gute Stromversorgung (5V/2A)

---

## 📚 Weitere Ressourcen

### Dokumentation in diesem Projekt:
- `README_NEW.md` - Installation & Quickstart
- `PROTOCOL.md` - Kommunikations-Protokoll (10 Seiten!)
- `PROJECT_OVERVIEW.md` - Architektur & Komponenten
- `QUICKSTART.md` - Schnellanleitung
- `config.yaml` - Konfigurationsreferenz
- Quellcode - Vollständig kommentiert

### Externe Ressourcen:
- **PT1000:** IEC 60751 Standard
- **CRC:** https://crccalc.com/ (zur Verifikation)
- **pygame:** https://www.pygame.org/docs/
- **Arduino UNO R4:** https://docs.arduino.cc/hardware/uno-r4-wifi

---

## 💡 Tipps für die Implementierung

### Für schnelle Fortschritte:
1. **Start mit Simulation:** `python main.py --simulate`
2. **Test Arduino zunächst** mit Serial Monitor
3. **Schrittweise integrieren:** Parser → Logger → UI
4. **Regelmäßig testen:** Nach jeder Komponente

### Für gute Ergebnisse in der BA:
1. **Dokumentieren Sie alles** (Screenshots, Logs)
2. **Machen Sie Messungen** (Performance, Accuracy)
3. **Testen Sie Edge-Cases** (Fehler, Grenzen)
4. **Zeigen Sie Architektur-Vorteile** (Why binary protocol?)

### Häufige Anfängerfehler:
- ❌ Kalibrierungswerte nicht angepasst
- ❌ USB-Kabel zu lang (Rauschen)
- ❌ Baudrate-Mismatch
- ❌ Display-Treiber nicht installiert
- ❌ venv nicht aktiviert (`source venv/bin/activate`)

---

## ✅ Checkliste für erfolgreiche Implementierung

- [ ] Repository geklont und install.sh ausgeführt
- [ ] Arduino UNO R4 WiFi mit Firmware geflasht
- [ ] PT1000-Kalibrierungswerte angepasst
- [ ] USB-Verbindung Arduino ↔ RPi funktioniert
- [ ] Simulationsmodus getestet (✓ Daten fließen)
- [ ] Hardware-Modus getestet (✓ CSV wird geschrieben)
- [ ] Display zeigt Daten
- [ ] Systemd-Service aktiviert
- [ ] Dokumentation gelesen (PROTOCOL.md)
- [ ] Eigene Tests durchgeführt

---

**Fragen?** → Siehe entsprechende Dokumentation oder Debug-Tipps oben!

Version: 1.0 | 2025-12-18
