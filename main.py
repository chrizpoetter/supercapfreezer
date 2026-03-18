"""
SUPERCAPFREEZER Main Application
================================

Integrates:
- ASCII protocol for dual serial (Peltier + Measurement controllers)
- Data logger to CSV (data_logger.py)
- Pygame UI with multiple screens (ui_app.py)

Usage:
    python main.py --port1 /dev/ttyACM0 --port2 /dev/ttyACM1 [--fullscreen]
    python main.py --simulate  # Simulation mode (no hardware needed)
"""

import sys
import argparse
import os
import time
import threading

from serial_handler import PeltierController, MeasurementController
from data_logger import DataLogger
from ui_app import PyGameApp
from config_loader import load_config

# Global instances
g_logger = None
g_peltier = None
g_measurement = None
g_setpoint = 25.0  # Default temperature setpoint


def on_temperature_packet(packet: dict):
    """
    Callback when temperature data is received from Peltier controller.
    Expected format: {'TEMP': 23.45, 'PWM': 128}
    """
    global g_logger, g_setpoint
    
    if 'TEMP' in packet and 'PWM' in packet:
        temp = packet['TEMP']
        pwm = int(packet['PWM'])
        
        # Log to CSV
        if g_logger:
            g_logger.push_temperature(temp, pwm, g_setpoint)


def on_measurement_packet(packet: dict):
    """
    Callback when measurement data is received from measurement controller.
    Expected format: {'MEAS': None, 'V1': 12.34, 'V2': 5.67, 'I1': 0.123, 'I2': 0.456, 'STATE': 'CHARGE'}
    """
    global g_logger
    
    if 'V1' in packet and 'I1' in packet:
        v1 = packet.get('V1', 0.0)
        v2 = packet.get('V2', 0.0)
        i1 = packet.get('I1', 0.0)
        i2 = packet.get('I2', 0.0)
        state = packet.get('STATE', 'IDLE')
        
        # Log to CSV
        if g_logger:
            g_logger.push_measurement(v1, v2, i1, i2, state)


def main():
    global g_logger, g_peltier, g_measurement, g_setpoint
    
    parser = argparse.ArgumentParser(
        description="SUPERCAPFREEZER: Dual microcontroller controller for Raspberry Pi"
    )
    parser.add_argument('--port1', help='Peltier controller port (e.g., /dev/ttyACM0)', default=None)
    parser.add_argument('--port2', help='Measurement controller port (e.g., /dev/ttyACM1)', default=None)
    parser.add_argument('--baud', type=int, default=None, help='Baud rate')
    parser.add_argument('--fullscreen', action='store_true', help='Fullscreen mode')
    parser.add_argument('--simulate', action='store_true', help='Simulate data (no hardware)')
    parser.add_argument('--config', default='config.yaml', help='Path to config.yaml')
    
    args = parser.parse_args()
    
    # Load configuration and merge CLI overrides
    cfg = load_config(args.config)
    baud = args.baud if args.baud else int(cfg["serial"]["baud"])
    port1 = args.port1 if args.port1 else cfg["serial"].get("port")
    port2 = args.port2 if args.port2 else cfg.get("measurement", {}).get("port")
    fullscreen = bool(args.fullscreen or cfg["display"].get("fullscreen", False))
    g_setpoint = float(cfg.get("control", {}).get("default_setpoint", 25.0))

    print("=" * 60)
    print("SUPERCAPFREEZER - Dual Controller System")
    print("=" * 60)
    print(f"Peltier Port: {port1 if port1 else ('<auto>' if not args.simulate else 'Simulation')}")
    print(f"Measurement Port: {port2 if port2 else ('<auto>' if not args.simulate else 'Simulation')}")
    print(f"Baud: {baud}")
    print(f"Setpoint: {g_setpoint}°C")
    print("=" * 60)
    
    # Initialize logger
    log_dir = cfg["logging"].get("directory", "./logs")
    max_hours = int(cfg["logging"].get("retention_hours", 24))
    g_logger = DataLogger(log_dir=log_dir, max_hours=max_hours)
    
    # Initialize Peltier controller
    g_peltier = PeltierController(
        port=port1,
        baud=baud,
        callback=on_temperature_packet,
        simulate=args.simulate
    )
    g_peltier.start()
    
    # Initialize Measurement controller
    g_measurement = MeasurementController(
        port=port2,
        baud=baud,
        callback=on_measurement_packet,
        simulate=args.simulate
    )
    g_measurement.start()
    
    # Set initial temperature setpoint
    time.sleep(1)  # Wait for connection
    g_peltier.set_temperature(g_setpoint)
    
    # Start CSV flusher thread (write to disk every second)
    def csv_flusher():
        while True:
            if g_logger:
                g_logger.flush_to_csv()
            time.sleep(1)
    
    flush_thread = threading.Thread(target=csv_flusher, daemon=True)
    flush_thread.start()
    
    # Initialize UI
    ui_app = PyGameApp(port=port1, baud=baud, fullscreen=fullscreen)
    ui_app.set_peltier(g_peltier)
    ui_app.set_measurement(g_measurement)
    ui_app.set_logger(g_logger)
    
    try:
        # Run UI
        ui_app.run()
    except KeyboardInterrupt:
        print("\n[MAIN] Interrupted by user")
    except Exception as e:
        print(f"[MAIN ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("[MAIN] Shutting down...")
        g_peltier.stop()
        g_measurement.stop()
        g_logger.close()
        print("[MAIN] Goodbye!")
        reader.stop()
        g_logger.close()
        ui_app.stop()
        print("[MAIN] Done")


if __name__ == '__main__':
    g_logger = None
    main()