from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field

class GroupPartitionSnapshot(BaseModel):
    topic: str
    partition: int
    committedOffset: Optional[int] = None
    endOffset: int
    lag: Optional[int] = None
    endOffsetTimestamp: Optional[str] = None  # ISO
    lastRecordTimestamp: Optional[str] = None # ISO
    timeLagSec: Optional[int] = None          # derived: end - last

class GroupSnapshotSummary(BaseModel):
    totalLag: int = 0
    maxLag: int = 0
    maxLagTopic: Optional[str] = None
    maxLagPartition: Optional[int] = None
    timeLagP95Sec: Optional[int] = None
    partitions: int = 0

class GroupSnapshot(BaseModel):
    groupId: str
    topic: str
    generatedAt: str
    partitions: List[GroupPartitionSnapshot] = Field(default_factory=list)
    summary: GroupSnapshotSummary

class GroupRates(BaseModel):
    groupId: str
    topic: str
    windowSec: float
    consumeRate: Optional[float] = None  # msgs/sec (committed delta / sec)
    produceRate: Optional[float] = None  # msgs/sec (end-offset delta / sec)
