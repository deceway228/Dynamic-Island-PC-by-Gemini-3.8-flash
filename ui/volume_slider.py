import time
from PySide6.QtCore import Qt, Signal, QRectF, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from PySide6.QtWidgets import QWidget

from core.volume_manager import VolumeManager

class MinimalVolumeSlider(QWidget):
    """
    Sleek, interactive per-app volume slider with 60 FPS fluid motion,
    active player badge, and click-to-mute.
    """
    volume_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.vol_mgr = VolumeManager.get_instance()
        self._target_volume = self.vol_mgr.get_volume()
        self._display_volume = self._target_volume
        self._is_muted = self.vol_mgr.get_mute()
        self._source_label = self.vol_mgr.get_source_label()
        self._is_app = self.vol_mgr.is_app_volume()

        self._is_dragging = False
        self._hovered = False
        self._hover_progress = 0.0
        self._last_tick_time = time.monotonic()

        self._accent_color = QColor("#1DB954")
        self._track_color = QColor(255, 255, 255, 35)
        self._text_color = QColor(255, 255, 255, 170)
        self._icon_color = QColor(255, 255, 255, 210)

        # 60 FPS animation timer (~16ms)
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(16)
        self._anim_timer.timeout.connect(self._on_anim_tick)
        self._anim_timer.start()

        # Background sync timer (~350ms) to detect changes from Windows / app
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(350)
        self._sync_timer.timeout.connect(self._sync_system_volume)
        self._sync_timer.start()

        self.setFixedHeight(22)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_accent_color(self, color: QColor):
        self._accent_color = color
        self.update()

    def _sync_system_volume(self):
        if not self._is_dragging:
            cur_vol = self.vol_mgr.get_volume()
            cur_mute = self.vol_mgr.get_mute()
            self._source_label = self.vol_mgr.get_source_label()
            self._is_app = self.vol_mgr.is_app_volume()

            if abs(cur_vol - self._target_volume) > 0.008 or cur_mute != self._is_muted:
                self._target_volume = cur_vol
                self._is_muted = cur_mute
                self.update()

    def _on_anim_tick(self):
        now = time.monotonic()
        dt = min(0.1, max(0.001, now - self._last_tick_time))
        self._last_tick_time = now

        needs_update = False

        # Smooth volume gliding
        vol_diff = self._target_volume - self._display_volume
        if abs(vol_diff) > 0.001:
            lerp_speed = 22.0 if self._is_dragging else 14.0
            self._display_volume += vol_diff * min(1.0, dt * lerp_speed)
            needs_update = True
        else:
            self._display_volume = self._target_volume

        # Smooth hover expansion
        target_hover = 1.0 if (self._hovered or self._is_dragging) else 0.0
        hover_diff = target_hover - self._hover_progress
        if abs(hover_diff) > 0.01:
            self._hover_progress += hover_diff * min(1.0, dt * 15.0)
            needs_update = True
        else:
            self._hover_progress = target_hover

        if needs_update:
            self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            x = event.position().x()
            icon_area_w = 24.0
            if x <= icon_area_w:
                # Clicked speaker icon: toggle mute
                self._is_muted = self.vol_mgr.toggle_mute()
                self.update()
            else:
                self._is_dragging = True
                self._update_slider_from_pos(x)

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            self._update_slider_from_pos(event.position().x())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False
            self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        step = 0.02 if delta > 0 else -0.02
        new_vol = self.vol_mgr.step_volume(step)
        self._target_volume = new_vol
        self._is_muted = self.vol_mgr.get_mute()
        self._source_label = self.vol_mgr.get_source_label()
        self._is_app = self.vol_mgr.is_app_volume()
        self.volume_changed.emit(new_vol)
        self.update()

    def _update_slider_from_pos(self, x: float):
        icon_w = 26.0
        text_w = 56.0
        slider_x = icon_w
        slider_w = self.width() - icon_w - text_w
        if slider_w > 0:
            ratio = max(0.0, min(1.0, (x - slider_x) / slider_w))
            self._target_volume = ratio
            self.vol_mgr.set_volume(ratio)
            if self._is_muted and ratio > 0:
                self.vol_mgr.set_mute(False)
                self._is_muted = False
            self.volume_changed.emit(ratio)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        icon_w = 22.0
        text_w = 56.0
        slider_x = icon_w + 4.0
        slider_w = w - slider_x - text_w
        slider_h = 3.2 + 1.6 * self._hover_progress
        slider_y = (h - slider_h) / 2.0

        # 1. Draw Speaker Icon
        self._draw_speaker_icon(painter, 0, (h - 16) / 2.0, 16, 16)

        # 2. Draw Slider Track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._track_color))
        painter.drawRoundedRect(QRectF(slider_x, slider_y, slider_w, slider_h), slider_h / 2.0, slider_h / 2.0)

        # 3. Draw Filled Progress
        eff_vol = 0.0 if self._is_muted else self._display_volume
        fill_w = max(slider_h, slider_w * eff_vol)
        if fill_w > 0:
            fill_col = QColor(160, 160, 165) if self._is_muted else self._accent_color
            painter.setBrush(QBrush(fill_col))
            painter.drawRoundedRect(QRectF(slider_x, slider_y, fill_w, slider_h), slider_h / 2.0, slider_h / 2.0)

        # 4. Draw Thumb on hover/drag
        if self._hover_progress > 0.02:
            thumb_r = 3.2 + 1.2 * self._hover_progress
            thumb_x = slider_x + fill_w
            thumb_y = slider_y + slider_h / 2.0

            # Subtle glow
            glow_col = QColor(self._accent_color.red(), self._accent_color.green(), self._accent_color.blue(), int(80 * self._hover_progress))
            painter.setBrush(QBrush(glow_col))
            painter.drawEllipse(QRectF(thumb_x - thumb_r - 2, thumb_y - thumb_r - 2, (thumb_r + 2) * 2, (thumb_r + 2) * 2))

            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(QRectF(thumb_x - thumb_r, thumb_y - thumb_r, thumb_r * 2, thumb_r * 2))

        # 5. Draw Percentage & Source Badge
        painter.setFont(QFont("Segoe UI Variable Text", 8, QFont.Weight.Medium))
        painter.setPen(self._text_color)
        pct_text = "0%" if self._is_muted else f"{int(self._display_volume * 100)}%"

        # If app-specific, display e.g. "Edge • 80%" or "Spotify • 75%"
        source = self._source_label if self._source_label else "PC"
        full_text = f"{source} {pct_text}"

        text_y = int((h + painter.fontMetrics().ascent() - painter.fontMetrics().descent()) / 2.0)
        painter.drawText(int(w - text_w + 2), text_y, full_text)

    def _draw_speaker_icon(self, painter: QPainter, x: float, y: float, w: float, h: float):
        painter.save()
        painter.translate(x, y)

        col = QColor(255, 100, 100) if self._is_muted else (self._icon_color if not self._hovered else QColor(255, 255, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(col))

        # Cone body
        path = QPainterPath()
        path.moveTo(1, 5)
        path.lineTo(4, 5)
        path.lineTo(8, 2)
        path.lineTo(8, 14)
        path.lineTo(4, 11)
        path.lineTo(1, 11)
        path.closeSubpath()
        painter.drawPath(path)

        # Sound waves or Mute cross
        if self._is_muted or self._display_volume <= 0.01:
            pen = QPen(col, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(10, 5, 15, 11)
            painter.drawLine(15, 5, 10, 11)
        else:
            pen = QPen(col, 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            # Small arc
            painter.drawArc(QRectF(7, 5, 4, 6), -60 * 16, 120 * 16)
            # Large arc if volume >= 0.5
            if self._display_volume >= 0.5:
                painter.drawArc(QRectF(6, 3, 8, 10), -60 * 16, 120 * 16)

        painter.restore()
