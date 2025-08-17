# app/services/store.py
import time
import threading
import collections
from typing import Dict, Tuple, Deque, Optional, Iterable

from app.models.monitoring import GroupSnapshot


class Store:
    """
    In-memory ring buffer of snapshots keyed by (group, topic).
    Thread-safe for simple get/put operations.

    Compatibility:
    - Existing callers can keep using:
        put_snapshot(...), get_two_snapshots(...), iter_latest()
    - New monitoring code can use:
        put(GroupSnapshot), two_points(...)
    """

    def __init__(self, capacity_per_key: int = 120):
        self._cap = int(capacity_per_key)
        self._data: Dict[Tuple[str, str], Deque[Tuple[float, GroupSnapshot]]] = (
            collections.defaultdict(collections.deque)
        )
        self._lock = threading.RLock()

    # -------- New-friendly API (used by updated group_monitoring.py) --------

    def put(self, snap: GroupSnapshot) -> None:
        """
        Append a snapshot for its (groupId, topic). Requires both fields present.
        """
        group_id = getattr(snap, "groupId", None)
        topic = getattr(snap, "topic", None)
        if not group_id or not topic:
            raise ValueError("GroupSnapshot must include groupId and topic")
        self.put_snapshot(group_id, topic, snap)

    def two_points(
        self, group_id: str, topic: str, window_sec: float
    ) -> tuple[Optional[GroupSnapshot], Optional[GroupSnapshot]]:
        """
        Return (prev, curr) snapshots for (group, topic) where prev is at least
        `window_sec` older than curr when possible; otherwise falls back to the
        immediately previous snapshot.

        This uses the timestamp stored alongside the snapshots (when they were
        inserted into the store) rather than time.time() at read time.
        """
        with self._lock:
            dq = self._data.get((group_id, topic))
            if not dq or len(dq) < 2:
                return None, None

            curr_ts, curr_snap = dq[-1]
            prev_snap: Optional[GroupSnapshot] = None

            # Walk newest -> oldest to find a point at least window_sec older than *curr*.
            for ts, snap in reversed(dq):
                if (curr_ts - ts) >= float(window_sec):
                    prev_snap = snap
                    break

            # If we couldn't find one far enough back, use the immediate previous.
            if prev_snap is None and len(dq) >= 2:
                prev_snap = dq[-2][1]

            return prev_snap, curr_snap

    # -------- Back-compat API (kept for existing callers) --------

    def put_snapshot(self, group_id: str, topic: str, snap: GroupSnapshot) -> None:
        with self._lock:
            key = (group_id, topic)
            dq = self._data[key]
            dq.append((time.time(), snap))
            while len(dq) > self._cap:
                dq.popleft()

    def get_two_snapshots(self, group_id: str, topic: str, window_sec: float):
        # Alias to the improved selection logic
        return self.two_points(group_id, topic, window_sec)

    def iter_latest(self) -> Iterable[Tuple[Tuple[str, str], GroupSnapshot]]:
        with self._lock:
            for k, dq in self._data.items():
                if dq:
                    yield k, dq[-1][1]
