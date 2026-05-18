from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from aiohttp import WSMsgType, web

from .config import Settings
from .episodes import EpisodeCache, EpisodeRepository
from .input import InputEvent, normalize_key
from .mpv import MPVClient, NullPlayer
from .state import RadioController


def create_controller(settings: Settings) -> RadioController:
    cache = EpisodeCache(settings.cache_path, settings.cache_ttl_seconds)
    repository = EpisodeRepository(cache)
    player = MPVClient(settings.mpv_socket) if settings.mpv_socket.exists() else NullPlayer()
    return RadioController(repository, player, settings)


async def create_app(settings: Settings | None = None) -> web.Application:
    settings = settings or Settings(
        host=os.environ.get("BC_RADIO_HOST", "0.0.0.0"),
        port=int(os.environ.get("BC_RADIO_PORT", "8765")),
        allow_shutdown=os.environ.get("BC_RADIO_ALLOW_SHUTDOWN") == "1",
    )
    controller = create_controller(settings)
    sockets: set[web.WebSocketResponse] = set()

    async def broadcast(state) -> None:
        payload = json.dumps(state.to_dict())
        stale: list[web.WebSocketResponse] = []
        for ws in sockets:
            if ws.closed:
                stale.append(ws)
            else:
                await ws.send_str(payload)
        for ws in stale:
            sockets.discard(ws)

    controller.add_listener(broadcast)

    async def ws_handler(request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        sockets.add(ws)
        await ws.send_str(json.dumps(controller.state.to_dict()))
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                event = data.get("event")
                key = data.get("key")
                normalized = InputEvent(event) if event else normalize_key(str(key))
                if normalized:
                    await controller.handle(normalized)
            elif msg.type == WSMsgType.ERROR:
                break
        sockets.discard(ws)
        return ws

    async def state_handler(_: web.Request) -> web.Response:
        return web.json_response(controller.state.to_dict())

    async def event_handler(request: web.Request) -> web.Response:
        data = await request.json()
        event = InputEvent(data["event"])
        await controller.handle(event)
        return web.json_response(controller.state.to_dict())

    async def on_startup(_: web.Application) -> None:
        await controller.boot()

    app = web.Application()
    app["controller"] = controller
    app.router.add_get("/ws", ws_handler)
    app.router.add_get("/api/state", state_handler)
    app.router.add_post("/api/event", event_handler)
    app.on_startup.append(on_startup)

    dist_dir = Path(os.environ.get("BC_RADIO_DIST", "dist")).resolve()
    if dist_dir.is_dir():
        async def index_handler(_: web.Request) -> web.StreamResponse:
            return web.FileResponse(dist_dir / "index.html")

        app.router.add_get("/", index_handler)
        assets_dir = dist_dir / "assets"
        if assets_dir.is_dir():
            app.router.add_static("/assets", assets_dir)

    return app


def main() -> None:
    settings = Settings(
        host=os.environ.get("BC_RADIO_HOST", "0.0.0.0"),
        port=int(os.environ.get("BC_RADIO_PORT", "8765")),
        allow_shutdown=os.environ.get("BC_RADIO_ALLOW_SHUTDOWN") == "1",
    )
    web.run_app(asyncio.run(create_app(settings)), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
