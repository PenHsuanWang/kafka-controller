from pydantic import BaseModel
from typing import List, Optional


class TopicSummary(BaseModel):
    name: str
    partitions: int
    replicationFactor: int
    # Optional sparkline data (backfilled from JMX)
    msgInSpark: Optional[list[float]] = None
    msgOutSpark: Optional[list[float]] = None


class PartitionInfo(BaseModel):
    id: int
    leader: int | None
    isr: list[int]
    startOffset: int | None
    endOffset: int | None


class TopicDetail(BaseModel):
    name: str
    replicationFactor: int
    partitions: List[PartitionInfo]
    configs: dict[str, str] | None = None
