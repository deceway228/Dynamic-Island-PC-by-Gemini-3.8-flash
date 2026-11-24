from PySide6.QtCore import Qt, Signal, QRectF, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from PySide6.QtWidgets import QWidget

from core.volume_manager import VolumeManager

class MinimalVolumeSlider(QWidget):
    """
    Sleek, interactive volume slider with speaker icon,
    live system volume synchronization, and click-to-mute.
    """
    volume_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.vol_mgr = VolumeManager.get_instance()
        self._volume = self.vol_mgr.get_volume()
        self._is_muted = self.vol_mgr.get_mute()
        self._is_dragging = False
        self._hovered = False
        self._accent_color = QColor("#1DB954")
        self._track_color = QColor(255, 255, 255, 35)
        self._text_color = QColor(255, 255, 255, 170)
        self._icon_color = QColor(255, 255, 255, 210)

        # Periodically sync with Windows Master Volume
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(400)
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
            if abs(cur_vol - self._volume) > 0.01 or cur_mute != self._is_muted:
                self._volume = cur_vol
                self._is_muted = cur_mute
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
        self._volume = new_vol
        self._is_muted = self.vol_mgr.get_mute()
        self.volume_changed.emit(new_vol)
        self.update()

    def _update_slider_from_pos(self, x: float):
        icon_w = 26.0
        text_w = 34.0
        slider_x = icon_w
        slider_w = self.width() - icon_w - text_w
        if slider_w > 0:
            ratio = max(0.0, min(1.0, (x - slider_x) / slider_w))
            self._volume = ratio
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

        icon_w = 24.0
        text_w = 32.0
        slider_x = icon_w + 2.0
        slider_w = w - slider_x - text_w
        slider_h = 4.5 if (self._hovered or self._is_dragging) else 3.2
        slider_y = (h - slider_h) / 2.0

        # 1. Draw Speaker Icon
        self._draw_speaker_icon(painter, 0, (h - 16) / 2.0, 16, 16)

        # 2. Draw Slider Track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._track_color))
        painter.drawRoundedRect(QRectF(slider_x, slider_y, slider_w, slider_h), slider_h / 2.0, slider_h / 2.0)

        # 3. Draw Filled Progress
        eff_vol = 0.0 if self._is_muted else self._volume
        fill_w = max(slider_h, slider_w * eff_vol)
        if fill_w > 0:
            fill_col = QColor(160, 160, 165) if self._is_muted else self._accent_color
            painter.setBrush(QBrush(fill_col))
            painter.drawRoundedRect(QRectF(slider_x, slider_y, fill_w, slider_h), slider_h / 2.0, slider_h / 2.0)

        # 4. Draw Thumb on hover/drag
        if self._hovered or self._is_dragging:
            thumb_r = 4.5 if self._is_dragging else 3.8
            thumb_x = slider_x + fill_w
            thumb_y = slider_y + slider_h / 2.0
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(QRectF(thumb_x - thumb_r, thumb_y - thumb_r, thumb_r * 2, thumb_r * 2))

        # 5. Draw Percentage Text
        painter.setFont(QFont("Segoe UI Variable Text", 8, QFont.Weight.Medium))
        painter.setPen(self._text_color)
        pct_text = "0%" if self._is_muted else f"{int(self._volume * 100)}%"
        text_y = int((h + painter.fontMetrics().ascent() - painter.fontMetrics().descent()) / 2.0)
        painter.drawText(int(w - text_w + 4), text_y, pct_text)

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
        if self._is_muted or self._volume <= 0.01:
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
            if self._volume >= 0.5:
                painter.drawArc(QRectF(6, 3, 8, 10), -60 * 16, 120 * 16)

        painter.restore()

