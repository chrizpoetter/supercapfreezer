"""
Minimal Arduino serial handler for SUPERCAPFREEZER.

ASCII protocol used:
- Pi -> Arduino: SET:25.0
- Pi -> Arduino: TEMP:23.5
- Arduino -> Pi: TEMP:23.45 PWM:128
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional


def parse_status_line(line: str) -> Optional[dict]:
    """Parse one Arduino status line: TEMP:<float> PWM:<int>."""
    if not line or line.startswith("#"):
        return None

    parts = line.strip().split()
    data = {}

    for part in parts:
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        data[key] = value

    if "TEMP" not in data or "PWM" not in data:
        return None

    try:
        return {
            "TEMP": float(data["TEMP"]),
            "PWM": int(float(data["PWM"])),
        }
    except ValueError:
        return None


class ArduinoPeltier:
    """Small threaded serial client for the Arduino peltier controller."""

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

    def send_setpoint(self, value: float) -> None:
        self._send_line(f"SET:{value:.2f}")

    def send_measured_temp(self, value: float) -> None:
        self._send_line(f"TEMP:{value:.2f}")

    def _send_line(self, line: str) -> None:
        if not self._serial or not self._serial.is_open:
            return
        try:
            self._serial.write((line + "\n").encode("utf-8"))
            self._serial.flush()
        except Exception as exc:
            print(f"[SERIAL] Send failed: {exc}")

    def _run(self) -> None:
        if self.simulate:
            self.connected = True
            self._run_simulated_status()
            return

        port = self.port or self._auto_detect_port()
        if not port:
            print("[SERIAL] No serial port found, switching to simulate mode.")
            self.connected = True
            self._run_simulated_status()
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
            self.connected = True
            self._run_simulated_status()

    def _run_simulated_status(self) -> None:
        """Emit fake TEMP/PWM lines when no hardware is connected."""
        import math

        t = 0.0
        while not self._stop.is_set():
            temp = 25.0 + 2.0 * math.sin(t)
            pwm = int(128 + 40 * math.sin(t * 0.5))
            if self.on_status:
                self.on_status({"TEMP": temp, "PWM": pwm})
            t += 0.1
            time.sleep(0.1)

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
            if "arduino" in desc or "uno" in desc or "r4" in desc:
                return port.device

        for port in ports:
            if port.device.startswith("/dev/ttyACM") or port.device.startswith("/dev/ttyUSB"):
                return port.device

        return ports[0].device
