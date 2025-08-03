"""Cluster- and broker-level DTOs for REST & WebSocket payloads."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class Broker(BaseModel):
    """Snapshot of a single broker’s health and JMX metrics."""

    broker_id: int = Field(..., ge=0, description="Numeric broker ID")
    host: str
    port: int
    version: str | None = None

    # KPI-style metrics (latest poll)
    cpu_pct: float | None = Field(
        default=None, ge=0, le=100, description="CPU utilisation (%)"
    )
    disk_pct: float | None = Field(
        default=None, ge=0, le=100, description="Data dir utilisation (%)"
    )
    leader_partitions: int | None = None
    under_replicated_partitions: int | None = None


class Cluster(BaseModel):
    """Minimal metadata + health KPIs for a Kafka cluster."""

    cluster_id: str = Field(..., alias="id")
    name: str
    broker_count: int = Field(..., ge=1)
    version: str | None = None

    # High-level KPIs (spec §3.1)
    under_replicated: int | None = None
    lagging_groups: int | None = None
    in_sync_topics: int | None = None
    controller_elections24h: int | None = None

    brokers: List[Broker] | None = None