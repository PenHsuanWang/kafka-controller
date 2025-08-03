"""Real-time WebSocket stream and broadcast manager.

Exports
-------
stream_handler : ASGI callable mounted at `/ws/v1/stream`
connection_manager : Singleton used by background tasks to push JSON frames
"""
from __future__ import annotations

import asyncio
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect

__all__ = ["stream_handler", "connection_manager"]  # ← make symbol public


class ConnectionManager:
    """Register WebSocket clients and broadcast JSON payloads."""

    def __init__(self) -> None:
        self._active: Set[WebSocket] = set()
        # Heart-beat every 30 s to keep NATs / LB alive
        asyncio.create_task(self._ping_loop(30))

    # ------------------------------------------------------------------ #
    # client lifecycle                                                   #
    # ------------------------------------------------------------------ #
    async def connect(self, ws: WebSocket) -> None:
        """Accept *ws* and notify it is ready."""
        await ws.accept()
        self._active.add(ws)
        await ws.send_json({"event": "ready"})

    def disconnect(self, ws: WebSocket) -> None:
        """Remove *ws* from the active set."""
        self._active.discard(ws)

    # ------------------------------------------------------------------ #
    # broadcast helpers                                                  #
    # ------------------------------------------------------------------ #
    async def broadcast(self, payload: dict) -> None:
        """Send *payload* to every connected client as JSON."""
        dead: Set[WebSocket] = set()
        for ws in self._active:
            try:
                await asyncio.wait_for(ws.send_json(payload), timeout=5)
            except (WebSocketDisconnect, asyncio.TimeoutError):
                dead.add(ws)
        for ws in dead:
            self.disconnect(ws)

    # ------------------------------------------------------------------ #
    # internal tasks                                                     #
    # ------------------------------------------------------------------ #
    async def _ping_loop(self, interval: int) -> None:
        """Send ping frames at a fixed *interval* (seconds)."""
        while True:
            await asyncio.sleep(interval)
            await self.broadcast({"event": "ping"})

    # ------------------------------------------------------------------ #
    # ASGI entry                                                         #
    # ------------------------------------------------------------------ #
async def stream_handler(ws: WebSocket) -> None:  # noqa: D401
    """Handle `/ws/v1/stream` upgrade and incoming messages."""
    await connection_manager.connect(ws)
    try:
        # Echo-back placeholder; extend with real command parsing
        while True:
            _ = await ws.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(ws)


# Singleton instance used across the app
connection_manager = ConnectionManager()

