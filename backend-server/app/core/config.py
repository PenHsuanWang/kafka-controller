"""Global application configuration loaded from environment variables.

This module uses *Pydantic Settings* (pydantic-settings>=2.0) which automatically
reads environment variables and optional `.env` files, providing strong typing,
validation, and JSON-Schema generation.  See FastAPI docs for details.  # noqa: E501
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime-configurable values for the backend."""

    # Kafka
    bootstrap_servers: List[str] = ["localhost:9092"]
    poll_interval: float = 1.0  # seconds between metric snapshots

    # Security / JWT
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Misc
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="KAFKA_ADMIN_",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return a **singleton** `Settings` instance (thread-safe)."""
    return Settings(_env_file=Path(__file__).parent.parent.parent / ".env")