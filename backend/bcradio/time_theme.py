from __future__ import annotations

from datetime import datetime

from .contract import Theme


def theme_for_time(now: datetime | None = None) -> Theme:
    current = now or datetime.now().astimezone()
    return Theme.LIGHT if 8 <= current.hour < 19 else Theme.DARK
