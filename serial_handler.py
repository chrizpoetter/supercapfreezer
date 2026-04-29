"""Serial handler for STM32 text telemetry and command ACK messages."""

from __future__ import annotations

import threading
import time
import re
import math
from typing import Callable, Optional


def _extract_number(value: str) -> Optional[float]:
    match = re.search(r"[-+]?\d*\.?\d+", value)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_status_line(line: str) -> Optional[dict]:
    """Parse one STM32 line or ACK message."""
    if not line or line.startswith("#"):
        return None

    text = line.strip()
    if not text:
        return None

    if text.upper().startswith("ACK"):
        return {
            "type": "ack",
            "ack": text,
            "raw": text,
        }

    parts = [part.strip() for part in text.split(",") if part.strip()]
    data = {}

    for part in parts:
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        data[key.strip().upper()] = value.strip()

    if not data:
        return None

    # Expected telemetry line example:
    # T:43440, V:0, I:6 mA, STATE:1, Temp: -1.2 C
    t_raw = _extract_number(data.get("T", ""))
    voltage = _extract_number(data.get("V", ""))
    current_ma = _extract_number(data.get("I", ""))
    state = _extract_number(data.get("STATE", ""))
    temp_c = _extract_number(data.get("TEMP", ""))

    if temp_c is None and "TEMPERATURE" in data:
        temp_c = _extract_number(data.get("TEMPERATURE", ""))

    if temp_c is None:
        return None

    return {
        "type": "telemetry",
        "T": int(t_raw) if t_raw is not None else None,
        "V": float(voltage) if voltage is not None else None,
        "I_mA": float(current_ma) if current_ma is not None else None,
        "STATE": int(state) if state is not None else None,
        "Temp_C": float(temp_c),
        "raw": text,
    }


class STM32Controller:
    """Small threaded serial client for STM32 telemetry and command channel."""

    def __init__(
        self,
        port: Optional[str],
        baud: int = 115200,
        on_status: Optional[Callable[[dict], None]] = None,
        simulate: bool = False,
    ):
        self.port = port
        self.baud = baud
        self.on_status = on_status
        self.simulate = simulate

        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._serial = None
        self._line_buffer = ""

        self.connected = False

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass

    def send_command(self, command: str) -> bool:
        return self._send_line(f"CMD: {command.strip().upper()}")

    def _send_line(self, line: str) -> bool:
        if not self._serial or not self._serial.is_open:
            return False
        try:
            self._serial.write((line + "\n").encode("utf-8"))
            self._serial.flush()
            return True
        except Exception as exc:
            print(f"[SERIAL] Send failed: {exc}")
            return False

    def _run(self) -> None:
        if self.simulate:
            self.connected = True
            self._run_simulated_status()
            return

        port = self.port or self._auto_detect_port()
        if not port:
            print("[SERIAL] No serial port found. STM32 input disabled.")
            return

        try:
            import serial

            self._serial = serial.Serial(port, self.baud, timeout=0.1)
            self.connected = True
            print(f"[SERIAL] Connected to {port} @ {self.baud}")

            while not self._stop.is_set():
                data = self._serial.read(self._serial.in_waiting or 1)
                if not data:
                    continue

                chunk = data.decode("utf-8", errors="ignore")
                self._line_buffer += chunk

                while "\n" in self._line_buffer:
                    line, self._line_buffer = self._line_buffer.split("\n", 1)
                    parsed = parse_status_line(line.strip())
                    if parsed and self.on_status:
                        self.on_status(parsed)

        except Exception as exc:
            print(f"[SERIAL] Read loop failed: {exc}")
            self.connected = False

    def _run_simulated_status(self) -> None:
        """Emit fake STM32 telemetry lines when no hardware is connected."""
        import math

        t = 0
        while not self._stop.is_set():
            sim_time = t / 10.0
            temp = -1.2 + 1.0 * math.sin(sim_time)
            current_ma = 6.0 + 2.0 * math.sin(sim_time * 0.5)
            state = 1 if sim_time % 30.0 < 10.0 else 0
            if self.on_status:
                self.on_status(
                    {
                        "type": "telemetry",
                        "T": 43440 + t,
                        "V": 0.0,
                        "I_mA": current_ma,
                        "STATE": state,
                        "Temp_C": temp,
                        "raw": f"T:{43440 + t}, V:0, I:{current_ma:.1f} mA, STATE:{state}, Temp: {temp:.2f} C",
                    }
                )
            t += 1
            time.sleep(0.2)

    @staticmethod
    def _auto_detect_port() -> Optional[str]:
        try:
            from serial.tools import list_ports
        except Exception:
            return None

        ports = list(list_ports.comports())
        if not ports:
            return None

        for port in ports:
            desc = (port.description or "").lower()
            if "stm" in desc or "arduino" in desc or "uno" in desc or "r4" in desc:
                return port.device

        for port in ports:
            if port.device.startswith("/dev/ttyACM") or port.device.startswith("/dev/ttyUSB"):
                return port.device

        return ports[0].device


