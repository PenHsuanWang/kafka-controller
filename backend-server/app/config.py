"""Application configuration loaded from environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global settings object.

    Attributes
    ----------
    bootstrap_servers : str
        Comma-separated list of Kafka brokers.
    poll_interval : float
        Seconds between metric snapshots.
    jwt_secret : str
        Shared key for HS256 signing.
    """

    bootstrap_servers: str = "localhost:9092"
    poll_interval: float = 1.0
    jwt_secret: str = "change-me"

    class Config:
        env_file = ".env"
        env_prefix = "KAFKA_ADMIN_"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()  # pragma: no cover