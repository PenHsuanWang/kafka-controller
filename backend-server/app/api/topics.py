from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.services.kafka_service import KafkaService
from app.models.topics import TopicSummary, TopicDetail, PartitionInfo

router = APIRouter(prefix="/topics", tags=["topics"])
svc = KafkaService()


@router.get("", response_model=list[TopicSummary])
def list_topics():
    rows = svc.list_topics()
    return [TopicSummary(**row) for row in rows]


@router.get("/{topic}", response_model=TopicDetail)
def describe_topic(topic: str):
    try:
        d = svc.topic_detail(topic)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    parts = [PartitionInfo(**p) for p in d["partitions"]]
    return TopicDetail(name=d["name"], replicationFactor=d["replicationFactor"], partitions=parts, configs=d["configs"])
