from __future__ import annotations

import json
import re
import time
from dataclasses import asdict
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from .config import GENRES
from .contract import Episode, Track


BANDCAMP_RADIO_URL = "https://bandcamp.com/radio"

FRANCHISE_TO_GENRE = {
    "Bandcamp Electronic": "Electronic",
    "Bandcamp Selects": "Selects",
    "The Game Show": "Games",
    "The Hip Hop Show": "Hip-Hop",
    "The Indie Show": "Indie",
    "The Metal Show": "Metal",
}


class EpisodeUnavailable(RuntimeError):
    pass


def demo_episode(genre: str) -> Episode:
    slug = genre.lower().replace("-", "").replace(" ", "-")
    return Episode(
        genre=genre,
        title=f"{genre} Radio",
        date="Demo",
        url=BANDCAMP_RADIO_URL,
        tracks=(
            Track(
                title=f"{genre} signal check",
                artist="Bandcamp Radio",
                audio_url=f"https://example.com/{slug}-signal-check.mp3",
                duration_seconds=180,
            ),
            Track(
                title=f"{genre} late night loop",
                artist="Bandcamp Radio",
                audio_url=f"https://example.com/{slug}-late-night-loop.mp3",
                duration_seconds=210,
            ),
        ),
    )


def _episode_from_dict(data: dict[str, Any]) -> Episode:
    tracks = tuple(Track(**track) for track in data.get("tracks", ()))
    return Episode(
        genre=data["genre"],
        title=data.get("title", ""),
        date=data.get("date", ""),
        url=data.get("url", BANDCAMP_RADIO_URL),
        tracks=tracks,
    )


def _episode_to_dict(episode: Episode) -> dict[str, Any]:
    data = asdict(episode)
    data["tracks"] = [asdict(track) for track in episode.tracks]
    return data


