"""
SUPERCAPFREEZER UI Application
==============================

Pygame-based GUI for 3.5" TFT display.

Features:
- Dashboard screen (current temp, stats)
- Graph screen (rolling plot over time)
- Settings screen
- Touchscreen support (gestures for screen switching)
"""

import pygame
import time
import numpy as np
from collections import deque
from typing import Optional, Tuple, List


class UIScreen:
    """Base class for UI screens"""
    
    def __init__(self, app, name: str):
        self.app = app
        self.name = name
    
    def draw(self, surface):
        raise NotImplementedError
    
    def on_touch(self, x: int, y: int):
        """Handle touch event (optional)"""
        pass


class DashboardScreen(UIScreen):
    """Main dashboard: current temperature, stats, info"""
    
    def __init__(self, app):
        super().__init__(app, "Dashboard")
        self.font_large = pygame.font.SysFont(None, 48, bold=True)
        self.font_medium = pygame.font.SysFont(None, 28)
        self.font_small = pygame.font.SysFont(None, 18)
    
    def draw(self, surface):
        surface.fill((10, 10, 10))
        
        # Get latest data
        if self.app.logger.temp_buffer:
            latest = self.app.logger.temp_buffer[-1]
            temp = latest['temperature']
            pwm = latest.get('pwm', 0)
            setpoint = latest.get('setpoint', 25.0)
        else:
            temp = 0.0
            pwm = 0
            setpoint = 25.0
        
        stats = self.app.logger.get_stats()
        
        # Title
        title = self.font_large.render("SUPERCAPFREEZER", True, (0, 200, 50))
        surface.blit(title, (20, 20))
        
        # Current temperature (large)
        temp_text = self.font_large.render(f"{temp:.2f}°C", True, (100, 255, 100))
        surface.blit(temp_text, (40, 80))
        
        # Setpoint and PWM
        setpoint_text = self.font_medium.render(f"Target: {setpoint:.1f}°C", True, (150, 150, 255))
        surface.blit(setpoint_text, (40, 140))
        
        pwm_text = self.font_medium.render(f"PWM: {pwm} ({pwm*100//255}%)", True, (255, 200, 100))
        surface.blit(pwm_text, (40, 170))
        
        # Stats
        y = 210
        lines = [
            f"Samples: {stats['count']}",
            f"Min: {stats['min_temp']:.2f}°C" if stats['min_temp'] is not None else "Min: --",
            f"Max: {stats['max_temp']:.2f}°C" if stats['max_temp'] is not None else "Max: --",
            f"Avg: {stats['avg_temp']:.2f}°C" if stats['avg_temp'] is not None else "Avg: --",
            f"Runtime: {int(stats['runtime_s'])}s",
        ]
        
        for line in lines:
            surf = self.font_medium.render(line, True, (200, 200, 200))
            surface.blit(surf, (40, y))
            y += 40
        
        # Parse stats
        if self.app.peltier:
            parser_stats = self.app.peltier.get_stats()
        else:
            parser_stats = {'valid_lines': 0, 'parse_errors': 0}
        y += 20
        parser_lines = [
            f"Peltier: {parser_stats.get('valid_lines', 0)} pkts",
            f"Errors: {parser_stats.get('parse_errors', 0)}",
        ]
        
        for line in parser_lines:
            surf = self.font_small.render(line, True, (180, 180, 180))
            surface.blit(surf, (40, y))
            y += 25
        
        # Bottom hint
        hint = self.font_small.render("Swipe for more | Press ESC to exit", True, (100, 100, 100))
        surface.blit(hint, (20, surface.get_height() - 35))


