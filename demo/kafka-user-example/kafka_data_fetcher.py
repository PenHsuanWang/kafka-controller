# kafka_data_fetcher.py
# -*- coding: utf-8 -*-
"""
Minimal, safe-ish Kafka consumer wrapper with:
- 20s broker RPC timeout (request_timeout_ms)
- Heartbeat/session tuning to stay in group
- fetch() method that wraps poll() and error handling
- Timeout errors are surfaced as KafkaDataFetcherException ONLY

Docs:
- KafkaConsumer parameters incl. request_timeout_ms.  (kafka-python) 
- poll(timeout_ms) semantics (returns empty if no data). 
"""
from __future__ import annotations

import logging
import sys
from time import monotonic
import os
import threading
from typing import Dict, List, Tuple, Iterable, Optional

from kafka import KafkaConsumer
from kafka.structs import TopicPartition
from kafka.errors import (
    KafkaError,
    KafkaTimeoutError,         # client-side request timeout
    RequestTimedOutError,      # broker-side request timeout
    NoBrokersAvailable,
)
try:
    # socket.timeout for extra safety (e.g., DNS / TCP layer)
    from socket import timeout as SocketTimeout
except Exception:  # pragma: no cover
    SocketTimeout = Exception  # fallback


class KafkaDataFetcherException(RuntimeError):
    """Raised when a broker interaction times out (normalized)."""
    pass


def _is_timeout_error(err: BaseException) -> bool:
    """Classify timeout-ish errors from kafka-python and lower layers."""
    if isinstance(err, (KafkaTimeoutError, RequestTimedOutError)):
        return True
    # Some envs may surface lower-level timeouts
    if isinstance(err, SocketTimeout):
        return True
    # Heuristic: certain KafkaError messages contain "timed out"
    msg = str(err).lower()
    return "timed out" in msg or "timeout" in msg


class KafkaDataFetcher:
    """
    Thin wrapper over kafka-python KafkaConsumer with sane defaults.
    - Uses request_timeout_ms=20000 (20s) to bound broker RPC waits.
    - Keeps consumer group membership healthy via heartbeat/session config.

    NOTE:
    - poll(timeout_ms) only bounds the loop wait; if there is no data,
      it returns empty dict rather than raising. We DO NOT treat that as timeout.
    """

    def __init__(
        self,
        topic: str,
        bootstrap_servers: Optional[List[str]] = None,
        group_id: str = "demo-group",
        auto_offset_reset: str = "earliest",
        enable_auto_commit: bool = True,
        poll_timeout_ms: int = 1000,
        max_records: int = 500,
    ) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self.topic = topic
        self.poll_timeout_ms = poll_timeout_ms
        self.max_records = max_records

        if bootstrap_servers is None:
            bootstrap_servers = ["localhost:9092"]

        try:
            # Important timeouts / liveness:
            # - request_timeout_ms: bounds network RPCs like metadata, commits, etc. (here 20s)
            # - session/heartbeat: keep consumer from being kicked out of the group
            # - fetch_max_wait_ms: broker-side wait before responding if not enough bytes
            self._consumer = KafkaConsumer(
                topic,
                bootstrap_servers=bootstrap_servers,
                group_id=group_id,
                auto_offset_reset=auto_offset_reset,
                enable_auto_commit=enable_auto_commit,
                # ---- network / RPC timeout ----
                request_timeout_ms=20000,       # 20s for broker RPCs (metadata, fetch, offset ops)
                fetch_min_bytes=1,
                fetch_max_wait_ms=500,          # broker waits up to 500ms to batch fetch bytes
                metadata_max_age_ms=300000,     # refresh metadata every 5 minutes
                # ---- group liveness ----
                session_timeout_ms=15000,       # 15s without heartbeat => kicked from group
                heartbeat_interval_ms=3000,     # ~1/5 of session; <= 1/3 is common
                max_poll_interval_ms=300000,    # must call poll() within 5 minutes
            )
        except (KafkaError, Exception) as e:
            if _is_timeout_error(e):
                # Normalize any timeout(-ish) into our custom exception
                raise KafkaDataFetcherException(f"Timeout during consumer initialization: {e}") from e
            # Preserve concrete error for non-timeout failures (e.g., NoBrokersAvailable)
            raise

    def fetch(self) -> Iterable[Tuple[str, int, int, Optional[str], Optional[str]]]:
        """
        Fetch records once using poll(); yields tuples:
        (topic, partition, offset, key_str, value_str)

        Behavior:
        - Returns an empty iterator when no data (this is NOT a timeout).
        - Any broker/RPC timeout is normalized to KafkaDataFetcherException.

        Example:
            for rec in fetcher.fetch():
                ...
        """
        try:
            records = self._consumer.poll(timeout_ms=self.poll_timeout_ms, max_records=self.max_records)
        except (KafkaError, Exception) as e:
            if _is_timeout_error(e):
                raise KafkaDataFetcherException(f"Timeout during poll(): {e}") from e
            raise

        if not records:
            return iter(())  # empty iterator

        def _decode(b):
            if isinstance(b, (bytes, bytearray)):
                try:
                    return b.decode("utf-8", "replace")
                except Exception:
                    return None
            return b

        out: List[Tuple[str, int, int, Optional[str], Optional[str]]] = []
        for tp, msgs in records.items():
            for msg in msgs:
                out.append((
                    msg.topic,
                    msg.partition,
                    msg.offset,
                    _decode(msg.key),
                    _decode(msg.value),
                ))
        return iter(out)

    def health_probe(self) -> bool:
        """
        Lightweight liveness probe.
        - Drives consumer heartbeats via poll(0)
        - Verifies topic metadata and leader reachability by calling end_offsets() on 1 partition
        Returns True if brokers appear reachable; False otherwise.
        """
        try:
            # Drive coordinator/heartbeats without blocking
            self._consumer.poll(0)

            # Try to get partitions for the topic; absence implies missing metadata
            parts = self._consumer.partitions_for_topic(self.topic)
            if not parts:
                return False

            # Ping exactly one partition's end offset to minimize load
            tp0 = TopicPartition(self.topic, min(parts))
            _ = self._consumer.end_offsets([tp0])
            return True
        except Exception as e:
            # Treat timeout-ish errors as probe failure; anything else also returns False
            if _is_timeout_error(e):
                return False
            return False

    def close(self) -> None:
        try:
            self._consumer.close()
        except (KafkaError, Exception) as e:
            if _is_timeout_error(e):
                raise KafkaDataFetcherException(f"Timeout during close(): {e}") from e
            raise

