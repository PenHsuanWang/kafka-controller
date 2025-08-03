"""Background collector that transforms raw metrics into push frames."""
from __future__ import annotations

import asyncio
from datetime import datetime

from app.api.web_socket import connection_manager
from app.domain.models.metrics import ClusterMetrics
from app.infra.kafka.admin import KafkaAdminFacade


async def _collect(bootstrap_servers: str, sec: float) -> None:
    admin = KafkaAdminFacade(bootstrap_servers)
    while True:
        # Simplest KPI-only snapshot
        cluster_meta = admin._client.describe_cluster()
        payload = ClusterMetrics(
            broker_online=len(cluster_meta["brokers"]),
            under_replicated=0,  # TODO: real JMX
            lagging_groups=0,
            in_sync_topics=0,
            ts=datetime.utcnow(),
        )
        await connection_manager.broadcast(payload.model_dump(mode="json"))
        await asyncio.sleep(sec)


def start_metric_collector(bootstrap_servers: str, interval: float) -> None:
    """Schedule async task from FastAPI startup event."""
    asyncio.get_event_loop().create_task(_collect(bootstrap_servers, interval))