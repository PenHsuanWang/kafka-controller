"""Business-level operations about clusters & brokers."""
from __future__ import annotations

from typing import List

from app.domain.models.cluster import Broker, Cluster
from app.infra.kafka.admin import KafkaAdminFacade


class ClusterService:
    """Coordinates cluster-wide queries using the Kafka facade."""

    def __init__(self, admin: KafkaAdminFacade) -> None:
        self._admin = admin

    # --------------------------------------------------------------------- #
    # Cluster-level                                                          #
    # --------------------------------------------------------------------- #
    def list_clusters(self) -> List[Cluster]:
        """Return a singleton list; placeholder for multi-cluster deployments."""
        meta = self._admin._client.describe_cluster()
        return [
            Cluster(
                cluster_id=meta["cluster_id"],
                name=meta["cluster_id"],
                broker_count=len(meta["brokers"]),
                version=meta.get("controller", {}).get("version"),
            )
        ]

    def get_cluster(self, cid: str) -> Cluster:
        """Return KPIs for *cid* or raise KeyError."""
        clusters = self.list_clusters()
        for c in clusters:
            if c.cluster_id == cid:
                return c
        raise KeyError(cid)

    # --------------------------------------------------------------------- #
    # Broker-level                                                           #
    # --------------------------------------------------------------------- #
    def list_brokers(self) -> List[Broker]:
        """Return broker snapshots (ID, host, port only)."""
        meta = self._admin._client.describe_cluster()
        return [
            Broker(
                broker_id=b["node_id"],
                host=b["host"],
                port=b["port"],
            )
            for b in meta["brokers"]
        ]

    def get_broker(self, broker_id: int) -> Broker:
        """Return **Broker** or raise KeyError."""
        for b in self.list_brokers():
            if b.broker_id == broker_id:
                return b
        raise KeyError(broker_id)