from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QSlider, QComboBox, QCheckBox, QPushButton, QColorDialog,
    QGroupBox, QSpinBox, QLineEdit, QFrame, QMessageBox
)
from core.config_manager import ConfigManager

DARK_STYLE = """
QDialog {
    background-color: #121318;
    color: #f0f0f5;
    font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid rgba(255, 255, 255, 0.08);
    background-color: #181920;
    border-radius: 12px;
    padding: 14px;
}
QTabBar::tab {
    background-color: transparent;
    color: #90909b;
    padding: 10px 18px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 500;
}
QTabBar::tab:selected {
    color: #ffffff;
    background-color: #181920;
    border-bottom: 2px solid #1DB954;
}
QTabBar::tab:hover:!selected {
    color: #d0d0d8;
    background-color: rgba(255, 255, 255, 0.04);
}
QGroupBox {
    font-weight: 600;
    font-size: 13px;
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 18px;
    padding-bottom: 10px;
    padding-left: 12px;
    padding-right: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 6px;
    color: #1DB954;
}
QLabel {
    color: #e0e0e8;
}
QComboBox {
    background-color: #20222b;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    padding: 6px 12px;
    color: #ffffff;
    min-width: 140px;
}
QComboBox:hover {
    border-color: #1DB954;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #20222b;
    color: #ffffff;
    selection-background-color: #1DB954;
    border: 1px solid rgba(255, 255, 255, 0.12);
}
QSlider::groove:horizontal {
    height: 6px;
    background: #2a2c36;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #1DB954;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #ffffff;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #1ed760;
}
QCheckBox {
    spacing: 8px;
    color: #e0e0e8;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    background-color: #20222b;
}
QCheckBox::indicator:checked {
    background-color: #1DB954;
    border-color: #1DB954;
}
QPushButton {
    background-color: #242632;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    padding: 7px 16px;
    color: #ffffff;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #2d3040;
    border-color: #1DB954;
}
QPushButton:pressed {
    background-color: #1a1c24;
}
QPushButton#primaryBtn {
    background-color: #1DB954;
    color: #000000;
    font-weight: 600;
    border: none;
}
QPushButton#primaryBtn:hover {
    background-color: #1ed760;
}
QLineEdit {
    background-color: #20222b;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    padding: 6px 10px;
    color: #ffffff;
}
"""

