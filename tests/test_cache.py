import json
import time

from bcradio.episodes import EpisodeCache, EpisodeRepository, EpisodeUnavailable, demo_episode


class FailingSource:
    def fetch(self):
        raise EpisodeUnavailable("offline")


def test_stale_cache_is_used_when_network_fails(tmp_path):
    path = tmp_path / "episodes.json"
    episode = demo_episode("Indie")
    path.write_text(
        json.dumps(
            {
                "fetched_at": time.time() - 7200,
                "episodes": {
                    "Indie": {
                        "genre": episode.genre,
                        "title": episode.title,
                        "date": episode.date,
                        "url": episode.url,
                        "tracks": [
                            {
                                "title": track.title,
                                "artist": track.artist,
                                "audio_url": track.audio_url,
                                "duration_seconds": track.duration_seconds,
                                "album_art_url": track.album_art_url,
                            }
                            for track in episode.tracks
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    repo = EpisodeRepository(EpisodeCache(path, 3600), FailingSource(), use_demo_when_empty=False)

    library, status = repo.get_latest()

    assert status == "offline_cached"
    assert library["Indie"].title == "Indie Radio"


def test_empty_offline_repo_can_raise_for_no_connection_state(tmp_path):
    repo = EpisodeRepository(
        EpisodeCache(tmp_path / "missing.json", 3600),
        FailingSource(),
        use_demo_when_empty=False,
    )

    try:
        repo.get_latest()
    except EpisodeUnavailable:
        assert True
    else:
        assert False, "expected offline empty repository to raise"

