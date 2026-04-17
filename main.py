"""Headless Pi app for STM32 telemetry logging and command triggering."""

from __future__ import annotations

import argparse
import threading
import time

from config_loader import load_config
from data_logger import DataLogger
from serial_handler import STM32Controller, ArduinoTemperatureSender


g_logger = None
g_controller = None
g_arduino_sender = None
g_arduino_decimals = 2
g_arduino_send_interval_s = 0.5
g_arduino_last_send_ts = 0.0
g_trigger_temp = None
g_trigger_direction = "below"
g_trigger_command = "CHARGE"
g_trigger_once = True
g_triggered = False


def _should_trigger(temp_c: float) -> bool:
    if g_trigger_temp is None:
        return False
    if g_trigger_direction == "above":
        return temp_c >= g_trigger_temp
    return temp_c <= g_trigger_temp

def on_stm32_status(packet: dict) -> None:
    """Process telemetry and ACK messages from STM32."""
    global g_logger, g_controller, g_arduino_sender, g_arduino_decimals
    global g_arduino_send_interval_s, g_arduino_last_send_ts, g_triggered

    packet_type = packet.get("type")

    if packet_type == "ack":
        ack_text = str(packet.get("ack", "ACK"))
        if g_logger:
            g_logger.push_ack(ack_text)
        print(f"[ACK] {ack_text}")
        return

    if packet_type != "telemetry":
        return

    timestamp_raw = packet.get("T")
    voltage = packet.get("V")
    current_ma = packet.get("I_mA")
    state = packet.get("STATE")
    temp_c = packet.get("Temp_C")

    if temp_c is None:
        return

    if g_logger:
        g_logger.push_telemetry(
            t_raw=timestamp_raw,
            voltage=voltage,
            current_ma=current_ma,
            state=state,
            temp_c=float(temp_c),
            raw_message=str(packet.get("raw", "")),
        )

    voltage_text = f"{float(voltage):.3f}" if voltage is not None else "--"
    current_text = f"{float(current_ma):.2f}" if current_ma is not None else "--"

    print(
        "[LIVE] "
        f"T:{timestamp_raw if timestamp_raw is not None else '--'} "
        f"V:{voltage_text} "
        f"I:{current_text}mA "
        f"STATE:{state if state is not None else '--'} "
        f"Temp:{float(temp_c):.2f}C"
    )

    # Forward measured temperature at a controlled interval to avoid serial spam.
    if g_arduino_sender:
        now = time.monotonic()
        if (
            g_arduino_send_interval_s <= 0.0
            or (now - g_arduino_last_send_ts) >= g_arduino_send_interval_s
        ):
            if g_arduino_sender.send_temperature(float(temp_c), decimals=g_arduino_decimals):
                g_arduino_last_send_ts = now

    if g_trigger_once and g_triggered:
        return

    if _should_trigger(float(temp_c)) and g_controller:
        if g_controller.send_command(g_trigger_command):
            g_triggered = True
            trigger_text = (
                f"AUTO TRIGGER: Temp={float(temp_c):.2f}C "
                f"({g_trigger_direction} {g_trigger_temp:.2f}C) -> CMD: {g_trigger_command}"
            )
            print(f"[TRIGGER] {trigger_text}")
            if g_logger:
                g_logger.push_event(trigger_text)


