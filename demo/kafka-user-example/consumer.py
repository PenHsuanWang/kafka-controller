# consumer.py
import os
import json
import signal
import argparse
from typing import Dict
from kafka import KafkaConsumer, TopicPartition

_running = True
def _stop(*_):
    global _running
    _running = False

def build_consumer(bootstrap: str, group_id: str, topic: str) -> KafkaConsumer:
    c = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap.split(","),
        group_id=group_id,
        enable_auto_commit=False,                 # we'll commit manually
        auto_offset_reset="earliest",             # read from earliest if no commit exists
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        key_deserializer=lambda b: b.decode("utf-8") if b is not None else None,
        max_poll_records=500,
        session_timeout_ms=45_000,
        heartbeat_interval_ms=3_000,
        max_poll_interval_ms=300_000,
        # If you prefer a non-blocking loop, set consumer_timeout_ms to break idle loops
        # consumer_timeout_ms=1000,
    )
    return c

def main():
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap", default=os.getenv("KAFKA_BOOTSTRAP", "localhost:9092"))
    ap.add_argument("--topic", default=os.getenv("TOPIC", "test-topic"))
    ap.add_argument("--group", default=os.getenv("GROUP_ID", "demo-group"))
    args = ap.parse_args()

    consumer = build_consumer(args.bootstrap, args.group, args.topic)
    print(f"Consuming {args.topic} as group {args.group}… Ctrl+C to stop")

    processed_since_commit = 0
    try:
        while _running:
            records: Dict[TopicPartition, list] = consumer.poll(timeout_ms=1000, max_records=1000)
            if not records:
                continue

            for tp, msgs in records.items():
                for m in msgs:
                    print(
                        f"{m.topic} p{m.partition} o{m.offset} "
                        f"key={m.key} value={m.value}"
                    )
                    processed_since_commit += 1

            # commit synchronously after each poll (or use a threshold)
            if processed_since_commit:
                consumer.commit()  # commit last consumed offsets
                processed_since_commit = 0
    finally:
        try:
            consumer.commit()  # best effort final commit
        finally:
            consumer.close()

if __name__ == "__main__":
    main()