class SettingsDialog(QDialog):
    """
    Comprehensive, sleek configuration and customization window.
    """
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_mgr = config_manager
        self.setWindowTitle("Настройки Dynamic Island Widget")
        self.setMinimumSize(540, 560)
        self.resize(560, 590)
        self.setStyleSheet(DARK_STYLE)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_appearance_tab(), "Внешний вид")
        self.tabs.addTab(self._create_layout_tab(), "Расположение")
        self.tabs.addTab(self._create_motion_tab(), "Анимации")
        self.tabs.addTab(self._create_behavior_tab(), "Поведение")
        self.tabs.addTab(self._create_about_tab(), "О программе")

        main_layout.addWidget(self.tabs)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_reset = QPushButton("Сбросить по умолчанию")
        btn_reset.clicked.connect(self._reset_defaults)
        btn_layout.addWidget(btn_reset)

        btn_layout.addStretch()

        btn_close = QPushButton("Закрыть")
        btn_close.setObjectName("primaryBtn")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        main_layout.addLayout(btn_layout)

    # 1. Appearance Tab
    def _create_appearance_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        # Themes Preset
        grp_theme = QGroupBox("Быстрые пресеты темы")
        theme_layout = QHBoxLayout(grp_theme)

        presets = [
            ("Тёмное стекло", "glass_dark", "#0d0f14", 0.90, True),
            ("OLED Black", "oled_black", "#000000", 0.96, False),
            ("Кибернеон", "cyber_glow", "#080a12", 0.92, True),
            ("Светлый стиль", "light", "#f5f6fa", 0.95, False)
        ]
        for name, key, bg, opac, glow in presets:
            btn = QPushButton(name)
            btn.clicked.connect(lambda _, k=key, b=bg, o=opac, g=glow: self._apply_theme_preset(k, b, o, g))
            theme_layout.addWidget(btn)
        layout.addWidget(grp_theme)

        # Accent Color
        grp_color = QGroupBox("Цветовая палитра и акценты")
        col_layout = QVBoxLayout(grp_color)

        row_mode = QHBoxLayout()
        row_mode.addWidget(QLabel("Режим акцентного цвета:"))
        self.combo_accent_mode = QComboBox()
        self.combo_accent_mode.addItem("Авто (из обложки трека)", "auto")
        self.combo_accent_mode.addItem("Пользовательский цвет", "custom")
        cur_mode = self.config_mgr.get("appearance", "accent_mode", "auto")
        idx = self.combo_accent_mode.findData(cur_mode)
        if idx >= 0:
            self.combo_accent_mode.setCurrentIndex(idx)
        self.combo_accent_mode.currentIndexChanged.connect(self._on_accent_mode_changed)
        row_mode.addWidget(self.combo_accent_mode)
        col_layout.addLayout(row_mode)

        row_pick = QHBoxLayout()
        row_pick.addWidget(QLabel("Пользовательский акцент:"))
        self.btn_pick_color = QPushButton("Выбрать цвет")
        self._update_color_btn_style(self.config_mgr.get("appearance", "custom_accent", "#1DB954"))
        self.btn_pick_color.clicked.connect(self._choose_custom_accent)
        row_pick.addWidget(self.btn_pick_color)
        col_layout.addLayout(row_pick)

        # Glow Toggle
        self.chk_glow = QCheckBox("Включить мягкое неоновое свечение (Ambient Glow)")
        self.chk_glow.setChecked(self.config_mgr.get("appearance", "glow_enabled", True))
        self.chk_glow.toggled.connect(lambda val: self.config_mgr.set("appearance", "glow_enabled", val))
        col_layout.addWidget(self.chk_glow)

        layout.addWidget(grp_color)

        # Sliders (Opacity, Corner Radius, Scale)
        grp_geometry = QGroupBox("Геометрия и прозрачность")
        geom_layout = QVBoxLayout(grp_geometry)

        # Opacity
        row_opac = QHBoxLayout()
        row_opac.addWidget(QLabel("Непрозрачность фона:"))
        self.lbl_opac_val = QLabel(f"{int(self.config_mgr.get('appearance', 'background_opacity', 0.90) * 100)}%")
        row_opac.addWidget(self.lbl_opac_val)
        geom_layout.addLayout(row_opac)

        self.slider_opac = QSlider(Qt.Orientation.Horizontal)
        self.slider_opac.setRange(30, 100)
        self.slider_opac.setValue(int(self.config_mgr.get("appearance", "background_opacity", 0.90) * 100))
        self.slider_opac.valueChanged.connect(self._on_opacity_changed)
        geom_layout.addWidget(self.slider_opac)

        # Corner Radius
        row_radius = QHBoxLayout()
        row_radius.addWidget(QLabel("Скругление углов (Corner Radius):"))
        self.lbl_radius_val = QLabel(f"{self.config_mgr.get('appearance', 'corner_radius', 24)}px")
        row_radius.addWidget(self.lbl_radius_val)
        geom_layout.addLayout(row_radius)

        self.slider_radius = QSlider(Qt.Orientation.Horizontal)
        self.slider_radius.setRange(12, 32)
        self.slider_radius.setValue(self.config_mgr.get("appearance", "corner_radius", 24))
        self.slider_radius.valueChanged.connect(self._on_radius_changed)
        geom_layout.addWidget(self.slider_radius)

        # Scale
        row_scale = QHBoxLayout()
        row_scale.addWidget(QLabel("Масштаб виджета:"))
        self.lbl_scale_val = QLabel(f"{int(self.config_mgr.get('appearance', 'scale', 1.0) * 100)}%")
        row_scale.addWidget(self.lbl_scale_val)
        geom_layout.addLayout(row_scale)

        self.slider_scale = QSlider(Qt.Orientation.Horizontal)
        self.slider_scale.setRange(70, 160)
        self.slider_scale.setValue(int(self.config_mgr.get("appearance", "scale", 1.0) * 100))
        self.slider_scale.valueChanged.connect(self._on_scale_changed)
        geom_layout.addWidget(self.slider_scale)

        layout.addWidget(grp_geometry)
        layout.addStretch()
        return widget

    def _apply_theme_preset(self, key: str, bg: str, opac: float, glow: bool):
        self.config_mgr.set("appearance", "theme", key)
        self.config_mgr.set("appearance", "background_color", bg)
        self.config_mgr.set("appearance", "background_opacity", opac)
        self.config_mgr.set("appearance", "glow_enabled", glow)
        self.slider_opac.setValue(int(opac * 100))
        self.chk_glow.setChecked(glow)

    def _on_accent_mode_changed(self, idx: int):
        val = self.combo_accent_mode.itemData(idx)
        self.config_mgr.set("appearance", "accent_mode", val)

    def _choose_custom_accent(self):
        cur_hex = self.config_mgr.get("appearance", "custom_accent", "#1DB954")
        col = QColorDialog.getColor(QColor(cur_hex), self, "Выберите акцентный цвет")
        if col.isValid():
            self.config_mgr.set("appearance", "custom_accent", col.name())
            self.config_mgr.set("appearance", "accent_mode", "custom")
            self.combo_accent_mode.setCurrentIndex(1)
            self._update_color_btn_style(col.name())

    def _update_color_btn_style(self, hex_code: str):
        self.btn_pick_color.setStyleSheet(f"""
            background-color: {hex_code};
            color: #000000;
            font-weight: 600;
            border-radius: 6px;
            padding: 5px 12px;
        """)

    def _on_opacity_changed(self, val: int):
        self.lbl_opac_val.setText(f"{val}%")
        self.config_mgr.set("appearance", "background_opacity", val / 100.0)

    def _on_radius_changed(self, val: int):
        self.lbl_radius_val.setText(f"{val}px")
        self.config_mgr.set("appearance", "corner_radius", val)

    def _on_scale_changed(self, val: int):
        self.lbl_scale_val.setText(f"{val}%")
        self.config_mgr.set("appearance", "scale", val / 100.0)

    # 2. Layout Tab
    def _create_layout_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)

        grp_pos = QGroupBox("Позиционирование на экране")
        pos_layout = QVBoxLayout(grp_pos)

        row_dock = QHBoxLayout()
        row_dock.addWidget(QLabel("Расположение виджета:"))
        self.combo_dock = QComboBox()
        self.combo_dock.addItem("Вверху по центру (Dynamic Island)", "top_center")
        self.combo_dock.addItem("Вверху справа", "top_right")
        self.combo_dock.addItem("Вверху слева", "top_left")
        self.combo_dock.addItem("Внизу по центру", "bottom_center")
        self.combo_dock.addItem("Внизу справа", "bottom_right")
        self.combo_dock.addItem("Свободное перемещение (Free drag)", "free")
        
        cur_dock = self.config_mgr.get("layout", "dock_position", "top_center")
        idx = self.combo_dock.findData(cur_dock)
        if idx >= 0:
            self.combo_dock.setCurrentIndex(idx)
        self.combo_dock.currentIndexChanged.connect(self._on_dock_changed)
        row_dock.addWidget(self.combo_dock)
        pos_layout.addLayout(row_dock)

        # Offsets
        row_top = QHBoxLayout()
        row_top.addWidget(QLabel("Отступ от верхнего края:"))
        self.lbl_top_val = QLabel(f"{self.config_mgr.get('layout', 'top_offset', 14)}px")
        row_top.addWidget(self.lbl_top_val)
        pos_layout.addLayout(row_top)

        self.slider_top = QSlider(Qt.Orientation.Horizontal)
        self.slider_top.setRange(0, 60)
        self.slider_top.setValue(self.config_mgr.get("layout", "top_offset", 14))
        self.slider_top.valueChanged.connect(self._on_top_offset_changed)
        pos_layout.addWidget(self.slider_top)

        layout.addWidget(grp_pos)

        # Info tip
        lbl_tip = QLabel("💡 Совет: В режиме 'Свободное перемещение' вы можете просто зажать виджет левой кнопкой мыши и переместить его в любое удобное место.")
        lbl_tip.setWordWrap(True)
        lbl_tip.setStyleSheet("color: #9da0b0; padding: 10px; background: rgba(255, 255, 255, 0.03); border-radius: 8px;")
        layout.addWidget(lbl_tip)

        layout.addStretch()
        return widget

    def _on_dock_changed(self, idx: int):
        val = self.combo_dock.itemData(idx)
        self.config_mgr.set("layout", "dock_position", val)

    def _on_top_offset_changed(self, val: int):
        self.lbl_top_val.setText(f"{val}px")
        self.config_mgr.set("layout", "top_offset", val)

    # 3. Motion Tab
    def _create_motion_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)

        grp_anim = QGroupBox("Динамика и скорость анимаций")
        anim_layout = QVBoxLayout(grp_anim)

        row_speed = QHBoxLayout()
        row_speed.addWidget(QLabel("Скорость морфинга (длительность):"))
        self.combo_speed = QComboBox()
        self.combo_speed.addItem("Сверхбыстрая (180 ms)", 180)
        self.combo_speed.addItem("Баланс / Динамично (320 ms)", 320)
        self.combo_speed.addItem("Плавная / Чилл (500 ms)", 500)
        cur_spd = self.config_mgr.get("motion", "animation_speed_ms", 320)
        idx = self.combo_speed.findData(cur_spd)
        if idx >= 0:
            self.combo_speed.setCurrentIndex(idx)
        self.combo_speed.currentIndexChanged.connect(lambda i: self.config_mgr.set("motion", "animation_speed_ms", self.combo_speed.itemData(i)))
        row_speed.addWidget(self.combo_speed)
        anim_layout.addLayout(row_speed)

        row_curve = QHBoxLayout()
        row_curve.addWidget(QLabel("Характер сглаживания (Easing Curve):"))
        self.combo_curve = QComboBox()
        self.combo_curve.addItem("OutCubic (Плавное торможение)", "OutCubic")
        self.combo_curve.addItem("OutBack (Лёгкая упругая пружина)", "OutBack")
        self.combo_curve.addItem("InOutQuad (Кинематографичный разгон)", "InOutQuad")
        self.combo_curve.addItem("Linear (Линейный)", "Linear")
        cur_curve = self.config_mgr.get("motion", "easing_curve", "OutCubic")
        idx = self.combo_curve.findData(cur_curve)
        if idx >= 0:
            self.combo_curve.setCurrentIndex(idx)
        self.combo_curve.currentIndexChanged.connect(lambda i: self.config_mgr.set("motion", "easing_curve", self.combo_curve.itemData(i)))
        anim_layout.addLayout(row_curve)

        layout.addWidget(grp_anim)

        # Visualizer
        grp_vis = QGroupBox("Эквалайзер / Визуализатор звука")
        vis_layout = QVBoxLayout(grp_vis)

        row_vis_style = QHBoxLayout()
        row_vis_style.addWidget(QLabel("Стиль визуализатора:"))
        self.combo_vis = QComboBox()
        self.combo_vis.addItem("Живые жидкие полосы (Liquid Bars)", "liquid_bars")
        self.combo_vis.addItem("Плавная звуковая волна (Fluid Wave)", "wave")
        self.combo_vis.addItem("Ритмичные неоновые точки (Dots)", "dots")
        self.combo_vis.addItem("Выключен", "off")
        cur_vis = self.config_mgr.get("motion", "visualizer_style", "liquid_bars")
        idx = self.combo_vis.findData(cur_vis)
        if idx >= 0:
            self.combo_vis.setCurrentIndex(idx)
        self.combo_vis.currentIndexChanged.connect(lambda i: self.config_mgr.set("motion", "visualizer_style", self.combo_vis.itemData(i)))
        row_vis_style.addWidget(self.combo_vis)
        vis_layout.addLayout(row_vis_style)

        # Sensitivity
        row_sens = QHBoxLayout()
        row_sens.addWidget(QLabel("Амплитуда колебаний:"))
        self.lbl_sens_val = QLabel(f"{int(self.config_mgr.get('motion', 'visualizer_sensitivity', 1.0) * 100)}%")
        row_sens.addWidget(self.lbl_sens_val)
        vis_layout.addLayout(row_sens)

        self.slider_sens = QSlider(Qt.Orientation.Horizontal)
        self.slider_sens.setRange(40, 180)
        self.slider_sens.setValue(int(self.config_mgr.get("motion", "visualizer_sensitivity", 1.0) * 100))
        self.slider_sens.valueChanged.connect(self._on_sens_changed)
        vis_layout.addWidget(self.slider_sens)

        layout.addWidget(grp_vis)
        layout.addStretch()
        return widget

    def _on_sens_changed(self, val: int):
        self.lbl_sens_val.setText(f"{val}%")
        self.config_mgr.set("motion", "visualizer_sensitivity", val / 100.0)

    # 4. Behavior Tab
    def _create_behavior_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)

        grp_bhv = QGroupBox("Поведение и жесты")
        bhv_layout = QVBoxLayout(grp_bhv)

        self.chk_ontop = QCheckBox("Всегда поверх всех окон (Always on top)")
        self.chk_ontop.setChecked(self.config_mgr.get("behavior", "always_on_top", True))
        self.chk_ontop.toggled.connect(lambda val: self.config_mgr.set("behavior", "always_on_top", val))
        bhv_layout.addWidget(self.chk_ontop)

        self.chk_hover = QCheckBox("Автоматически разворачивать виджет при наведении мыши")
        self.chk_hover.setChecked(self.config_mgr.get("behavior", "expand_on_hover", True))
        self.chk_hover.toggled.connect(lambda val: self.config_mgr.set("behavior", "expand_on_hover", val))
        bhv_layout.addWidget(self.chk_hover)

        self.chk_click = QCheckBox("Переключать компактный/развёрнутый вид по клику")
        self.chk_click.setChecked(self.config_mgr.get("behavior", "click_to_expand", True))
        self.chk_click.toggled.connect(lambda val: self.config_mgr.set("behavior", "click_to_expand", val))
        bhv_layout.addWidget(self.chk_click)

        self.chk_scroll = QCheckBox("Регулировка громкости колёсиком мыши над виджетом (±2%)")
        self.chk_scroll.setChecked(self.config_mgr.get("behavior", "scroll_volume_control", True))
        self.chk_scroll.toggled.connect(lambda val: self.config_mgr.set("behavior", "scroll_volume_control", val))
        bhv_layout.addWidget(self.chk_scroll)

        layout.addWidget(grp_bhv)

        # Idle Text
        grp_idle = QGroupBox("Режим ожидания (когда музыка не играет)")
        idle_layout = QVBoxLayout(grp_idle)

        row_idle = QHBoxLayout()
        row_idle.addWidget(QLabel("Текст в режиме ожидания:"))
        self.edit_idle = QLineEdit(self.config_mgr.get("behavior", "idle_text", "Ready to play"))
        self.edit_idle.textChanged.connect(lambda txt: self.config_mgr.set("behavior", "idle_text", txt))
        row_idle.addWidget(self.edit_idle)
        idle_layout.addLayout(row_idle)

        layout.addWidget(grp_idle)
        layout.addStretch()
        return widget

    # 5. About Tab
    def _create_about_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)

        lbl_title = QLabel("Dynamic Island Music Widget for Windows 10/11")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Минималистичный стильный виджет с плавной динамической анимацией (motion design), "
            "автоматически считывающий играющую музыку из любой платформы через системную интеграцию Windows Media Control."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #b0b4c4; line-height: 140%;")
        layout.addWidget(lbl_desc)

        grp_support = QGroupBox("Поддерживаемые платформы")
        sup_layout = QVBoxLayout(grp_support)
        platforms = [
            "🟢 Spotify (Десктопное приложение и веб)",
            "🍎 Apple Music (Нативное Windows-приложение и браузер)",
            "🟠 SoundCloud (Chrome, Edge, Firefox, Opera, Brave)",
            "🔴 YouTube Music / YouTube",
            "🟡 Яндекс Музыка, VK Музыка, Deezer, Tidal, Foobar2000, AIMP, VLC"
        ]
        for p in platforms:
            lbl = QLabel(p)
            lbl.setStyleSheet("color: #e4e6ed; padding: 2px 0;")
            sup_layout.addWidget(lbl)
        layout.addWidget(grp_support)

        layout.addStretch()
        return widget

    def _reset_defaults(self):
        confirm = QMessageBox.question(
            self,
            "Сброс настроек",
            "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.config_mgr.reset_defaults()
            self.accept()

