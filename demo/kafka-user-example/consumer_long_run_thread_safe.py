#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production-ready kafka-python consumer with:
- CLI config
- Safe rebalance (commit on revoke)
- Periodic async commits + final sync commit
- Health checks (lag, assignment, connectivity)
- Self-healing: auto close & recreate on stall/errors

Docs & rationale:
- max.poll.interval.ms semantics / KIP-62 (rebalance if no poll before timeout)
- Rebalance callbacks: revoked -> assigned order and common usage
- Heartbeat vs session timeout (heartbeat <= 1/3 session)
- reconnect_backoff_ms / reconnect_backoff_max_ms for client reconnect backoff
- kafka-python KafkaConsumer API (poll, commit, metrics, end_offsets, position)
Refs: KIP-62, Apache Kafka Javadoc, Confluent configs, kafka-python docs.
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
from typing import Dict, Optional, Set

from kafka import KafkaConsumer, TopicPartition

try:
    # ABIs differ across versions; fall back to duck-typing if not present
    from kafka.consumer.subscription_state import ConsumerRebalanceListener
except Exception:  # pragma: no cover
    class ConsumerRebalanceListener:  # type: ignore
        def on_partitions_revoked(self, revoked): ...
        def on_partitions_assigned(self, assigned): ...


LOG = logging.getLogger("kafka_consumer_guard")
STOP = False


# ---------- CLI ----------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Reliable kafka-python Consumer with auto-recovery and health checks",
        allow_abbrev=False,  # 建議關閉自動縮寫，避免混淆
    )
    ap.add_argument("-b", "--bootstrap",
                    default=os.getenv("KAFKA_BOOTSTRAP", "localhost:9092"),
                    help="Comma-separated bootstrap servers")
    ap.add_argument("-t", "--topic",
                    default=os.getenv("TOPIC", "test-topic"),
                    help="Topic name(s), comma-separated")

    # 加入多個別名：--group / --consumer-group / -g -> args.group
    ap.add_argument("-g", "--group", "--consumer-group",
                    dest="group",
                    default=os.getenv("GROUP_ID") or os.getenv("CONSUMER_GROUP", "demo-group"),
                    help="Consumer group id")

    ap.add_argument("--auto-offset-reset",
                    default=os.getenv("AUTO_OFFSET_RESET", "earliest"),
                    choices=["earliest", "latest"],
                    help="Offset reset policy when no committed offset")
    ap.add_argument("--value-format",
                    default=os.getenv("VALUE_FORMAT", "json"),
                    choices=["json", "raw"], help="Decode values as JSON or return raw bytes")
    ap.add_argument("--max-poll-records", type=int,
                    default=int(os.getenv("MAX_POLL_RECORDS", "200")),
                    help="Max records returned per poll()")
    ap.add_argument("--max-poll-interval-ms", type=int,
                    default=int(os.getenv("MAX_POLL_INTERVAL_MS", "600000")),
                    help="Max gap between polls before the client leaves group")
    ap.add_argument("--session-timeout-ms", type=int,
                    default=int(os.getenv("SESSION_TIMEOUT_MS", "30000")),
                    help="Group session timeout")
    ap.add_argument("--heartbeat-interval-ms", type=int,
                    default=int(os.getenv("HEARTBEAT_INTERVAL_MS", "3000")),
                    help="Heartbeat interval (≤ 1/3 session)")
    ap.add_argument("--request-timeout-ms", type=int,
                    default=int(os.getenv("REQUEST_TIMEOUT_MS", "120000")),
                    help="Client request timeout to brokers")
    ap.add_argument("--reconnect-backoff-ms", type=int,
                    default=int(os.getenv("RECONNECT_BACKOFF_MS", "100")),
                    help="Initial reconnect backoff in ms")
    ap.add_argument("--reconnect-backoff-max-ms", type=int,
                    default=int(os.getenv("RECONNECT_BACKOFF_MAX_MS", "5000")),
                    help="Max reconnect backoff in ms")
    ap.add_argument("--poll-timeout-ms", type=int,
                    default=int(os.getenv("POLL_TIMEOUT_MS", "1000")),
                    help="poll() timeout in ms (local wait for fetched data)")
    ap.add_argument("--commit-interval", type=float,
                    default=float(os.getenv("COMMIT_INTERVAL", "5")),
                    help="Periodic async commit interval in seconds")
    ap.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"),
                    help="Logging level (DEBUG, INFO, WARN, ERROR)")
    # Self-healing knobs
    ap.add_argument("--stall-seconds", type=int,
                    default=int(os.getenv("STALL_SECONDS", "120")),
                    help="If no progress for this many seconds, recreate consumer")
    ap.add_argument("--max-consecutive-errors", type=int,
                    default=int(os.getenv("MAX_CONSECUTIVE_ERRORS", "5")),
                    help="Recreate after this many consecutive errors in poll/processing")
    ap.add_argument("--recreate-backoff-seconds", type=float,
                    default=float(os.getenv("RECREATE_BACKOFF_SECONDS", "3")),
                    help="Sleep before recreating consumer")
    ap.add_argument("--exit-after-seconds", type=float, default=None,
                    help="Optional: exit after N seconds (smoke test)")
    ap.add_argument("--health-json", default=os.getenv("HEALTH_JSON", ""),
                    help="Optional: write health info JSON to this file path periodically")
    return ap.parse_args()


