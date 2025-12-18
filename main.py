import sys
import threading
import time
from collections import deque

try:
	import serial
except Exception:
	serial = None

import numpy as np
import pygame

# Starter template: SerialReader + pygame UI with rolling plot

class SerialReader(threading.Thread):
	"""Reads either a newline-delimited ASCII float from serial or simulates data.

	Use binary/fixed-packet mode for higher throughput (can be added later).
	"""

	def __init__(self, port=None, baud=115200, callback=None, simulate=False):
		super().__init__(daemon=True)
		self.port = port
		self.baud = baud
		self.callback = callback
		self.simulate = simulate or (serial is None)
		self._stop = threading.Event()

	def run(self):
		if self.simulate or not self.port:
			self._simulate()
			return
		try:
			with serial.Serial(self.port, self.baud, timeout=1) as ser:
				while not self._stop.is_set():
					line = ser.readline()
					if not line:
						continue
					try:
						s = line.decode('utf-8', errors='ignore').strip()
						# expect single float value (temperature)
						val = float(s)
						if self.callback:
							self.callback(val)
					except Exception:
						continue
		except Exception:
			# fallback to simulation on error
			self._simulate()

	def _simulate(self):
		t = 0.0
		while not self._stop.is_set():
			val = 25 + 3.0 * np.sin(t) + (np.random.rand() - 0.5) * 0.3
			if self.callback:
				self.callback(float(val))
			t += 0.05
			time.sleep(0.05)

	def stop(self):
		self._stop.set()


class App:
	def __init__(self, port=None, baud=115200, fullscreen=False):
		pygame.init()
		# default size matches many 3.5" displays; adjustable
		self.size = (480, 320)
		flags = 0
		if fullscreen:
			flags = pygame.FULLSCREEN
		self.screen = pygame.display.set_mode(self.size, flags)
		pygame.display.set_caption('Data Viewer')
		self.clock = pygame.time.Clock()

		self.running = True
		self.data = deque(maxlen=10000)
		self.start_time = time.time()
		self.port = port
		self.baud = baud

		self.reader = SerialReader(port=port, baud=baud, callback=self.push, simulate=(port is None))
		self.reader.start()

		self.font = pygame.font.SysFont(None, 20)

	def push(self, value):
		self.data.append((time.time() - self.start_time, value))

	def draw_plot(self, surface, rect):
		pygame.draw.rect(surface, (10, 10, 10), rect)
		if len(self.data) < 2:
			return
		times = np.array([d[0] for d in self.data])
		vals = np.array([d[1] for d in self.data])
		t_end = times[-1]
		window = 10.0  # seconds shown
		t_start = t_end - window
		mask = times >= t_start
		times = times[mask]
		vals = vals[mask]
		if times.size < 2:
			return
		xmin, xmax = times[0], times[-1]
		ymin, ymax = vals.min(), vals.max()
		if ymin == ymax:
			ymax = ymin + 1.0
		points = []
		for t, v in zip(times, vals):
			x = rect.left + int((t - xmin) / (xmax - xmin) * rect.width)
			y = rect.top + int((1.0 - (v - ymin) / (ymax - ymin)) * rect.height)
			points.append((x, y))
		if len(points) >= 2:
			pygame.draw.lines(surface, (0, 200, 50), False, points, 2)
		# axis labels
		lbl_min = self.font.render(f"{ymin:.2f}", True, (200, 200, 200))
		lbl_max = self.font.render(f"{ymax:.2f}", True, (200, 200, 200))
		surface.blit(lbl_max, (rect.left + 4, rect.top + 4))
		surface.blit(lbl_min, (rect.left + 4, rect.bottom - 18))

	def run(self):
		while self.running:
			for ev in pygame.event.get():
				if ev.type == pygame.QUIT:
					self.running = False
				if ev.type == pygame.KEYDOWN:
					if ev.key == pygame.K_ESCAPE:
						self.running = False
					if ev.key == pygame.K_s:
						self.save_csv()

			self.screen.fill((0, 0, 0))
			plot_rect = pygame.Rect(10, 10, self.size[0] - 140, self.size[1] - 20)
			info_rect = pygame.Rect(self.size[0] - 120, 10, 110, self.size[1] - 20)
			self.draw_plot(self.screen, plot_rect)

			pygame.draw.rect(self.screen, (30, 30, 30), info_rect)
			y = info_rect.top + 8
			if self.data:
				t, v = self.data[-1]
				lines = [f"Temp: {v:.2f} C", f"Uptime: {int(time.time()-self.start_time)} s", f"Samples: {len(self.data)}"]
			else:
				lines = ["No data", f"Uptime: {int(time.time()-self.start_time)} s", "Samples: 0"]
			for txt in lines:
				surf = self.font.render(txt, True, (220, 220, 220))
				self.screen.blit(surf, (info_rect.left + 8, y))
				y += 26

			pygame.display.flip()
			self.clock.tick(30)

		self.reader.stop()
		pygame.quit()

	def save_csv(self):
		fname = f"log_{int(time.time())}.csv"
		try:
			with open(fname, 'w') as f:
				f.write('time_s,temperature\n')
				for t, v in self.data:
					f.write(f"{t:.6f},{v:.6f}\n")
			print('Saved', fname)
		except Exception as e:
			print('Save error', e)


if __name__ == '__main__':
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument('--port', help='serial port (e.g. /dev/ttyACM0)')
	parser.add_argument('--baud', type=int, default=115200)
	parser.add_argument('--fullscreen', action='store_true')
	args = parser.parse_args()

	app = App(port=args.port, baud=args.baud, fullscreen=args.fullscreen)
	app.run()