from __future__ import annotations
import datetime as dt
from fastapi import APIRouter, HTTPException, Query
from app.services.kafka_service import KafkaService
from app.models.consumers import GroupLagResponse, GroupLagPartition

router = APIRouter(prefix="/consumer-groups", tags=["consumer-groups"])
svc = KafkaService()


@router.get("/{group_id}/lag", response_model=GroupLagResponse)
def group_lag(group_id: str, topic: str = Query(..., description="Topic to compute lag for")):
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
    topic: str,
    timestamp: str,
    partitions: list[int] | None = Query(None),
    dry_run: bool = True,
):
    try:
        ts = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=400, detail="timestamp must be ISO8601")

    try:
        result = svc.reset_offsets_by_timestamp(group_id, topic, ts, partitions=partitions, dry_run=dry_run)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
