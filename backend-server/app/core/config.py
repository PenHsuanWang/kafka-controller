from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Kafka bootstrap (comma-separated)
    kafka_bootstrap: str = Field("localhost:9092")

    # Optional: pin to avoid version probe (e.g. "3.6.0" or "2.8.0")
    kafka_api_version: str | None = None

    # Client timeouts (ms)
    request_timeout_ms: int = 20000
    metadata_max_age_ms: int = 30000
    api_version_auto_timeout_ms: int = 10000

    # Admin connection retry
    admin_connect_max_tries: int = 8
    admin_connect_backoff_sec: float = 1.5

    # Security (set when using SASL/SSL)
    security_protocol: str = "PLAINTEXT"   # "SASL_SSL", "SSL", ...
    sasl_mechanism: str | None = None
    sasl_plain_username: str | None = None
    sasl_plain_password: str | None = None
    ssl_cafile: str | None = None

    # JMX
    jmx_host: str = "localhost"
    jmx_port: int = 9999

    # WS
    ws_cluster_tick: float = 2.0

    # Allow overriding CORS at runtime:
    cors_allow_origins: list[str] | None = None
    # Accept either JSON array (e.g. '["http://localhost:3000"]')
    # or comma-separated string (e.g. 'http://localhost:3000,http://127.0.0.1:3000')
    @field_validator("cors_allow_origins", mode="before")
    def _parse_cors_origins(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)  # JSON array
            except Exception:
                return [s.strip() for s in v.split(",") if s.strip()]
        return v

settings = Settings()