def main() -> None:
    global g_logger, g_controller, g_arduino_sender, g_arduino_decimals
    global g_arduino_send_interval_s, g_arduino_last_send_ts
    global g_trigger_temp, g_trigger_direction, g_trigger_command, g_trigger_once

    parser = argparse.ArgumentParser(description="SUPERCAPFREEZER STM32 logger/controller")

    parser.add_argument("--port", dest="port", default=None, help="STM32 serial port")
    parser.add_argument("--baud", type=int, default=None, help="Serial baud")
    parser.add_argument("--simulate", action="store_true", help="Simulate temperature input")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")

    parser.add_argument(
        "--trigger-temp",
        type=float,
        default=None,
        help="Automatically send test command when temperature threshold is met",
    )
    parser.add_argument(
        "--trigger-direction",
        choices=["below", "above"],
        default=None,
        help="Trigger when temperature goes below/above threshold",
    )
    parser.add_argument(
        "--command",
        default=None,
        help="Command name for test start (sent as CMD: <command>)",
    )
    parser.add_argument(
        "--start-test",
        action="store_true",
        help="Send CMD: CHARGE immediately on startup",
    )
    parser.add_argument(
        "--allow-retrigger",
        action="store_true",
        help="Allow repeated auto-triggers instead of one-shot behavior",
    )

    args = parser.parse_args()

    cfg = load_config(args.config)

    baud = args.baud if args.baud is not None else int(cfg.get("serial", {}).get("baud", 115200))
    port = args.port if args.port else cfg.get("serial", {}).get("port")
    trigger_cfg = cfg.get("trigger", {})
    g_trigger_temp = args.trigger_temp if args.trigger_temp is not None else trigger_cfg.get("temperature_celsius")
    if g_trigger_temp is not None:
        g_trigger_temp = float(g_trigger_temp)

    g_trigger_direction = (
        args.trigger_direction
        if args.trigger_direction is not None
        else str(trigger_cfg.get("direction", "below")).lower()
    )
    if g_trigger_direction not in {"below", "above"}:
        g_trigger_direction = "below"

    g_trigger_command = (
        args.command if args.command is not None else str(trigger_cfg.get("command", "CHARGE"))
    ).strip().upper()

    g_trigger_once = not args.allow_retrigger
    if "once" in trigger_cfg and not args.allow_retrigger:
        g_trigger_once = bool(trigger_cfg.get("once", True))

    log_dir = cfg.get("logging", {}).get("directory", "./logs")
    max_hours = int(cfg.get("logging", {}).get("retention_hours", 24))
    flush_interval = float(cfg.get("logging", {}).get("flush_interval_s", 1.0))

    arduino_cfg = cfg.get("arduino_temp", {})
    arduino_enabled = bool(arduino_cfg.get("enabled", True))
    arduino_port = arduino_cfg.get("port", "/dev/ttyUSB0")
    arduino_baud = int(arduino_cfg.get("baud", 9600))
    g_arduino_decimals = int(arduino_cfg.get("decimals", 2))
    g_arduino_send_interval_s = float(arduino_cfg.get("send_interval_s", 0.5))
    g_arduino_last_send_ts = 0.0

    print("=" * 60)
    print("SUPERCAPFREEZER - STM32 Telemetry Logger")
    print("=" * 60)
    print(f"Port: {port if port else ('<auto>' if not args.simulate else 'Simulation')}")
    print(f"Baud: {baud}")
    print(f"Auto trigger temp: {g_trigger_temp if g_trigger_temp is not None else 'disabled'}")
    print(f"Auto trigger direction: {g_trigger_direction}")
    print(f"Trigger command: CMD: {g_trigger_command}")
    print(f"Trigger mode: {'one-shot' if g_trigger_once else 'retrigger'}")
    print(
        f"Arduino temp forward: {'enabled' if arduino_enabled else 'disabled'}"
        f" ({arduino_port if arduino_port else 'no port'} @ {arduino_baud}, "
        f"every {g_arduino_send_interval_s:.2f}s)"
    )
    print("=" * 60)

    g_logger = DataLogger(log_dir=log_dir, max_hours=max_hours)

    g_controller = STM32Controller(
        port=port,
        baud=baud,
        on_status=on_stm32_status,
        simulate=args.simulate,
    )
    g_controller.start()

    if arduino_enabled:
        g_arduino_sender = ArduinoTemperatureSender(port=arduino_port, baud=arduino_baud)
        g_arduino_sender.start()

    time.sleep(1.0)
    if args.start_test:
        if g_controller.send_command("CHARGE"):
            print("[MAIN] Startup test command sent: CMD: CHARGE")
            if g_logger:
                g_logger.push_event("Startup command sent: CMD: CHARGE")

    def flush_loop() -> None:
        while True:
            if g_logger:
                g_logger.flush_to_csv()
            time.sleep(flush_interval)

    threading.Thread(target=flush_loop, daemon=True).start()

    print("[MAIN] Running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(0.25)
    except KeyboardInterrupt:
        print("\n[MAIN] Interrupted by user")
    finally:
        print("[MAIN] Shutting down...")
        if g_controller:
            g_controller.stop()
        if g_arduino_sender:
            g_arduino_sender.stop()
        if g_logger:
            g_logger.close()
        print("[MAIN] Goodbye!")


if __name__ == "__main__":
    main()
