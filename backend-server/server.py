# server.py
import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api import cluster as cluster_router
from app.api import topics as topics_router
from app.api import consumer_groups as cg_router
from app.api import messages as messages_router
from app.core.errors import install_exception_handlers
from app.ws.manager import WSManager


# Lifespan handler replaces @app.on_event("startup"/"shutdown")
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create shared WS manager and start the broadcast loop
    app.state.ws_manager = WSManager()
    task = asyncio.create_task(app.state.ws_manager.broadcast_cluster_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Kafka Admin API", version="1.0.0", lifespan=lifespan)

# CORS for local dev; tighten in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

install_exception_handlers(app)

# REST routes
app.include_router(cluster_router.router,  prefix="/api/v1")
app.include_router(topics_router.router,   prefix="/api/v1")
app.include_router(cg_router.router,       prefix="/api/v1")
app.include_router(messages_router.router, prefix="/api/v1")


# WebSocket route (note: not under /api/v1)
@app.websocket("/ws/v1/stream")
async def ws_stream(ws: WebSocket):
    ws_manager: WSManager = app.state.ws_manager
    await ws_manager.connect(ws)
    try:
        # No inbound messages yet; keep connection open
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)