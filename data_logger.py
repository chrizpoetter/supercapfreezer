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
                        (if None, calculated from max_hours and 100Hz rate for measurements)
        """
        self.log_dir = log_dir
        self.max_hours = max_hours
        
        # Calculate buffer size: 24h × 3600s/h × 100Hz = 8,640,000 samples (larger for 100Hz)
        if buffer_size is None:
            self.buffer_size = int(max_hours * 3600 * 100)
        else:
            self.buffer_size = buffer_size
        
        # Ring buffers
        self.buffer = deque(maxlen=self.buffer_size)  # Combined data
        self.temp_buffer = deque(maxlen=int(max_hours * 3600 * 10))  # Temperature only
        self.meas_buffer = deque(maxlen=self.buffer_size)  # Measurements only
        
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
            
            # Write header with all columns
            self.csv_writer.writerow([
                'timestamp_utc',
                'time_elapsed_s',
                'temperature_celsius',
                'pwm',
                'setpoint_celsius',
                'v1_volts',
                'v2_volts',
                'i1_amps',
                'i2_amps',
                'meas_state'
            ])
            self.log_file.flush()
            
            print(f"[LOG] Opened logfile: {filepath}")
        except Exception as e:
            print(f"[LOG ERROR] Failed to open logfile: {e}")
            self.log_file = None
            self.csv_writer = None
    
    def push_temperature(self, temp: float, pwm: int, setpoint: float):
        """
        Log temperature data from Peltier controller.
        
        Args:
            temp: Temperature in °C
            pwm: PWM value (0-255)
            setpoint: Target temperature in °C
        """
        time_elapsed = (datetime.now() - self.start_time).total_seconds()
        timestamp_str = datetime.now().isoformat()
        
        record = {
            'timestamp': timestamp_str,
            'time_elapsed': time_elapsed,
            'temperature': temp,
            'pwm': pwm,
            'setpoint': setpoint,
        }
        
        self.temp_buffer.append(record)
    
    def push_measurement(self, v1: float, v2: float, i1: float, i2: float, state: str):
        """
        Log measurement data from measurement controller.
        
        Args:
            v1, v2: Voltages in volts
            i1, i2: Currents in amps
            state: State machine state (IDLE, CHARGE, DISCHARGE)
        """
        time_elapsed = (datetime.now() - self.start_time).total_seconds()
        timestamp_str = datetime.now().isoformat()
        
        record = {
            'timestamp': timestamp_str,
            'time_elapsed': time_elapsed,
            'v1': v1,
            'v2': v2,
            'i1': i1,
            'i2': i2,
            'state': state,
        }
        
        self.meas_buffer.append(record)
    
    def flush_to_csv(self):
        """
        Write buffered data to CSV (merges temp + measurement by time).
        Call this periodically (e.g., every second) to write to disk.
        """
        if not self.csv_writer:
            return
        
        # Get latest from each buffer
        latest_temp = self.temp_buffer[-1] if self.temp_buffer else None
        latest_meas = self.meas_buffer[-1] if self.meas_buffer else None
        
        if not latest_temp and not latest_meas:
            return
        
        time_elapsed = (datetime.now() - self.start_time).total_seconds()
        timestamp_str = datetime.now().isoformat()
        
        try:
            self.csv_writer.writerow([
                timestamp_str,
                f"{time_elapsed:.3f}",
                f"{latest_temp['temperature']:.2f}" if latest_temp else "",
                latest_temp['pwm'] if latest_temp else "",
                f"{latest_temp['setpoint']:.2f}" if latest_temp else "",
                f"{latest_meas['v1']:.3f}" if latest_meas else "",
                f"{latest_meas['v2']:.3f}" if latest_meas else "",
                f"{latest_meas['i1']:.3f}" if latest_meas else "",
                f"{latest_meas['i2']:.3f}" if latest_meas else "",
                latest_meas['state'] if latest_meas else "",
            ])
            self.log_file.flush()
        except Exception as e:
            print(f"[LOG ERROR] Failed to write: {e}")
    
    def get_recent(self, seconds: int = 60) -> list:
        """
        Get recent temperature measurements from buffer.
        
        Args:
            seconds: How many seconds back to retrieve
            
        Returns:
            List of dicts with recent measurements
        """
        cutoff_time = datetime.now() - timedelta(seconds=seconds)
        result = []
        
        for record in self.temp_buffer:
            try:
                record_time = datetime.fromisoformat(record['timestamp'])
                if record_time >= cutoff_time:
                    result.append(record)
            except:
                pass
        
        return result
    
    def get_all(self) -> list:
        """Get all buffered temperature measurements."""
        return list(self.temp_buffer)
    
    def get_all_measurements(self) -> list:
        """Get all buffered measurement data."""
        return list(self.meas_buffer)
    
    def get_stats(self) -> dict:
        """Get temperature buffer statistics."""
        if not self.temp_buffer:
            return {
                'count': 0,
                'min_temp': None,
                'max_temp': None,
                'avg_temp': None,
                'runtime_s': 0,
            }
        
        temps = [r['temperature'] for r in self.temp_buffer]
        runtime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'count': len(self.temp_buffer),
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
