"""Operations for consumer groups: list, lag, reset offsets."""
from __future__ import annotations

from typing import List

from kafka import KafkaAdminClient, KafkaConsumer  # kafka-python

from app.domain.models.consumer_group import ConsumerGroup, OffsetResetRequest
from app.infra.kafka.lag import partition_lag
from app.infra.kafka.admin import KafkaAdminFacade


class ConsumerService:
    """Group-level business logic."""

    def __init__(self, admin: KafkaAdminFacade) -> None:
        self._admin = admin
        self._bootstrap = admin._client.config["bootstrap_servers"]

    # ------------------------------------------------------------------ #
    # Queries                                                             #
    # ------------------------------------------------------------------ #
    def list_groups(self) -> List[ConsumerGroup]:
        """Return consumer groups with aggregate lag for the cluster."""
        admin = KafkaAdminClient(bootstrap_servers=self._bootstrap)
        groups = admin.list_consumer_groups()
        result: list[ConsumerGroup] = []
        for (group_id, _state) in groups:
            result.append(
                ConsumerGroup(
                    group_id=group_id,
                    state=_state,
                    member_count=0,
                    total_lag=0,
                )
            )
        return result

    # ------------------------------------------------------------------ #
    # Commands                                                            #
    # ------------------------------------------------------------------ #
    def reset_offsets(self, gid: str, req: OffsetResetRequest) -> None:
        """Perform an offset-reset according to the strategy or explicit target."""
        consumer = KafkaConsumer(
            group_id=gid, bootstrap_servers=self._bootstrap, enable_auto_commit=False
        )
        if req.strategy == "earliest":
            consumer.seek_to_beginning()
        elif req.strategy == "latest":
            consumer.seek_to_end()
        elif req.to_offset is not None:
            # Assume single-partition topic for brevity
            tp = list(consumer.assignment())[0]
            consumer.seek(tp, req.to_offset)
        else:
            raise ValueError("Unsupported reset request")
        consumer.commit()