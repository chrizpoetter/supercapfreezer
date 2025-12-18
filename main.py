#!/usr/bin/env python3
"""
SUPERCAPFREEZER Main Application
================================

Integrates:
- Binary protocol parser (serial_handler.py)
- Data logger to CSV (data_logger.py)
- Pygame UI with multiple screens (ui_app.py)

Usage:
    python main.py --port /dev/ttyACM0 --baud 115200 [--fullscreen]
    python main.py                          # Simulate mode (no hardware needed)
"""

import sys
import argparse
import os
import time

from serial_handler import SerialReaderThread
from data_logger import DataLogger
from ui_app import PyGameApp
from config_loader import load_config

def on_packet_received(packet: dict):
    """
    Callback when a complete packet is received from Arduino.
    Extracts temperature and logs it.
    """
    if packet['type'] == 0x01:  # Temperature packet
        temp = packet['values']
        timestamp_ms = packet['timestamp_ms']
        seq_num = packet['seq_num']
        
        # Log to CSV
        global g_logger
        if g_logger:
            g_logger.push(timestamp_ms, temp, seq_num)


def main():
    parser = argparse.ArgumentParser(
        description="SUPERCAPFREEZER: Real-time temperature monitoring for Raspberry Pi"
    )
    parser.add_argument('--port', help='Serial port (e.g., /dev/ttyACM0)', default=None)
    parser.add_argument('--baud', type=int, default=None, help='Baud rate')
    parser.add_argument('--fullscreen', action='store_true', help='Fullscreen mode')
    parser.add_argument('--simulate', action='store_true', help='Simulate data (no hardware)')
    parser.add_argument('--config', default='config.yaml', help='Path to config.yaml')
    
    args = parser.parse_args()
    
    # Load configuration and merge CLI overrides
    cfg = load_config(args.config)
    baud = args.baud if args.baud else int(cfg["serial"]["baud"])  # CLI overrides config
    port = args.port if args.port else cfg["serial"].get("port")
    fullscreen = bool(args.fullscreen or cfg["display"].get("fullscreen", False))

    print("=" * 60)
    print("SUPERCAPFREEZER - Temperature Monitor")
    print("=" * 60)
    print(f"Port: {port if port else ('<auto-detect>' if not args.simulate else 'Simulation mode')}")
    print(f"Baud: {baud}")
    print("=" * 60)
    
    # Initialize logger
    global g_logger
    log_dir = cfg["logging"].get("directory", "./logs")
    max_hours = int(cfg["logging"].get("retention_hours", 24))
    g_logger = DataLogger(log_dir=log_dir, max_hours=max_hours)
    
    # Initialize serial reader
    reader = SerialReaderThread(
        port=port,
        baud=baud,
        callback=on_packet_received,
        simulate=args.simulate
    )
    reader.start()
    
    # Initialize UI
    # Optional: Set SDL for framebuffer if needed (respect environment)
    # Users can override via environment variables before launching
    ui_app = PyGameApp(port=port, baud=baud, fullscreen=fullscreen)
    ui_app.set_reader(reader)
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
        reader.stop()
        g_logger.close()
        ui_app.stop()
        print("[MAIN] Done")


if __name__ == '__main__':
    g_logger = None
    main()