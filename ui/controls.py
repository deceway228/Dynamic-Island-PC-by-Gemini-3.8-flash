from PySide6.QtCore import Qt, Signal, QRectF, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath
from PySide6.QtWidgets import QWidget

class MotionIconButton(QWidget):
    """
    Minimalist vector icon button with smooth hover glow and press feedback.
    """
    clicked = Signal()

    def __init__(self, icon_type: str = "play", size: int = 32, parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self._btn_size = size
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._hover_progress = 0.0
        self._press_progress = 0.0
        self._icon_color = QColor(255, 255, 255, 220)
        self._accent_color = QColor("#1DB954")
        self._is_down = False

        # Property animation for hover
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(180)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_size(self, size: int):
        s = max(16, int(size))
        if self._btn_size != s:
            self._btn_size = s
            self.setFixedSize(s, s)
            self.update()

    def get_hover_progress(self) -> float:
        return self._hover_progress

    def set_hover_progress(self, val: float):
        self._hover_progress = val
        self.update()

    hoverProgress = Property(float, get_hover_progress, set_hover_progress)

    def set_icon_type(self, icon_type: str):
        if self.icon_type != icon_type:
            self.icon_type = icon_type
            self.update()

    def set_accent_color(self, color: QColor):
        self._accent_color = color
        self.update()

    def set_icon_color(self, color: QColor):
        self._icon_color = color
        self.update()

    def enterEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()

    def leaveEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_down = True
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_down:
            self._is_down = False
            self.update()
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        center_x = w / 2.0
        center_y = h / 2.0

        # Draw hover background circle
        if self._hover_progress > 0.01:
            bg_alpha = int(45 * self._hover_progress)
            bg_color = QColor(255, 255, 255, bg_alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_color))
            r = (w / 2.0) - 2
            painter.drawEllipse(QRectF(center_x - r, center_y - r, r * 2, r * 2))

        # Pressed scale
        if self._is_down:
            painter.translate(center_x, center_y)
            painter.scale(0.90, 0.90)
            painter.translate(-center_x, -center_y)

        # Draw icon
        color = self._icon_color if self._hover_progress < 0.8 else QColor(255, 255, 255)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)

        if self.icon_type == "play":
            # Play triangle
            pw = w * 0.36
            ph = h * 0.42
            x_left = center_x - pw * 0.4
            path = QPainterPath()
            path.moveTo(x_left, center_y - ph / 2.0)
            path.lineTo(x_left + pw, center_y)
            path.lineTo(x_left, center_y + ph / 2.0)
            path.closeSubpath()
            painter.drawPath(path)

        elif self.icon_type == "pause":
            # Two rounded capsules
            bar_w = max(2.5, w * 0.11)
            bar_h = h * 0.38
            gap = w * 0.10
            r = bar_w / 2.0
            
            x1 = center_x - gap / 2.0 - bar_w
            x2 = center_x + gap / 2.0
            y = center_y - bar_h / 2.0
            
            painter.drawRoundedRect(QRectF(x1, y, bar_w, bar_h), r, r)
            painter.drawRoundedRect(QRectF(x2, y, bar_w, bar_h), r, r)

        elif self.icon_type == "next":
            # Triangle + bar
            tw = w * 0.24
            th = h * 0.34
            bar_w = max(2.0, w * 0.08)
            gap = 2.0
            total_w = tw + gap + bar_w
            x_start = center_x - total_w / 2.0

            path = QPainterPath()
            path.moveTo(x_start, center_y - th / 2.0)
            path.lineTo(x_start + tw, center_y)
            path.lineTo(x_start, center_y + th / 2.0)
            path.closeSubpath()
            painter.drawPath(path)

            bx = x_start + tw + gap
            painter.drawRoundedRect(QRectF(bx, center_y - th / 2.0, bar_w, th), bar_w / 2.0, bar_w / 2.0)

        elif self.icon_type == "prev":
            # Bar + Triangle (pointing left)
            tw = w * 0.24
            th = h * 0.34
            bar_w = max(2.0, w * 0.08)
            gap = 2.0
            total_w = tw + gap + bar_w
            x_start = center_x - total_w / 2.0

            painter.drawRoundedRect(QRectF(x_start, center_y - th / 2.0, bar_w, th), bar_w / 2.0, bar_w / 2.0)

            tx = x_start + bar_w + gap
            path = QPainterPath()
            path.moveTo(tx + tw, center_y - th / 2.0)
            path.lineTo(tx, center_y)
            path.lineTo(tx + tw, center_y + th / 2.0)
            path.closeSubpath()
            painter.drawPath(path)

        elif self.icon_type == "settings":
            # Sleek minimal gear or 3 dots
            dot_r = 2.2
            spacing = 6.0
            painter.drawEllipse(QRectF(center_x - spacing - dot_r, center_y - dot_r, dot_r * 2, dot_r * 2))
            painter.drawEllipse(QRectF(center_x - dot_r, center_y - dot_r, dot_r * 2, dot_r * 2))
            painter.drawEllipse(QRectF(center_x + spacing - dot_r, center_y - dot_r, dot_r * 2, dot_r * 2))

        elif self.icon_type == "close":
            # Minimalistic X
            pen = QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            sz = w * 0.22
            painter.drawLine(center_x - sz, center_y - sz, center_x + sz, center_y + sz)
            painter.drawLine(center_x + sz, center_y - sz, center_x - sz, center_y + sz)

