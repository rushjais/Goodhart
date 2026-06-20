"""FastAPI surface: serve the single-file dashboard and stream the bus over a websocket."""

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from rampart.server.bus import EventBus

# Resolved relative to the package, not the cwd, so the server runs from anywhere.
_ROOT = Path(__file__).resolve().parents[3]
_DASHBOARD = _ROOT / "dashboard" / "index.html"
# Tier B capability chart data — present ONLY after a real two-model run is recorded.
# Absent (the default) → /capability.json 404s → the dashboard keeps the slot hidden.
_CAPABILITY = _ROOT / "capability_run.json"


def create_app(bus: EventBus, startup: Callable[[], Awaitable[None]] | None = None) -> FastAPI:
    """Build the app. `startup` (e.g. a replay task) is launched on the event loop at boot."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        task = asyncio.create_task(startup()) if startup else None
        yield
        if task:
            task.cancel()

    app = FastAPI(lifespan=lifespan)

    @app.get("/")
    async def index() -> HTMLResponse:
        return HTMLResponse(_DASHBOARD.read_text())

    @app.get("/capability.json")
    async def capability() -> Response:
        if _CAPABILITY.exists():
            return Response(_CAPABILITY.read_text(), media_type="application/json")
        return Response(status_code=404)  # no recorded run yet → slot stays hidden

    @app.websocket("/ws")
    async def stream(websocket: WebSocket) -> None:
        await websocket.accept()
        queue = bus.subscribe()
        try:
            while True:
                await websocket.send_json(await queue.get())
        except WebSocketDisconnect:
            pass
        finally:
            bus.unsubscribe(queue)

    return app
