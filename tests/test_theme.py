from datetime import datetime

from bcradio.contract import Theme
from bcradio.time_theme import theme_for_time


def test_light_theme_hours():
    assert theme_for_time(datetime(2026, 5, 18, 8, 0)) == Theme.LIGHT
    assert theme_for_time(datetime(2026, 5, 18, 18, 59)) == Theme.LIGHT


def test_dark_theme_hours():
    assert theme_for_time(datetime(2026, 5, 18, 7, 59)) == Theme.DARK
    assert theme_for_time(datetime(2026, 5, 18, 19, 0)) == Theme.DARK

