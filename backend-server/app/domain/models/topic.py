"""Topic metadata model used by REST and WebSocket routes."""
from __future__ import annotations

from datetime import datetime
from typing import Dict

from pydantic import BaseModel, Field, field_validator

class Topic(BaseModel):
    """Immutable view of a Kafka topic’s configuration & KPIs."""

    name: str = Field(
        ...,
        pattern=r"^[\w\-.]+$",
        examples=["checkout-orders"],
        description="Kafka topic name",
    )
    partitions: int = Field(..., ge=1)
    replication_factor: int = Field(..., ge=1)
    configs: Dict[str, str] = Field(default_factory=dict)

    # KPIs populated by metric collector
    msg_in_per_sec: float | None = None
    msg_out_per_sec: float | None = None
    total_size_bytes: int | None = None
    last_write_time: datetime | None = None

    @field_validator("configs")
    @staticmethod
    def lowercase_keys(v: Dict[str, str]) -> Dict[str, str]:
        """Ensure config keys are case-insensitive."""
        return {k.lower(): val for k, val in v.items()}