class GraphScreen(UIScreen):
    """Graph screen: rolling temperature plot"""
    
    def __init__(self, app):
        super().__init__(app, "Graph")
        self.font_small = pygame.font.SysFont(None, 16)
        self.font_medium = pygame.font.SysFont(None, 20)
        self.window_seconds = 60  # Show last 60 seconds
    
    def draw(self, surface):
        surface.fill((10, 10, 10))
        
        # Title
        title = self.font_medium.render(f"Temperature Graph ({self.window_seconds}s)", 
                                       True, (0, 200, 50))
        surface.blit(title, (20, 10))
        
        # Plot area
        plot_rect = pygame.Rect(50, 50, surface.get_width() - 100, surface.get_height() - 120)
        self._draw_plot(surface, plot_rect)
        
        # Instructions
        inst = self.font_small.render("← Swipe left for more screens →", True, (100, 100, 100))
        surface.blit(inst, (20, surface.get_height() - 30))
    
    def _draw_plot(self, surface, rect):
        """Draw the temperature plot"""
        # Background
        pygame.draw.rect(surface, (20, 20, 20), rect)
        pygame.draw.rect(surface, (60, 60, 60), rect, 1)
        
        # Get data
        recent = self.app.logger.get_recent(seconds=self.window_seconds)
        
        if len(recent) < 2:
            no_data = self.font_small.render("No data yet...", True, (150, 150, 150))
            surface.blit(no_data, (rect.centerx - 50, rect.centery))
            return
        
        # Extract times and temperatures
        start_time = recent[0]['time_elapsed']
        times = [r['time_elapsed'] - start_time for r in recent]
        temps = [r['temperature'] for r in recent]
        
        # Calculate Y range
        temp_min = min(temps)
        temp_max = max(temps)
        temp_range = temp_max - temp_min
        if temp_range < 1.0:
            temp_range = 1.0
            temp_min -= 0.5
            temp_max += 0.5
        
        # Draw grid lines
        for temp_val in np.linspace(temp_min, temp_max, 5):
            y = rect.bottom - (temp_val - temp_min) / temp_range * rect.height
            color = (40, 40, 40)
            pygame.draw.line(surface, color, (rect.left, int(y)), (rect.right, int(y)), 1)
            label = self.font_small.render(f"{temp_val:.1f}", True, (100, 100, 100))
            surface.blit(label, (rect.left - 35, int(y) - 8))
        
        # Draw plot line
        points = []
        for t, temp in zip(times, temps):
            x = rect.left + (t / self.window_seconds) * rect.width
            y = rect.bottom - (temp - temp_min) / temp_range * rect.height
            points.append((x, y))
        
        if len(points) >= 2:
            pygame.draw.lines(surface, (0, 255, 100), False, points, 2)
        
        # Draw points
        for point in points:
            pygame.draw.circle(surface, (100, 255, 100), point, 3)


class SettingsScreen(UIScreen):
    """Settings and system info"""
    
    def __init__(self, app):
        super().__init__(app, "Settings")
        self.font_small = pygame.font.SysFont(None, 18)
        self.font_medium = pygame.font.SysFont(None, 24)
        self._export_btn = pygame.Rect(0, 0, 0, 0)
    
    def draw(self, surface):
        surface.fill((10, 10, 10))
        
        # Title
        title = self.font_medium.render("System Info", True, (0, 200, 50))
        surface.blit(title, (20, 10))
        
        # System info
        y = 60
        import os
        import psutil
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            
            lines = [
                f"CPU: {cpu_percent:.1f}%",
                f"RAM: {mem.percent:.1f}% ({mem.used // (1024**2)} MB)",
                f"Temperature data logged",
                f"Serial port: {self.app.port}",
                f"Baud: {self.app.baud}",
            ]
        except:
            lines = [
                "Serial port: (unknown)",
                "Baud: 115200",
            ]
        
        for line in lines:
            surf = self.font_small.render(line, True, (200, 200, 200))
            surface.blit(surf, (40, y))
            y += 35
        
        # Button area
        self._export_btn = pygame.Rect(40, surface.get_height() - 60,
                                       surface.get_width() - 80, 50)
        pygame.draw.rect(surface, (0, 100, 50), self._export_btn)
        pygame.draw.rect(surface, (0, 150, 100), self._export_btn, 2)
        
        btn_text = self.font_small.render("Export CSV", True, (200, 200, 200))
        surface.blit(btn_text, (self._export_btn.centerx - 40, self._export_btn.centery - 10))

    def on_touch(self, x: int, y: int):
        # Handle button tap
        if self._export_btn.collidepoint(x, y):
            try:
                self.app._save_csv()
            except Exception as e:
                print(f"[UI] Export failed: {e}")


