# Programmuebersicht: SUPERCAPFREEZER

## 1. Zielsetzung und Einordnung
SUPERCAPFREEZER ist eine headless Laufzeitanwendung fuer einen Raspberry Pi zur Erfassung, Verarbeitung und Protokollierung von Telemetriedaten eines externen STM32-Systems. Darueber hinaus implementiert das Programm eine ereignisgetriebene Steuerlogik, mit der auf Basis gemessener Temperaturen automatisiert Testkommandos ausgeloest werden koennen.

Die Anwendung adressiert damit drei Kernaufgaben:
1. Zuverlaessige serielle Datenaufnahme vom STM32.
2. Steuerung experimenteller Ablaeufe durch definierte Triggerbedingungen.
3. Nachvollziehbare Datenspeicherung als CSV fuer spaetere Auswertung.

## 2. Gesamtarchitektur
Die Software ist modular aufgebaut und trennt Konfiguration, Kommunikation, Laufzeitsteuerung und Persistenz.

- Konfigurationsschicht: Laden und Zusammenfuehren von Standard- und Nutzerparametern.
- Kommunikationsschicht: Serielle Ein- und Ausgabe fuer STM32 sowie optionales Arduino-Forwarding.
- Steuerungsschicht: Laufzeitlogik fuer Trigger, Kommandoversand und Bedienung.
- Persistenzschicht: Gepufferte CSV-Protokollierung von Telemetrie, ACKs und Ereignissen.

## 3. Modulstruktur und Verantwortlichkeiten
### 3.1 Laufzeit-Orchestrierung (main.py)
Datei: main.py

Hauptaufgaben:
- Einlesen von CLI-Argumenten und Konfigurationsdatei.
- Initialisierung von Logger, STM32-Controller und optionalem Arduino-Sender.
- Verarbeitung eingehender Datenpakete ueber Callback-Mechanismus.
- Umsetzung der Triggerlogik (Temperatur oberhalb/unterhalb eines Schwellwertes).
- Start eines periodischen Flush-Threads zur Dateischreibung.
- Optionaler Runtime-Kommandoeingang ueber STDIN.

### 3.2 Serielle Kommunikation und Parsing (serial_handler.py)
Datei: serial_handler.py

Hauptaufgaben:
- Parsen textbasierter STM32-Zeilen in strukturierte Pakete.
- Unterscheidung zwischen Telemetriepaketen und ACK-Nachrichten.
- Senden standardisierter Kommandos im Format CMD: <BEFEHL>.
- Threadbasierter Empfangsloop mit optionalem Simulationsmodus.
- Separater Sender fuer Temperatur- und Sollwertuebertragung an ein Arduino-System.

### 3.3 Datenerfassung und CSV-Protokollierung (data_logger.py)
Datei: data_logger.py

Hauptaufgaben:
- Anlage zeitgestempelter CSV-Logdateien pro Lauf.
- In-Memory-Pufferung von Datensaetzen (Ringpuffer via deque).
- Entkoppelte, periodische Persistierung ueber Pending-Queue.
- Verwaltung von Telemetrie-, ACK- und Event-Eintraegen.
- Bereitstellung einfacher Laufzeitstatistiken (z. B. Temperaturmittelwert).

### 3.4 Konfigurationsmanagement (config_loader.py)
Datei: config_loader.py

Hauptaufgaben:
- Bereitstellung eines vollstaendigen Default-Konfigurationssatzes.
- Rekursives Mergen von config.yaml in die Standardwerte.
- Robustes Fallback-Verhalten bei fehlender oder fehlerhafter YAML-Datei.

## 4. Datenfluss und Steuerungsablauf
1. Beim Start werden CLI-Parameter und config.yaml zusammengefuehrt.
2. Der STM32-Controller liest serielle Daten kontinuierlich ein.
3. Jede gueltige Zeile wird geparst und als Paket (ACK oder Telemetrie) bereitgestellt.
4. Telemetriepakete werden:
   - in den Logger uebernommen,
   - auf der Konsole ausgegeben,
   - optional als Temperaturwert an Arduino weitergeleitet.
5. Bei erfuellter Triggerbedingung wird ein Kommando (z. B. CMD: CHARGE) an den STM32 gesendet.
6. ACK-Nachrichten und Laufzeitereignisse werden ebenfalls protokolliert.
7. Ein Hintergrundthread schreibt gepufferte Datensaetze periodisch in CSV-Dateien.

## 5. Kommunikationsschnittstellen
### 5.1 Eingehende STM32-Telemetrie (Beispiel)
T:43440, V:0, I:6 mA, STATE:1, Temp: -1.2 C

### 5.2 Eingehende ACK-Nachricht (Beispiel)
ACK: CMD: CHARGE

### 5.3 Ausgehendes Steuerkommando
CMD: CHARGE

### 5.4 Optionale Arduino-Weiterleitung
- Temperatur-Istwert: TEMP:<wert>
- Sollwertsetzung: SET:<wert>

## 6. Konfigurierbare Parameter (Auszug)
Quelle: config.yaml

- serial.port, serial.baud
- arduino_temp.enabled, arduino_temp.port, arduino_temp.baud
- arduino_temp.decimals, arduino_temp.send_interval_s
- trigger.temperature_celsius, trigger.direction, trigger.command, trigger.once
- logging.directory, logging.retention_hours, logging.flush_interval_s

## 7. Nebenlaeufigkeit und Robustheit
- Serielle Kommunikation laeuft in eigenem Thread.
- CSV-Flush laeuft in eigenem Hintergrundthread.
- Laufzeitkommandos (optional) laufen in separatem Eingabethread.
- Bei nicht verfuegbarer serieller Schnittstelle ist ein Simulationsmodus vorhanden.
- Fehler in Einzelnachrichten beeinflussen den Gesamtlauf nur lokal (defensives Parsing).

## 8. Wissenschaftliche Verwertbarkeit
Fuer eine wissenschaftliche Arbeit bietet die Implementierung folgende Vorteile:
- Reproduzierbarkeit durch explizite Konfigurationsdatei und CLI-Parameter.
- Nachvollziehbarkeit durch strukturierte, zeitgestempelte CSV-Logs.
- Trennschaerfe zwischen Messwerterfassung, Steuerlogik und Persistenz.
- Erweiterbarkeit durch klar abgegrenzte Module und dokumentierte Nachrichtenformate.

## 9. Einschraenkungen und Annahmen
- Das Datenformat ist textbasiert und setzt ein konsistentes STM32-Ausgabeformat voraus.
- Harte Echtzeitanforderungen werden nicht adressiert (Python-Threading, User-Space).
- Die Triggerlogik ist ereignisorientiert und standardmaessig als One-Shot ausgelegt.

## 10. Kurzfazit
SUPERCAPFREEZER realisiert eine modulare und praxisorientierte Mess- und Steuerpipeline fuer temperaturabhaengige Versuchsablaeufe. Durch die Kombination aus serieller Telemetrieaufnahme, regelbasierter Kommandosteuerung und persistenter Protokollierung eignet sich das System als belastbare Softwarebasis fuer experimentelle Untersuchungen und deren wissenschaftliche Dokumentation.
