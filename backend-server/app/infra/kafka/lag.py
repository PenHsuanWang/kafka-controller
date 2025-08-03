"""Utility helpers for consumer lag calculations."""
from kafka import KafkaConsumer


def partition_lag(consumer: KafkaConsumer, topic: str, partition: int) -> int:
    """Compute lag = high-water offset − committed offset."""
    tp = consumer.assignment().pop()  # simplification
    highwater = consumer.highwater(tp)  # may need fetch cycle
    committed = consumer.committed(tp)
    return highwater - committed  # see kafka-python API notes