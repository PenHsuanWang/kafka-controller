# producer.py
import os
import json
import time
import uuid
import random
import argparse
from datetime import datetime, timezone
from kafka import KafkaProducer, errors as kerrors


def build_producer(bootstrap: str) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=bootstrap.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
        # idempotence settings (supported by kafka-python 2.x)
        enable_idempotence=True,
        acks=-1,
        max_in_flight_requests_per_connection=1,
        # perf tuning
        linger_ms=20,
        batch_size=32_768,
        compression_type="gzip",
        request_timeout_ms=30_000,
        retries=5,
    )


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_event(i: int) -> dict:
    # Randomized, IID event payload
    user_id = random.randint(1, 10_000)
    device = random.choice(["ios", "android", "web", "backend"])
    action = random.choice(["view", "click", "checkout", "create", "update"])
    # Log-normal-ish spend; small but occasionally spiky
    amount = round(random.lognormvariate(2.0, 0.8), 2)
    return {
        "iid": str(uuid.uuid4()),          # independent ID per event
        "seq": i,                           # local monotonic sequence
        "ts": iso_now(),
        "actor": {"user_id": user_id, "device": device},
        "event": {"name": action, "amount": amount},
        "payload": {"msg": f"hello #{i}"},
    }, str(user_id)  # value, key (partition by user by default)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap", default=os.getenv("KAFKA_BOOTSTRAP", "localhost:9092"))
    ap.add_argument("--topic", default=os.getenv("TOPIC", "test-topic"))
    ap.add_argument("--key", default=None, help="Static key. If omitted, uses user_id per event.")
    ap.add_argument("--avg-per-minute", type=float, default=120.0,
                    help="Target average events per minute.")
    ap.add_argument("--burst-sec", type=float, default=5.0,
                    help="Seconds of high-rate burst inside each minute.")
    ap.add_argument("--burst-share", type=float, default=0.90,
                    help="Fraction of minute's traffic that occurs in the burst window.")
    ap.add_argument("--quiet", action="store_true", help="Reduce console logging.")
    args = ap.parse_args()

    if not (0.0 < args.burst_share < 1.0):
        raise SystemExit("--burst-share must be in (0,1)")
    if not (0.0 < args.burst_sec < 60.0):
        raise SystemExit("--burst-sec must be in (0,60)")

    # Compute piecewise-constant rates to hit the desired averages:
    # - high rate during burst window
    # - low rate during the rest of the minute
    burst_rate = (args.avg_per_minute * args.burst_share) / args.burst_sec               # events/sec in burst
    rest_seconds = 60.0 - args.burst_sec
    rest_rate = (args.avg_per_minute * (1.0 - args.burst_share)) / rest_seconds          # events/sec outside burst

    producer = build_producer(args.bootstrap)

    # Per-minute windowing (not wall-clock aligned; relative to start time)
    window_start = time.time()
    # Choose a random burst start offset inside the minute (so it looks natural)
    burst_start = random.uniform(0.0, 60.0 - args.burst_sec)
    i = 0
    sent_in_window = 0
    last_stat_emit = time.time()

    if not args.quiet:
        print(f"[boot] avg={args.avg_per_minute:.1f}/min, burst={args.burst_sec:.1f}s "
              f"({args.burst_share*100:.0f}%), rates: burst={burst_rate:.2f}/s rest={rest_rate:.3f}/s")

    try:
        while True:
            now = time.time()

            # Advance window(s) if we crossed minute boundary
            if now - window_start >= 60.0:
                # Emit minute stats
                if not args.quiet:
                    elapsed_min = int((now - window_start) // 60) or 1
                    print(f"[minute] sent={sent_in_window} events in last minute "
                          f"(~{sent_in_window/elapsed_min:.1f}/min)")
                # Start the next window at the nearest 60s boundary from current window
                # Keep moving forward in case we slept across multiple minutes
                n_advance = int((now - window_start) // 60.0)
                window_start += 60.0 * n_advance
                sent_in_window = 0
                burst_start = random.uniform(0.0, 60.0 - args.burst_sec)

            # Determine current segment and rate
            offset = now - window_start  # 0..60
            burst_end = burst_start + args.burst_sec
            if offset < burst_start:
                rate = rest_rate
                seg_end = burst_start
            elif offset < burst_end:
                rate = burst_rate
                seg_end = burst_end
            else:
                rate = rest_rate
                seg_end = 60.0

            seg_remaining = max(0.0, seg_end - offset)

            # Sample waiting time for current (piecewise-constant) rate
            if rate > 0:
                wait = random.expovariate(rate)  # mean 1/rate
            else:
                wait = float("inf")

            # If next event crosses the segment boundary, just advance to the boundary and resample
            sleep_for = min(wait, seg_remaining)
            if sleep_for > 0:
                time.sleep(sleep_for)

            # If the sampled arrival happens before the boundary, emit an event
            if wait <= seg_remaining and rate > 0:
                value, user_key = make_event(i)
                key = args.key if args.key is not None else user_key
                try:
                    producer.send(
                        args.topic,
                        key=key,
                        value=value,
                        timestamp_ms=int(time.time() * 1000),
                    )
                except (kerrors.KafkaTimeoutError, kerrors.KafkaError) as e:
                    if not args.quiet:
                        print(f"[warn] send failed: {e}; retrying after short backoff")
                    time.sleep(0.5)
                    continue

                i += 1
                sent_in_window += 1

            # Light periodic flush to bound memory/latency during bursts
            if time.time() - last_stat_emit >= 1.0:
                try:
                    producer.flush(timeout=0.2)
                except Exception:
                    # ignore transient flush errors; send() will retry based on producer config
                    pass
                last_stat_emit = time.time()

    except KeyboardInterrupt:
        if not args.quiet:
            print("\n[shutdown] draining producer...")
        try:
            producer.flush()
        finally:
            producer.close()
        if not args.quiet:
            print("[done] closed cleanly")


if __name__ == "__main__":
    main()
