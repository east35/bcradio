import pytest

from bcradio.config import Settings
from bcradio.contract import Mode, PlaybackStatus
from bcradio.episodes import EpisodeCache, EpisodeRepository, demo_episode
from bcradio.input import InputEvent
from bcradio.mpv import NullPlayer
from bcradio.state import RadioController


class StaticSource:
    def fetch(self):
        return {
            genre: demo_episode(genre)
            for genre in ("Electronic", "Selects", "Hip-Hop", "Indie", "Metal", "Games")
        }


@pytest.fixture
async def controller(tmp_path):
    cache = EpisodeCache(tmp_path / "episodes.json", 3600)
    repo = EpisodeRepository(cache, StaticSource())
    player = NullPlayer()
    radio = RadioController(repo, player, Settings(fade_seconds=0), shutdown=lambda: noop())
    await radio.boot()
    return radio


async def noop():
    return None


@pytest.mark.asyncio
async def test_tune_press_enters_station_select_without_playback(controller):
    await controller.start_station("Indie")
    await controller.handle(InputEvent.TUNE_PRESS)

    assert controller.state.mode == Mode.STATION_SELECT
    assert controller.state.playbackStatus == PlaybackStatus.PLAYING


@pytest.mark.asyncio
async def test_confirming_new_station_fades_and_loads(controller):
    await controller.start_station("Indie")
    await controller.handle(InputEvent.TUNE_PRESS)
    await controller.handle(InputEvent.TUNE_RIGHT)
    selected = controller.selected_genre
    await controller.handle(InputEvent.TUNE_PRESS)

    assert controller.state.mode == Mode.PLAYBACK
    assert controller.state.genre == selected
    assert controller.state.playbackStatus == PlaybackStatus.PLAYING
    assert "fade:0:0" in controller.player.commands
    assert any(command.startswith("load:") for command in controller.player.commands)


@pytest.mark.asyncio
async def test_pause_and_resume_use_fades(controller):
    await controller.start_station("Indie")
    await controller.handle(InputEvent.VOLUME_PRESS)

    assert controller.state.mode == Mode.PAUSED
    assert controller.state.playbackStatus == PlaybackStatus.PAUSED

    await controller.handle(InputEvent.VOLUME_PRESS)

    assert controller.state.mode == Mode.PLAYBACK
    assert controller.state.playbackStatus == PlaybackStatus.PLAYING
    assert controller.player.commands.count("pause") >= 1
    assert controller.player.commands.count("play") >= 2


@pytest.mark.asyncio
async def test_paused_track_change_remains_paused(controller):
    await controller.start_station("Indie")
    await controller.handle(InputEvent.VOLUME_PRESS)
    await controller.handle(InputEvent.TUNE_RIGHT)

    assert controller.state.mode == Mode.PAUSED
    assert controller.state.trackIndex == 1
    assert controller.state.playbackStatus == PlaybackStatus.PAUSED


@pytest.mark.asyncio
async def test_soft_off_clears_session_resume(controller):
    await controller.start_station("Indie")
    await controller.handle(InputEvent.TUNE_RIGHT)
    assert controller.track_positions["Indie"] == 1

    await controller.handle(InputEvent.POWER_PRESS)

    assert controller.state.mode == Mode.OFF
    assert controller.track_positions == {}
    assert "stop" in controller.player.commands

