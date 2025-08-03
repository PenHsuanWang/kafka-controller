"""Consumer-group DTOs and helper payloads."""
from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class PartitionLag(BaseModel):
    """Lag information for one partition."""

    partition: int
    lag: int = Field(..., ge=0)
    end_offset_ts: datetime | None = None
    commit_ts: datetime | None = None


class ConsumerGroup(BaseModel):
    """Aggregate view of a consumer group plus partition-level detail."""

    group_id: str = Field(..., alias="id")
    state: str  # Stable / Rebalancing / Dead …
    member_count: int = Field(..., ge=0)
    total_lag: int = Field(..., ge=0)
    max_offset_timestamp: datetime | None = None
    partitions: List[PartitionLag] | None = None


class OffsetResetRequest(BaseModel):
    """Body model for `POST …/offsets:reset` (spec §4.1)."""

    to_offset: int | None = None
    to_timestamp: datetime | None = None
    strategy: str | None = Field(
        default=None,
        pattern=r"^(earliest|latest)$",
        description="Shortcut strategies supported by Kafka",
    )

    @field_validator("strategy")
    @staticmethod
    def ensure_one_of(cls, v, info):  # noqa: D401
        """Require *either* strategy or explicit target."""
        if v is None and not (info.data.get("to_offset") or info.data.get("to_timestamp")):
            raise ValueError("Specify strategy or to_offset/to_timestamp")
        return v