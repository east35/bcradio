from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from .config import GENRES, Settings
from .contract import ConnectionStatus, Episode, Mode, PlaybackStatus, RadioState
from .episodes import EpisodeRepository
from .input import InputEvent
from .mpv import Player
from .time_theme import theme_for_time


StateListener = Callable[[RadioState], Awaitable[None]]


class RadioController:
    def __init__(
        self,
        episodes: EpisodeRepository,
        player: Player,
        settings: Settings = Settings(),
        shutdown: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self.episodes = episodes
        self.player = player
        self.settings = settings
        self.shutdown = shutdown or self._default_shutdown
        self.state = RadioState(genre="Indie", theme=theme_for_time())
        self.library: dict[str, Episode] = {}
        self.track_positions: dict[str, int] = {}
        self.current_genre = self.state.genre
        self.selected_genre = self.state.genre
        self.listeners: list[StateListener] = []
        self._volume_overlay_task: asyncio.Task[None] | None = None
        self._progress_task: asyncio.Task[None] | None = None

    async def boot(self) -> None:
        await self.refresh_episodes()
        if self.state.mode != Mode.NO_CONNECTION:
            self.state.mode = Mode.IDLE
        await self.publish()
        if self._progress_task is None:
            self._progress_task = asyncio.create_task(self._tick_progress())

    async def _tick_progress(self) -> None:
        while True:
            try:
                await asyncio.sleep(1.0)
                if self.state.playbackStatus != PlaybackStatus.PLAYING:
                    continue
                episode = self.library.get(self.state.genre)
                if not episode or not episode.tracks:
                    continue
                track = episode.tracks[self.state.trackIndex]
                pos = await self.player.get_time_pos()
                if pos is None:
                    continue
                elapsed = max(0, int(pos) - int(track.start_seconds))
                if elapsed >= self.state.durationSeconds > 0:
                    await self.next_track()
                    continue
                if elapsed != self.state.elapsedSeconds:
                    self.state.elapsedSeconds = elapsed
                    await self.publish()
            except asyncio.CancelledError:
                return
            except Exception:
                continue

    async def refresh_episodes(self) -> None:
        library, status = await asyncio.to_thread(self.episodes.get_latest)
        self.library = library
        self.state.connectionStatus = ConnectionStatus(status)
        if status == "offline_unavailable" and not library:
            self.state.mode = Mode.NO_CONNECTION
            self.state.errorMessage = "no connection"
        self._apply_episode(self.state.genre)

    def add_listener(self, listener: StateListener) -> None:
        self.listeners.append(listener)

    async def publish(self) -> None:
        self.state.theme = theme_for_time()
        for listener in list(self.listeners):
            await listener(self.state)

    async def handle(self, event: InputEvent) -> None:
        if event == InputEvent.POWER_PRESS:
            await self.soft_off()
            return
        if event == InputEvent.TUNE_PRESS:
            await self._handle_tune_press()
        elif event in (InputEvent.TUNE_LEFT, InputEvent.TUNE_RIGHT):
            await self._handle_tune_turn(1 if event == InputEvent.TUNE_RIGHT else -1)
        elif event in (InputEvent.VOLUME_UP, InputEvent.VOLUME_DOWN):
            await self._handle_volume(5 if event == InputEvent.VOLUME_UP else -5)
        elif event == InputEvent.VOLUME_PRESS:
            await self.toggle_pause()
        await self.publish()

    async def _handle_tune_press(self) -> None:
        if self.state.mode in (Mode.IDLE, Mode.PLAYBACK, Mode.PAUSED):
            self.selected_genre = self.current_genre
            self.state.genre = self.selected_genre
            self.state.mode = Mode.STATION_SELECT
            return
        if self.state.mode == Mode.STATION_SELECT:
            if self.selected_genre == self.current_genre and self.state.playbackStatus != PlaybackStatus.STOPPED:
                self.state.genre = self.current_genre
                self.state.mode = Mode.PAUSED if self.state.playbackStatus == PlaybackStatus.PAUSED else Mode.PLAYBACK
                return
            await self.start_station(self.selected_genre)

    async def _handle_tune_turn(self, direction: int) -> None:
        if self.state.mode == Mode.STATION_SELECT:
            current = GENRES.index(self.selected_genre)
            self.selected_genre = GENRES[(current + direction) % len(GENRES)]
            self.state.genre = self.selected_genre
            self._apply_episode(self.selected_genre, preview=True)
            return
        if self.state.mode in (Mode.PLAYBACK, Mode.PAUSED):
            keep_paused = self.state.mode == Mode.PAUSED
            if direction > 0:
                await self.next_track(keep_paused=keep_paused)
            elif self.state.elapsedSeconds > 3:
                await self.restart_track(keep_paused=keep_paused)
            else:
                await self.previous_track(keep_paused=keep_paused)

    async def _handle_volume(self, delta: int) -> None:
        self.state.volume = max(0, min(100, self.state.volume + delta))
        await self.player.set_volume(self.state.volume)
        self.state.volumeOverlayVisible = True
        if self._volume_overlay_task:
            self._volume_overlay_task.cancel()
        self._volume_overlay_task = asyncio.create_task(self._hide_volume_overlay())

    async def _hide_volume_overlay(self) -> None:
        try:
            await asyncio.sleep(1.2)
            self.state.volumeOverlayVisible = False
            await self.publish()
        except asyncio.CancelledError:
            return

    async def start_station(self, genre: str) -> None:
        if genre not in self.library or not self.library[genre].tracks:
            self.state.mode = Mode.NO_CONNECTION
            self.state.connectionStatus = ConnectionStatus.OFFLINE_UNAVAILABLE
            self.state.errorMessage = "no connection"
            self.state.playbackStatus = PlaybackStatus.STOPPED
            return
        if self.state.playbackStatus != PlaybackStatus.STOPPED:
            self.state.playbackStatus = PlaybackStatus.FADING_OUT
            await self.publish()
            await self.player.fade_to(0, self.settings.fade_seconds)
        self.state.genre = genre
        self.current_genre = genre
        self.selected_genre = genre
        self._apply_episode(genre)
        await self._load_current_track(pause=False)
        self.state.mode = Mode.PLAYBACK
        self.state.playbackStatus = PlaybackStatus.FADING_IN
        await self.publish()
        await self.player.fade_to(self.state.volume, self.settings.fade_seconds)
        self.state.playbackStatus = PlaybackStatus.PLAYING

    async def toggle_pause(self) -> None:
        if self.state.mode == Mode.PLAYBACK:
            self.state.playbackStatus = PlaybackStatus.FADING_OUT
            await self.publish()
            await self.player.fade_to(0, self.settings.fade_seconds)
            await self.player.pause()
            self.state.mode = Mode.PAUSED
            self.state.playbackStatus = PlaybackStatus.PAUSED
            await self.player.set_volume(self.state.volume)
        elif self.state.mode == Mode.PAUSED:
            await self.player.play()
            self.state.mode = Mode.PLAYBACK
            self.state.playbackStatus = PlaybackStatus.FADING_IN
            await self.publish()
            await self.player.fade_to(self.state.volume, self.settings.fade_seconds)
            self.state.playbackStatus = PlaybackStatus.PLAYING

    async def next_track(self, *, keep_paused: bool = False) -> None:
        episode = self.library.get(self.state.genre)
        if not episode or not episode.tracks:
            return
        self.track_positions[self.state.genre] = (self.state.trackIndex + 1) % len(episode.tracks)
        await self._change_track(keep_paused=keep_paused)

    async def previous_track(self, *, keep_paused: bool = False) -> None:
        episode = self.library.get(self.state.genre)
        if not episode or not episode.tracks:
            return
        total = len(episode.tracks)
        self.track_positions[self.state.genre] = (self.state.trackIndex - 1) % total
        await self._change_track(keep_paused=keep_paused)

    async def restart_track(self, *, keep_paused: bool = False) -> None:
        self.state.elapsedSeconds = 0
        await self._change_track(keep_paused=keep_paused)

    async def _change_track(self, *, keep_paused: bool) -> None:
        self.state.playbackStatus = PlaybackStatus.FADING_OUT
        await self.publish()
        await self.player.fade_to(0, self.settings.fade_seconds)
        self._apply_episode(self.state.genre)
        self.state.elapsedSeconds = 0
        await self._load_current_track(pause=keep_paused)
        if keep_paused:
            self.state.mode = Mode.PAUSED
            self.state.playbackStatus = PlaybackStatus.PAUSED
            await self.player.set_volume(self.state.volume)
        else:
            self.state.mode = Mode.PLAYBACK
            self.state.playbackStatus = PlaybackStatus.FADING_IN
            await self.publish()
            await self.player.fade_to(self.state.volume, self.settings.fade_seconds)
            self.state.playbackStatus = PlaybackStatus.PLAYING

    async def soft_off(self) -> None:
        await self.player.pause()
        self.state.playbackStatus = PlaybackStatus.PAUSED
        await self.publish()
        await self.shutdown()

    async def _load_current_track(self, *, pause: bool) -> None:
        episode = self.library[self.state.genre]
        track = episode.tracks[self.state.trackIndex]
        await self.player.load(track.audio_url, pause=pause, start_seconds=track.start_seconds)
        if pause:
            await self.player.pause()
        else:
            await self.player.play()

    def _apply_episode(self, genre: str, *, preview: bool = False) -> None:
        episode = self.library.get(genre)
        if not episode:
            return
        index = self.track_positions.get(genre, 0)
        track = episode.tracks[index] if episode.tracks else None
        self.state.showTitle = episode.title
        self.state.showDate = episode.date
        self.state.trackIndex = index
        self.state.trackTotal = len(episode.tracks)
        if track:
            self.state.artistName = track.artist
            self.state.trackTitle = track.title
            self.state.durationSeconds = track.duration_seconds
            self.state.albumArtUrl = track.album_art_url or "/assets/album art fallback/Art=No.png"
        elif preview:
            self.state.artistName = ""
            self.state.trackTitle = "tune to load"
            self.state.durationSeconds = 0

    async def _default_shutdown(self) -> None:
        if not self.settings.allow_shutdown:
            return
        proc = await asyncio.create_subprocess_exec(*self.settings.shutdown_command)
        await proc.wait()