if __name__ == "__main__":

    # Minimal logging for visibility
    #logging.basicConfig(level=logging.INFO)
    #logging.getLogger("kafka").setLevel(logging.WARNING)

    # Construct fetcher; if cluster is down at startup, exit fast
    try:
        fetcher = KafkaDataFetcher(
            topic="my-topic",
            bootstrap_servers=["localhost:19092"],
            group_id="demo-group",
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            poll_timeout_ms=1000,  # single poll waits up to 1s
            max_records=500,
        )
    except NoBrokersAvailable as e:
        print(f"Startup failed: {e}")
        sys.exit(2)

    HEALTH_CHECK_INTERVAL_SEC = 5
    last_probe_ts = 0.0

    exit_code = 0

    try:
        while True:
            # 1) Consume normally
            for topic, part, off, key, val in fetcher.fetch():
                print(f"{topic} p{part}@{off} key={key} value={val}")

            # 2) Periodic lightweight health probe (minimizes broker load)
            now = monotonic()
            if now - last_probe_ts >= HEALTH_CHECK_INTERVAL_SEC:
                ok = fetcher.health_probe()
                last_probe_ts = now
                if not ok:
                    raise KafkaDataFetcherException("Health probe failed: brokers unreachable or metadata missing")
    except KeyboardInterrupt:
        pass
    except KafkaDataFetcherException as e:
        # Fail fast on outage: do not sit around waiting for brokers to return
        print(f"Fetcher timeout/outage detected: {e}")
        exit_code = 1
    finally:
        # Ensure close cannot hang the process. Bound it with a short timeout; then hard-exit.
        def _do_close():
            try:
                # Try to use a bounded close if available; fall back to unbounded.
                try:
                    fetcher._consumer.close(timeout=1)
                except TypeError:
                    fetcher._consumer.close()
                except Exception:
                    # If bounded close fails, try wrapper close which normalizes timeouts
                    try:
                        fetcher.close()
                    except Exception:
                        pass
            except Exception:
                pass

        t = threading.Thread(target=_do_close, daemon=True)
        t.start()
        t.join(2.5)

        if t.is_alive():
            print("Close hang detected; forcing process termination.")
            os._exit(exit_code)
        else:
            os._exit(exit_code)
