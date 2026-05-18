from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Protocol


class Player(Protocol):
    async def load(self, url: str, *, pause: bool = False, start_seconds: int = 0) -> None: ...
    async def play(self) -> None: ...
    async def pause(self) -> None: ...
    async def stop(self) -> None: ...
    async def set_volume(self, volume: int) -> None: ...
    async def fade_to(self, target: int, seconds: float) -> None: ...
    async def get_time_pos(self) -> float | None: ...


class NullPlayer:
    def __init__(self) -> None:
        self.commands: list[str] = []
        self.volume = 70
        self.time_pos: float = 0.0

    async def load(self, url: str, *, pause: bool = False, start_seconds: int = 0) -> None:
        self.commands.append(f"load:{url}:pause={pause}:start={start_seconds}")
        self.time_pos = float(start_seconds)

    async def get_time_pos(self) -> float | None:
        return self.time_pos

    async def play(self) -> None:
        self.commands.append("play")

    async def pause(self) -> None:
        self.commands.append("pause")

    async def stop(self) -> None:
        self.commands.append("stop")

    async def set_volume(self, volume: int) -> None:
        self.volume = max(0, min(100, volume))
        self.commands.append(f"volume:{self.volume}")

    async def fade_to(self, target: int, seconds: float) -> None:
        self.volume = max(0, min(100, target))
        self.commands.append(f"fade:{self.volume}:{seconds}")


class MPVClient:
    def __init__(self, socket_path: Path, initial_volume: int = 70) -> None:
        self.socket_path = socket_path
        self.volume = initial_volume
        self._current_url: str | None = None

    async def _command(self, command: list[Any]) -> dict[str, Any]:
        reader, writer = await asyncio.open_unix_connection(str(self.socket_path))
        payload = json.dumps({"command": command}) + "\n"
        writer.write(payload.encode("utf-8"))
        await writer.drain()
        line = await reader.readline()
        writer.close()
        await writer.wait_closed()
        try:
            return json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}

    async def load(self, url: str, *, pause: bool = False, start_seconds: int = 0) -> None:
        if url == self._current_url:
            await self._command(["seek", start_seconds, "absolute", "exact"])
            await self._command(["set_property", "pause", pause])
            return
        await self._command(["loadfile", url, "replace"])
        self._current_url = url
        if start_seconds > 0:
            for _ in range(40):
                await asyncio.sleep(0.05)
                result = await self._command(["get_property", "duration"])
                if isinstance(result.get("data"), (int, float)):
                    break
            await self._command(["seek", start_seconds, "absolute", "exact"])
        await self._command(["set_property", "pause", pause])

    async def get_time_pos(self) -> float | None:
        result = await self._command(["get_property", "time-pos"])
        value = result.get("data")
        if isinstance(value, (int, float)):
            return float(value)
        return None

    async def play(self) -> None:
        await self._command(["set_property", "pause", False])

    async def pause(self) -> None:
        await self._command(["set_property", "pause", True])

    async def stop(self) -> None:
        await self._command(["stop"])
        self._current_url = None

    async def set_volume(self, volume: int) -> None:
        self.volume = max(0, min(100, volume))
        await self._command(["set_property", "volume", self.volume])

    async def fade_to(self, target: int, seconds: float) -> None:
        target = max(0, min(100, target))
        start = self.volume
        steps = max(1, int(seconds / 0.05))
        for step in range(1, steps + 1):
            value = round(start + ((target - start) * step / steps))
            await self.set_volume(value)
            await asyncio.sleep(seconds / steps)
