import math
import random
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath
from PySide6.QtWidgets import QWidget

class MotionVisualizer(QWidget):
    """
    Animated minimalist sound visualizer with customizable styles:
    - liquid_bars: Sleek organic jumping bars with rounded caps
    - wave: Flowing sine wave curve
    - dots: Modern pulsing geometric dots
    """
    def __init__(self, bar_count: int = 5, style: str = "liquid_bars", parent=None):
        super().__init__(parent)
        self.bar_count = bar_count
        self.visualizer_style = style
        self.is_playing = False
        self.accent_color = QColor("#1DB954")
        self.sensitivity = 1.0

        # Bar heights interpolation: [current, target]
        self._heights = [0.15 for _ in range(self.bar_count)]
        self._target_heights = [0.15 for _ in range(self.bar_count)]
        self._phases = [i * 0.8 for i in range(self.bar_count)]
        self._time = 0.0

        # Animation timer (approx 60 FPS for buttery motion)
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._update_animation)
        self._timer.start()

        self.setMinimumSize(24, 16)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_playing(self, playing: bool):
        self.is_playing = playing
        if not playing:
            for i in range(self.bar_count):
                self._target_heights[i] = 0.12

    def set_accent_color(self, color: QColor):
        self.accent_color = color
        self.update()

    def set_style(self, style: str):
        self.visualizer_style = style
        self.update()

    def _update_animation(self):
        self._time += 0.065
        
        if self.is_playing:
            # Generate rhythmic, organic heights with multi-frequency sines
            for i in range(self.bar_count):
                phase = self._phases[i]
                v1 = math.sin(self._time * 2.8 + phase) * 0.4
                v2 = math.cos(self._time * 4.2 - phase * 0.5) * 0.25
                v3 = math.sin(self._time * 1.5 + phase * 1.2) * 0.2
                base = 0.5 + v1 + v2 + v3
                clamped = max(0.12, min(0.98, base * self.sensitivity))
                self._target_heights[i] = clamped
        else:
            # Idle/paused: settle down to gentle resting height
            for i in range(self.bar_count):
                self._target_heights[i] = 0.12

        # Smooth spring-like lerp to target heights
        lerp_factor = 0.22 if self.is_playing else 0.12
        needs_redraw = False
        for i in range(self.bar_count):
            diff = self._target_heights[i] - self._heights[i]
            if abs(diff) > 0.005:
                self._heights[i] += diff * lerp_factor
                needs_redraw = True

        if needs_redraw:
            self.update()

    def paintEvent(self, event):
        if self.visualizer_style == "off":
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        if self.visualizer_style == "wave":
            self._paint_wave(painter, w, h)
        elif self.visualizer_style == "dots":
            self._paint_dots(painter, w, h)
        else:
            self._paint_bars(painter, w, h)

    def _paint_bars(self, painter: QPainter, w: float, h: float):
        total_bars = self.bar_count
        spacing = 3.0
        bar_width = max(2.5, (w - (total_bars - 1) * spacing) / total_bars)
        total_width = total_bars * bar_width + (total_bars - 1) * spacing
        start_x = (w - total_width) / 2.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.accent_color))

        for i in range(total_bars):
            bar_h = max(3.0, h * self._heights[i])
            x = start_x + i * (bar_width + spacing)
            y = (h - bar_h) / 2.0  # Center vertically for dynamic wave look
            
            radius = bar_width / 2.0
            rect = QRectF(x, y, bar_width, bar_h)
            painter.drawRoundedRect(rect, radius, radius)

    def _paint_wave(self, painter: QPainter, w: float, h: float):
        pen = QPen(self.accent_color, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        path = QPainterPath()
        points = 20
        mid_y = h / 2.0
        amp = (h / 2.5) * (0.8 if self.is_playing else 0.15)

        for i in range(points + 1):
            norm_x = i / points
            x = norm_x * w
            freq = 2.5
            y = mid_y + math.sin(norm_x * math.pi * freq - self._time * 3.0) * amp
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        painter.drawPath(path)

    def _paint_dots(self, painter: QPainter, w: float, h: float):
        total_dots = min(4, self.bar_count)
        spacing = 5.0
        dot_d = min(6.0, (w - (total_dots - 1) * spacing) / total_dots)
        total_w = total_dots * dot_d + (total_dots - 1) * spacing
        start_x = (w - total_w) / 2.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.accent_color))

        for i in range(total_dots):
            scale = 0.5 + 0.5 * self._heights[i]
            cur_d = dot_d * scale
            x = start_x + i * (dot_d + spacing) + (dot_d - cur_d) / 2.0
            y = (h - cur_d) / 2.0
            painter.drawEllipse(QRectF(x, y, cur_d, cur_d))

