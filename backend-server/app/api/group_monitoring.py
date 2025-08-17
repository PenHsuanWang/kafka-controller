# app/api/group_monitoring.py
from __future__ import annotations
import datetime as dt
from typing import Optional

import httpx
from fastapi import APIRouter, Request, Query

from app.core.config import settings
from app.services.store import Store
from app.models.monitoring import (
    GroupSnapshot, GroupPartitionSnapshot, GroupSnapshotSummary, GroupRates
)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


def _iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _seconds_between(a_iso: Optional[str], b_iso: Optional[str]) -> Optional[int]:
    if not a_iso or not b_iso:
        return None
    try:
        a = dt.datetime.fromisoformat(a_iso.replace("Z", "+00:00"))
        b = dt.datetime.fromisoformat(b_iso.replace("Z", "+00:00"))
        return int((a - b).total_seconds())
    except Exception:
        return None


async def _fetch_group_lag_via_http(group_id: str, topic: str) -> dict:
    """
    Calls your existing endpoint: /api/v1/consumer-groups/{groupId}/lag?topic=...
    """
    base = (settings.monitor_api_base or "http://127.0.0.1:8000/api/v1").rstrip("/")
    url = f"{base}/consumer-groups/{group_id}/lag"
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url, params={"topic": topic})
        r.raise_for_status()
        return r.json()


@router.get("/groups/{group_id}/snapshot", response_model=GroupSnapshot)
async def get_snapshot(request: Request, group_id: str, topic: str = Query(...)):
    # 1) pull the same data your UI uses today
    raw = await _fetch_group_lag_via_http(group_id, topic)
    parts_raw = raw.get("partitions") or []

    # 2) normalize & enrich with time-lag
    parts: list[GroupPartitionSnapshot] = []
    for p in parts_raw:
        end_ts = p.get("endOffsetTimestamp") or p.get("endTs") or p.get("headTimestamp")
        last_ts = p.get("lastRecordTimestamp")
        parts.append(GroupPartitionSnapshot(
            topic=topic,
            partition=p["partition"],
            committedOffset=p.get("committedOffset"),
            endOffset=p.get("endOffset", 0),
            lag=p.get("lag"),
            endOffsetTimestamp=end_ts,
            lastRecordTimestamp=last_ts,
            timeLagSec=_seconds_between(end_ts, last_ts)
        ))

    # 3) compute summary
    total_lag = sum(int(pp.lag or 0) for pp in parts)
    max_part = max(parts, key=lambda x: (x.lag or -1), default=None)
    tl = sorted([pp.timeLagSec for pp in parts if pp.timeLagSec is not None])
    p95 = tl[int(0.95 * (len(tl) - 1))] if tl else None

    summary = GroupSnapshotSummary(
        totalLag=total_lag,
        maxLag=max_part.lag if max_part and max_part.lag is not None else 0,
        maxLagTopic=topic if max_part else None,
        maxLagPartition=max_part.partition if max_part else None,
        timeLagP95Sec=p95,
        partitions=len(parts),
    )

    snap = GroupSnapshot(
        groupId=group_id,
        topic=topic,
        generatedAt=_iso_now(),
        partitions=parts,
        summary=summary,
    )

    # 4) store for rate calculations
    store: Store = request.app.state.monitor_store  # created in lifespan
    store.put_snapshot(group_id, topic, snap)
    return snap


@router.get("/groups/{group_id}/rates", response_model=GroupRates)
async def get_rates(
    request: Request,
    group_id: str,
    topic: str = Query(...),
    windowSec: float = Query(60.0, ge=1, le=600),
):
    store: Store = request.app.state.monitor_store
    prev, curr = store.get_two_snapshots(group_id, topic, windowSec)
    rates = GroupRates(groupId=group_id, topic=topic, windowSec=windowSec)

    if not prev or not curr:
        return rates

    # aggregate deltas across partitions
    by_prev = {(p.topic, p.partition): p for p in prev.partitions}
    by_curr = {(p.topic, p.partition): p for p in curr.partitions}

    consume_delta = produce_delta = 0
    for k, now in by_curr.items():
        before = by_prev.get(k)
        if not before:
            continue
        if isinstance(now.committedOffset, int) and isinstance(before.committedOffset, int):
            if now.committedOffset >= before.committedOffset:
                consume_delta += (now.committedOffset - before.committedOffset)
        if isinstance(now.endOffset, int) and isinstance(before.endOffset, int):
            if now.endOffset >= before.endOffset:
                produce_delta += (now.endOffset - before.endOffset)

    rates.consumeRate = (consume_delta / windowSec) if windowSec > 0 else None
    rates.produceRate = (produce_delta / windowSec) if windowSec > 0 else None
    return rates
