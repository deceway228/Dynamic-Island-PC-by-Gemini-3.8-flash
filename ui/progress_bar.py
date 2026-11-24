import time
from PySide6.QtCore import Qt, Signal, QRectF, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget

def format_seconds(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

class MinimalProgressBar(QWidget):
    """
    Sleek, interactive progress bar with motion hover, scrubbing,
    and continuous smooth timeline interpolation.
    """
    seek_requested = Signal(float)  # target seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self._position = 0.0
        self._duration = 0.0
        self._is_dragging = False
        self._hovered = False
        self._drag_ratio = 0.0
        self._is_playing = False
        self._last_tick_time = time.monotonic()
        self._accent_color = QColor("#1DB954")
        self._track_color = QColor(255, 255, 255, 38)
        self._text_color = QColor(255, 255, 255, 160)

        # Smooth local tick (~30 FPS) for buttery smooth progress between GSMTC snapshots
        self._smooth_timer = QTimer(self)
        self._smooth_timer.setInterval(33)
        self._smooth_timer.timeout.connect(self._on_smooth_tick)

        self.setFixedHeight(24)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_playing(self, is_playing: bool):
        self._is_playing = is_playing
        self._last_tick_time = time.monotonic()
        if is_playing and not self._smooth_timer.isActive():
            self._smooth_timer.start()
        elif not is_playing and self._smooth_timer.isActive():
            self._smooth_timer.stop()
        self.update()

    def _on_smooth_tick(self):
        now = time.monotonic()
        dt = now - self._last_tick_time
        self._last_tick_time = now

        if self._is_playing and not self._is_dragging and self._duration > 0:
            if self._position < self._duration:
                self._position = min(self._duration, self._position + dt)
                self.update()

    def set_timeline(self, position: float, duration: float):
        if not self._is_dragging:
            self._duration = max(0.0, duration)
            self._last_tick_time = time.monotonic()

            if self._position == 0.0 or abs(self._position - position) > 0.8:
                self._position = max(0.0, min(self._duration, position))
            else:
                # Soft correction to eliminate jitter while keeping smooth movement
                self._position += (position - self._position) * 0.4
            self.update()

    def set_accent_color(self, color: QColor):
        self._accent_color = color
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._duration > 0:
            self._is_dragging = True
            self._update_drag_pos(event.position().x())

    def mouseMoveEvent(self, event):
        if self._is_dragging and self._duration > 0:
            self._update_drag_pos(event.position().x())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False
            target_sec = self._drag_ratio * self._duration
            self._position = target_sec
            self._last_tick_time = time.monotonic()
            self.seek_requested.emit(target_sec)
            self.update()

    def _update_drag_pos(self, x: float):
        margin_x = 0
        w = self.width() - 2 * margin_x
        if w > 0:
            ratio = max(0.0, min(1.0, (x - margin_x) / w))
            self._drag_ratio = ratio
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        bar_h = 5.0 if (self._hovered or self._is_dragging) else 3.5
        bar_y = 6.0

        # Current ratio
        if self._is_dragging:
            ratio = self._drag_ratio
            cur_pos = self._drag_ratio * self._duration
        else:
            ratio = (self._position / self._duration) if self._duration > 0 else 0.0
            ratio = max(0.0, min(1.0, ratio))
            cur_pos = self._position

        # Draw background track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._track_color))
        track_rect = QRectF(0, bar_y, w, bar_h)
        painter.drawRoundedRect(track_rect, bar_h / 2.0, bar_h / 2.0)

        # Draw filled progress
        fill_w = max(bar_h, w * ratio)
        if fill_w > 0:
            fill_rect = QRectF(0, bar_y, fill_w, bar_h)
            painter.setBrush(QBrush(self._accent_color))
            painter.drawRoundedRect(fill_rect, bar_h / 2.0, bar_h / 2.0)

        # Draw thumb handle on hover or dragging
        if self._hovered or self._is_dragging:
            thumb_radius = 5.0 if self._is_dragging else 4.0
            thumb_x = fill_w
            thumb_y = bar_y + bar_h / 2.0
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(QRectF(thumb_x - thumb_radius, thumb_y - thumb_radius, thumb_radius * 2, thumb_radius * 2))

        # Draw timestamps
        painter.setFont(QFont("Segoe UI Variable Text", 8))
        painter.setPen(self._text_color)
        pos_str = format_seconds(cur_pos)
        dur_str = format_seconds(self._duration)
        
        text_y = int(bar_y + bar_h + 10)
        painter.drawText(0, text_y, pos_str)
        
        # Right aligned duration
        dur_w = painter.fontMetrics().horizontalAdvance(dur_str)
        painter.drawText(int(w - dur_w), text_y, dur_str)
