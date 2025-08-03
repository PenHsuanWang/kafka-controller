"""Use-case coordination for topic CRUD + KPIs."""
from __future__ import annotations

from typing import List, Optional

from app.domain.models.topic import Topic
from app.infra.kafka.admin import KafkaAdminFacade


class TopicService:
    """Stateless wrapper combining facade calls and business rules."""

    def __init__(self, admin: KafkaAdminFacade) -> None:
        self._admin = admin

    # ------------------------------------------------------------------ #
    # Queries                                                             #
    # ------------------------------------------------------------------ #
    def list_topics(self, name_filter: Optional[str] = None) -> List[Topic]:
        """Return topics, optionally filtered by substring."""
        topics = self._admin.list_topics()
        if name_filter:
            topics = [t for t in topics if name_filter in t.name]
        return topics

    # ------------------------------------------------------------------ #
    # Commands                                                            #
    # ------------------------------------------------------------------ #
    def create_topic(self, topic: Topic) -> None:
        """Idempotent create (spec §4.1)."""
        self._admin.create_topic(topic)

    def schedule_delete_topic(self, name: str, confirm_token: str | None) -> None:
        """Soft-delete workflow (example implementation)."""
        if not confirm_token:
            raise ValueError("Confirmation token required (spec §3)")
        # Placeholder: mark topic in external store or tag via config
        # Real deletion handled asynchronously