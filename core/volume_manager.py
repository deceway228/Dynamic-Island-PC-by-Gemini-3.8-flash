import ctypes
from ctypes import POINTER, c_float, cast, HRESULT, c_void_p, byref, c_int
from ctypes.wintypes import DWORD, BOOL
import uuid
import time
from typing import List, Tuple, Optional

try:
    import psutil
except ImportError:
    psutil = None

class VolumeManager:
    """
    Intelligent per-app and master volume manager using Windows CoreAudio WASAPI.
    Directly reads and controls the volume of the active playing app/website (e.g. Spotify,
    SoundCloud/YouTube on Edge/Chrome, Apple Music, Yandex Music) without affecting the rest of the PC,
    with automatic graceful fallback to Windows Master Volume.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = VolumeManager()
        return cls._instance

    def __init__(self):
        try:
            ctypes.windll.ole32.CoInitialize(None)
        except Exception:
            pass

        self._clsid_enum = self._get_guid('BCDE0395-E52F-467C-8E3D-C4579291692E')
        self._iid_enum = self._get_guid('A95664D2-9614-4F35-A746-DE8DB63617E6')
        self._iid_vol = self._get_guid('5CDF2C82-841E-4546-9722-0CF74078229A')
        self._iid_mgr2 = self._get_guid('77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F')
        self._iid_ctrl2 = self._get_guid('bfb7ff88-7239-4fc9-8fa2-07c950be9c6d')
        self._iid_simple_vol = self._get_guid('87CE5498-68D6-44E5-9215-6DA47EF883D8')

        self._target_app_id = ""
        self._target_player_name = ""
        self._last_source_label = "Master"
        self._last_is_app = False
        self._cached_volume = 0.5
        self._cached_mute = False

    def _get_guid(self, s: str):
        u = uuid.UUID(s)
        class GUID(ctypes.Structure):
            _fields_ = [('D1', DWORD), ('D2', ctypes.c_ushort), ('D3', ctypes.c_ushort), ('D4', ctypes.c_ubyte * 8)]
        g = GUID()
        g.D1 = u.time_low
        g.D2 = u.time_mid
        g.D3 = u.time_hi_version
        for i, b in enumerate(u.bytes[8:]):
            g.D4[i] = b
        return g

    def set_target_media(self, media_data: dict):
        """Update target player info from MediaWorker."""
        app_id = media_data.get("app_id", "") or ""
        player_name = media_data.get("player_name", "") or ""
        self._target_app_id = app_id.lower().strip()
        self._target_player_name = player_name.lower().strip()

    def set_target_app(self, app_id: str, player_name: str = ""):
        self._target_app_id = (app_id or "").lower().strip()
        self._target_player_name = (player_name or "").lower().strip()

    def _get_default_device(self) -> Optional[c_void_p]:
        try:
            enumerator = c_void_p()
            if ctypes.windll.ole32.CoCreateInstance(
                byref(self._clsid_enum), None, 1, byref(self._iid_enum), byref(enumerator)
            ) != 0 or not enumerator.value:
                return None

            vtable = cast(cast(enumerator, POINTER(c_void_p)).contents, POINTER(c_void_p))
            get_def_ep = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD, DWORD, POINTER(c_void_p))(vtable[4])
            device = c_void_p()
            if get_def_ep(enumerator, 0, 0, byref(device)) != 0 or not device.value:
                return None
            return device
        except Exception:
            return None

    def _match_process(self, proc_name: str) -> bool:
        pn = proc_name.lower().replace(".exe", "")
        aid = self._target_app_id
        pname = self._target_player_name

        if not aid and not pname:
            return False

        if pn and (pn in aid or aid in pn or pn in pname or pname in pn):
            return True

        aliases = {
            "msedge": ["edge", "msedge"],
            "chrome": ["chrome", "googlechrome"],
            "spotify": ["spotify"],
            "applemusic": ["apple", "applemusic", "itunes"],
            "yandex": ["yandex", "browser"],
            "firefox": ["firefox", "mozilla"],
            "vlc": ["vlc"],
            "opera": ["opera"],
            "brave": ["brave"]
        }
        for k, v in aliases.items():
            if any(x in pn for x in v):
                if any(x in aid or x in pname for x in v):
                    return True

        return False

    def _get_target_sessions(self) -> List[Tuple[c_void_p, str, int]]:
        """Returns list of (ISimpleAudioVolume, proc_name, pid) matching the active media app."""
        device = self._get_default_device()
        if not device:
            return []

        try:
            dev_vtable = cast(cast(device, POINTER(c_void_p)).contents, POINTER(c_void_p))
            activate = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, DWORD, c_void_p, POINTER(c_void_p))(dev_vtable[3])
            mgr2 = c_void_p()
            if activate(device, byref(self._iid_mgr2), 1, None, byref(mgr2)) != 0 or not mgr2.value:
                return []

            mgr_vtable = cast(cast(mgr2, POINTER(c_void_p)).contents, POINTER(c_void_p))
            get_session_enum = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_void_p))(mgr_vtable[5])
            session_enum = c_void_p()
            if get_session_enum(mgr2, byref(session_enum)) != 0 or not session_enum.value:
                return []

            enum_vtable = cast(cast(session_enum, POINTER(c_void_p)).contents, POINTER(c_void_p))
            get_count = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_int))(enum_vtable[3])
            get_session = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_int, POINTER(c_void_p))(enum_vtable[4])
            count = c_int()
            get_count(session_enum, byref(count))

            matched = []
            for i in range(count.value):
                session = c_void_p()
                if get_session(session_enum, i, byref(session)) != 0 or not session.value:
                    continue
                s_vtable = cast(cast(session, POINTER(c_void_p)).contents, POINTER(c_void_p))
                qi = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, POINTER(c_void_p))(s_vtable[0])

                ctrl2 = c_void_p()
                hr = qi(session, byref(self._iid_ctrl2), byref(ctrl2))
                pid = DWORD(0)
                proc_name = ""
                if hr == 0 and ctrl2.value:
                    c2_vtable = cast(cast(ctrl2, POINTER(c_void_p)).contents, POINTER(c_void_p))
                    get_pid = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(DWORD))(c2_vtable[14])
                    get_pid(ctrl2, byref(pid))
                    if pid.value > 0 and psutil:
                        try:
                            proc_name = psutil.Process(pid.value).name().lower()
                        except Exception:
                            pass

                if self._match_process(proc_name):
                    vol = c_void_p()
                    if qi(session, byref(self._iid_simple_vol), byref(vol)) == 0 and vol.value:
                        matched.append((vol, proc_name, pid.value))

            return matched
        except Exception:
            return []

    def _get_master_endpoint(self) -> Optional[c_void_p]:
        device = self._get_default_device()
        if not device:
            return None
        try:
            dev_vtable = cast(cast(device, POINTER(c_void_p)).contents, POINTER(c_void_p))
            activate = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, DWORD, c_void_p, POINTER(c_void_p))(dev_vtable[3])
            ep_vol = c_void_p()
            if activate(device, byref(self._iid_vol), 1, None, byref(ep_vol)) == 0 and ep_vol.value:
                return ep_vol
        except Exception:
            pass
        return None

    def get_source_label(self) -> str:
        return self._last_source_label

    def is_app_volume(self) -> bool:
        return self._last_is_app

    def get_volume(self) -> float:
        """Returns the volume (0.0 - 1.0) of the active app/site, or master volume as fallback."""
        try:
            sessions = self._get_target_sessions()
            if sessions:
                vol, proc_name, pid = sessions[0]
                v_vtable = cast(cast(vol, POINTER(c_void_p)).contents, POINTER(c_void_p))
                get_vol = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_float))(v_vtable[4])
                cur = c_float()
                if get_vol(vol, byref(cur)) == 0:
                    self._last_is_app = True
                    self._last_source_label = self._pretty_name(proc_name)
                    self._cached_volume = max(0.0, min(1.0, float(cur.value)))
                    return self._cached_volume

            # Fallback to master PC volume
            ep = self._get_master_endpoint()
            if ep:
                vtable = cast(cast(ep, POINTER(c_void_p)).contents, POINTER(c_void_p))
                get_scalar = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_float))(vtable[9])
                cur = c_float()
                if get_scalar(ep, byref(cur)) == 0:
                    self._last_is_app = False
                    self._last_source_label = "PC"
                    self._cached_volume = max(0.0, min(1.0, float(cur.value)))
                    return self._cached_volume
        except Exception:
            pass
        return self._cached_volume

    def set_volume(self, val: float):
        """Sets the volume (0.0 - 1.0) of the active app/site, or master volume as fallback."""
        val = max(0.0, min(1.0, float(val)))
        self._cached_volume = val
        try:
            sessions = self._get_target_sessions()
            if sessions:
                for vol, _, _ in sessions:
                    v_vtable = cast(cast(vol, POINTER(c_void_p)).contents, POINTER(c_void_p))
                    set_vol = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_float, c_void_p)(v_vtable[3])
                    set_vol(vol, val, None)
                self._last_is_app = True
                return

            # Fallback to master
            ep = self._get_master_endpoint()
            if ep:
                vtable = cast(cast(ep, POINTER(c_void_p)).contents, POINTER(c_void_p))
                set_scalar = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_float, c_void_p)(vtable[7])
                set_scalar(ep, val, None)
                self._last_is_app = False
        except Exception:
            pass

    def get_mute(self) -> bool:
        """Returns whether the active app/site or master is muted."""
        try:
            sessions = self._get_target_sessions()
            if sessions:
                vol, _, _ = sessions[0]
                v_vtable = cast(cast(vol, POINTER(c_void_p)).contents, POINTER(c_void_p))
                get_m = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(BOOL))(v_vtable[6])
                m = BOOL()
                if get_m(vol, byref(m)) == 0:
                    self._cached_mute = bool(m.value)
                    return self._cached_mute

            ep = self._get_master_endpoint()
            if ep:
                vtable = cast(cast(ep, POINTER(c_void_p)).contents, POINTER(c_void_p))
                get_m = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(BOOL))(vtable[15])
                m = BOOL()
                if get_m(ep, byref(m)) == 0:
                    self._cached_mute = bool(m.value)
                    return self._cached_mute
        except Exception:
            pass
        return self._cached_mute

    def set_mute(self, muted: bool):
        """Sets mute for the active app/site or master."""
        self._cached_mute = muted
        b = BOOL(muted)
        try:
            sessions = self._get_target_sessions()
            if sessions:
                for vol, _, _ in sessions:
                    v_vtable = cast(cast(vol, POINTER(c_void_p)).contents, POINTER(c_void_p))
                    set_m = ctypes.WINFUNCTYPE(HRESULT, c_void_p, BOOL, c_void_p)(v_vtable[5])
                    set_m(vol, b, None)
                return

            ep = self._get_master_endpoint()
            if ep:
                vtable = cast(cast(ep, POINTER(c_void_p)).contents, POINTER(c_void_p))
                set_m = ctypes.WINFUNCTYPE(HRESULT, c_void_p, BOOL, c_void_p)(vtable[14])
                set_m(ep, b, None)
        except Exception:
            pass

    def toggle_mute(self) -> bool:
        cur = self.get_mute()
        new_m = not cur
        self.set_mute(new_m)
        return new_m

    def step_volume(self, step: float) -> float:
        cur = self.get_volume()
        new_vol = max(0.0, min(1.0, cur + step))
        self.set_volume(new_vol)
        if self.get_mute() and new_vol > 0.01:
            self.set_mute(False)
        return new_vol

    def _pretty_name(self, proc_name: str) -> str:
        pn = proc_name.lower().replace(".exe", "")
        pretty_map = {
            "msedge": "Edge",
            "chrome": "Chrome",
            "spotify": "Spotify",
            "applemusic": "Apple Music",
            "firefox": "Firefox",
            "yandexmusic": "Yandex",
            "browser": "Yandex",
            "vlc": "VLC",
            "opera": "Opera",
            "brave": "Brave"
        }
        return pretty_map.get(pn, pn.capitalize() if pn else "App")