class ControlScreen(UIScreen):
    """Control screen: Adjust temperature setpoint"""
    
    def __init__(self, app):
        super().__init__(app, "Control")
        self.font_large = pygame.font.SysFont(None, 42, bold=True)
        self.font_medium = pygame.font.SysFont(None, 28)
        self.font_small = pygame.font.SysFont(None, 20)
        self._btn_up = None
        self._btn_down = None
    
    def draw(self, surface):
        surface.fill((10, 10, 10))
        
        # Title
        title = self.font_large.render("Temperature Control", True, (0, 200, 50))
        surface.blit(title, (20, 10))
        
        # Get current setpoint
        if self.app.logger.temp_buffer:
            setpoint = self.app.logger.temp_buffer[-1].get('setpoint', 25.0)
            current_temp = self.app.logger.temp_buffer[-1].get('temperature', 0.0)
        else:
            setpoint = 25.0
            current_temp = 0.0
        
        # Current temperature
        temp_text = self.font_medium.render(f"Current: {current_temp:.2f}°C", True, (200, 200, 200))
        surface.blit(temp_text, (40, 70))
        
        # Setpoint (large)
        setpoint_text = self.font_large.render(f"Target: {setpoint:.1f}°C", True, (100, 255, 100))
        surface.blit(setpoint_text, (40, 120))
        
        # Buttons for adjustment
        btn_width = 100
        btn_height = 60
        center_x = surface.get_width() // 2
        
        # Down button
        self._btn_down = pygame.Rect(center_x - btn_width - 20, 200, btn_width, btn_height)
        pygame.draw.rect(surface, (100, 50, 50), self._btn_down)
        pygame.draw.rect(surface, (150, 100, 100), self._btn_down, 2)
        down_text = self.font_large.render("-", True, (255, 255, 255))
        surface.blit(down_text, (self._btn_down.centerx - 10, self._btn_down.centery - 20))
        
        # Up button
        self._btn_up = pygame.Rect(center_x + 20, 200, btn_width, btn_height)
        pygame.draw.rect(surface, (50, 100, 50), self._btn_up)
        pygame.draw.rect(surface, (100, 150, 100), self._btn_up, 2)
        up_text = self.font_large.render("+", True, (255, 255, 255))
        surface.blit(up_text, (self._btn_up.centerx - 10, self._btn_up.centery - 20))
        
        # Instructions
        inst = self.font_small.render("Tap +/- to adjust setpoint by 0.5°C", True, (150, 150, 150))
        surface.blit(inst, (40, 290))
    
    def on_touch(self, x: int, y: int):
        if self._btn_up and self._btn_up.collidepoint(x, y):
            # Increase setpoint
            if self.app.peltier and self.app.logger.temp_buffer:
                current_setpoint = self.app.logger.temp_buffer[-1].get('setpoint', 25.0)
                new_setpoint = min(current_setpoint + 0.5, 40.0)  # Max 40°C
                self.app.peltier.set_temperature(new_setpoint)
                import main
                main.g_setpoint = new_setpoint
                print(f"[UI] Setpoint increased to {new_setpoint:.1f}°C")
        
        elif self._btn_down and self._btn_down.collidepoint(x, y):
            # Decrease setpoint
            if self.app.peltier and self.app.logger.temp_buffer:
                current_setpoint = self.app.logger.temp_buffer[-1].get('setpoint', 25.0)
                new_setpoint = max(current_setpoint - 0.5, -10.0)  # Min -10°C
                self.app.peltier.set_temperature(new_setpoint)
                import main
                main.g_setpoint = new_setpoint
                print(f"[UI] Setpoint decreased to {new_setpoint:.1f}°C")


class MeasurementScreen(UIScreen):
    """Measurement screen: Display voltage/current and state"""
    
    def __init__(self, app):
        super().__init__(app, "Measurement")
        self.font_large = pygame.font.SysFont(None, 42, bold=True)
        self.font_medium = pygame.font.SysFont(None, 26)
        self.font_small = pygame.font.SysFont(None, 18)
        self._btn_start = None
        self._btn_stop = None
        self._btn_reset = None
    
    def draw(self, surface):
        surface.fill((10, 10, 10))
        
        # Title
        title = self.font_large.render("Measurement", True, (0, 200, 50))
        surface.blit(title, (20, 10))
        
        # Get latest measurement data
        if self.app.logger.meas_buffer:
            latest = self.app.logger.meas_buffer[-1]
            v1 = latest.get('v1', 0.0)
            v2 = latest.get('v2', 0.0)
            i1 = latest.get('i1', 0.0)
            i2 = latest.get('i2', 0.0)
            state = latest.get('state', 'IDLE')
        else:
            v1, v2, i1, i2 = 0.0, 0.0, 0.0, 0.0
            state = 'IDLE'
        
        # State indicator
        state_color = {
            'IDLE': (200, 200, 200),
            'CHARGE': (100, 255, 100),
            'DISCHARGE': (255, 100, 100)
        }.get(state, (200, 200, 200))
        
        state_text = self.font_large.render(f"State: {state}", True, state_color)
        surface.blit(state_text, (40, 60))
        
        # Measurements
        y = 120
        lines = [
            f"V1: {v1:.3f} V",
            f"V2: {v2:.3f} V",
            f"I1: {i1:.3f} A",
            f"I2: {i2:.3f} A",
        ]
        
        for line in lines:
            surf = self.font_medium.render(line, True, (200, 200, 200))
            surface.blit(surf, (40, y))
            y += 35
        
        # Control buttons
        btn_w, btn_h = 90, 45
        y_btn = surface.get_height() - 80
        
        # Start button
        self._btn_start = pygame.Rect(20, y_btn, btn_w, btn_h)
        pygame.draw.rect(surface, (50, 100, 50), self._btn_start)
        start_text = self.font_small.render("START", True, (255, 255, 255))
        surface.blit(start_text, (self._btn_start.centerx - 25, self._btn_start.centery - 8))
        
        # Stop button
        self._btn_stop = pygame.Rect(125, y_btn, btn_w, btn_h)
        pygame.draw.rect(surface, (100, 50, 50), self._btn_stop)
        stop_text = self.font_small.render("STOP", True, (255, 255, 255))
        surface.blit(stop_text, (self._btn_stop.centerx - 22, self._btn_stop.centery - 8))
        
        # Reset button
        self._btn_reset = pygame.Rect(230, y_btn, btn_w, btn_h)
        pygame.draw.rect(surface, (50, 50, 100), self._btn_reset)
        reset_text = self.font_small.render("RESET", True, (255, 255, 255))
        surface.blit(reset_text, (self._btn_reset.centerx - 25, self._btn_reset.centery - 8))
    
    def on_touch(self, x: int, y: int):
        if self._btn_start and self._btn_start.collidepoint(x, y):
            if self.app.measurement:
                self.app.measurement.start_measurement()
                print("[UI] Measurement started")
        
        elif self._btn_stop and self._btn_stop.collidepoint(x, y):
            if self.app.measurement:
                self.app.measurement.stop_measurement()
                print("[UI] Measurement stopped")
        
        elif self._btn_reset and self._btn_reset.collidepoint(x, y):
            if self.app.measurement:
                self.app.measurement.reset()
                print("[UI] Measurement reset")


