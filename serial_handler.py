"""
SUPERCAPFREEZER Dual Serial Handler
====================================

Handles ASCII protocol communication with two microcontrollers:
1. Arduino (Peltier Controller) - Temperature control
2. Measurement MCU - Voltage/Current measurement with state machine

Simple ASCII line-based protocol for both devices.
"""

import threading
import time
from typing import Optional, Callable, Dict


class ASCIILineParser:
    """
    Simple ASCII line parser for both microcontrollers.
    
    Handles:
    - Arduino: "TEMP:23.45 PWM:128"
    - Measurement: "MEAS:V1:12.34 V2:5.67 I1:0.123 I2:0.456 STATE:CHARGE"
    - Comments: "# Message"
    """
    
    def __init__(self):
        self.line_buffer = ""
        self.stats = {
            'total_lines': 0,
            'valid_lines': 0,
            'parse_errors': 0,
            'comment_lines': 0,
        }
    
    def push_data(self, data: str) -> list:
        """
        Push incoming data (can be partial lines).
        Returns list of parsed packets (one per complete line).
        """
        packets = []
        self.line_buffer += data
        
        # Process complete lines
        while '\n' in self.line_buffer:
            line, self.line_buffer = self.line_buffer.split('\n', 1)
            line = line.strip()
            
            if line:
                packet = self._parse_line(line)
                if packet:
                    packets.append(packet)
        
        return packets
    
    def _parse_line(self, line: str) -> Optional[dict]:
        """Parse a single line into a packet dict."""
        self.stats['total_lines'] += 1
        
        # Skip comments
        if line.startswith('#'):
            self.stats['comment_lines'] += 1
            return None
        
        try:
            # Parse key:value pairs
            parts = line.split()
            data = {}
            
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    # Try to convert to float, otherwise keep as string
                    try:
                        data[key] = float(value)
                    except ValueError:
                        data[key] = value
            
            if data:
                self.stats['valid_lines'] += 1
                return data
            
        except Exception:
            self.stats['parse_errors'] += 1
        
        return None
    
    def get_stats(self) -> dict:
        """Return parsing statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics counters."""
        self.stats = {
            'total_lines': 0,
            'valid_lines': 0,
            'parse_errors': 0,
            'comment_lines': 0,
        }


class SerialDevice:
        
        if packet_crc != calculated_crc:
            return None
        
        # Parse header
        frame_type = self.buffer[2]
        samples_count = self.buffer[3]
        timestamp_ms = struct.unpack_from('<I', self.buffer, 4)[0]
        seq_num = struct.unpack_from('<H', self.buffer, 8)[0]
        
        # Parse payload
        samples = []
        payload_offset = self.HEADER_SIZE
        
        for i in range(samples_count):
            offset = payload_offset + i * self.SAMPLE_SIZE
            raw_int16 = struct.unpack_from('<h', self.buffer, offset)[0]
            value = raw_int16 / 100.0  # Convert back to float (divide by 100)
            samples.append(value)
        
        return {
            'type': frame_type,
            'timestamp_ms': timestamp_ms,
            'seq_num': seq_num,
            'samples': samples,
            'values': samples[0] if len(samples) == 1 else samples,  # Convenience
        }
    
    @staticmethod
    def _crc16_ccitt(data: bytes) -> int:
        """
        Calculate CRC16-CCITT checksum.
        
        Polynomial: 0x1021
        Init: 0xFFFF
        """
        crc = 0xFFFF
