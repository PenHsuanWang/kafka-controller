# app/services/group_monitor.py
from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from kafka import TopicPartition

from app.services.kafka_service import KafkaService
from app.services.store import Store
from app.models.monitoring import (
    GroupSnapshot, GroupPartitionSnapshot, GroupSnapshotSummary, GroupRates
)


class GroupMonitor:
    """
    Builds snapshots of a consumer group's position vs log end, and computes
    produce/consume rates from stored snapshots.
    """
    def __init__(self, svc: KafkaService, store: Store, max_workers: int = 8):
        self._svc = svc
        self._store = store
        self._max_workers = max_workers

    # ------- public API -------

    def snapshot_one(self, group_id: str, topic: str) -> GroupSnapshot:
        admin = self._svc._ensure_admin()  # uses existing project KafkaService
        offsets = admin.list_consumer_group_offsets(group_id)

        parts_meta = admin.describe_topics([topic])[0].get("partitions", [])
        tps = [TopicPartition(topic, p["partition"]) for p in parts_meta]
        if not tps:
            snap = GroupSnapshot(
                groupId=group_id,
                generatedAt=_now_iso(),
                partitions=[],
                summary=GroupSnapshotSummary(
                    totalLag=0, maxLag=0, maxLagTopic=None, maxLagPartition=None,
                    timeLagP95Sec=None, partitions=0
                ),
            )
            self._store.put_snapshot(group_id, topic, snap)
            return snap

        end = self._svc._end_offsets(tps)

        def _one(tp: TopicPartition) -> GroupPartitionSnapshot:
            # committed offset
            meta = offsets.get(tp)
            committed = meta.offset if meta is not None else None
            endoff = int(end.get(tp, 0) or 0)

            lag = None
            if committed is not None and committed >= 0:
                lag = max(0, endoff - committed)

            head_ts_ms: Optional[int] = None
            last_ts_ms: Optional[int] = None
            if endoff > 0:
                head_ts_ms = self._svc._timestamp_of_offset(tp, endoff - 1)
            if isinstance(committed, int) and committed > 0:
                last_ts_ms = self._svc._timestamp_of_offset(tp, committed - 1)

            drift = None
            if head_ts_ms is not None and last_ts_ms is not None:
                drift = int((head_ts_ms - last_ts_ms) / 1000)

            return GroupPartitionSnapshot(
                topic=tp.topic,
                partition=tp.partition,
                committedOffset=committed,
                endOffset=endoff,
                lag=lag,
                endOffsetTimestamp=_fmt_iso(head_ts_ms) if head_ts_ms else None,
                lastRecordTimestamp=_fmt_iso(last_ts_ms) if last_ts_ms else None,
                timeLagSec=drift,
            )

        parts: List[GroupPartitionSnapshot] = []
        with ThreadPoolExecutor(max_workers=self._max_workers) as ex:
            futures = [ex.submit(_one, tp) for tp in tps]
            for f in as_completed(futures):
                parts.append(f.result())

        total_lag = sum(p.lag or 0 for p in parts)
        maxp = max(parts, key=lambda p: (p.lag or -1), default=None)
        tl = sorted([p.timeLagSec for p in parts if p.timeLagSec is not None])
        p95 = tl[int(0.95 * (len(tl) - 1))] if tl else None

        snap = GroupSnapshot(
            groupId=group_id,
            generatedAt=_now_iso(),
            partitions=sorted(parts, key=lambda p: p.partition),
            summary=GroupSnapshotSummary(
                totalLag=total_lag,
                maxLag=(maxp.lag if maxp and maxp.lag is not None else 0),
                maxLagTopic=(maxp.topic if maxp else None),
                maxLagPartition=(maxp.partition if maxp else None),
                timeLagP95Sec=p95,
                partitions=len(parts),
            ),
        )
        self._store.put_snapshot(group_id, topic, snap)
        return snap

    def rates(self, group_id: str, topic: str, window_sec: float) -> GroupRates:
        prev, curr = self._store.get_two_snapshots(group_id, topic, window_sec)
        if not prev or not curr:
            return GroupRates(groupId=group_id, windowSec=window_sec, consumeRate=None, produceRate=None)

        by_prev = {(p.topic, p.partition): p for p in prev.partitions}
        by_curr = {(p.topic, p.partition): p for p in curr.partitions}

        consume_delta = 0
        produce_delta = 0

        for k, now in by_curr.items():
            before = by_prev.get(k)
            if not before:
                continue
            if (
                isinstance(before.committedOffset, int) and isinstance(now.committedOffset, int)
                and now.committedOffset >= before.committedOffset
            ):
                consume_delta += (now.committedOffset - before.committedOffset)
            if (
                isinstance(before.endOffset, int) and isinstance(now.endOffset, int)
                and now.endOffset >= before.endOffset
            ):
                produce_delta += (now.endOffset - before.endOffset)

        return GroupRates(
            groupId=group_id,
            windowSec=window_sec,
            consumeRate=(consume_delta / window_sec) if window_sec > 0 else None,
            produceRate=(produce_delta / window_sec) if window_sec > 0 else None,
        )


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _fmt_iso(ts_ms: int | None) -> str | None:
    if ts_ms is None:
        return None
    return dt.datetime.utcfromtimestamp(ts_ms / 1000.0).replace(tzinfo=dt.timezone.utc).isoformat()
