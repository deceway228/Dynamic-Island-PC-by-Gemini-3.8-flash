import asyncio
import time
from typing import Optional
from PySide6.QtCore import QThread, Signal
from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    GlobalSystemMediaTransportControlsSession as MediaSession,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus
)
from winrt.windows.storage.streams import DataReader
from core.color_extractor import ColorExtractor

def detect_player_name(app_id: str, title: str = "", artist: str = "") -> dict:
    """Detects clean player name and icon type from app_id and metadata."""
    app_lower = (app_id or "").lower()
    meta_lower = f"{title} {artist}".lower()

    if "spotify" in app_lower:
        return {"name": "Spotify", "type": "spotify", "brand_color": "#1DB954"}
    elif "applemusic" in app_lower or "apple" in app_lower:
        return {"name": "Apple Music", "type": "apple", "brand_color": "#FC3C44"}
    elif "soundcloud" in app_lower or "soundcloud" in meta_lower:
        return {"name": "SoundCloud", "type": "soundcloud", "brand_color": "#FF5500"}
    elif "deezer" in app_lower:
        return {"name": "Deezer", "type": "deezer", "brand_color": "#A238FF"}
    elif "tidal" in app_lower:
        return {"name": "TIDAL", "type": "tidal", "brand_color": "#00FFFF"}
    elif "yandex" in app_lower:
        return {"name": "Yandex Music", "type": "yandex", "brand_color": "#FFCC00"}
    elif "chrome" in app_lower:
        if "soundcloud" in meta_lower:
            return {"name": "SoundCloud (Chrome)", "type": "soundcloud", "brand_color": "#FF5500"}
        return {"name": "Chrome Media", "type": "browser", "brand_color": "#4285F4"}
    elif "msedge" in app_lower:
        if "soundcloud" in meta_lower:
            return {"name": "SoundCloud (Edge)", "type": "soundcloud", "brand_color": "#FF5500"}
        return {"name": "Edge Media", "type": "browser", "brand_color": "#0078D7"}
    elif "firefox" in app_lower:
        if "soundcloud" in meta_lower:
            return {"name": "SoundCloud (Firefox)", "type": "soundcloud", "brand_color": "#FF5500"}
        return {"name": "Firefox Media", "type": "browser", "brand_color": "#FF7139"}
    elif "brave" in app_lower:
        return {"name": "Brave Media", "type": "browser", "brand_color": "#FB542B"}
    
    clean_name = app_id.replace(".exe", "").split("\\")[-1] if app_id else "Media Player"
    return {"name": clean_name, "type": "generic", "brand_color": "#8A8A8E"}


