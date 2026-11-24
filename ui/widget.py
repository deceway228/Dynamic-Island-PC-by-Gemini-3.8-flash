import math
import time
from typing import Optional
from PySide6.QtCore import (
    Qt, QRect, QRectF, QPoint, QTimer, QPropertyAnimation, QEasingCurve,
    Signal, Property
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QPixmap, QImage,
    QFont, QLinearGradient, QRadialGradient, QCursor, QAction
)
from PySide6.QtWidgets import (
    QWidget, QApplication, QMenu
)

from core.config_manager import ConfigManager
from core.media_manager import MediaWorker
from ui.visualizer import MotionVisualizer
from ui.marquee_label import MarqueeLabel
from ui.progress_bar import MinimalProgressBar
from ui.controls import MotionIconButton

class DynamicIslandWidget(QWidget):
    """
    Floating minimalistic motion design Dynamic Island widget for Windows 10/11.
    """
    open_settings_requested = Signal()

    def __init__(self, config_manager: ConfigManager, media_worker: MediaWorker, parent=None):
        super().__init__(parent)
        self.config_mgr = config_manager
        self.media_worker = media_worker

        # State
        self.is_expanded = False
        self.is_hovered = False
        self.is_dragging_window = False
        self._drag_start_pos = QPoint()
        self.has_active_session = False
        self.is_playing = False

        # Current media payload
        self.media_data = {
            "title": "Ready to play",
            "artist": "No media detected",
            "album": "",
            "player_name": "Media Player",
            "player_type": "generic",
            "brand_color": "#1DB954",
            "thumbnail_bytes": b"",
            "palette": {
                "accent": "#1DB954",
                "bright_accent": "#25E066",
                "glow": "rgba(29, 185, 84, 0.45)",
                "ambient_bg": "rgba(29, 185, 84, 0.12)",
                "qcolor_accent": QColor("#1DB954"),
                "qcolor_glow": QColor(29, 185, 84, 110)
            }
        }

        # Cached album artwork pixmaps
        self._cached_thumb_bytes = b""
        self._thumb_pixmap: Optional[QPixmap] = None

        # Hover timers for smooth intentional expansion
        self._hover_expand_timer = QTimer(self)
        self._hover_expand_timer.setSingleShot(True)
        self._hover_expand_timer.timeout.connect(self._on_hover_expand_trigger)

        self._hover_collapse_timer = QTimer(self)
        self._hover_collapse_timer.setSingleShot(True)
        self._hover_collapse_timer.timeout.connect(self._on_hover_collapse_trigger)

        # Geometry animation
        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Content opacity for cross-fade during expansion
        self._content_expand_ratio = 0.0
        self._fade_anim = QPropertyAnimation(self, b"expandRatio", self)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Window configuration
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        # Child widgets
        self._init_child_widgets()

        # Connect signals
        self.media_worker.media_changed.connect(self.on_media_changed)
        self.media_worker.playback_state_changed.connect(self.on_playback_state_changed)
        self.media_worker.timeline_updated.connect(self.on_timeline_updated)
        self.media_worker.session_status_changed.connect(self.on_session_status_changed)
        self.config_mgr.config_changed.connect(self.on_config_changed)

        # Apply initial layout & theme
        self.apply_theme()
        self.update_dimensions(animate=False)

    def get_expand_ratio(self) -> float:
        return self._content_expand_ratio

    def set_expand_ratio(self, val: float):
        self._content_expand_ratio = val
        self._layout_child_widgets()
        self.update()

    expandRatio = Property(float, get_expand_ratio, set_expand_ratio)

    def _init_child_widgets(self):
        # Compact mode widgets
        self.compact_title_label = MarqueeLabel("", font_size=10, bold=True, color="#ffffff", parent=self)
        self.compact_artist_label = MarqueeLabel("", font_size=9, bold=False, color="#a0a0a5", parent=self)
        self.compact_visualizer = MotionVisualizer(bar_count=4, style="liquid_bars", parent=self)
        self.compact_play_btn = MotionIconButton(icon_type="play", size=24, parent=self)
        self.compact_play_btn.clicked.connect(self.media_worker.toggle_play_pause)

        # Expanded mode widgets
        self.exp_title_label = MarqueeLabel("", font_size=12, bold=True, color="#ffffff", parent=self)
        self.exp_artist_label = MarqueeLabel("", font_size=10, bold=False, color="#b0b0b8", parent=self)
        self.exp_album_label = MarqueeLabel("", font_size=9, bold=False, color="#808088", parent=self)
        self.exp_visualizer = MotionVisualizer(bar_count=6, style="liquid_bars", parent=self)
        
        self.progress_bar = MinimalProgressBar(parent=self)
        self.progress_bar.seek_requested.connect(self.media_worker.seek_to)

        self.btn_prev = MotionIconButton(icon_type="prev", size=30, parent=self)
        self.btn_prev.clicked.connect(self.media_worker.previous_track)

        self.btn_play = MotionIconButton(icon_type="play", size=36, parent=self)
        self.btn_play.clicked.connect(self.media_worker.toggle_play_pause)

        self.btn_next = MotionIconButton(icon_type="next", size=30, parent=self)
        self.btn_next.clicked.connect(self.media_worker.next_track)

        self.btn_settings = MotionIconButton(icon_type="settings", size=24, parent=self)
        self.btn_settings.clicked.connect(self.open_settings_requested.emit)

        # Update initial text
        self._update_ui_text()

    def _update_ui_text(self):
        title = self.media_data.get("title", "") or "Ready to play"
        artist = self.media_data.get("artist", "") or (self.config_mgr.get("behavior", "idle_text") if not self.has_active_session else "Music Player")
        album = self.media_data.get("album", "")
        
        self.compact_title_label.set_text(title)
        self.compact_artist_label.set_text(artist)

        self.exp_title_label.set_text(title)
        self.exp_artist_label.set_text(artist)
        self.exp_album_label.set_text(album)

    def apply_theme(self):
        app_cfg = self.config_mgr.get("appearance", {})
        motion_cfg = self.config_mgr.get("motion", {})

        # Accent color
        accent_mode = app_cfg.get("accent_mode", "auto")
        if accent_mode == "auto":
            accent = self.media_data["palette"]["qcolor_accent"]
        else:
            accent = QColor(app_cfg.get("custom_accent", "#1DB954"))

        # Visualizer style & sensitivity
        vis_style = motion_cfg.get("visualizer_style", "liquid_bars")
        vis_sens = motion_cfg.get("visualizer_sensitivity", 1.0)

        for vis in (self.compact_visualizer, self.exp_visualizer):
            vis.set_accent_color(accent)
            vis.set_style(vis_style)
            vis.sensitivity = vis_sens

        self.progress_bar.set_accent_color(accent)
        self.btn_play.set_accent_color(accent)
        self.compact_play_btn.set_accent_color(accent)

        # Speed and easing curves
        duration = motion_cfg.get("animation_speed_ms", 320)
        self._anim.setDuration(duration)
        self._fade_anim.setDuration(duration)

        curve_name = motion_cfg.get("easing_curve", "OutCubic")
        curve_type = getattr(QEasingCurve.Type, curve_name, QEasingCurve.Type.OutCubic)
        self._anim.setEasingCurve(curve_type)
        self._fade_anim.setEasingCurve(curve_type)

        self.update()

    def on_media_changed(self, data: dict):
        self.media_data = data
        self.has_active_session = True
        self.is_playing = data.get("is_playing", False)
        
        # Invalidate thumbnail pixmap cache
        thumb_bytes = data.get("thumbnail_bytes", b"")
        if thumb_bytes != self._cached_thumb_bytes:
            self._cached_thumb_bytes = thumb_bytes
            if thumb_bytes:
                img = QImage.fromData(thumb_bytes)
                if not img.isNull():
                    self._thumb_pixmap = QPixmap.fromImage(img)
                else:
                    self._thumb_pixmap = None
            else:
                self._thumb_pixmap = None

        self._update_ui_text()
        self.apply_theme()
        self.on_playback_state_changed(self.is_playing)
        self.update()

    def on_playback_state_changed(self, is_playing: bool):
        self.is_playing = is_playing
        icon_type = "pause" if is_playing else "play"
        self.compact_play_btn.set_icon_type(icon_type)
        self.btn_play.set_icon_type(icon_type)
        self.compact_visualizer.set_playing(is_playing)
        self.exp_visualizer.set_playing(is_playing)
        self.progress_bar.set_playing(is_playing)

    def on_timeline_updated(self, position: float, duration: float):
        self.progress_bar.set_timeline(position, duration)

    def on_session_status_changed(self, has_session: bool):
        self.has_active_session = has_session
        if not has_session:
            self.on_playback_state_changed(False)
            self._update_ui_text()
        self.update()

    def on_config_changed(self, cfg: dict):
        self.apply_theme()
        self.update_dimensions(animate=True)

    def get_target_dimensions(self) -> tuple[int, int]:
        scale = self.config_mgr.get("appearance", "scale", 1.0)
        if self.is_expanded:
            return int(390 * scale), int(172 * scale)
        else:
            return int(270 * scale), int(46 * scale)

    def update_dimensions(self, animate: bool = True):
        w, h = self.get_target_dimensions()
        target_rect = self._calculate_target_geometry(w, h)

        if not animate:
            self.setGeometry(target_rect)
            self.set_expand_ratio(1.0 if self.is_expanded else 0.0)
        else:
            self._anim.stop()
            self._anim.setStartValue(self.geometry())
            self._anim.setEndValue(target_rect)
            self._anim.start()

            self._fade_anim.stop()
            self._fade_anim.setStartValue(self._content_expand_ratio)
            self._fade_anim.setEndValue(1.0 if self.is_expanded else 0.0)
            self._fade_anim.start()

    def _calculate_target_geometry(self, w: int, h: int) -> QRect:
        layout_cfg = self.config_mgr.get("layout", {})
        dock = layout_cfg.get("dock_position", "top_center")
        top_offset = layout_cfg.get("top_offset", 14)
        bottom_offset = layout_cfg.get("bottom_offset", 24)
        side_offset = layout_cfg.get("side_offset", 24)

        screen = QApplication.primaryScreen()
        geom = screen.availableGeometry()

        if dock == "top_center":
            x = geom.x() + (geom.width() - w) // 2
            y = geom.y() + top_offset
        elif dock == "top_right":
            x = geom.x() + geom.width() - w - side_offset
            y = geom.y() + top_offset
        elif dock == "top_left":
            x = geom.x() + side_offset
            y = geom.y() + top_offset
        elif dock == "bottom_center":
            x = geom.x() + (geom.width() - w) // 2
            y = geom.y() + geom.height() - h - bottom_offset
        elif dock == "bottom_right":
            x = geom.x() + geom.width() - w - side_offset
            y = geom.y() + geom.height() - h - bottom_offset
        else:  # "free"
            x = layout_cfg.get("free_x", 400)
            y = layout_cfg.get("free_y", 40)

        return QRect(x, y, w, h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_child_widgets()

    def _layout_child_widgets(self):
        w = self.width()
        h = self.height()
        r = self._content_expand_ratio  # 0.0 = compact, 1.0 = expanded

        # Determine visibility
        show_compact = (r < 0.6)
        show_expanded = (r > 0.4)

        self.compact_title_label.setVisible(show_compact)
        self.compact_artist_label.setVisible(show_compact)
        self.compact_visualizer.setVisible(show_compact)
        self.compact_play_btn.setVisible(show_compact)

        self.exp_title_label.setVisible(show_expanded)
        self.exp_artist_label.setVisible(show_expanded)
        self.exp_album_label.setVisible(show_expanded)
        self.exp_visualizer.setVisible(show_expanded)
        self.progress_bar.setVisible(show_expanded)
        self.btn_prev.setVisible(show_expanded)
        self.btn_play.setVisible(show_expanded)
        self.btn_next.setVisible(show_expanded)
        self.btn_settings.setVisible(show_expanded)

        if show_compact:
            # Compact Pill Layout
            # Left: small album art (28x28 at x=10, y=8)
            text_x = 44
            vis_w = 32
            btn_w = 26
            text_w = max(40, w - text_x - vis_w - btn_w - 18)

            self.compact_title_label.setGeometry(text_x, 7, text_w, 16)
            self.compact_artist_label.setGeometry(text_x, 23, text_w, 15)

            self.compact_visualizer.setGeometry(text_x + text_w + 6, (h - 18) // 2, vis_w, 18)
            self.compact_play_btn.setGeometry(w - btn_w - 10, (h - btn_w) // 2, btn_w, btn_w)

        if show_expanded:
            # Expanded Card Layout
            pad = 14
            # Top header: Platform name + badge + Settings button
            self.btn_settings.setGeometry(w - pad - 24, pad, 24, 24)

            # Center section:
            # Left: Large album art (64x64 at x=16, y=36)
            art_size = 64
            art_x = pad + 2
            art_y = 34

            text_x = art_x + art_size + 14
            text_w = max(60, w - text_x - pad - 42)

            self.exp_title_label.setGeometry(text_x, art_y, text_w, 20)
            self.exp_artist_label.setGeometry(text_x, art_y + 20, text_w, 18)
            self.exp_album_label.setGeometry(text_x, art_y + 38, text_w, 16)

            self.exp_visualizer.setGeometry(w - pad - 44, art_y + 4, 38, 24)

            # Interactive Progress Bar
            prog_y = art_y + art_size + 6
            self.progress_bar.setGeometry(pad, prog_y, w - 2 * pad, 24)

            # Controls at bottom
            ctrl_y = prog_y + 26
            center_x = w // 2
            self.btn_play.setGeometry(center_x - 18, ctrl_y - 4, 36, 36)
            self.btn_prev.setGeometry(center_x - 18 - 42, ctrl_y - 1, 30, 30)
            self.btn_next.setGeometry(center_x + 18 + 12, ctrl_y - 1, 30, 30)

    # Mouse & Gesture Interactions
    def enterEvent(self, event):
        self.is_hovered = True
        self._hover_collapse_timer.stop()
        
        behavior = self.config_mgr.get("behavior", {})
        if behavior.get("expand_on_hover", True) and not self.is_expanded:
            delay = behavior.get("hover_expand_delay_ms", 150)
            self._hover_expand_timer.start(delay)

    def leaveEvent(self, event):
        self.is_hovered = False
        self._hover_expand_timer.stop()
        
        behavior = self.config_mgr.get("behavior", {})
        if behavior.get("expand_on_hover", True) and self.is_expanded:
            delay = behavior.get("hover_collapse_delay_ms", 500)
            self._hover_collapse_timer.start(delay)

    def _on_hover_expand_trigger(self):
        if self.is_hovered and not self.is_expanded:
            self.toggle_expanded(True)

    def _on_hover_collapse_trigger(self):
        if not self.is_hovered and self.is_expanded:
            self.toggle_expanded(False)

    def toggle_expanded(self, expanded: Optional[bool] = None):
        if expanded is None:
            self.is_expanded = not self.is_expanded
        else:
            self.is_expanded = expanded
        self.update_dimensions(animate=True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicked on a child button/scrubber
            child = self.childAt(event.position().toPoint())
            if child is None or child == self:
                layout_cfg = self.config_mgr.get("layout", {})
                if layout_cfg.get("dock_position") == "free":
                    self.is_dragging_window = True
                    self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                else:
                    # Click to expand/collapse toggle
                    if self.config_mgr.get("behavior", "click_to_expand", True):
                        self.toggle_expanded()

        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self.is_dragging_window:
            new_pos = event.globalPosition().toPoint() - self._drag_start_pos
            self.move(new_pos)
            self.config_mgr.set("layout", "free_x", new_pos.x())
            self.config_mgr.set("layout", "free_y", new_pos.y())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging_window:
            self.is_dragging_window = False

    def wheelEvent(self, event):
        # Mouse wheel on widget adjusts master volume or skips
        behavior = self.config_mgr.get("behavior", {})
        if behavior.get("scroll_volume_control", True):
            delta = event.angleDelta().y()
            if delta > 0:
                self.media_worker.seek_to(self.progress_bar._position + 5.0)
            elif delta < 0:
                self.media_worker.seek_to(max(0.0, self.progress_bar._position - 5.0))

    def _show_context_menu(self, global_pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1b20;
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
                padding: 6px;
                font-family: 'Segoe UI Variable Text';
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.08);
                margin: 4px 6px;
            }
        """)

        # Toggle Expand
        act_expand = menu.addAction("Свернуть / Развернуть" if self.is_expanded else "Развернуть")
        act_expand.triggered.connect(lambda: self.toggle_expanded())

        menu.addSeparator()

        # Docking submenu
        dock_menu = menu.addMenu("Позиция на экране")
        dock_opts = [
            ("Вверху по центру (Dynamic Island)", "top_center"),
            ("Вверху справа", "top_right"),
            ("Внизу по центру", "bottom_center"),
            ("Свободное перемещение", "free")
        ]
        cur_dock = self.config_mgr.get("layout", "dock_position")
        for label, code in dock_opts:
            act = dock_menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(cur_dock == code)
            act.triggered.connect(lambda checked, c=code: self._set_dock_position(c))

        # Always on top
        act_top = menu.addAction("Поверх всех окон")
        act_top.setCheckable(True)
        act_top.setChecked(self.config_mgr.get("behavior", "always_on_top", True))
        act_top.triggered.connect(self._toggle_always_on_top)

        menu.addSeparator()

        # Settings
        act_settings = menu.addAction("Настройки...")
        act_settings.triggered.connect(self.open_settings_requested.emit)

        # Exit
        act_exit = menu.addAction("Закрыть")
        act_exit.triggered.connect(QApplication.instance().quit)

        menu.exec(global_pos)

    def _set_dock_position(self, code: str):
        self.config_mgr.set("layout", "dock_position", code)
        self.update_dimensions(animate=True)

    def _toggle_always_on_top(self, checked: bool):
        self.config_mgr.set("behavior", "always_on_top", checked)
        flags = self.windowFlags()
        if checked:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()

    # Paint Event
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        r_expand = self._content_expand_ratio

        app_cfg = self.config_mgr.get("appearance", {})
        corner_radius = app_cfg.get("corner_radius", 24)
        if self.is_expanded:
            corner_radius = min(corner_radius, 26)

        # Glow and border colors
        accent_mode = app_cfg.get("accent_mode", "auto")
        if accent_mode == "auto":
            accent = self.media_data["palette"]["qcolor_accent"]
            glow = self.media_data["palette"]["qcolor_glow"]
        else:
            accent = QColor(app_cfg.get("custom_accent", "#1DB954"))
            glow = QColor(accent.red(), accent.green(), accent.blue(), 100)

        # Background base
        bg_hex = app_cfg.get("background_color", "#0d0f14")
        bg_opacity = app_cfg.get("background_opacity", 0.90)
        base_bg = QColor(bg_hex)
        base_bg.setAlphaF(bg_opacity)

        # 1. Ambient Glow / Drop Shadow
        if app_cfg.get("glow_enabled", True) and (self.is_playing or self.is_hovered):
            glow_layers = 3
            for i in range(glow_layers):
                expand = (i + 1) * 3
                alpha = int((35 / (i + 1)) * (1.2 if self.is_playing else 0.7))
                layer_col = QColor(accent.red(), accent.green(), accent.blue(), alpha)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(layer_col))
                painter.drawRoundedRect(
                    QRectF(-expand / 2.0, -expand / 2.0, w + expand, h + expand),
                    corner_radius + expand / 2.0,
                    corner_radius + expand / 2.0
                )

        # 2. Main Frosted / Glass Container
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), corner_radius, corner_radius)
        painter.setClipPath(path)

        # Gradient background
        gradient = QLinearGradient(0, 0, 0, h)
        top_tint = QColor(base_bg.red() + 15, base_bg.green() + 15, base_bg.blue() + 20, int(base_bg.alpha()))
        gradient.setColorAt(0.0, top_tint)
        gradient.setColorAt(1.0, base_bg)
        painter.fillPath(path, gradient)

        # Subtle dynamic ambient tint from cover art
        ambient_tint = QColor(accent.red(), accent.green(), accent.blue(), int(25 * (1.0 if self.is_playing else 0.4)))
        painter.fillPath(path, ambient_tint)

        # 3. Inner 1px Border
        painter.setClipping(False)
        border_opacity = app_cfg.get("border_opacity", 0.14)
        border_col = QColor(255, 255, 255, int(255 * border_opacity))
        border_pen = QPen(border_col, 1.0)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), corner_radius, corner_radius)

        # 4. Render Album Cover Art
        if r_expand < 0.6:
            # Compact thumbnail (28x28 at x=9, y=(h-28)/2)
            c_size = 28
            c_x = 9
            c_y = (h - c_size) // 2
            self._draw_album_art(painter, QRectF(c_x, c_y, c_size, c_size), radius=c_size / 2.0)
        else:
            # Header in expanded mode: Platform badge
            painter.setFont(QFont("Segoe UI Variable Text", 8, QFont.Weight.DemiBold))
            player_name = self.media_data.get("player_name", "Media Player")
            badge_text = player_name.upper()

            brand_col = QColor(self.media_data.get("brand_color", "#1DB954"))
            # Platform dot
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(brand_col))
            painter.drawEllipse(QRectF(16, 17, 7, 7))

            # Platform label
            painter.setPen(QColor(255, 255, 255, 170))
            painter.drawText(28, 24, badge_text)

            # Large album art (64x64 at x=16, y=34)
            art_size = 64
            art_x = 16
            art_y = 34
            self._draw_album_art(painter, QRectF(art_x, art_y, art_size, art_size), radius=10.0)

    def _draw_album_art(self, painter: QPainter, rect: QRectF, radius: float):
        painter.save()
        art_path = QPainterPath()
        art_path.addRoundedRect(rect, radius, radius)
        painter.setClipPath(art_path)

        if self._thumb_pixmap and not self._thumb_pixmap.isNull():
            # Draw real album artwork
            painter.drawPixmap(
                int(rect.x()), int(rect.y()), int(rect.width()), int(rect.height()),
                self._thumb_pixmap
            )
        else:
            # Fallback sleek music icon with gradient
            grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
            accent = self.media_data["palette"]["qcolor_accent"]
            grad.setColorAt(0.0, accent)
            grad.setColorAt(1.0, accent.darker(170))
            painter.fillRect(rect, grad)

            # Draw note icon
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
            cx = rect.center().x()
            cy = rect.center().y()
            sz = rect.width() * 0.22
            painter.drawEllipse(QRectF(cx - sz, cy, sz, sz))
            painter.drawRect(QRectF(cx, cy - sz * 1.4, sz * 0.35, sz * 1.6))

        # Thin 1px subtle art border
        painter.setClipping(False)
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)
        painter.restore()

