"""Kafka Admin façade built on kafka-python."""
from typing import Iterable
from kafka.admin import KafkaAdminClient, NewTopic  # kafka-python
from kafka.errors import TopicAlreadyExistsError
from app.domain.models.topic import Topic


class KafkaAdminFacade:
    """Encapsulates admin operations against a Kafka cluster."""

    def __init__(self, bootstrap_servers: str) -> None:
        self._client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)

    # ---------- Topic CRUD -------------------------------------------------

    def list_topics(self) -> list[Topic]:
        """Return metadata for all topics."""
        metadata = self._client.list_topics()  # names only
        return [Topic(name=n) for n in metadata]

    def create_topic(self, topic: Topic) -> None:
        """Create a new topic if it does not exist.

        Parameters
        ----------
        topic : Topic
            Desired topic definition.
        """
        new_topic = NewTopic(
            name=topic.name,
            num_partitions=topic.partitions,
            replication_factor=topic.replication_factor,
        )
        try:
            self._client.create_topics([new_topic])
        except TopicAlreadyExistsError:
            # idempotent ← spec §4.1
            return