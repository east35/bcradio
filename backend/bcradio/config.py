from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


GENRES = ("Electronic", "Selects", "Hip-Hop", "Indie", "Metal", "Games")


@dataclass(frozen=True)
class Settings:
    host: str = "0.0.0.0"
    port: int = 8765
    cache_path: Path = Path(".cache/bandcamp_episodes.json")
    mpv_socket: Path = Path("/tmp/bc-radio-mpv.sock")
    fade_seconds: float = 0.5
    cache_ttl_seconds: int = 3600
    shutdown_command: tuple[str, ...] = ("sudo", "shutdown", "-h", "now")
    allow_shutdown: bool = False

