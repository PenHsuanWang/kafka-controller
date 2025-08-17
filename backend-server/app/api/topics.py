# app/api/topics.py
from __future__ import annotations
import datetime as dt
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.kafka_service import KafkaService

router = APIRouter(prefix="/topics", tags=["topics"])
svc = KafkaService()


def _clean_q(q: Optional[str]) -> Optional[str]:
    """
    Make 'q' safe & optional:
      - None, empty string, or "[object Object]" -> None
      - If JSON-looking, try to pull a useful string field.
    """
    if not q:
        return None
    q = q.strip()
    if q == "" or q == "[object Object]":
        return None
    if q.startswith("{") or q.startswith("["):
        try:
            data = json.loads(q)
            if isinstance(data, dict):
                for key in ("q", "query", "value", "inputValue", "name", "label"):
                    v = data.get(key)
                    if isinstance(v, str) and v.strip():
                        return v.strip()
            # if it's a list or unhelpful dict, fall through
        except Exception:
            return None
    return q


@router.get("")
def list_topics(q: Optional[str] = Query(None, description="Optional filter substring")):
    """
    Returns a list of topics with minimal details:
      [{ name, partitions, replicationFactor }, ...]
    Backward compatible with the previous shape.
    """
    items = svc.list_topics()
    qq = _clean_q(q)
    if qq:
        qq_l = qq.lower()
        items = [t for t in items if qq_l in t["name"].lower()]
    return items


@router.get("/{topic}")
def topic_detail(topic: str):
    try:
        return svc.topic_detail(topic)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{topic}/messages")
def read_messages(
    topic: str,
    partition: int | None = Query(None, description="Partition number (optional)"),
    offset: int | None = Query(None, description="Absolute offset to seek from (optional)"),
    timestamp: str | None = Query(None, description="ISO8601 timestamp to seek from (optional)"),
    limit: int = Query(50, ge=1, le=500),
):
    try:
        ts_dt: dt.datetime | None = None
        if timestamp:
            ts_dt = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return svc.read_messages(topic=topic, partition=partition, offset=offset, timestamp=ts_dt, limit=limit)
    except ValueError:
        raise HTTPException(status_code=400, detail="timestamp must be ISO8601")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