class EpisodeCache:
    def __init__(self, path: Path, ttl_seconds: int) -> None:
        self.path = path
        self.ttl_seconds = ttl_seconds

    def read_all(self, *, allow_stale: bool = True) -> dict[str, Episode]:
        if not self.path.exists():
            return {}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        fetched_at = raw.get("fetched_at", 0)
        if not allow_stale and time.time() - fetched_at > self.ttl_seconds:
            return {}
        return {
            genre: _episode_from_dict(payload)
            for genre, payload in raw.get("episodes", {}).items()
        }

    def is_fresh(self) -> bool:
        if not self.path.exists():
            return False
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return time.time() - raw.get("fetched_at", 0) <= self.ttl_seconds

    def write_all(self, episodes: dict[str, Episode]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "fetched_at": time.time(),
            "episodes": {
                genre: _episode_to_dict(episode)
                for genre, episode in episodes.items()
            },
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class BandcampEpisodeSource:
    def __init__(self, timeout_seconds: float = 8.0, max_pages: int = 6) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_pages = max_pages

    def fetch(self) -> dict[str, Episode]:
        discovered: dict[str, Episode] = {}
        for page in range(1, self.max_pages + 1):
            blob = self._fetch_archive_page(page)
            shows = blob.get("appData", {}).get("shows", [])
            for show in shows:
                franchise = show.get("radioFranchiseTitle", "")
                genre = FRANCHISE_TO_GENRE.get(franchise)
                show_id = show.get("itemId")
                if not genre or genre in discovered or not show_id:
                    continue
                discovered[genre] = self._fetch_show(show_id, genre, fallback_show=show)
            if all(genre in discovered for genre in GENRES):
                break

        if not discovered:
            raise EpisodeUnavailable("No Bandcamp Radio episodes found")
        return discovered

    def _fetch_archive_page(self, page: int) -> dict[str, Any]:
        url = BANDCAMP_RADIO_URL if page == 1 else f"{BANDCAMP_RADIO_URL}?page={page}"
        request = Request(
            url,
            headers={"User-Agent": "bc-radio-prototype/0.1"},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                html = response.read().decode("utf-8", errors="replace")
        except URLError as exc:
            raise EpisodeUnavailable(str(exc)) from exc
        return self._extract_blob(html)

    def _extract_blob(self, html: str) -> dict[str, Any]:
        match = re.search(r'data-blob="([^"]+)"', html)
        if not match:
            raise EpisodeUnavailable("Bandcamp radio data blob not found")
        return json.loads(unescape(match.group(1)))

    def _fetch_show(self, show_id: int, genre: str, *, fallback_show: dict[str, Any]) -> Episode:
        payload = json.dumps({"id": show_id}).encode("utf-8")
        request = Request(
            "https://bandcamp.com/api/bcradio_api/1/get_show",
            data=payload,
            headers={
                "Content-Type": "application/json; charset=UTF-8",
                "User-Agent": "bc-radio-prototype/0.1",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                show = json.loads(response.read().decode("utf-8", errors="replace"))
        except (URLError, json.JSONDecodeError) as exc:
            raise EpisodeUnavailable(str(exc)) from exc

        compiled = show.get("compiledTrack") or {}
        stream_url = compiled.get("streamUrl")
        if not stream_url:
            raise EpisodeUnavailable(f"Show {show_id} has no stream URL")
        source_tracks = show.get("tracks") or []
        total_duration = int(compiled.get("duration") or 0)
        tracks: list[Track] = []
        for index, track in enumerate(source_tracks):
            start = int(track.get("timecode") or 0)
            next_start = (
                int(source_tracks[index + 1].get("timecode") or 0)
                if index + 1 < len(source_tracks)
                else total_duration
            )
            art_id = track.get("artId") or show.get("imageId")
            tracks.append(
                Track(
                    title=unescape(track.get("title") or show.get("title") or ""),
                    artist=unescape(track.get("artistName") or show.get("title") or ""),
                    audio_url=stream_url,
                    duration_seconds=max(0, next_start - start),
                    album_art_url=self._image_url(art_id),
                    start_seconds=start,
                )
            )
        if not tracks:
            tracks.append(
                Track(
                    title=unescape(show.get("title") or fallback_show.get("title") or genre),
                    artist=show.get("title") or genre,
                    audio_url=stream_url,
                    duration_seconds=total_duration,
                    album_art_url=self._image_url(show.get("imageId") or fallback_show.get("imageId")),
                )
            )
        return Episode(
            genre=genre,
            title=unescape(fallback_show.get("title") or show.get("title") or genre),
            date=self._format_date(show.get("date") or fallback_show.get("date") or ""),
            url=f"https://bandcamp.com/radio?show={show_id}",
            tracks=tuple(tracks),
        )

    def _format_date(self, value: str) -> str:
        if not value:
            return ""
        try:
            parsed = datetime.strptime(value, "%d %b %Y %H:%M:%S %Z")
            return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"
        except ValueError:
            return value

    def _image_url(self, image_id: int | None) -> str | None:
        if not image_id:
            return None
        return f"https://f4.bcbits.com/img/a{image_id:010d}_10.jpg"


class EpisodeRepository:
    def __init__(
        self,
        cache: EpisodeCache,
        source: BandcampEpisodeSource | None = None,
        *,
        use_demo_when_empty: bool = True,
    ) -> None:
        self.cache = cache
        self.source = source or BandcampEpisodeSource()
        self.use_demo_when_empty = use_demo_when_empty

    def get_latest(self) -> tuple[dict[str, Episode], str]:
        if self.cache.is_fresh():
            return self.cache.read_all(allow_stale=False), "online"
        try:
            fetched = self.source.fetch()
            cached = self.cache.read_all(allow_stale=True)
            merged = {
                genre: fetched.get(genre) or cached.get(genre) or demo_episode(genre)
                for genre in GENRES
            }
            self.cache.write_all(merged)
            return merged, "online"
        except EpisodeUnavailable:
            cached = self.cache.read_all(allow_stale=True)
            if cached:
                return cached, "offline_cached"
            if self.use_demo_when_empty:
                demos = {genre: demo_episode(genre) for genre in GENRES}
                return demos, "offline_unavailable"
            raise
