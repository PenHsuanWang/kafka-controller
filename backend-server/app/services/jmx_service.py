from __future__ import annotations
from jmxquery import JMXConnection, JMXQuery
from app.core.config import settings

class JmxService:
    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        host = host or settings.jmx_host
        port = port or settings.jmx_port
        self._url = f"service:jmx:rmi:///jndi/rmi://{host}:{port}/jmxrmi"
        self._conn: JMXConnection | None = None

    def _ensure_conn(self) -> JMXConnection | None:
        if self._conn:
            return self._conn
        try:
            self._conn = JMXConnection(self._url)
            return self._conn
        except Exception:
            return None

    def cluster_kpis(self) -> dict:
        conn = self._ensure_conn()
        if not conn:
            return {
                "activeControllerCount": 0,
                "underReplicatedPartitions": 0,
                "throughput": {"bytesInPerSec": 0.0, "bytesOutPerSec": 0.0, "messagesInPerSec": 0.0},
            }
        try:
            queries = [
                JMXQuery("kafka.controller:type=KafkaController,name=ActiveControllerCount"),
                JMXQuery("kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions"),
                JMXQuery("kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec", attribute="OneMinuteRate"),
                JMXQuery("kafka.server:type=BrokerTopicMetrics,name=BytesOutPerSec", attribute="OneMinuteRate"),
                JMXQuery("kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec", attribute="OneMinuteRate"),
            ]
            res = conn.query(queries)
            flat = {f"{r.getMBeanName()}/{r.getAttribute() or 'Value'}": r.getValue() for r in res}
            return {
                "activeControllerCount": int(flat.get("kafka.controller:type=KafkaController,name=ActiveControllerCount/Value", 0)),
                "underReplicatedPartitions": int(flat.get("kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions/Value", 0)),
                "throughput": {
                    "bytesInPerSec": float(flat.get("kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec/OneMinuteRate", 0.0)),
                    "bytesOutPerSec": float(flat.get("kafka.server:type=BrokerTopicMetrics,name=BytesOutPerSec/OneMinuteRate", 0.0)),
                    "messagesInPerSec": float(flat.get("kafka.server:type=BrokerTopicMetrics,name=MessagesInPerSec/OneMinuteRate", 0.0)),
                },
            }
        except Exception:
            return {
                "activeControllerCount": 0,
                "underReplicatedPartitions": 0,
                "throughput": {"bytesInPerSec": 0.0, "bytesOutPerSec": 0.0, "messagesInPerSec": 0.0},
            }