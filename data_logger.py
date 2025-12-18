"""
SUPERCAPFREEZER Data Logger
===========================

Logs temperature data to CSV file.
Implements 24-hour rolling buffer with configurable retention.
"""

import csv
import os
from datetime import datetime, timedelta
from collections import deque
from typing import Optional


class DataLogger:
    """
    Logs measurement data to CSV file.
    
    Features:
    - CSV format with timestamp, temperature, sequence number
    - Automatic file rotation
    - In-memory ring buffer (24h default)
    - Data export capabilities
    """
    
    def __init__(self, log_dir: str = "./logs", 
                 max_hours: int = 24,
                 buffer_size: Optional[int] = None):
        """
        Initialize logger.
        
        Args:
            log_dir: Directory to store log files
            max_hours: Hours of data to retain in memory (24h default)
            buffer_size: Max number of records in ring buffer
                        (if None, calculated from max_hours and 10Hz rate)
        """
        self.log_dir = log_dir
        self.max_hours = max_hours
        
        # Calculate buffer size: 24h × 3600s/h × 10Hz = 864,000 samples
        if buffer_size is None:
            self.buffer_size = int(max_hours * 3600 * 10)
        else:
            self.buffer_size = buffer_size
        
        # Ring buffer
        self.buffer = deque(maxlen=self.buffer_size)
        
        # Create log directory
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        self.log_file = None
        self.csv_writer = None
        self.start_time = datetime.now()
        self._open_logfile()
    
    def _open_logfile(self):
        """Open or create new CSV log file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"supercapfreezer_{timestamp}.csv"
        filepath = os.path.join(self.log_dir, filename)
        
        try:
            self.log_file = open(filepath, 'w', newline='', buffering=1)
            self.csv_writer = csv.writer(self.log_file)
            
            # Write header
            self.csv_writer.writerow([
                'timestamp_utc',
                'time_elapsed_s',
                'temperature_celsius',
                'seq_num'
            ])
            self.log_file.flush()
            
            print(f"[LOG] Opened logfile: {filepath}")
        except Exception as e:
            print(f"[LOG ERROR] Failed to open logfile: {e}")
            self.log_file = None
            self.csv_writer = None
    
    def push(self, timestamp_ms: int, temperature: float, seq_num: int):
        """
        Log a temperature measurement.
        
        Args:
            timestamp_ms: System time in milliseconds
            temperature: Temperature in °C
            seq_num: Packet sequence number
        """
        time_elapsed = (datetime.now() - self.start_time).total_seconds()
        timestamp_str = datetime.now().isoformat()
        
        # Add to ring buffer
        self.buffer.append({
            'timestamp': timestamp_str,
            'time_elapsed': time_elapsed,
            'temperature': temperature,
            'seq_num': seq_num,
        })
        
        # Write to CSV
        if self.csv_writer:
            try:
                self.csv_writer.writerow([
                    timestamp_str,
                    f"{time_elapsed:.3f}",
                    f"{temperature:.2f}",
                    seq_num
                ])
                self.log_file.flush()
            except Exception as e:
                print(f"[LOG ERROR] Failed to write: {e}")
    
    def get_recent(self, seconds: int = 60) -> list:
        """
        Get recent measurements from buffer.
        
        Args:
            seconds: How many seconds back to retrieve
            
        Returns:
            List of dicts with recent measurements
        """
        cutoff_time = datetime.now() - timedelta(seconds=seconds)
        result = []
        
        for record in self.buffer:
            try:
                record_time = datetime.fromisoformat(record['timestamp'])
                if record_time >= cutoff_time:
                    result.append(record)
            except:
                pass
        
        return result
    
    def get_all(self) -> list:
        """Get all buffered measurements"""
        return list(self.buffer)
    
    def get_stats(self) -> dict:
        """Get buffer statistics"""
        if not self.buffer:
            return {
                'count': 0,
                'min_temp': None,
                'max_temp': None,
                'avg_temp': None,
                'runtime_s': 0,
            }
        
        temps = [r['temperature'] for r in self.buffer]
        runtime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'count': len(self.buffer),
            'min_temp': min(temps),
            'max_temp': max(temps),
            'avg_temp': sum(temps) / len(temps),
            'runtime_s': runtime,
        }
    
    def close(self):
        """Close logfile"""
        if self.log_file:
            try:
                self.log_file.close()
            except:
                pass
    
    def __del__(self):
        self.close()
