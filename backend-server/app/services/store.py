import time
import collections
from typing import Dict, Tuple, Deque, Optional, List
from app.models.monitoring import GroupSnapshot

class Store:
    """Bounded ring buffer of recent snapshots per (group, topic)."""
    def __init__(self, capacity_per_key: int = 60):
        self._cap = capacity_per_key
        self._data: Dict[Tuple[str, str], Deque[Tuple[float, GroupSnapshot]]] = collections.defaultdict(collections.deque)

    def put(self, snap: GroupSnapshot) -> None:
        key = (snap.groupId, snap.topic)
        dq = self._data[key]
        dq.append((time.time(), snap))
        while len(dq) > self._cap:
            dq.popleft()

    def latest(self, group: str, topic: str) -> Optional[GroupSnapshot]:
        dq = self._data.get((group, topic))
        return dq[-1][1] if dq else None

    def two_points(self, group: str, topic: str, window_sec: float) -> tuple[Optional[GroupSnapshot], Optional[GroupSnapshot]]:
        dq = self._data.get((group, topic))
        if not dq or len(dq) < 2:
            return None, None
        now = time.time()
        curr = dq[-1][1]
        prev = None
        # find the earliest sample at least `window_sec` in the past
        for ts, s in reversed(dq):
            if now - ts >= window_sec:
                prev = s
                break
        return prev, curr

    def items(self):
        return self._data.items()