class SerialDevice:
    """
    Handles serial communication with one microcontroller.
    Threaded reader with ASCII line parsing.
    """
    
    def __init__(self, name: str, port: Optional[str], baud: int = 115200, 
                 callback: Optional[Callable] = None, simulate: bool = False):
        self.name = name
        self.port = port
        self.baud = baud
        self.callback = callback
        self.simulate = simulate
        self._stop = threading.Event()
        self.parser = ASCIILineParser()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.ser = None
        self.connected = False
    
    def start(self):
        """Start reader thread."""
        self.thread.start()
    
    def stop(self):
        """Stop reader thread."""
        self._stop.set()
        if self.ser:
            try:
                self.ser.close()
            except:
                pass
    
    def send(self, command: str):
        """Send command to device (adds newline)."""
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(f"{command}\n".encode('utf-8'))
                self.ser.flush()
            except Exception as e:
                print(f"[{self.name}] Send error: {e}")
    
    def _run(self):
        """Main thread loop."""
        if self.simulate:
            self._simulate_data()
            return
        
        # Auto-detect port if not provided
        port = self.port or self._auto_detect_port()
        if not port:
            print(f"[{self.name}] No port found. Simulation mode.")
            self._simulate_data()
            return
        
        try:
            import serial
            self.ser = serial.Serial(port, self.baud, timeout=0.1)
            self.connected = True
            print(f"[{self.name}] Connected to {port} @ {self.baud} baud")
            
            while not self._stop.is_set():
                if self.ser.in_waiting > 0:
                    # Read available data
                    data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                    packets = self.parser.push_data(data)
                    
                    # Call callback for each packet
                    if self.callback:
                        for packet in packets:
                            self.callback(packet)
                else:
                    time.sleep(0.01)
        
        except Exception as e:
            print(f"[{self.name}] Serial error: {e}")
            self.connected = False
            self._simulate_data()
    
    @staticmethod
    def _auto_detect_port() -> Optional[str]:
        """Try to detect Arduino/MCU port automatically."""
        try:
            from serial.tools import list_ports
        except:
            return None
        
        ports = list(list_ports.comports())
        if not ports:
            return None
        
        # Prefer Arduino-like descriptions
        for p in ports:
            desc = (p.description or "").lower()
            if "arduino" in desc or "r4" in desc or "uno" in desc:
                return p.device
        
        # Fallback: first ACM/USB
        for p in ports:
            if p.device.startswith("/dev/ttyACM") or p.device.startswith("/dev/ttyUSB"):
                return p.device
        
        return ports[0].device if ports else None
    
    def _simulate_data(self):
        """Simulate data for testing."""
        pass  # Overridden by subclasses
    
    def get_stats(self) -> dict:
        """Return parser statistics."""
        return self.parser.get_stats()
    
    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self.connected


class PeltierController(SerialDevice):
    """Arduino Peltier temperature controller."""
    
    def __init__(self, port: Optional[str], baud: int = 115200, 
                 callback: Optional[Callable] = None, simulate: bool = False):
        super().__init__("Peltier", port, baud, callback, simulate)
    
    def set_temperature(self, temp: float):
        """Send temperature setpoint to Arduino."""
        self.send(f"SET:{temp:.2f}")
    
    def _simulate_data(self):
        """Simulate temperature data."""
        import numpy as np
        t = 0.0
        
        while not self._stop.is_set():
            temp = 25.0 + 3.0 * np.sin(t) + (np.random.rand() - 0.5) * 0.3
            pwm = int(128 + 50 * np.sin(t * 0.5))
            
            line = f"TEMP:{temp:.2f} PWM:{pwm}\n"
            packets = self.parser.push_data(line)
            
            if self.callback:
                for packet in packets:
                    self.callback(packet)
            
            t += 0.1
            time.sleep(0.1)


class MeasurementController(SerialDevice):
    """Second microcontroller for voltage/current measurements."""
    
    def __init__(self, port: Optional[str], baud: int = 115200, 
                 callback: Optional[Callable] = None, simulate: bool = False):
        super().__init__("Measurement", port, baud, callback, simulate)
        self.state = "IDLE"
    
    def start_measurement(self):
        """Start measurement sequence."""
        self.send("START")
    
    def stop_measurement(self):
        """Stop measurement sequence."""
        self.send("STOP")
    
    def reset(self):
        """Reset state machine."""
        self.send("RESET")
    
    def set_state(self, state: str):
        """Set specific state (IDLE, CHARGE, DISCHARGE)."""
        self.send(f"STATE:{state}")
    
    def _simulate_data(self):
        """Simulate measurement data at 100 Hz."""
        import numpy as np
        t = 0.0
        states = ["IDLE", "CHARGE", "DISCHARGE", "IDLE"]
        state_idx = 0
        state_counter = 0
        
        while not self._stop.is_set():
            # Cycle through states every 200 samples
            if state_counter >= 200:
                state_counter = 0
                state_idx = (state_idx + 1) % len(states)
            
            self.state = states[state_idx]
            state_counter += 1
            
            # Simulate voltages and currents
            v1 = 12.0 + 2.0 * np.sin(t) + (np.random.rand() - 0.5) * 0.1
            v2 = 5.0 + 0.5 * np.cos(t) + (np.random.rand() - 0.5) * 0.05
            i1 = 1.0 + 0.3 * np.sin(t * 2) + (np.random.rand() - 0.5) * 0.02
            i2 = 0.5 + 0.1 * np.cos(t * 3) + (np.random.rand() - 0.5) * 0.01
            
            line = f"MEAS:V1:{v1:.3f} V2:{v2:.3f} I1:{i1:.3f} I2:{i2:.3f} STATE:{self.state}\n"
            packets = self.parser.push_data(line)
            
            if self.callback:
                for packet in packets:
                    self.callback(packet)
            
            t += 0.01
            time.sleep(0.01)  # 100 Hz


# Legacy compatibility (for existing code)
class SerialReaderThread(PeltierController):
    """Backward compatibility wrapper."""
    def __init__(self, port: str, baud: int = 115200, callback=None, simulate=False):
        super().__init__(port, baud, callback, simulate)

