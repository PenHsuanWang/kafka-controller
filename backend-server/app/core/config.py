# app/core/config.py
import json
from typing import Dict, List

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    Central application settings loaded from environment variables (and .env).

    Notes
    -----
    - All monitoring controls are feature-flagged and default OFF.
    - `monitor_topics` supports either JSON (recommended) or a compact string form:
        MONITOR_TOPICS='{"orders-cg":["orders.v1","payments.v1"]}'
      or:
        MONITOR_TOPICS='orders-cg:orders.v1,payments.v1; other-cg:topicA'
    - `cors_allow_origins` accepts JSON array or comma-separated string.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- Kafka client/admin ----------
    kafka_bootstrap: str = Field("localhost:9092")
    kafka_api_version: str | None = None

    # Client timeouts (ms)
    request_timeout_ms: int = 20_000
    metadata_max_age_ms: int = 30_000
    api_version_auto_timeout_ms: int = 10_000

    # Admin connection retry
    admin_connect_max_tries: int = 8
    admin_connect_backoff_sec: float = 1.5

    # ---------- Security (set when using SASL/SSL) ----------
    security_protocol: str = "PLAINTEXT"   # e.g. "SASL_SSL", "SSL"
    sasl_mechanism: str | None = None
    sasl_plain_username: str | None = None
    sasl_plain_password: str | None = None
    ssl_cafile: str | None = None

    # ---------- JMX ----------
    jmx_host: str = "localhost"
    jmx_port: int = 9999

    # ---------- WebSocket ----------
    ws_cluster_tick: float = 2.0

    # ---------- CORS ----------
    cors_allow_origins: list[str] | None = None

    @field_validator("cors_allow_origins", mode="before")
    def _parse_cors_origins(cls, v):
        """Accept JSON array or comma-separated string."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                parsed = json.loads(v)  # JSON array
                if isinstance(parsed, list):
                    return [str(s).strip() for s in parsed if str(s).strip()]
            except Exception:
                return [s.strip() for s in v.split(",") if s.strip()]
        return v

    # ---------- Monitoring (feature-flagged; default OFF) ----------
    monitor_enabled: bool = Field(
        default=False,
        description="Enable background snapshot loop."
    )
    monitor_rest_enabled: bool = Field(
        default=False,
        description="Expose /api/v1/monitoring/* REST endpoints."
    )

    monitor_interval_sec: int = Field(
        default=15, ge=1,
        description="Polling interval for background monitor."
    )
    monitor_max_workers: int = Field(
        default=8, ge=1, le=64,
        description="Reserved for future use (timestamp lookups)."
    )

    # Which groups/topics to monitor
    monitor_groups: List[str] = Field(default_factory=list)
    monitor_topics: Dict[str, List[str]] = Field(default_factory=dict)

    # Base URL used by the internal monitor loop when it polls our own REST.
    # If None, defaults to http://127.0.0.1:8000/api/v1 inside server.py
    monitor_api_base: str | None = Field(default=None)

    @field_validator("monitor_groups", mode="before")
    def _parse_monitor_groups(cls, v):
        """Accept JSON array or comma-separated string."""
        if v is None:
            return []
        if isinstance(v, list):
            return [str(s).strip() for s in v if str(s).strip()]
        if isinstance(v, str):
            try:
                arr = json.loads(v)
                if isinstance(arr, list):
                    return [str(s).strip() for s in arr if str(s).strip()]
            except Exception:
                return [s.strip() for s in v.split(",") if s.strip()]
        return list(v)

    @field_validator("monitor_topics", mode="before")
    def _parse_monitor_topics(cls, v):
        """
        Accept JSON mapping or a compact string format:
          'group1:topicA,topicB; group2:topicX'
        """
        if v is None:
            return {}
        if isinstance(v, dict):
            return {str(g): [str(t).strip() for t in topics if str(t).strip()]
                    for g, topics in v.items()}
        if isinstance(v, str):
            # Try JSON mapping first
            try:
                obj = json.loads(v)
                if isinstance(obj, dict):
                    return {str(g): [str(t).strip() for t in topics if str(t).strip()]
                            for g, topics in obj.items()}
            except Exception:
                pass
            # Fallback compact form
            result: Dict[str, List[str]] = {}
            for part in v.split(";"):
                part = part.strip()
                if not part or ":" not in part:
                    continue
                group, topics_s = part.split(":", 1)
                topics = [s.strip() for s in topics_s.split(",") if s.strip()]
                if topics:
                    result[group.strip()] = topics
            return result
        try:
            return dict(v)  # type: ignore[arg-type]
        except Exception:
            return {}

settings = Settings()
