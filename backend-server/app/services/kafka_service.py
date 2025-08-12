from __future__ import annotations
import time
import datetime as dt
from typing import Dict, Iterable, List, Optional

from kafka import KafkaAdminClient, KafkaConsumer, TopicPartition
from kafka.errors import KafkaTimeoutError, NoBrokersAvailable, NodeNotReadyError
from app.core.config import settings

_RETRYABLE = (KafkaTimeoutError, NoBrokersAvailable, NodeNotReadyError)


class KafkaService:
    """
    Lazy, retrying adapter around kafka-python Admin + Consumer APIs.
    Avoids network work at import-time and survives transient broker unavailability.
    """

    def __init__(self, bootstrap: Optional[str] = None) -> None:
        self.bootstrap = bootstrap or settings.kafka_bootstrap
        self._admin: KafkaAdminClient | None = None

    # ---------- bootstrap common kwargs ----------
    def _common_kwargs(self) -> dict:
        kw = dict(
            bootstrap_servers=self.bootstrap,
            client_id="kafka-admin-api",
            request_timeout_ms=settings.request_timeout_ms,
            metadata_max_age_ms=settings.metadata_max_age_ms,
            api_version_auto_timeout_ms=settings.api_version_auto_timeout_ms,
            security_protocol=settings.security_protocol,
        )
        if settings.kafka_api_version:
            kw["api_version"] = settings.kafka_api_version
        if settings.security_protocol.startswith("SASL"):
            kw.update(
                sasl_mechanism=settings.sasl_mechanism,
                sasl_plain_username=settings.sasl_plain_username,
                sasl_plain_password=settings.sasl_plain_password,
            )
        if settings.security_protocol.endswith("SSL"):
            kw.update(ssl_cafile=settings.ssl_cafile)
        return kw

    def _ensure_admin(self) -> KafkaAdminClient:
        if self._admin is not None:
            return self._admin

        last_exc: Exception | None = None
        for attempt in range(1, settings.admin_connect_max_tries + 1):
            try:
                self._admin = KafkaAdminClient(**self._common_kwargs())
                return self._admin
            except _RETRYABLE as exc:
                last_exc = exc
                time.sleep(settings.admin_connect_backoff_sec * attempt)
        # give up
        raise last_exc or RuntimeError("Failed to create KafkaAdminClient")

    def _consumer(self, **kw) -> KafkaConsumer:
        return KafkaConsumer(**{**self._common_kwargs(), **kw})

    # ---------- Cluster / Brokers ----------
    def brokers_online(self) -> int:
        try:
            meta = self._ensure_admin().describe_cluster()
            return len(meta.get("brokers", []))
        except _RETRYABLE:
            # transient: report 0 instead of crashing dashboards
            return 0

    def describe_cluster(self) -> dict:
        return self._ensure_admin().describe_cluster()

    # ---------- Topics ----------
    def list_topics(self) -> list[dict]:
        """
        Returns minimal topic info (name, partitions, replicationFactor).
        """
        admin = self._ensure_admin()
        try:
            names = list(admin.list_topics())
        except AttributeError:
            # older kafka-python: fall back to describe all via metadata names
            names = [t["topic"] for t in admin.describe_topics([])]
        topics = admin.describe_topics(names)
        out = []
        for t in topics:
            rf = len(t["partitions"][0]["replicas"]) if t.get("partitions") else 0
            out.append(
                {"name": t["topic"], "partitions": len(t.get("partitions", [])), "replicationFactor": rf}
            )
        return out

    def topic_detail(self, topic: str) -> dict:
        admin = self._ensure_admin()
        d = admin.describe_topics([topic])[0]
        tp_list = [TopicPartition(topic, p["partition"]) for p in d.get("partitions", [])]
        start = self._beginning_offsets(tp_list)
        end = self._end_offsets(tp_list)

        partitions = []
        for p in d.get("partitions", []):
            pid = p["partition"]
            partitions.append(
                {
                    "id": pid,
                    "leader": p.get("leader"),
                    "isr": p.get("isr", []),
                    "startOffset": start.get(TopicPartition(topic, pid)),
                    "endOffset": end.get(TopicPartition(topic, pid)),
                }
            )
        rf = len(d["partitions"][0]["replicas"]) if d.get("partitions") else 0
        return {"name": topic, "replicationFactor": rf, "partitions": partitions, "configs": None}

    # ---------- Consumer Groups / Lag ----------
    def list_consumer_groups(self) -> list[tuple[str, str]]:
        return self._ensure_admin().list_consumer_groups()

    def describe_consumer_groups(self, ids: list[str]) -> list[dict]:
        return self._ensure_admin().describe_consumer_groups(ids)

    def group_offsets(self, group_id: str, topic: str) -> list[dict]:
        admin = self._ensure_admin()
        offsets = admin.list_consumer_group_offsets(group_id)
        tps = [TopicPartition(topic, p["partition"]) for p in admin.describe_topics([topic])[0]["partitions"]]
        end = self._end_offsets(tps)

        rows: list[dict] = []
        for tp in tps:
            committed_meta = offsets.get(tp)
            committed = committed_meta.offset if committed_meta is not None else None
            endoff = end[tp]
            lag = (endoff - committed) if (committed is not None and committed >= 0) else None
            end_ts = self._timestamp_of_offset(tp, endoff - 1) if endoff > 0 else None
            last_rec_ts = self._timestamp_of_offset(tp, (committed - 1)) if committed and committed > 0 else None
            rows.append(
                {
                    "partition": tp.partition,
                    "committedOffset": committed,
                    "endOffset": endoff,
                    "lag": lag,
                    "endOffsetTimestamp": _fmt_iso(end_ts) if end_ts else None,
                    "lastRecordTimestamp": _fmt_iso(last_rec_ts) if last_rec_ts else None,
                    "eventTimeDriftSec": _diff_sec(last_rec_ts, end_ts) if last_rec_ts and end_ts else None,
                }
            )
        return rows

    def reset_offsets_by_timestamp(
        self,
        group_id: str,
        topic: str,
        ts: dt.datetime,
        partitions: list[int] | None = None,
        dry_run: bool = True,
    ) -> dict:
        admin = self._ensure_admin()
        tps = [TopicPartition(topic, p["partition"]) for p in admin.describe_topics([topic])[0]["partitions"]]
        if partitions:
            tps = [tp for tp in tps if tp.partition in partitions]

        ts_ms = int(ts.timestamp() * 1000)
        target = self._offsets_for_times({tp: ts_ms for tp in tps})
        preview = {tp.partition: (target[tp] if target.get(tp) is not None else None) for tp in tps}
        if dry_run:
            return {"groupId": group_id, "topic": topic, "apply": False, "targets": preview}

        c = self._consumer(group_id=group_id, enable_auto_commit=False, consumer_timeout_ms=1000)
        try:
            c.assign(tps)
            c.poll(timeout_ms=0)  # ensure coordinator handshake before commit
            for tp in tps:
                off = target.get(tp)
                if off is not None:
                    c.seek(tp, off)
            c.commit()
            return {"groupId": group_id, "topic": topic, "apply": True, "targets": preview}
        finally:
            c.close()

    # ---------- Messages Explorer ----------
    def fetch_by_offset(self, topic: str, partition: int, offset: int, limit: int = 50) -> list[dict]:
        tp = TopicPartition(topic, partition)
        c = self._consumer(enable_auto_commit=False, consumer_timeout_ms=1000)
        try:
            c.assign([tp])
            c.seek(tp, offset)
            out = []
            while len(out) < limit:
                batch = c.poll(timeout_ms=500)
                if not batch:
                    break
                for _, records in batch.items():
                    for r in records:
                        out.append(
                            {"topic": r.topic, "partition": r.partition, "offset": r.offset,
                             "timestamp": r.timestamp, "key": r.key, "value": r.value}
                        )
                        if len(out) >= limit:
                            break
            return out
        finally:
            c.close()

    def fetch_from_timestamp(self, topic: str, partition: int, ts: dt.datetime, limit: int = 50) -> list[dict]:
        tp = TopicPartition(topic, partition)
        ts_ms = int(ts.timestamp() * 1000)
        c = self._consumer(enable_auto_commit=False, consumer_timeout_ms=1000)
        try:
            target = c.offsets_for_times({tp: ts_ms})
            off = target[tp].offset if target and target.get(tp) is not None else None
            if off is None:
                return []
            c.assign([tp])
            c.seek(tp, off)
            out = []
            while len(out) < limit:
                batch = c.poll(timeout_ms=500)
                if not batch:
                    break
                for _, records in batch.items():
                    for r in records:
                        out.append(
                            {"topic": r.topic, "partition": r.partition, "offset": r.offset,
                             "timestamp": r.timestamp, "key": r.key, "value": r.value}
                        )
                        if len(out) >= limit:
                            break
            return out
        finally:
            c.close()

    # ---------- Helpers ----------
    def _end_offsets(self, tps: Iterable[TopicPartition]) -> Dict[TopicPartition, int]:
        c = self._consumer()
        try:
            return c.end_offsets(list(tps))
        finally:
            c.close()

    def _beginning_offsets(self, tps: Iterable[TopicPartition]) -> Dict[TopicPartition, int]:
        c = self._consumer()
        try:
            return c.beginning_offsets(list(tps))
        finally:
            c.close()

    def _offsets_for_times(self, ts_map: Dict[TopicPartition, int]) -> Dict[TopicPartition, Optional[int]]:
        c = self._consumer()
        try:
            res = c.offsets_for_times(ts_map)
            return {tp: (res[tp].offset if res and res.get(tp) is not None else None) for tp in ts_map}
        finally:
            c.close()

    def _timestamp_of_offset(self, tp: TopicPartition, offset: int | None) -> Optional[int]:
        if offset is None or offset < 0:
            return None
        c = self._consumer(consumer_timeout_ms=1000, enable_auto_commit=False)
        try:
            c.assign([tp])
            c.seek(tp, offset)
            batch = c.poll(timeout_ms=1000)
            for _, records in batch.items():
                if records:
                    return records[-1].timestamp
            return None
        finally:
            c.close()


def _fmt_iso(ts_ms: Optional[int]) -> Optional[str]:
    if ts_ms is None:
        return None
    return dt.datetime.utcfromtimestamp(ts_ms / 1000.0).replace(tzinfo=dt.timezone.utc).isoformat()

def _diff_sec(a_ms: int | None, b_ms: int | None) -> Optional[int]:
    if a_ms is None or b_ms is None:
        return None
    return int((b_ms - a_ms) / 1000)