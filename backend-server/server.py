# server.py
from __future__ import annotations

import asyncio
import contextlib
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api import cluster as cluster_router
from app.api import topics as topics_router
from app.api import consumer_groups as cg_router
from app.api import messages as messages_router
from app.core.config import settings
from app.core.errors import install_exception_handlers
from app.ws.manager import WSManager

# Import the monitoring router we just implemented
from app.api import monitoring as monitoring_router

# The store class is created inside monitoring.py; we just use the instance hanging off app.state


@asynccontextmanager
async def lifespan(app: FastAPI):
    # WebSocket manager (existing)
    app.state.ws_manager = WSManager()
    cluster_task = asyncio.create_task(app.state.ws_manager.broadcast_cluster_loop())

    # In-memory monitoring store
    # (created in monitoring.get_store if absent, but we create it eagerly here)
    from app.api.monitoring import MonitorStore  # local import to avoid circulars
    app.state.monitor_store = MonitorStore(capacity_per_key=600)

    # Kafka bootstrap (used by monitoring snapshot endpoint)
    app.state.kafka_bootstrap = (
        getattr(settings, "kafka_bootstrap", None)
        or os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        or "localhost:9092"
    )

    monitor_task = None
    if (
        getattr(settings, "monitor_enabled", True)
        and getattr(settings, "monitor_rest_enabled", True)
        and getattr(settings, "monitor_groups", None)
        and getattr(settings, "monitor_topics", None)
    ):
        import httpx

        async def _monitor_loop():
            base = (getattr(settings, "monitor_api_base", None) or "http://127.0.0.1:8000/api/v1").rstrip("/")
            interval = max(5, int(getattr(settings, "monitor_interval_sec", 15)))
            while True:
                try:
                    async with httpx.AsyncClient(timeout=20.0) as client:
                        for gid in settings.monitor_groups:
                            topics = settings.monitor_topics.get(gid, []) or []
                            for topic in topics:
                                await client.get(
                                    f"{base}/monitoring/groups/{gid}/snapshot",
                                    params={"topic": topic},
                                )
                except Exception:
                    # Swallow errors to keep the loop alive (you'll still see 5xx in server logs)
                    pass
                await asyncio.sleep(interval)

        monitor_task = asyncio.create_task(_monitor_loop())

    try:
        yield
    finally:
        cluster_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await cluster_task
        if monitor_task:
            monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor_task


app = FastAPI(
    title="Kafka Admin API",
    version="1.0.0",
    lifespan=lifespan,
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
)

# CORS
allow_origins = settings.cors_allow_origins or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

install_exception_handlers(app)

# Existing routes
app.include_router(cluster_router.router,  prefix="/api/v1")
app.include_router(topics_router.router,   prefix="/api/v1")
app.include_router(cg_router.router,       prefix="/api/v1")
app.include_router(messages_router.router, prefix="/api/v1")

# Monitoring routes
app.include_router(monitoring_router.router, prefix="/api/v1")


@app.websocket("/ws/v1/stream")
async def ws_stream(ws: WebSocket):
    ws_manager: WSManager = app.state.ws_manager
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
