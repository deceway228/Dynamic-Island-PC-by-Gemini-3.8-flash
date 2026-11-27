import sys
import winreg
from pathlib import Path

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "DynamicIsland"

def get_executable_path() -> str:
    """Returns the absolute path to DynamicIsland.exe."""
    if getattr(sys, "frozen", False):
        return sys.executable

    # Check for the compiled exe in workspace
    workspace_exe = Path(__file__).resolve().parent.parent / "DynamicIsland.exe"
    if workspace_exe.exists():
        return str(workspace_exe)

    return sys.executable

def is_autostart_enabled() -> bool:
    """Checks whether DynamicIsland is registered in Windows autostart."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception:
        return False

def set_autostart(enable: bool, exe_path: str = None) -> bool:
    """Adds or removes DynamicIsland from Windows autostart registry key."""
    if exe_path is None:
        exe_path = get_executable_path()

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                cmd = f'"{exe_path}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"[AutostartManager] Error setting autostart ({enable}): {e}")
        return False

def sync_autostart_with_config(config_mgr) -> bool:
    """Ensures registry state matches the user's config."""
    should_autostart = config_mgr.get("behavior", "autostart", True)
    if should_autostart:
        exe_path = get_executable_path()
        return set_autostart(True, exe_path)
    else:
        return set_autostart(False)
