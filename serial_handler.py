"""
SUPERCAPFREEZER Binary Protocol Parser
======================================

Parses binary packets from Arduino and validates them using CRC16-CCITT.
Converts payload to temperature/voltage values.
Handles synchronization and error recovery.
"""

import struct
from collections import deque
from typing import Optional, Tuple, List


class ProtocolError(Exception):
    """Protocol-related exceptions"""
    pass


class PacketParser:
    """
    Stateful parser for binary protocol packets.
    
    Implements:
    - Byte-by-byte synchronization (looking for 0xAA 0x55)
    - Frame size validation
    - CRC16-CCITT checksum verification
    - Payload decoding
    """
    
    # Protocol constants
    SYNC_0 = 0xAA
    SYNC_1 = 0x55
    TYPE_TEMP = 0x01
    TYPE_VOLT = 0x02
    HEADER_SIZE = 10  # SYNC(2) + TYPE(1) + SAMPLES(1) + TIMESTAMP(4) + SEQ(2)
    CRC_SIZE = 2
    SAMPLE_SIZE = 2
    
    # State machine
    STATE_SYNC_0 = 0
    STATE_SYNC_1 = 1
    STATE_HEADER = 2
    STATE_PAYLOAD = 3
    STATE_CRC = 4
    
    def __init__(self):
        self.state = self.STATE_SYNC_0
        self.buffer = bytearray()
        self.frame_size = 0
        self.samples_count = 0
        self.stats = {
            'total_packets': 0,
            'valid_packets': 0,
            'crc_errors': 0,
            'sync_errors': 0,
            'frame_errors': 0,
        }
    
    def push_byte(self, byte: int) -> Optional[dict]:
        """
        Push one byte to the parser.
        
        Args:
            byte: Single byte (0-255)
            
        Returns:
            Parsed packet dict if complete, else None
            
        Raises:
            ProtocolError: If irrecoverable error
        """
        byte = byte & 0xFF
        
        if self.state == self.STATE_SYNC_0:
            if byte == self.SYNC_0:
                self.buffer = bytearray([byte])
                self.state = self.STATE_SYNC_1
            else:
                self.stats['sync_errors'] += 1
        
        elif self.state == self.STATE_SYNC_1:
            if byte == self.SYNC_1:
                self.buffer.append(byte)
                self.state = self.STATE_HEADER
            else:
                self.stats['sync_errors'] += 1
                self.state = self.STATE_SYNC_0
        
        elif self.state == self.STATE_HEADER:
            self.buffer.append(byte)
            if len(self.buffer) == self.HEADER_SIZE:
                # Parse header
                frame_type = self.buffer[2]
                self.samples_count = self.buffer[3]
                
                if self.samples_count == 0 or self.samples_count > 255:
                    self.stats['frame_errors'] += 1
                    self.state = self.STATE_SYNC_0
                    self.buffer.clear()
                    return None
                
                self.frame_size = (self.HEADER_SIZE + 
                                  self.samples_count * self.SAMPLE_SIZE + 
                                  self.CRC_SIZE)
                
                self.state = self.STATE_PAYLOAD
        
        elif self.state == self.STATE_PAYLOAD:
            self.buffer.append(byte)
            payload_start = self.HEADER_SIZE
            payload_end = payload_start + self.samples_count * self.SAMPLE_SIZE
            
            if len(self.buffer) >= payload_end:
                self.state = self.STATE_CRC
        
        elif self.state == self.STATE_CRC:
            self.buffer.append(byte)
            
            if len(self.buffer) == self.frame_size:
                # Complete frame received
                packet = self._validate_and_parse()
                self.stats['total_packets'] += 1
                
                if packet:
                    self.stats['valid_packets'] += 1
                else:
                    self.stats['crc_errors'] += 1
                
                # Reset state machine
                self.state = self.STATE_SYNC_0
                self.buffer.clear()
                
                return packet
        
        return None
    
    def _validate_and_parse(self) -> Optional[dict]:
        """
        Validate packet (CRC) and extract data.
        
        Returns:
            Packet dict with decoded values, or None if CRC fails
        """
        # Extract CRC from packet
        crc_offset = len(self.buffer) - self.CRC_SIZE
        packet_crc = struct.unpack_from('<H', self.buffer, crc_offset)[0]
        
        # Calculate CRC over header + payload (excluding CRC field)
        calculated_crc = self._crc16_ccitt(self.buffer[:crc_offset])
        
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
        
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                crc = crc << 1
                if crc & 0x10000:
                    crc = (crc ^ 0x1021) & 0xFFFF
        
        return crc
    
    def get_stats(self) -> dict:
        """Return parser statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics counters"""
        self.stats = {
            'total_packets': 0,
            'valid_packets': 0,
            'crc_errors': 0,
            'sync_errors': 0,
            'frame_errors': 0,
        }


class SerialReaderThread:
    """
    Reads from serial port in separate thread.
    Feeds bytes to PacketParser.
    Calls callback for each complete packet.
    """
    
    def __init__(self, port: str, baud: int = 115200, callback=None, simulate=False):
        import threading
        import time
        
        self.port = port
        self.baud = baud
        self.callback = callback
        self.simulate = simulate
        self._stop = threading.Event()
        self.parser = PacketParser()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.ser = None
    
    def start(self):
        """Start reader thread"""
        self.thread.start()
    
    def stop(self):
        """Stop reader thread"""
        self._stop.set()
        if self.ser:
            try:
                self.ser.close()
            except:
                pass
    
    def _run(self):
        import time
        
        if self.simulate:
            self._simulate_data()
            return

        # Auto-detect port if not provided
        port = self.port or self._auto_detect_port()
        if not port:
            print("[Serial] No port found. Falling back to simulation.")
            self._simulate_data()
            return

        try:
            import serial
            self.ser = serial.Serial(port, self.baud, timeout=1)
            
            while not self._stop.is_set():
                if self.ser.in_waiting > 0:
                    byte = self.ser.read(1)[0]
                    packet = self.parser.push_byte(byte)
                    
                    if packet and self.callback:
                        self.callback(packet)
                else:
                    time.sleep(0.01)
        
        except Exception as e:
            print(f"Serial error: {e}")
            self._simulate_data()

    @staticmethod
    def _auto_detect_port() -> str | None:
        """Try to detect Arduino UNO R4 port automatically.

        Preference order:
        - Ports whose description contains 'Arduino' or 'R4'
        - First /dev/ttyACM* or /dev/ttyUSB*
        """
        try:
            from serial.tools import list_ports  # type: ignore
        except Exception:
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
        # Otherwise first available
        return ports[0].device
    
    def _simulate_data(self):
        """Simulate temperature data for testing"""
        import time
        import numpy as np
        
        t = 0.0
        seq = 0
        
        while not self._stop.is_set():
            # Simulate temperature: 25°C ± 3°C with small noise
            temp = 25.0 + 3.0 * np.sin(t) + (np.random.rand() - 0.5) * 0.3
            
            packet = {
                'type': self.parser.TYPE_TEMP,
                'timestamp_ms': int(time.time() * 1000),
                'seq_num': seq,
                'samples': [temp],
                'values': temp,
            }
            
            if self.callback:
                self.callback(packet)
            
            seq += 1
            t += 0.1
            time.sleep(0.1)
    
    def get_stats(self) -> dict:
        """Return parser statistics"""
        return self.parser.get_stats()