def setup_logging(level: str) -> None:
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=lvl, format="%(asctime)s %(levelname)s %(name)s - %(message)s")


# ---------- Rebalance listener ----------

class RebalanceCommitter(ConsumerRebalanceListener):
    """Commit offsets on revoke to minimize duplicates; log assigns for visibility."""
    def __init__(self, consumer: KafkaConsumer):
        self.consumer = consumer

    def on_partitions_revoked(self, revoked):
        tps = list(revoked) if revoked else []
        LOG.warning("Rebalance: partitions revoked: %s", tps)
        try:
            # Safe point before giving up partitions
            self.consumer.commit()
            LOG.info("Committed offsets before revoke")
        except Exception:
            LOG.exception("Commit on revoke failed")

    def on_partitions_assigned(self, assigned):
        tps = list(assigned) if assigned else []
        LOG.info("Rebalance: partitions assigned: %s", tps)
        # If you maintain external offsets/state, seek() here.
        # Example: for tp in tps: self.consumer.seek(tp, desired_offset)


# ---------- Consumer wrapper with guard loop ----------

class ConsumerRunner:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.consumer: Optional[KafkaConsumer] = None
        self.listener: Optional[RebalanceCommitter] = None
        self.last_progress_ts: float = time.time()
        self.last_commit_ts: float = 0.0
        self.consecutive_errors: int = 0
        self.pending_offsets: Dict[TopicPartition, int] = {}
        self.assignment: Set[TopicPartition] = set()

    # ---- lifecycle ----
    def build_consumer(self) -> KafkaConsumer:
        value_deser = (lambda b: json.loads(b.decode("utf-8")) if b is not None else None) \
            if self.args.value_format == "json" else (lambda b: b)
        c = KafkaConsumer(
            bootstrap_servers=[s.strip() for s in self.args.bootstrap.split(",") if s.strip()],
            group_id=self.args.group,
            client_id=f"{self.args.group}-pycli",
            enable_auto_commit=False,
            auto_offset_reset=self.args.auto_offset_reset,
            max_poll_records=self.args.max_poll_records,
            max_poll_interval_ms=self.args.max_poll_interval_ms,
            session_timeout_ms=self.args.session_timeout_ms,
            heartbeat_interval_ms=self.args.heartbeat_interval_ms,
            request_timeout_ms=self.args.request_timeout_ms,
            reconnect_backoff_ms=self.args.reconnect_backoff_ms,
            reconnect_backoff_max_ms=self.args.reconnect_backoff_max_ms,
            value_deserializer=value_deser,
            key_deserializer=lambda b: b.decode("utf-8") if b else None,
            metrics_enabled=True,
        )
        self.listener = RebalanceCommitter(c)
        topics = [t.strip() for t in self.args.topic.split(",") if t.strip()]
        c.subscribe(topics=topics, listener=self.listener)
        LOG.info("Consumer created. bootstrap=%s group=%s topics=%s",
                 self.args.bootstrap, self.args.group, topics)
        return c

    def close_consumer(self) -> None:
        if self.consumer is None:
            return
        try:
            if self.pending_offsets:
                self.consumer.commit()  # final sync commit
        except Exception:
            LOG.exception("final commit failed")
        try:
            self.consumer.close()
            LOG.info("Consumer closed")
        except Exception:
            LOG.exception("consumer.close failed")
        finally:
            self.consumer = None
            self.listener = None
            self.pending_offsets.clear()
            self.assignment = set()

    def recreate_consumer(self, reason: str) -> None:
        LOG.warning("Recreating consumer due to: %s", reason)
        self.close_consumer()
        time.sleep(self.args.recreate_backoff_seconds)
        self.consumer = self.build_consumer()
        self.last_progress_ts = time.time()
        self.consecutive_errors = 0

    # ---- processing ----
    def process_record(self, rec) -> None:
        # Replace with your business logic
        LOG.info("Process %s:%d@%d key=%s value=%s",
                 rec.topic, rec.partition, rec.offset, rec.key, rec.value)

    def maybe_commit_async(self) -> None:
        if not self.consumer:
            return
        now = time.time()
        if now - self.last_commit_ts >= self.args.commit_interval and self.pending_offsets:
            try:
                self.consumer.commit_async()
                self.last_commit_ts = now
                LOG.debug("commit_async done")
            except Exception:
                LOG.exception("commit_async failed")

    # ---- health / metrics ----
    def compute_lag(self) -> Dict[str, int]:
        """Return per-partition lag numbers."""
        if not self.consumer:
            return {}
        try:
            tps = self.consumer.assignment()
            if not tps:
                return {}
            end = self.consumer.end_offsets(list(tps))  # {tp: end_offset}
            lag: Dict[str, int] = {}
            for tp in tps:
                try:
                    pos = self.consumer.position(tp)
                    lag[f"{tp.topic}-{tp.partition}"] = max(0, end.get(tp, 0) - pos)
                except Exception:
                    lag[f"{tp.topic}-{tp.partition}"] = -1
            return lag
        except Exception:
            LOG.debug("compute_lag failed", exc_info=True)
            return {}

    def write_health(self) -> None:
        if not self.args.health_json:
            return
        data = {
            "ts": int(time.time()),
            "bootstrap_connected": bool(self.consumer and self.consumer.bootstrap_connected()),
            "assignment": [f"{tp.topic}-{tp.partition}" for tp in (self.consumer.assignment() if self.consumer else [])],
            "lag": self.compute_lag(),
            "consecutive_errors": self.consecutive_errors,
            "seconds_since_progress": int(time.time() - self.last_progress_ts),
        }
        try:
            with open(self.args.health_json, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            LOG.debug("write_health failed", exc_info=True)

    # ---- main loop ----
    def run(self) -> None:
        self.consumer = self.build_consumer()
        self.last_commit_ts = time.time()

        while not STOP:
            # optional timed exit
            if self.args.exit_after_seconds is not None and \
               (time.time() - self.last_commit_ts) >= self.args.exit_after_seconds:
                LOG.info("exit-after-seconds reached; stopping")
                break

            try:
                batches = self.consumer.poll(timeout_ms=self.args.poll_timeout_ms) if self.consumer else {}
                made_progress = False

                if batches:
                    for tp, records in batches.items():
                        for rec in records:
                            self.process_record(rec)
                            self.pending_offsets[tp] = rec.offset + 1
                            made_progress = True
                    self.assignment = set(batches.keys())

                if made_progress:
                    self.last_progress_ts = time.time()
                    self.consecutive_errors = 0

                self.maybe_commit_async()
                self.write_health()

                # stall detection (no progress too long)
                if (time.time() - self.last_progress_ts) >= self.args.stall_seconds:
                    self.recreate_consumer(f"stall {int(time.time() - self.last_progress_ts)}s without progress")
                    continue

                # connectivity sanity (optional visibility)
                if self.consumer and not self.consumer.bootstrap_connected():
                    LOG.warning("bootstrap_connected=False (broker unreachable); will rely on reconnect/backoff")

            except Exception:
                self.consecutive_errors += 1
                LOG.exception("error in poll/process; consecutive_errors=%d", self.consecutive_errors)
                if self.consecutive_errors >= self.args.max_consecutive_errors:
                    self.recreate_consumer(f"errors x{self.consecutive_errors}")
                else:
                    time.sleep(0.5)

        # graceful shutdown
        self.close_consumer()


# ---------- entry ----------

def main():
    args = parse_args()
    setup_logging(args.log_level)

    def _shutdown(signum, _frame):
        global STOP
        STOP = True
        LOG.info("Signal %s received. Shutting down...", signum)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    runner = ConsumerRunner(args)
    runner.run()


if __name__ == "__main__":
    main()