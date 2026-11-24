import time
from PySide6.QtCore import Qt, Signal, QRectF, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
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
    and ultra-smooth 60 FPS sub-pixel continuous timeline interpolation.
    """
    seek_requested = Signal(float)  # target seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self._target_position = 0.0
        self._display_position = 0.0
        self._duration = 0.0
        self._is_dragging = False
        self._hovered = False
        self._target_drag_ratio = 0.0
        self._display_drag_ratio = 0.0
        self._hover_progress = 0.0  # 0.0 to 1.0
        self._is_playing = False
        self._last_tick_time = time.monotonic()

        self._accent_color = QColor("#1DB954")
        self._track_color = QColor(255, 255, 255, 38)
        self._text_color = QColor(255, 255, 255, 160)

        # 60 FPS render & interpolation timer (~16ms)
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._on_anim_tick)
        self._anim_timer.start()

        self.setFixedHeight(24)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_playing(self, is_playing: bool):
        self._is_playing = is_playing
        self._last_tick_time = time.monotonic()
        self.update()

    def _on_anim_tick(self):
        now = time.monotonic()
        dt = min(0.1, max(0.001, now - self._last_tick_time))
        self._last_tick_time = now

        needs_update = False

        # 1. Timeline advance when playing
        if self._is_playing and not self._is_dragging and self._duration > 0:
            if self._target_position < self._duration:
                self._target_position = min(self._duration, self._target_position + dt)

        # 2. Smooth exponential lerp of display position toward target
        if not self._is_dragging:
            pos_diff = self._target_position - self._display_position
            if abs(pos_diff) > 0.002:
                # Smooth fluid easing factor
                lerp_speed = 14.0 if abs(pos_diff) > 0.5 else 9.0
                self._display_position += pos_diff * min(1.0, dt * lerp_speed)
                needs_update = True
            else:
                self._display_position = self._target_position
        else:
            # Smooth drag scrubbing
            drag_diff = self._target_drag_ratio - self._display_drag_ratio
            if abs(drag_diff) > 0.001:
                self._display_drag_ratio += drag_diff * min(1.0, dt * 22.0)
                needs_update = True
            else:
                self._display_drag_ratio = self._target_drag_ratio

        # 3. Smooth hover scale progress
        target_hover = 1.0 if (self._hovered or self._is_dragging) else 0.0
        hover_diff = target_hover - self._hover_progress
        if abs(hover_diff) > 0.01:
            self._hover_progress += hover_diff * min(1.0, dt * 15.0)
            needs_update = True
        else:
            self._hover_progress = target_hover

        if needs_update or self._is_playing:
            self.update()

    def set_timeline(self, position: float, duration: float):
        if not self._is_dragging:
            self._duration = max(0.0, duration)
            self._last_tick_time = time.monotonic()

            pos_diff = abs(self._target_position - position)
            if self._target_position == 0.0 or pos_diff > 1.2:
                # Real seek or track start: update target directly
                self._target_position = max(0.0, min(self._duration, position))
                if pos_diff > 3.0 or self._display_position == 0.0:
                    self._display_position = self._target_position
            else:
                # Soft drift correction without visual jump
                self._target_position += (position - self._target_position) * 0.18
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
            target_sec = self._target_drag_ratio * self._duration
            self._target_position = target_sec
            self._display_position = target_sec
            self._last_tick_time = time.monotonic()
            self.seek_requested.emit(target_sec)
            self.update()

    def _update_drag_pos(self, x: float):
        w = self.width()
        if w > 0:
            ratio = max(0.0, min(1.0, x / w))
            self._target_drag_ratio = ratio
            if self._display_drag_ratio == 0.0:
                self._display_drag_ratio = ratio
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Dynamic animated heights
        bar_h = 3.4 + 1.8 * self._hover_progress
        bar_y = 6.0 - (0.9 * self._hover_progress)

        # Current smooth ratio
        if self._is_dragging:
            ratio = self._display_drag_ratio
            cur_pos = self._display_drag_ratio * self._duration
        else:
            ratio = (self._display_position / self._duration) if self._duration > 0 else 0.0
            ratio = max(0.0, min(1.0, ratio))
            cur_pos = self._display_position

        # 1. Background Track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._track_color))
        track_rect = QRectF(0.0, bar_y, float(w), bar_h)
        painter.drawRoundedRect(track_rect, bar_h / 2.0, bar_h / 2.0)

        # 2. Filled Progress with Accent Color
        fill_w = max(bar_h, w * ratio)
        if fill_w > 0:
            fill_rect = QRectF(0.0, bar_y, float(fill_w), bar_h)
            painter.setBrush(QBrush(self._accent_color))
            painter.drawRoundedRect(fill_rect, bar_h / 2.0, bar_h / 2.0)

        # 3. Floating Bloom Thumb
        if self._hover_progress > 0.02:
            thumb_radius = 4.2 * self._hover_progress
            thumb_x = fill_w
            thumb_y = bar_y + bar_h / 2.0

            # Subtle glow around thumb
            glow_col = QColor(self._accent_color.red(), self._accent_color.green(), self._accent_color.blue(), int(90 * self._hover_progress))
            painter.setBrush(QBrush(glow_col))
            painter.drawEllipse(QRectF(thumb_x - thumb_radius - 2, thumb_y - thumb_radius - 2, (thumb_radius + 2) * 2, (thumb_radius + 2) * 2))

            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(QRectF(thumb_x - thumb_radius, thumb_y - thumb_radius, thumb_radius * 2, thumb_radius * 2))

        # 4. Antialiased Timestamps
        painter.setFont(QFont("Segoe UI Variable Text", 8))
        painter.setPen(self._text_color)
        pos_str = format_seconds(cur_pos)
        dur_str = format_seconds(self._duration)

        text_y = int(bar_y + bar_h + 10)
        painter.drawText(0, text_y, pos_str)

        # Right aligned duration
        dur_w = painter.fontMetrics().horizontalAdvance(dur_str)
        painter.drawText(int(w - dur_w), text_y, dur_str)
