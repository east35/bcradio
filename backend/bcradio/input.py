from __future__ import annotations

from enum import StrEnum


class InputEvent(StrEnum):
    TUNE_LEFT = "tune_left"
    TUNE_RIGHT = "tune_right"
    TUNE_PRESS = "tune_press"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    VOLUME_PRESS = "volume_press"
    POWER_PRESS = "power_press"


KEY_MAP = {
    "a": InputEvent.TUNE_LEFT,
    "d": InputEvent.TUNE_RIGHT,
    "enter": InputEvent.TUNE_PRESS,
    "w": InputEvent.VOLUME_UP,
    "s": InputEvent.VOLUME_DOWN,
    " ": InputEvent.VOLUME_PRESS,
    "p": InputEvent.POWER_PRESS,
}


def normalize_key(key: str) -> InputEvent | None:
    return KEY_MAP.get(key.lower())