class PyGameApp:
    """Main Pygame application"""
    
    def __init__(self, port: str, baud: int = 115200, fullscreen: bool = False):
        pygame.init()
        
        # Display setup
        self.size = (480, 320)  # 3.5" TFT typical resolution
        flags = 0
        if fullscreen:
            flags = pygame.FULLSCREEN
        
        self.screen = pygame.display.set_mode(self.size, flags)
        pygame.display.set_caption("SUPERCAPFREEZER")
        self.clock = pygame.time.Clock()
        
        # App state
        self.running = True
        self.port = port
        self.baud = baud
        
        # Screens
        self.screens = []
        self.current_screen_idx = 0
        
        # Controllers and logger
        self.peltier = None
        self.measurement = None
        self.logger = None
    
    def set_peltier(self, peltier):
        """Set Peltier controller instance."""
        self.peltier = peltier
    
    def set_measurement(self, measurement):
        """Set Measurement controller instance."""
        self.measurement = measurement
    
    def set_logger(self, logger):
        """Set data logger instance."""
        self.logger = logger
        
        # Initialize screens
        self.screens = [
            DashboardScreen(self),
            GraphScreen(self),
            ControlScreen(self),
            MeasurementScreen(self),
            SettingsScreen(self),
        ]
    
    def run(self):
        """Main event loop"""
        last_touch_time = 0
        touch_start_x = 0
        
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_s:
                        self._save_csv()
                    elif event.key == pygame.K_LEFT:
                        self._prev_screen()
                    elif event.key == pygame.K_RIGHT:
                        self._next_screen()
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    touch_start_x = event.pos[0]
                    last_touch_time = time.time()
                
                elif event.type == pygame.MOUSEBUTTONUP:
                    # Detect swipe gesture
                    delta_x = event.pos[0] - touch_start_x
                    delta_t = time.time() - last_touch_time
                    
                    if delta_t < 0.3 and abs(delta_x) > 50:
                        if delta_x > 0:
                            self._prev_screen()
                        else:
                            self._next_screen()
                    else:
                        # Treat as tap
                        try:
                            self.screens[self.current_screen_idx].on_touch(event.pos[0], event.pos[1])
                        except Exception:
                            pass
            
            # Draw current screen
            if self.screens:
                self.screens[self.current_screen_idx].draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(30)
    
    def _next_screen(self):
        """Switch to next screen (with wrap)"""
        self.current_screen_idx = (self.current_screen_idx + 1) % len(self.screens)
    
    def _prev_screen(self):
        """Switch to previous screen (with wrap)"""
        self.current_screen_idx = (self.current_screen_idx - 1) % len(self.screens)
    
    def _save_csv(self):
        """Save current data to CSV."""
        filename = f"export_{int(time.time())}.csv"
        try:
            import csv
            data = self.logger.get_all()
            with open(filename, 'w', newline='') as f:
                if data:
                    fieldnames = list(data[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
            print(f"[APP] Exported {len(data)} temperature records to {filename}")
        except Exception as e:
            print(f"[APP ERROR] Export failed: {e}")
    
    def stop(self):
        """Stop app and cleanup"""
        self.running = False
        pygame.quit()