class MediaWorker(QThread):
    # Signals to main thread
    media_changed = Signal(dict)
    playback_state_changed = Signal(bool)
    timeline_updated = Signal(float, float)  # position, duration
    session_status_changed = Signal(bool)    # has_active_session

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._action_queue = asyncio.Queue()
        
        # State tracking to avoid redundant emissions
        self._last_title = ""
        self._last_artist = ""
        self._last_is_playing = None
        self._last_duration = 0.0
        self._last_app_id = ""
        self._last_thumb_bytes = b""
        self._thumb_retries = 0

        # Smooth timeline tracking
        self._base_position = 0.0
        self._base_monotonic = time.monotonic()
        self._last_winrt_position = -1.0
        self._last_winrt_update_time = None
        self._duration = 0.0
        self._is_playing_cache = False

    async def _read_thumbnail(self, props) -> bytes:
        """Safely extracts thumbnail bytes from WinRT stream reference."""
        if not props or not props.thumbnail:
            return b""
        try:
            stream = await props.thumbnail.open_read_async()
            if not stream or stream.size == 0:
                return b""
            size = stream.size
            reader = DataReader(stream.get_input_stream_at(0))
            await reader.load_async(size)
            buf = bytearray(size)
            reader.read_bytes(buf)
            return bytes(buf)
        except Exception:
            return b""

    def run(self):
        asyncio.run(self._main_loop())

    def stop(self):
        self._running = False
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._action_queue.put({"action": "stop"}), self._loop)
        self.wait(2000)

    # Thread-safe control methods called from UI
    def toggle_play_pause(self):
        self._post_action({"action": "toggle"})

    def play(self):
        self._post_action({"action": "play"})

    def pause(self):
        self._post_action({"action": "pause"})

    def next_track(self):
        self._post_action({"action": "next"})

    def previous_track(self):
        self._post_action({"action": "prev"})

    def seek_to(self, seconds: float):
        self._base_position = max(0.0, seconds)
        self._base_monotonic = time.monotonic()
        self._last_winrt_position = seconds
        self._post_action({"action": "seek", "seconds": seconds})

    def _post_action(self, action_dict: dict):
        if self._loop and self._loop.is_running():
            try:
                self._loop.call_soon_threadsafe(self._action_queue.put_nowait, action_dict)
            except Exception as e:
                print(f"[MediaWorker] Post action error: {e}")

    async def _main_loop(self):
        self._loop = asyncio.get_running_loop()
        manager = None

        while self._running:
            try:
                if manager is None:
                    manager = await MediaManager.request_async()
            except Exception as e:
                print(f"[MediaWorker] Manager request error: {e}")
                await asyncio.sleep(2.0)
                continue

            try:
                # Process any pending UI control actions first
                while not self._action_queue.empty():
                    action = self._action_queue.get_nowait()
                    if action.get("action") == "stop":
                        return
                    await self._execute_action(manager, action)

                # Fetch active session
                session = manager.get_current_session()
                if not session:
                    # Check if any session exists in sessions list
                    all_sessions = manager.get_sessions()
                    if all_sessions and len(all_sessions) > 0:
                        session = all_sessions[0]

                if not session:
                    if self._last_is_playing is not None:
                        self._last_is_playing = None
                        self._last_title = ""
                        self._last_artist = ""
                        self.session_status_changed.emit(False)
                        self.playback_state_changed.emit(False)
                    await asyncio.sleep(0.6)
                    continue

                # Query playback info
                playback_info = session.get_playback_info()
                is_playing = (playback_info.playback_status == PlaybackStatus.PLAYING) if playback_info else False
                self._is_playing_cache = is_playing

                if is_playing != self._last_is_playing:
                    # When switching play state, update monotonic anchor
                    if is_playing:
                        self._base_monotonic = time.monotonic()
                    else:
                        if self._duration > 0:
                            elapsed = time.monotonic() - self._base_monotonic
                            self._base_position = min(self._duration, max(0.0, self._base_position + elapsed))
                        self._base_monotonic = time.monotonic()

                    self._last_is_playing = is_playing
                    self.playback_state_changed.emit(is_playing)
                    self.session_status_changed.emit(True)

                # Query media properties (metadata & thumbnail)
                props = await session.try_get_media_properties_async()
                title = props.title if props else ""
                artist = props.artist if props else ""
                album = props.album_title if props else ""
                app_id = session.source_app_user_model_id or ""

                track_changed = (title != self._last_title or artist != self._last_artist or app_id != self._last_app_id)

                if track_changed:
                    self._last_title = title
                    self._last_artist = artist
                    self._last_app_id = app_id
                    self._last_thumb_bytes = b""
                    self._thumb_retries = 0

                    # Reset timeline tracking for new track
                    self._base_position = 0.0
                    self._base_monotonic = time.monotonic()
                    self._last_winrt_position = -1.0
                    self._last_winrt_update_time = None
                    self._duration = 0.0

                    # Read thumbnail image bytes with quick async retry for auto-song transitions
                    thumb_bytes = await self._read_thumbnail(props)
                    if not thumb_bytes:
                        for _ in range(4):
                            await asyncio.sleep(0.12)
                            fresh_props = await session.try_get_media_properties_async()
                            thumb_bytes = await self._read_thumbnail(fresh_props)
                            if thumb_bytes:
                                props = fresh_props
                                break

                    self._last_thumb_bytes = thumb_bytes

                    # Extract palette and branding
                    player_info = detect_player_name(app_id, title, artist)
                    palette = ColorExtractor.extract_palette(thumb_bytes, fallback_hex=player_info["brand_color"])

                    media_data = {
                        "title": title or "Unknown Track",
                        "artist": artist or "Unknown Artist",
                        "album": album or "",
                        "app_id": app_id,
                        "player_name": player_info["name"],
                        "player_type": player_info["type"],
                        "brand_color": player_info["brand_color"],
                        "thumbnail_bytes": thumb_bytes,
                        "palette": palette,
                        "is_playing": is_playing
                    }
                    self.media_changed.emit(media_data)

                elif not self._last_thumb_bytes and self._thumb_retries < 15:
                    # If thumbnail arrived a bit late after title changed, fetch and update it!
                    self._thumb_retries += 1
                    fresh_thumb = await self._read_thumbnail(props)
                    if fresh_thumb:
                        self._last_thumb_bytes = fresh_thumb
                        player_info = detect_player_name(app_id, title, artist)
                        palette = ColorExtractor.extract_palette(fresh_thumb, fallback_hex=player_info["brand_color"])
                        media_data = {
                            "title": title or "Unknown Track",
                            "artist": artist or "Unknown Artist",
                            "album": album or "",
                            "app_id": app_id,
                            "player_name": player_info["name"],
                            "player_type": player_info["type"],
                            "brand_color": player_info["brand_color"],
                            "thumbnail_bytes": fresh_thumb,
                            "palette": palette,
                            "is_playing": is_playing
                        }
                        self.media_changed.emit(media_data)

                # Query timeline
                timeline = session.get_timeline_properties()
                if timeline:
                    pos_sec = timeline.position.total_seconds() if timeline.position else 0.0
                    dur_sec = timeline.end_time.total_seconds() if timeline.end_time else 0.0
                    last_updated = timeline.last_updated_time

                    # Check if WinRT provided a fresh snapshot (user seeked, paused, or started track)
                    has_fresh_snapshot = (
                        (last_updated is not None and last_updated != self._last_winrt_update_time) or
                        (self._last_winrt_position < 0) or
                        abs(pos_sec - self._last_winrt_position) > 1.2
                    )

                    if has_fresh_snapshot:
                        self._base_position = pos_sec
                        self._base_monotonic = time.monotonic()
                        self._last_winrt_position = pos_sec
                        self._last_winrt_update_time = last_updated
                        self._duration = dur_sec
                    else:
                        if dur_sec > 0:
                            self._duration = dur_sec

                    # Calculate continuous interpolated position
                    if self._is_playing_cache and self._duration > 0:
                        elapsed = time.monotonic() - self._base_monotonic
                        current_pos = min(self._duration, max(0.0, self._base_position + elapsed))
                    else:
                        current_pos = min(self._duration, max(0.0, self._base_position)) if self._duration > 0 else self._base_position

                    self.timeline_updated.emit(current_pos, self._duration)

            except Exception as e:
                # Silently catch brief COM/session transition flickers
                pass

            # Sleep between queries
            await asyncio.sleep(0.20)

    async def _execute_action(self, manager, action: dict):
        try:
            session = manager.get_current_session()
            if not session:
                sessions = manager.get_sessions()
                if sessions and len(sessions) > 0:
                    session = sessions[0]
            if not session:
                return

            act = action.get("action")
            if act == "toggle":
                await session.try_toggle_play_pause_async()
            elif act == "play":
                await session.try_play_async()
            elif act == "pause":
                await session.try_pause_async()
            elif act == "next":
                await session.try_skip_next_async()
            elif act == "prev":
                await session.try_skip_previous_async()
            elif act == "seek":
                secs = action.get("seconds", 0.0)
                # Convert to 100-nanosecond ticks
                ticks = int(secs * 10_000_000)
                await session.try_change_playback_position_async(ticks)
        except Exception as e:
            print(f"[MediaWorker] Execute action error: {e}")

