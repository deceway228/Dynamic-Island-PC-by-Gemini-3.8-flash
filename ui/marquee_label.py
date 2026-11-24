from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QFont, QColor, QFontMetrics
from PySide6.QtWidgets import QWidget

class MarqueeLabel(QWidget):
    """
    Minimalist text label with dynamic font scaling and smooth marquee
    scrolling when text overflows the container width.
    """
    def __init__(self, text: str = "", font_size: int = 12, bold: bool = False, color: str = "#ffffff", parent=None):
        super().__init__(parent)
        self._text = text
        self._color = QColor(color)
        self._font = QFont("Segoe UI Variable Display", font_size)
        if bold:
            self._font.setBold(True)
            self._font.setWeight(QFont.Weight.DemiBold)
        else:
            self._font.setWeight(QFont.Weight.Normal)

        self._offset = 0.0
        self._pause_ticks = 40
        self._speed = 1.0
        self._is_overflowing = False

        self._timer = QTimer(self)
        self._timer.setInterval(25)  # 40 fps
        self._timer.timeout.connect(self._scroll_step)

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_text(self, text: str):
        if self._text != text:
            self._text = text
            self._offset = 0.0
            self._pause_ticks = 40
            self._check_overflow()
            self.update()

    def set_color(self, color: str or QColor):
        self._color = QColor(color)
        self.update()

    def set_font_size(self, size: int):
        target_size = max(6, int(size))
        if self._font.pointSize() != target_size:
            self._font.setPointSize(target_size)
            self._check_overflow()
            self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._check_overflow()

    def _check_overflow(self):
        if not self._text:
            self._is_overflowing = False
            self._offset = 0.0
            if self._timer.isActive():
                self._timer.stop()
            return

        fm = QFontMetrics(self._font)
        text_w = fm.horizontalAdvance(self._text)
        avail_w = self.width()

        if text_w > avail_w and avail_w > 10:
            self._is_overflowing = True
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._is_overflowing = False
            self._offset = 0.0
            if self._timer.isActive():
                self._timer.stop()

    def _scroll_step(self):
        if not self._is_overflowing:
            return

        if self._pause_ticks > 0:
            self._pause_ticks -= 1
            return

        fm = QFontMetrics(self._font)
        text_w = fm.horizontalAdvance(self._text)
        max_scroll = text_w - self.width() + 16

        self._offset += 0.85 * self._speed
        if self._offset >= max_scroll:
            self._offset = max_scroll
            self._pause_ticks = 60
            self._offset = 0.0
            self._pause_ticks = 45

        self.update()

    def paintEvent(self, event):
        if not self._text:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setFont(self._font)
        painter.setPen(self._color)

        fm = QFontMetrics(self._font)
        baseline = (self.height() + fm.ascent() - fm.descent()) / 2.0

        if not self._is_overflowing:
            # When text fits, draw left aligned
            painter.drawText(0, int(baseline), self._text)
        else:
            # Clip and translate
            painter.setClipRect(self.rect())
            painter.drawText(int(-self._offset), int(baseline), self._text)
