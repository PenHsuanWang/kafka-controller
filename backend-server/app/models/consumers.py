from pydantic import BaseModel
from typing import List, Optional


class ConsumerGroupRow(BaseModel):
    groupId: str
    members: int
    state: str
    totalLag: Optional[int] = None
    latestCommitWallClock: Optional[str] = None


class GroupLagPartition(BaseModel):
    partition: int
    committedOffset: int | None
    endOffset: int
    lag: int | None
    endOffsetTimestamp: Optional[str] = None
    commitTimestamp: Optional[str] = None
    eventTimeDriftSec: Optional[int] = None


class GroupLagResponse(BaseModel):
    groupId: str
    topic: str
    partitions: List[GroupLagPartition]
