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
from app.core.config import settings
from app.core.errors import install_exception_handlers
from app.ws.manager import WSManager

# --- NEW: optional monitoring/metrics (all behind flags) ---
# Routers are imported lazily so the code runs fine even if flags are off.
from app.services.store import Store  # lightweight; okay to import unconditionally

# Lifespan handler replaces @app.on_event("startup"/"shutdown")
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create shared WS manager and start the broadcast loop
    app.state.ws_manager = WSManager()
    cluster_task = asyncio.create_task(app.state.ws_manager.broadcast_cluster_loop())

    # --- NEW: create the in-memory snapshot store used by /monitoring and /metrics
    # Keep it always available; empty store is harmless and simplifies code paths.
    app.state.monitor_store = Store(capacity_per_key=120)

    # --- NEW: optional background monitor task (only if explicitly enabled)
    monitor_task = None
    if (
        settings.monitor_enabled
        and settings.monitor_groups
        and settings.monitor_topics
        and settings.monitor_rest_enabled  # background loop hits /monitoring/*
    ):
        import httpx

        async def _monitor_loop():
            base = (settings.monitor_api_base or "http://127.0.0.1:8000/api/v1").rstrip("/")
            interval = max(5, int(settings.monitor_interval_sec or 15))
            while True:
                try:
                    async with httpx.AsyncClient(timeout=20.0) as client:
                        for gid in settings.monitor_groups:
                            topics = settings.monitor_topics.get(gid, []) or []
                            for topic in topics:
                                # Calling our own feature-flagged endpoint will compute & store a sample
                                await client.get(f"{base}/monitoring/groups/{gid}/snapshot", params={"topic": topic})
                except Exception:
                    # Swallow transient errors; next tick will retry
                    pass
                await asyncio.sleep(interval)

        monitor_task = asyncio.create_task(_monitor_loop())

    try:
        yield
    finally:
        # Stop cluster loop
        cluster_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await cluster_task
        # Stop monitor loop if it was started
        if monitor_task:
            monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor_task


app = FastAPI(
    title="Kafka Admin API",
    version="1.0.0",
    lifespan=lifespan,
    # Put OpenAPI/docs under /api/v1 for consistency with your REST prefix
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
)

# --- CORS: allow web-ui during development (configurable via settings.cors_allow_origins) ---
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

# REST routes (existing)
app.include_router(cluster_router.router,  prefix="/api/v1")
app.include_router(topics_router.router,   prefix="/api/v1")
app.include_router(cg_router.router,       prefix="/api/v1")
app.include_router(messages_router.router, prefix="/api/v1")

# --- NEW: optional routers (feature-flagged) ---
if settings.monitor_rest_enabled:
    from app.api import group_monitoring as monitoring_router
    app.include_router(monitoring_router.router, prefix="/api/v1")

if settings.metrics_enabled:
    from app.api import metrics as metrics_router
    # metrics lives at /metrics (Prometheus convention)
    app.include_router(metrics_router.router, prefix="")

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
