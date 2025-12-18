# Raspberry Pi Data Viewer (Starter Template)

Kurz: kleines Starter‑Template zum Empfangen serieller Messdaten (Arduino UNO R4 wifi über USB), Live‑Plot und Anzeige auf einem angeschlossenen Display (3.5" SPI‑TFT).

Eigenschaften
- SerialReader (pyserial) mit Fallback auf Simulationsdaten
- Einfacher Echtzeit‑Plot und Info‑Panel mit `pygame`
- CSV‑Export (Taste `s`)
- Konfigurierbar: `--port`, `--baud`, `--fullscreen`

Installation (auf Raspberry Pi):

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo apt install -y python3-serial
```

Hinweise zur GUI/Display
- Dieses Template verwendet `pygame`, das direkt auf X oder auf dem Linux framebuffer laufen kann.
- Für viele 3.5" SPI‑TFT Module sollte vorher der passende Framebuffer/Treiber installiert werden (z.B. `fbtft`/Device Tree overlays) damit das Display als `/dev/fb1` verfügbar ist.
- Wenn du stattdessen X laufen lassen kannst auf dem Display, kannst du `--fullscreen` nutzen.

Starten

```bash
python main.py --port /dev/ttyACM0 --baud 115200 --fullscreen
```

Wenn kein serieller Port angegeben oder Port nicht verfügbar, läuft das Programm im Simulationsmodus.

Weiteres
- Wenn du ein binäres, sehr kompaktes Paketformat willst (für hohe Datenraten), sag mir kurz, dann ergänze ich Parser/Protokollbeispiele (Header+Payload+CRC).
- Teile mir Modell des 3.5" SPI‑TFT mit, damit ich Hinweise für den Treiber/Framebuffer geben kann.

Empfehlung: effiziente Paketformate für hohe Datenraten
---------------------------------------------------

Kurz: Für maximale Durchsatzleistung sende binäre, gepackte Messwerte in Batches statt ASCII‑Zeilen. Verwende ein einfaches, robustes Framing (zwei Sync‑Bytes oder Längenfeld) plus eine Prüfsumme (CRC16/CRC32). Packe Messwerte als kleine Integer (z.B. int16) oder float32, je nach Genauigkeit.

Wichtige Prinzipien
- Binary statt ASCII: ASCII ist sehr overhead‑intensiv (z. B. "25.123\n" ≈ 7 Bytes). Binär (2–4 Bytes/Wert) spart Bandbreite.
- Batch mehrere Messwerte pro Paket: reduziert Framing-Overhead.
- Verwende Sequenznummern + CRC: detektiere verlorene/vertauschte Pakete.
- Timestamping: sende Basiszeit (uint32 ms) pro Batch + delta pro Sample (optional) für geringe Overhead.
- Wahl der Datentypen: `int16` mit Skalierung (z.B. value*100) ist oft ausreichend und halbiert gegenüber `float32` die Größe.

Beispiel: robustes, kompaktes Paket (empfohlen)

Layout (Little Endian):

- 0x00..0x01: Sync (2 Byte) = 0xAA 0x55
- 0x02: Type (1 Byte) — z.B. 0x01 = Temp Batch
- 0x03: Samples (1 Byte) — Anzahl N (1..255)
- 0x04..0x07: Seq (uint32) — fortlaufende Sequenznummer
- 0x08..0x0B: Timestamp (uint32 ms) — Basiszeit der ersten Probe
- 0x0C..: Payload — N x int16 (Temperatur*100; i16 little-endian)
- ..last-1: CRC16 (2 Byte, z.B. CRC-16-CCITT über Header+Payload)

Beispiel C/C++-Struct (konzeptuell):

struct Packet {
	uint8_t sync[2]; // 0xAA,0x55
	uint8_t type;    // 0x01
	uint8_t samples; // N
	uint32_t seq;
	uint32_t t_ms;
	int16_t samples[N]; // little-endian, temperature*100
	uint16_t crc;
};

Vorteile dieses Formats
- Einfach zu parsen: zuerst Sync prüfen, dann Header lesen, dann genau `N*2` Bytes Payload lesen.
- Batch-Größe flexibel: z.B. N=10..100 je nach Latenz/Throughput‑Tradeoff.
- int16 mit Skalierung ist effizient und genügt meist für Temperaturen.

Beispielrechnung (theoretisch bei 115200 baud)
- 115200 bit/s ≈ 11.52 kByte/s netto (bei 10 bit/Byte framing)
- Mit int16 Samples (2 Byte) ≈ 5760 Samples/s maximal (ohne große Header‑Overheads)
- Mit Batch‑Header z.B. 12 Byte + N*2 payload → Overhead/Probe sinkt mit größerem N.

Weitere Optimierungen
- Verwende größere Batches (z.B. 20–100) wenn Latenz bis zu Batch‑Dauer tolerierbar ist.
- Wenn du sehr hohe Raten brauchst, erwäge komprimierte/packed-formats oder USB Bulk statt virt. COM (falls Hardware/Bootloader das erlaubt).
- Alternativ: sende rohe ADC‑Werte (int16) und mache Kalibrierung am Pi (spart CPU auf Arduino).

Framing-Alternativen
- Länge‑prefix: Ein Start‑Byte + 2‑Byte Length — lesbar und robust.
- COBS / SLIP: verhindert Sync‑Bytes im Payload ohne aufwändige Escaping‑Logik.

Prüfsumme
- CRC16-CCITT ist klein und schnell und genügt meist; für höchste Sicherheit CRC32 verwenden.

Arduino-Hinweis (Pseudo)

```cpp
uint8_t buf[...];
// fülle Header
// memcpy Payload (int16_t scaled samples)
uint16_t crc = crc16(buf, len_without_crc);
buf[len-2] = crc & 0xFF; buf[len-1] = crc >> 8;
Serial.write(buf, len);
```

Raspberry Pi / Python Hinweis

- Lese zuerst 2 Bytes Sync, prüfe, dann Header (next 6..8 Bytes), lies dann `N*2` Bytes Payload, verifiziere CRC.
- Nutze `struct.unpack_from('<h', data, offset)` oder `numpy.frombuffer` zum schnellen Umwandeln in Array.

Beispiel-Python (konzeptuell):

```py
import struct
hdr = ser.read(8) # sync(2)+type(1)+samples(1)+seq(4)
N = hdr[3]
payload = ser.read(N*2 + 6) # samples + timestamp+crc ...
values = struct.unpack('<' + 'h'*N, payload[:N*2])
```

Fallback / sehr low-complexity
- Wenn du maximal einfach starten willst: sende ASCII‑Zeilen mit `\n` als Trenner ("25.12\n"). Das ist einfacher zu debuggen, aber weniger effizient.

Wenn du möchtest, erstelle ich dir:
- Arduino‑Sketch‑Snippet zum Erzeugen solcher Pakete (mit CRC16 + Batch‑Logik)
- Python‑Parser (robust, resynchronisierend, mit CRC‑Prüfung) zum Einlesen auf dem Pi

