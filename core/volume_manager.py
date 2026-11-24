import ctypes
from ctypes import POINTER, c_float, cast, HRESULT, c_void_p, byref
from ctypes.wintypes import DWORD, BOOL
import uuid

class VolumeManager:
    """
    Direct Windows CoreAudio master volume controller using ctypes.
    Does not require any third-party dependencies (no pycaw or comtypes needed).
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = VolumeManager()
        return cls._instance

    def __init__(self):
        self._endpoint_vol = None
        self._init_endpoint()

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

    def _init_endpoint(self):
        try:
            ctypes.windll.ole32.CoInitialize(None)
            clsid_enum = self._get_guid('BCDE0395-E52F-467C-8E3D-C4579291692E')
            iid_enum = self._get_guid('A95664D2-9614-4F35-A746-DE8DB63617E6')
            iid_vol = self._get_guid('5CDF2C82-841E-4546-9722-0CF74078229A')

            enumerator = c_void_p()
            if ctypes.windll.ole32.CoCreateInstance(byref(clsid_enum), None, 1, byref(iid_enum), byref(enumerator)) != 0:
                return

            vtable = cast(cast(enumerator, POINTER(c_void_p)).contents, POINTER(c_void_p))
            get_def_ep = ctypes.WINFUNCTYPE(HRESULT, c_void_p, DWORD, DWORD, POINTER(c_void_p))(vtable[4])
            device = c_void_p()
            if get_def_ep(enumerator, 0, 0, byref(device)) != 0:
                return

            dev_vtable = cast(cast(device, POINTER(c_void_p)).contents, POINTER(c_void_p))
            activate = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_void_p, DWORD, c_void_p, POINTER(c_void_p))(dev_vtable[3])
            ep_vol = c_void_p()
            if activate(device, byref(iid_vol), 1, None, byref(ep_vol)) != 0:
                return

            self._endpoint_vol = ep_vol
        except Exception:
            self._endpoint_vol = None

    def get_volume(self) -> float:
        if not self._endpoint_vol:
            self._init_endpoint()
        if not self._endpoint_vol:
            return 0.5
        try:
            vtable = cast(cast(self._endpoint_vol, POINTER(c_void_p)).contents, POINTER(c_void_p))
            get_scalar = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(c_float))(vtable[9])
            cur = c_float()
            if get_scalar(self._endpoint_vol, byref(cur)) == 0:
                return max(0.0, min(1.0, float(cur.value)))
        except Exception:
            self._init_endpoint()
        return 0.5

    def set_volume(self, val: float):
        if not self._endpoint_vol:
            self._init_endpoint()
        if not self._endpoint_vol:
            return
        try:
            val = max(0.0, min(1.0, float(val)))
            vtable = cast(cast(self._endpoint_vol, POINTER(c_void_p)).contents, POINTER(c_void_p))
            set_scalar = ctypes.WINFUNCTYPE(HRESULT, c_void_p, c_float, c_void_p)(vtable[7])
            set_scalar(self._endpoint_vol, val, None)
        except Exception:
            self._init_endpoint()

    def get_mute(self) -> bool:
        if not self._endpoint_vol:
            self._init_endpoint()
        if not self._endpoint_vol:
            return False
        try:
            vtable = cast(cast(self._endpoint_vol, POINTER(c_void_p)).contents, POINTER(c_void_p))
            get_m = ctypes.WINFUNCTYPE(HRESULT, c_void_p, POINTER(BOOL))(vtable[15])
            m = BOOL()
            if get_m(self._endpoint_vol, byref(m)) == 0:
                return bool(m.value)
        except Exception:
            self._init_endpoint()
        return False

    def set_mute(self, is_muted: bool):
        if not self._endpoint_vol:
            self._init_endpoint()
        if not self._endpoint_vol:
            return
        try:
            vtable = cast(cast(self._endpoint_vol, POINTER(c_void_p)).contents, POINTER(c_void_p))
            set_m = ctypes.WINFUNCTYPE(HRESULT, c_void_p, BOOL, c_void_p)(vtable[14])
            set_m(self._endpoint_vol, BOOL(is_muted), None)
        except Exception:
            self._init_endpoint()

    def toggle_mute(self) -> bool:
        new_state = not self.get_mute()
        self.set_mute(new_state)
        return new_state

    def step_volume(self, delta: float) -> float:
        current = self.get_volume()
        new_vol = max(0.0, min(1.0, current + delta))
        self.set_volume(new_vol)
        if new_vol > 0 and self.get_mute():
            self.set_mute(False)
        return new_vol

