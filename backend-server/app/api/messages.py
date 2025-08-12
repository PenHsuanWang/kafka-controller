from __future__ import annotations
import datetime as dt
from fastapi import APIRouter, HTTPException
from app.services.kafka_service import KafkaService
from app.models.messages import MessageRecord

router = APIRouter(prefix="/messages", tags=["messages"])
svc = KafkaService()


@router.get("/by-offset", response_model=list[MessageRecord])
def by_offset(topic: str, partition: int, offset: int, limit: int = 50):
    try:
        out = svc.fetch_by_offset(topic, partition, offset, limit=limit)
        return [MessageRecord(**r) for r in out]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/from-timestamp", response_model=list[MessageRecord])
def from_ts(topic: str, partition: int, ts: str, limit: int = 50):
    try:
        dt_ts = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=400, detail="ts must be ISO8601")
    try:
        out = svc.fetch_from_timestamp(topic, partition, dt_ts, limit=limit)
        return [MessageRecord(**r) for r in out]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
