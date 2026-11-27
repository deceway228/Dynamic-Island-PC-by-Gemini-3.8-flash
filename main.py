import sys
import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from core.config_manager import ConfigManager
from core.media_manager import MediaWorker
from core.autostart_manager import sync_autostart_with_config
from ui.widget import DynamicIslandWidget
from ui.settings_dialog import SettingsDialog

def create_tray_icon() -> QIcon:
    """Generates a crisp modern Dynamic Island pill tray icon."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Dark rounded capsule
    pill_path = QPainterPath()
    pill_path.addRoundedRect(2, 8, 28, 16, 8, 8)
    painter.fillPath(pill_path, QColor("#121318"))

    # Accent outline
    painter.setPen(QPen(QColor("#1DB954"), 1.5))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(pill_path)

    # 3 green waveform bars inside
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#1DB954")))
    painter.drawRoundedRect(9, 13, 2.5, 6, 1.2, 1.2)
    painter.drawRoundedRect(14, 11, 2.5, 10, 1.2, 1.2)
    painter.drawRoundedRect(19, 14, 2.5, 4, 1.2, 1.2)

    painter.end()
    return QIcon(pix)


def main():
    # Enable DPI awareness
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("Dynamic Island Music Widget")
    app.setOrganizationName("DynamicIsland")
    app.setQuitOnLastWindowClosed(False)

    # Core engines
    config_mgr = ConfigManager()
    sync_autostart_with_config(config_mgr)
    media_worker = MediaWorker()
    media_worker.start()

    # Main widget
    widget = DynamicIslandWidget(config_mgr, media_worker)
    widget.show()

    # Settings dialog instance
    settings_dialog = None

    def show_settings():
        nonlocal settings_dialog
        if settings_dialog is None:
            settings_dialog = SettingsDialog(config_mgr)
        settings_dialog.show()
        settings_dialog.raise_()
        settings_dialog.activateWindow()

    widget.open_settings_requested.connect(show_settings)

    # System Tray Icon
    tray = QSystemTrayIcon(create_tray_icon(), app)
    tray.setToolTip("Dynamic Island Music Widget")

    tray_menu = QMenu()
    tray_menu.setStyleSheet("""
        QMenu {
            background-color: #1a1b20;
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            padding: 4px;
            font-family: 'Segoe UI Variable Text';
            font-size: 12px;
        }
        QMenu::item {
            padding: 6px 18px;
            border-radius: 5px;
        }
        QMenu::item:selected {
            background-color: rgba(255, 255, 255, 0.12);
        }
        QMenu::separator {
            height: 1px;
            background: rgba(255, 255, 255, 0.08);
            margin: 4px 6px;
        }
    """)

    # Tray actions
    act_status = tray_menu.addAction("Dynamic Island: Ожидание")
    act_status.setEnabled(False)

    def update_tray_status(data: dict):
        title = data.get("title", "")
        artist = data.get("artist", "")
        if title:
            act_status.setText(f"🎵 {title} — {artist}")
            tray.setToolTip(f"{title}\n{artist}")
        else:
            act_status.setText("Dynamic Island: Ожидание")
            tray.setToolTip("Dynamic Island Music Widget")

    media_worker.media_changed.connect(update_tray_status)

    tray_menu.addSeparator()

    act_toggle = tray_menu.addAction("Свернуть / Развернуть")
    act_toggle.triggered.connect(lambda: widget.toggle_expanded())

    act_show_hide = tray_menu.addAction("Скрыть виджет")

    def toggle_widget_visibility():
        if widget.isVisible():
            widget.hide()
            act_show_hide.setText("Показать виджет")
        else:
            widget.show()
            act_show_hide.setText("Скрыть виджет")

    act_show_hide.triggered.connect(toggle_widget_visibility)

    act_settings = tray_menu.addAction("Настройки...")
    act_settings.triggered.connect(show_settings)

    tray_menu.addSeparator()

    act_quit = tray_menu.addAction("Выход")
    act_quit.triggered.connect(app.quit)

    tray.setContextMenu(tray_menu)
    tray.activated.connect(lambda reason: toggle_widget_visibility() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
    tray.show()

    # Clean shutdown
    app.aboutToQuit.connect(media_worker.stop)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

