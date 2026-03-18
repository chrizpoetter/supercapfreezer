"""
Simple headless Pi app for SUPERCAPFREEZER.

Behavior:
- Connect to Arduino serial.
- Send setpoint: SET:<value>
- Send measured temp from Pi: TEMP:<value>
- Read Arduino status: TEMP:<value> PWM:<value>
- Log status to CSV.
"""

from __future__ import annotations

import argparse
import math
import threading
import time

from config_loader import load_config
from data_logger import DataLogger
from serial_handler import ArduinoPeltier


g_logger = None
g_setpoint = 25.0
g_last_pi_temp = None


def on_arduino_status(packet: dict) -> None:
    """Log Arduino status packets."""
    global g_logger, g_setpoint, g_last_pi_temp

    temp = packet.get("TEMP")
    pwm = packet.get("PWM")

    if temp is None or pwm is None:
        return

    if g_logger:
        g_logger.push_temperature(float(temp), int(pwm), g_setpoint)

    # Live CLI output so current values are visible while running.
    pi_temp_text = f"{g_last_pi_temp:.2f}" if g_last_pi_temp is not None else "--"
    print(
        f"[LIVE] PI_TEMP:{pi_temp_text}C "
        f"ARD_TEMP:{float(temp):.2f}C PWM:{int(pwm):3d} SET:{g_setpoint:.2f}C"
    )


def make_pi_temperature_source(simulate: bool, base_temp: float):
    """Return a function that gives the current Pi temperature input value."""
    if not simulate:
        return lambda now: base_temp

    # Simulation: simple sine around base_temp.
    return lambda now: base_temp + 2.0 * math.sin(now * 0.2)


def main() -> None:
    global g_logger, g_setpoint, g_last_pi_temp

    parser = argparse.ArgumentParser(description="SUPERCAPFREEZER simple ASCII Pi controller")

    # Keep both names so existing service files continue to work.
    parser.add_argument("--port", "--port1", dest="port", default=None, help="Arduino serial port")
    parser.add_argument("--baud", type=int, default=None, help="Serial baud")
    parser.add_argument("--simulate", action="store_true", help="Simulate temperature input")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")

    # Simple runtime knobs.
    parser.add_argument("--setpoint", type=float, default=None, help="Setpoint sent to Arduino")
    parser.add_argument("--pi-temp", type=float, default=None, help="Fixed Pi temperature to send")
    parser.add_argument("--temp-rate", type=float, default=10.0, help="Pi TEMP send rate in Hz")

    # Keep old arg accepted for compatibility; it is not used.
    parser.add_argument("--port2", default=None, help=argparse.SUPPRESS)

    args = parser.parse_args()

    cfg = load_config(args.config)

    baud = args.baud if args.baud is not None else int(cfg.get("serial", {}).get("baud", 115200))
    port = args.port if args.port else cfg.get("serial", {}).get("port")
    g_setpoint = args.setpoint if args.setpoint is not None else float(cfg.get("control", {}).get("default_setpoint", 25.0))

    pi_temp_base = args.pi_temp if args.pi_temp is not None else g_setpoint
    temp_rate_hz = max(1.0, float(args.temp_rate))
    temp_period = 1.0 / temp_rate_hz

    log_dir = cfg.get("logging", {}).get("directory", "./logs")
    max_hours = int(cfg.get("logging", {}).get("retention_hours", 24))
    flush_interval = float(cfg.get("logging", {}).get("flush_interval_s", 1.0))

    print("=" * 60)
    print("SUPERCAPFREEZER - Simple ASCII Controller")
    print("=" * 60)
    print(f"Port: {port if port else ('<auto>' if not args.simulate else 'Simulation')}")
    print(f"Baud: {baud}")
    print(f"Setpoint: {g_setpoint:.2f} C")
    print(f"Pi temp source: {'simulated' if args.simulate else 'fixed'}")
    print("=" * 60)

    g_logger = DataLogger(log_dir=log_dir, max_hours=max_hours)

    arduino = ArduinoPeltier(
        port=port,
        baud=baud,
        on_status=on_arduino_status,
        simulate=args.simulate,
    )
    arduino.start()

    # Give serial a moment to come up, then send setpoint once.
    time.sleep(1.0)
    arduino.send_setpoint(g_setpoint)

    def flush_loop() -> None:
        while True:
            if g_logger:
                g_logger.flush_to_csv()
            time.sleep(flush_interval)

    threading.Thread(target=flush_loop, daemon=True).start()

    pi_temp_fn = make_pi_temperature_source(args.simulate, pi_temp_base)

    print("[MAIN] Running. Press Ctrl+C to stop.")

    try:
        while True:
            now = time.time()
            measured_temp = pi_temp_fn(now)
            g_last_pi_temp = measured_temp
            arduino.send_measured_temp(measured_temp)
            time.sleep(temp_period)
    except KeyboardInterrupt:
        print("\n[MAIN] Interrupted by user")
    finally:
        print("[MAIN] Shutting down...")
        arduino.stop()
        if g_logger:
            g_logger.close()
        print("[MAIN] Goodbye!")


if __name__ == "__main__":
    main()
