# app/api/monitoring.py
from __future__ import annotations

from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request

# ---- Router -----------------------------------------------------------------

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


# ---- Simple in-memory store (ring buffer per (group, topic)) ----------------

@dataclass
class Snap:
    ts: float                    # unix seconds
    produced_total: int          # sum of end offsets across partitions
    partitions: int
    totalLag: int
    maxLag: int
    maxLagPartition: Optional[int]

    def to_public(self) -> Dict:
        d = asdict(self)
        d["generated"] = datetime.fromtimestamp(self.ts, tz=timezone.utc).isoformat()
        # Keep front-end keys stable
        d["partitions"] = self.partitions
        return d


class MonitorStore:
    """Ring-buffer store of snapshots keyed by (group, topic)."""

    def __init__(self, capacity_per_key: int = 600) -> None:
        self.capacity = capacity_per_key
        self._buf: Dict[Tuple[str, str], Deque[Snap]] = defaultdict(lambda: deque(maxlen=self.capacity))

    @staticmethod
    def _key(group_id: str, topic: str) -> Tuple[str, str]:
        return (group_id, topic)

    def push(self, group_id: str, topic: str, snap: Snap) -> None:
        self._buf[self._key(group_id, topic)].append(snap)

    def last_two(self, group_id: str, topic: str, window_sec: int = 120) -> Tuple[Optional[Snap], Optional[Snap]]:
        buf = self._buf.get(self._key(group_id, topic))
        if not buf or len(buf) == 0:
            return None, None
        curr = buf[-1]
        # walk backwards to find the first point older than (curr.ts - window_sec)
        prev = None
        cutoff = curr.ts - float(window_sec)
        for s in reversed(buf):
            if s.ts <= cutoff:
                prev = s
                break
        # if none old enough, fall back to the earliest point we have (if different than curr)
        if prev is None and len(buf) >= 2:
            prev = buf[-2]
        return prev, curr

    def history_rates(self, group_id: str, topic: str, bins: int = 60) -> List[float]:
        """
        Return 'bins' points representing per-second production rate
        over the last ~bins seconds, derived from produced_total deltas.
        """
        buf = self._buf.get(self._key(group_id, topic))
        if not buf or len(buf) < 2:
            return [0.0] * bins

        # Build (second -> rate) map from adjacent pairs
        pairs = list(buf)
        rates: Dict[int, float] = {}
        for a, b in zip(pairs, pairs[1:]):
            dt = max(1e-6, b.ts - a.ts)
            rate = float(b.produced_total - a.produced_total) / dt
            rates[int(b.ts)] = rate

        # Fill last N seconds
        end_sec = int(pairs[-1].ts)
        start_sec = end_sec - bins + 1
        out: List[float] = []
        for s in range(start_sec, end_sec + 1):
            out.append(rates.get(s, 0.0))
        return out


# ---- Dependency --------------------------------------------------------------

def get_store(req: Request) -> MonitorStore:
    store = getattr(req.app.state, "monitor_store", None)
    if store is None:
        # Should never happen if server.py is set up correctly
        req.app.state.monitor_store = MonitorStore()
        store = req.app.state.monitor_store
    return store


# ---- Kafka probe (no JMX) ----------------------------------------------------

def compute_group_snapshot(bootstrap: str, group_id: str, topic: str) -> Snap:
    """
    Ask Kafka for:
      - end offsets per partition (producer side)
      - committed group offsets per partition
    Then compute total lag, max lag, etc.
    """
    try:
        # Lazy imports so the module is optional at boot
        from kafka import KafkaAdminClient, KafkaConsumer, TopicPartition  # type: ignore
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"kafka-python not installed: {e}")

    # Consumer just for end_offsets
    try:
        consumer = KafkaConsumer(
            bootstrap_servers=bootstrap,
            client_id="monitoring-probe",
            enable_auto_commit=False,
            request_timeout_ms=15000,
            api_version_auto_timeout_ms=5000,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot connect to Kafka at {bootstrap}: {e}")

    try:
        parts = consumer.partitions_for_topic(topic)
        if not parts:
            raise HTTPException(status_code=404, detail=f"Topic '{topic}' not found or has no partitions")

        tps = [TopicPartition(topic, p) for p in sorted(parts)]
        end_offsets = consumer.end_offsets(tps)  # {TP: offset}
        produced_total = int(sum(end_offsets.values()))

        # Group committed offsets
        admin = KafkaAdminClient(bootstrap_servers=bootstrap, client_id="monitoring-probe-admin")
        gr = admin.list_consumer_group_offsets(group_id)
        total_lag = 0
        max_lag = 0
        max_lag_partition: Optional[int] = None

        for tp in tps:
            end = int(end_offsets.get(tp, 0))
            meta = gr.get(tp)
            committed = int(getattr(meta, "offset", -1) or -1)
            # If no commit yet, treat as -1 -> lag = end - (-1) - 1 = end
            if committed < 0:
                lag = end
            else:
                lag = max(0, end - committed)
            total_lag += lag
            if lag >= max_lag:
                max_lag = lag
                max_lag_partition = tp.partition

        snap = Snap(
            ts=datetime.now(tz=timezone.utc).timestamp(),
            produced_total=produced_total,
            partitions=len(tps),
            totalLag=total_lag,
            maxLag=max_lag,
            maxLagPartition=max_lag_partition,
        )
        return snap
    finally:
        with contextlib.suppress(Exception):
            consumer.close()


# ---- Routes ------------------------------------------------------------------

@router.get("/groups/{groupId}/snapshot")
def take_snapshot(groupId: str, topic: str, request: Request, store: MonitorStore = Depends(get_store)):
    """
    Trigger a fresh snapshot (used by the optional background poller),
    push it into the in-memory store, and return the public shape.
    """
    import os

    bootstrap = (
        getattr(request.app.state, "kafka_bootstrap", None)
        or os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        or "localhost:9092"
    )

    snap = compute_group_snapshot(bootstrap, groupId, topic)
    store.push(groupId, topic, snap)
    return {"groupId": groupId, "topic": topic, "snapshot": snap.to_public()}


@router.get("/latest")
def latest(groupId: str, topic: str, store: MonitorStore = Depends(get_store)):
    prev, curr = store.last_two(groupId, topic, window_sec=120)
    if curr is None:
        # Nothing captured yet
        return {"groupId": groupId, "topic": topic, "snapshot": None}
    return {"groupId": groupId, "topic": topic, "snapshot": curr.to_public()}


@router.get("/history")
def history(groupId: str, topic: str, bins: int = 60, store: MonitorStore = Depends(get_store)):
    # Sparkline-like series and simple stats derived from it
    points = store.history_rates(groupId, topic, bins=bins)
    now = points[-1] if points else 0.0
    # robust p95 on non-negative series
    if points:
        idx = max(0, int(round(0.95 * (len(points) - 1))))
        p95 = sorted(points)[idx]
    else:
        p95 = 0.0
    return {"groupId": groupId, "topic": topic, "bins": bins, "points": points, "stats": {"now": now, "p95": p95}}
