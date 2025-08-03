"""
Kafka Cluster Admin – FastAPI entry-point.

Run in development:

    uvicorn server:app --host 0.0.0.0 --port 8000 --reload

…or simply:

    python server.py       # thanks to the __main__ guard below
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# Ensure reusable deps (e.g., require_jwt) are imported once
from app.api import dependencies as _  # noqa: F401  (lint silence)

from app.api.routers import api_router
from app.api.web_socket import stream_handler
from app.core.config import get_settings
from app.core.exceptions import add_problem_detail_handler
from app.domain.services.metric_service import start_metric_collector

settings = get_settings()


# --------------------------------------------------------------------------- #
# Factory                                                                     #
# --------------------------------------------------------------------------- #
def create_app() -> FastAPI:
    """Build and configure a FastAPI application instance."""
    application = FastAPI(
        title="Kafka Cluster Admin API",
        version="1.0.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
    )

    # ---------- middleware --------------------------------------------------
    application.add_middleware(GZipMiddleware, minimum_size=1024)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],          # TODO: lock down in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------- REST + WS routes -------------------------------------------
    application.include_router(api_router, prefix="/api/v1")
    application.add_api_websocket_route("/ws/v1/stream", stream_handler)

    # ---------- problem-detail JSON (RFC 7807) ------------------------------
    add_problem_detail_handler(application)

    # ---------- background tasks -------------------------------------------
    application.add_event_handler(
        "startup",
        lambda: start_metric_collector(
            bootstrap_servers=settings.bootstrap_servers,
            interval=settings.poll_interval,
        ),
    )

    return application


app = create_app()

# --------------------------------------------------------------------------- #
# Optional CLI launcher                                                       #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,   # ⚠️ turn off in production
        workers=1,     # reload=True requires single worker
    )