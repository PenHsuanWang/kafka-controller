"""Background collector that transforms raw metrics into push frames."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from functools import lru_cache

from kafka.errors import NoBrokersAvailable

from app.api.web_socket import connection_manager
from app.domain.models.metrics import ClusterMetrics
from app.infra.kafka.admin import KafkaAdminFacade


logger = logging.getLogger(__name__)


@lru_cache
def _get_admin(bootstrap_servers: str) -> KafkaAdminFacade:
    """Return a cached Kafka admin facade for the cluster."""
    return KafkaAdminFacade(bootstrap_servers)


async def _collect(bootstrap_servers: str, sec: float) -> None:
    try:
        admin = _get_admin(bootstrap_servers)
    except NoBrokersAvailable:
        logger.warning("Kafka brokers unavailable; metrics collection disabled.")
        return
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
    try:
        _get_admin(bootstrap_servers)
    except NoBrokersAvailable:
        logger.warning("Kafka brokers unavailable; metric collector not started.")
        return
    asyncio.get_event_loop().create_task(_collect(bootstrap_servers, interval))