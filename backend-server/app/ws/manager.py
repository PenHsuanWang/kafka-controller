from __future__ import annotations
import asyncio
from typing import Set
from fastapi import WebSocket
from app.core.config import settings
from app.services.kafka_service import KafkaService
from app.services.jmx_service import JmxService

class WSManager:
    def __init__(self) -> None:
        self.clients: Set[WebSocket] = set()
        self.kafka = KafkaService()   # lazy connection inside
        self.jmx = JmxService()       # lazy connection inside

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket):
        self.clients.discard(ws)

    async def broadcast_cluster_loop(self):
        while True:
            if not self.clients:
                await asyncio.sleep(max(2 * settings.ws_cluster_tick, 2.0))
                continue
            payload = {
                "type": "event",
                "channel": "cluster",
                "event": "kpi.update",
                "data": self._build_cluster_kpis(),
            }
            await self._broadcast(payload)
            await asyncio.sleep(settings.ws_cluster_tick)

    async def _broadcast(self, payload: dict):
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def _build_cluster_kpis(self) -> dict:
        j = self.jmx.cluster_kpis()
        return {
            "brokersOnline": self.kafka.brokers_online(),
            "underReplicatedPartitions": j["underReplicatedPartitions"],
            "activeControllerCount": j["activeControllerCount"],
            "controllerElections24h": None,
            "throughput": j["throughput"],
        }