# app/api/consusmer_group.py
from __future__ import annotations

import datetime as dt
from typing import List, Optional, Union

from fastapi import APIRouter, HTTPException, Query

from app.services.kafka_service import KafkaService
from app.models.consumers import GroupLagResponse, GroupLagPartition

router = APIRouter(prefix="/consumer-groups", tags=["consumer-groups"])
svc = KafkaService()


# ---------- helpers ----------

def _parse_iso8601(ts: str) -> dt.datetime:
    """
    Accepts ISO 8601 with 'Z' or offset, e.g. '2025-08-15T09:30:00Z' or '+00:00'.
    Raises ValueError on bad input.
    """
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _parse_partitions_q(arg: Optional[Union[List[int], str]]) -> Optional[List[int]]:
    """
    Frontend sends partitions either as a CSV string (e.g. "0,1,2")
    or leaves it undefined. Support both CSV and repeated query params.
    """
    if arg is None:
        return None
    if isinstance(arg, list):
        # Already parsed by FastAPI (when sent as repeated query keys)
        return [int(x) for x in arg]
    # CSV in a single query param
    s = str(arg).strip()
    if not s:
        return None
    return [int(p.strip()) for p in s.split(",") if p.strip() != ""]


# ---------- endpoints ----------

@router.get("", response_model=list[str])
def list_consumer_groups(
    q: Optional[str] = Query(
        default=None,
        description="Substring filter applied to group IDs (case-insensitive).",
    ),
    limit: int = Query(500, ge=1, le=5000, description="Max number of IDs to return."),
):
    """
    Returns a (filtered) list of consumer group IDs.
    Matches the UI's /consumer-groups request used to populate the dropdown.
    """
    try:
        # Kafka-python returns list[tuple[group_id, protocol]]
        pairs = svc.list_consumer_groups()
        ids = sorted({gid for gid, _ in pairs})
        if q:
            ql = q.lower()
            ids = [gid for gid in ids if ql in gid.lower()]
        return ids[:limit]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{group_id}/lag", response_model=GroupLagResponse)
def group_lag(
    group_id: str,
    topic: str = Query(..., description="Topic to compute lag for."),
):
    """
    Returns per-partition lag and timestamps for the given group/topic.
    Shape matches GroupLagResponse used by the UI.
    """
    try:
        parts = svc.group_offsets(group_id, topic)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return GroupLagResponse(
        groupId=group_id,
        topic=topic,
        partitions=[GroupLagPartition(**p) for p in parts],
    )


@router.post("/{group_id}:reset-by-timestamp")
def reset_by_timestamp(
    group_id: str,
    topic: str = Query(..., description="Topic to reset offsets for."),
    timestamp: str = Query(..., description="ISO8601 timestamp (e.g. 2025-08-15T09:30:00Z)."),
    partitions: Optional[Union[List[int], str]] = Query(
        None,
        description="Target partition list. Accepts repeated ?partitions=0&partitions=1 or CSV '0,1'. Empty/omitted = all.",
    ),
    dry_run: bool = Query(
        True,
        description="If true, only preview targets. If false, commit the new offsets.",
    ),
):
    """
    Preview or apply an offset reset to the position at (or after) the given timestamp.
    Accepts query-string params to match the current frontend client.
    """
    # Parse inputs
    try:
        ts = _parse_iso8601(timestamp)
    except Exception:
        raise HTTPException(status_code=400, detail="timestamp must be ISO8601")

    try:
        parts_list = _parse_partitions_q(partitions)
        result = svc.reset_offsets_by_timestamp(
            group_id=group_id,
            topic=topic,
            ts=ts,
            partitions=parts_list,
            dry_run=dry_run,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
