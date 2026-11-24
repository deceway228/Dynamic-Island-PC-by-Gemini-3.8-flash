import json
import os
from pathlib import Path
from PySide6.QtCore import QObject, Signal

CONFIG_DIR = Path(os.environ.get("APPDATA", ".")) / "DynamicIslandWidget"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "appearance": {
        "theme": "glass_dark",  # "glass_dark", "cyber_glow", "oled_black", "nord_frost", "light", "custom"
        "accent_mode": "auto",   # "auto" (extract from album art), "custom"
        "custom_accent": "#1DB954",
        "background_color": "#0d0f14",
        "background_opacity": 0.90,
        "border_color": "#ffffff",
        "border_opacity": 0.14,
        "border_width": 1.0,
        "corner_radius": 24,
        "glow_enabled": True,
        "glow_radius": 20,
        "glow_opacity": 0.35,
        "scale": 1.0
    },
    "layout": {
        "dock_position": "top_center",  # "top_center", "top_right", "top_left", "bottom_center", "free"
        "top_offset": 14,
        "bottom_offset": 24,
        "side_offset": 24,
        "free_x": 400,
        "free_y": 40
    },
    "motion": {
        "animation_speed_ms": 320,
        "easing_curve": "OutCubic",  # "OutCubic", "OutBack", "InOutQuad", "Linear"
        "visualizer_style": "liquid_bars",  # "liquid_bars", "wave", "dots", "minimal", "off"
        "visualizer_sensitivity": 1.0,
        "marquee_speed": 40,
        "marquee_pause_ms": 1600,
        "smooth_scrubbing": True
    },
    "behavior": {
        "always_on_top": True,
        "expand_on_hover": True,
        "hover_expand_delay_ms": 150,
        "hover_collapse_delay_ms": 500,
        "click_to_expand": True,
        "scroll_volume_control": True,
        "auto_hide_when_paused": False,
        "auto_hide_delay_seconds": 15,
        "show_when_idle": True,
        "idle_text": "Ready to play",
        "close_to_tray": True
    }
}

class ConfigManager(QObject):
    config_changed = Signal(dict)

    def __init__(self):
        super().__init__()
        self.config_path = CONFIG_FILE
        self._config = self._load_config()

    def _load_config(self) -> dict:
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    user_cfg = json.load(f)
                    return self._deep_merge(DEFAULT_CONFIG, user_cfg)
        except Exception as e:
            print(f"[ConfigManager] Error reading config: {e}")
        return json.loads(json.dumps(DEFAULT_CONFIG))

    def _deep_merge(self, default: dict, user: dict) -> dict:
        merged = default.copy()
        for k, v in user.items():
            if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
                merged[k] = self._deep_merge(merged[k], v)
            else:
                merged[k] = v
        return merged

    def get_section(self, section: str) -> dict:
        sec = self._config.get(section, {})
        return sec if isinstance(sec, dict) else {}

    def get(self, section: str, key=None, fallback=None):
        if key is None or isinstance(key, (dict, list)):
            sec = self._config.get(section, {})
            return sec if isinstance(sec, dict) else (fallback if fallback is not None else {})
        sec = self._config.get(section, {})
        if not isinstance(sec, dict):
            return fallback
        return sec.get(key, fallback)

    def set(self, section: str, key: str, value):
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value
        self.save()
        self.config_changed.emit(self._config)

    def update_bulk(self, new_data: dict):
        self._config = self._deep_merge(self._config, new_data)
        self.save()
        self.config_changed.emit(self._config)

    def reset_defaults(self):
        self._config = json.loads(json.dumps(DEFAULT_CONFIG))
        self.save()
        self.config_changed.emit(self._config)

    def save(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ConfigManager] Error saving config: {e}")

    @property
    def data(self) -> dict:
        return self._config
