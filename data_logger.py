"""CSV logger for STM32 telemetry, ACK, and runtime events."""

import csv
import os
from datetime import datetime, timedelta
from collections import deque
from typing import Optional, Any, Dict


class DataLogger:
    """Logs STM32 messages and writes buffered rows to CSV."""
    
    def __init__(self, log_dir: str = "./logs", 
                 max_hours: int = 24,
                 buffer_size: Optional[int] = None):
        """Initialize logger and output CSV file."""
        self.log_dir = log_dir
        self.max_hours = max_hours
        
        # 10 rows/s default retention model.
        if buffer_size is None:
            self.buffer_size = int(max_hours * 3600 * 10)
        else:
            self.buffer_size = buffer_size
        
        self.buffer = deque(maxlen=self.buffer_size)
        self.pending_rows = deque()
        
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
            
            self.csv_writer.writerow([
                'timestamp_utc',
                'time_elapsed_s',
                'message_type',
                't_raw',
                'v_volts',
                'i_mA',
                'state',
                'temp_celsius',
                'message',
            ])
            self.log_file.flush()
            
            print(f"[LOG] Opened logfile: {filepath}")
        except Exception as e:
            print(f"[LOG ERROR] Failed to open logfile: {e}")
            self.log_file = None
            self.csv_writer = None
    
    def _push_record(self, message_type: str, payload: Dict[str, Any]) -> None:
        time_elapsed = (datetime.now() - self.start_time).total_seconds()
        timestamp_str = datetime.now().isoformat()

        record = {
            'timestamp': timestamp_str,
            'time_elapsed': time_elapsed,
            'message_type': message_type,
            't_raw': payload.get('t_raw'),
            'v_volts': payload.get('v_volts'),
            'i_mA': payload.get('i_mA'),
            'state': payload.get('state'),
            'temp_celsius': payload.get('temp_celsius'),
            'message': payload.get('message', ''),
        }

        self.buffer.append(record)
        self.pending_rows.append(record)

    def push_telemetry(
        self,
        t_raw: Optional[int],
        voltage: Optional[float],
        current_ma: Optional[float],
        state: Optional[int],
        temp_c: float,
        raw_message: str,
    ) -> None:
        self._push_record(
            "telemetry",
            {
                't_raw': t_raw,
                'v_volts': voltage,
                'i_mA': current_ma,
                'state': state,
                'temp_celsius': temp_c,
                'message': raw_message,
            },
        )

    def push_ack(self, ack_message: str) -> None:
        self._push_record("ack", {'message': ack_message})

    def push_event(self, event_message: str) -> None:
        self._push_record("event", {'message': event_message})
    
    def flush_to_csv(self):
        """
        Write all pending rows to CSV.
        """
        if not self.csv_writer:
            return

        try:
            while self.pending_rows:
                row = self.pending_rows.popleft()
                self.csv_writer.writerow([
                    row['timestamp'],
                    f"{row['time_elapsed']:.3f}",
                    row['message_type'],
                    row['t_raw'] if row['t_raw'] is not None else "",
                    f"{float(row['v_volts']):.3f}" if row['v_volts'] is not None else "",
                    f"{float(row['i_mA']):.3f}" if row['i_mA'] is not None else "",
                    row['state'] if row['state'] is not None else "",
                    f"{float(row['temp_celsius']):.3f}" if row['temp_celsius'] is not None else "",
                    row['message'],
                ])
            if self.log_file:
                self.log_file.flush()
        except Exception as e:
            print(f"[LOG ERROR] Failed to write: {e}")
    
    def get_recent(self, seconds: int = 60) -> list:
        """
        Get recent records from buffer.
        
        Args:
            seconds: How many seconds back to retrieve
            
        Returns:
            List of dicts with recent records
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
        """Get all buffered records."""
        return list(self.buffer)
    
    def get_stats(self) -> dict:
        """Get telemetry temperature statistics."""
        temps = [r['temp_celsius'] for r in self.buffer if r.get('temp_celsius') is not None]
        if not temps:
            return {
                'count': 0,
                'min_temp': None,
                'max_temp': None,
                'avg_temp': None,
                'runtime_s': 0,
            }

        runtime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'count': len(temps),
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
