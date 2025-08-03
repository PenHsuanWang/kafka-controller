"""Typed payloads for WebSocket push frames (spec §5)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal  # ← import Literal

from pydantic import BaseModel, Field


class ClusterMetrics(BaseModel):
    """`clusterMetrics` push every second."""

    event: Literal["clusterMetrics"] = "clusterMetrics"
    broker_online: int
    under_replicated: int
    lagging_groups: int
    in_sync_topics: int
    ts: datetime


class TopicThroughput(BaseModel):
    """`topicThroughput` push."""

    event: Literal["topicThroughput"] = "topicThroughput"
    topic: str
    in_mb_per_s: float
    out_mb_per_s: float
    ts: datetime


class ConsumerLagPush(BaseModel):
    """`consumerLag` push frame."""

    event: Literal["consumerLag"] = "consumerLag"
    group_id: str
    total_lag: int
    offsets: List[dict]
    ts: datetime