class ArduinoTemperatureSender:
    """Simple serial sender for forwarding TEMP messages to Arduino."""

    def __init__(
        self,
        port: Optional[str],
        baud: int = 9600,
        on_line: Optional[Callable[[str], None]] = None,
    ):
        self.port = port
        self.baud = baud
        self.on_line = on_line
        self._serial = None
        self.connected = False
        self._stop = threading.Event()
        self._reader_thread: Optional[threading.Thread] = None
        self._line_buffer = ""

    def start(self) -> bool:
        if not self.port:
            return False

        try:
            import serial

            self._serial = serial.Serial(self.port, self.baud, timeout=0.1)
            self.connected = True
            self._stop.clear()
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._reader_thread.start()
            print(f"[ARDUINO] Connected to {self.port} @ {self.baud}")
            return True
        except Exception as exc:
            print(f"[ARDUINO] Connect failed on {self.port}: {exc}")
            self.connected = False
            self._serial = None
            return False

    def stop(self) -> None:
        self._stop.set()
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None
        self.connected = False

    def send_temperature(self, temp_c: float, decimals: int = 2) -> bool:
        """Send latest measured temperature to Arduino as TEMP:<value>."""
        try:
            temp_value = float(temp_c)
        except (TypeError, ValueError):
            return False

        if not math.isfinite(temp_value):
            return False

        if not self._serial or not self._serial.is_open:
            return False

        precision = max(0, int(decimals))
        try:
            line = f"TEMP:{temp_value:.{precision}f}\n"
            self._serial.write(line.encode("utf-8"))
            self._serial.flush()
            return True
        except Exception as exc:
            print(f"[ARDUINO] Send failed: {exc}")
            return False

    def send_setpoint(self, setpoint_c: float, decimals: int = 2) -> bool:
        """Send target setpoint to Arduino as SET:<value>."""
        try:
            setpoint_value = float(setpoint_c)
        except (TypeError, ValueError):
            return False

        if not math.isfinite(setpoint_value):
            return False

        if not self._serial or not self._serial.is_open:
            return False

        precision = max(0, int(decimals))
        try:
            line = f"SET:{setpoint_value:.{precision}f}\n"
            self._serial.write(line.encode("utf-8"))
            self._serial.flush()
            return True
        except Exception as exc:
            print(f"[ARDUINO] Send failed: {exc}")
            return False

    def _read_loop(self) -> None:
        """Continuously drain Arduino output so device-side serial writes do not block."""
        while not self._stop.is_set():
            ser = self._serial
            if not ser or not ser.is_open:
                break

            try:
                data = ser.read(ser.in_waiting or 1)
            except Exception:
                break

            if not data:
                continue

            chunk = data.decode("utf-8", errors="ignore")
            self._line_buffer += chunk

            while "\n" in self._line_buffer:
                line, self._line_buffer = self._line_buffer.split("\n", 1)
                line = line.strip()
                if line and self.on_line:
                    try:
                        self.on_line(line)
                    except Exception:
                        pass
