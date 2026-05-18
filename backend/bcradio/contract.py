from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum


class Mode(StrEnum):
    OFF = "off"
    IDLE = "idle"
    STATION_SELECT = "station_select"
    PLAYBACK = "playback"
    PAUSED = "paused"
    NO_CONNECTION = "no_connection"
    SOFT_OFF_PENDING = "soft_off_pending"


class ConnectionStatus(StrEnum):
    ONLINE = "online"
    OFFLINE_CACHED = "offline_cached"
    OFFLINE_UNAVAILABLE = "offline_unavailable"


class PlaybackStatus(StrEnum):
    PLAYING = "playing"
    PAUSED = "paused"
    FADING_IN = "fading_in"
    FADING_OUT = "fading_out"
    STOPPED = "stopped"


class Theme(StrEnum):
    LIGHT = "light"
    DARK = "dark"


@dataclass(frozen=True)
class Track:
    title: str
    artist: str
    audio_url: str
    duration_seconds: int = 0
    album_art_url: str | None = None
    start_seconds: int = 0


@dataclass(frozen=True)
class Episode:
    genre: str
    title: str
    date: str
    url: str
    tracks: tuple[Track, ...]


@dataclass
class RadioState:
    mode: Mode = Mode.IDLE
    genre: str = "Indie"
    showTitle: str = ""
    showDate: str = ""
    artistName: str = ""
    trackTitle: str = ""
    albumArtUrl: str = "/assets/album art fallback/Art=No.png"
    trackIndex: int = 0
    trackTotal: int = 0
    elapsedSeconds: float = 0
    durationSeconds: float = 0
    volume: int = 70
    volumeOverlayVisible: bool = False
    connectionStatus: ConnectionStatus = ConnectionStatus.ONLINE
    errorMessage: str = ""
    playbackStatus: PlaybackStatus = PlaybackStatus.STOPPED
    theme: Theme = Theme.LIGHT

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["mode"] = self.mode.value
        data["connectionStatus"] = self.connectionStatus.value
        data["playbackStatus"] = self.playbackStatus.value
        data["theme"] = self.theme.value
        return data
