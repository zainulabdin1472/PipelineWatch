"""Demo pipeline that exposes Prometheus metrics and sometimes fails."""

from __future__ import annotations

import logging
import os
import random
import sys
import time
from pathlib import Path

from prometheus_client import Counter, Gauge, Histogram, start_http_server

PIPELINE = os.environ.get("PIPELINE_NAME", "demo")
LOG_PATH = os.environ.get("LOG_PATH", "/var/log/pipeline/demo.log")
SLOW_RUN_CHANCE = 0.15
DURATION_ALERT_SECONDS = 30.0


def read_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"invalid {name}={raw!r}", file=sys.stderr)
        raise SystemExit(2)


FAIL_RATE = min(1.0, max(0.0, read_float("DEMO_FAIL_RATE", 0.25)))
STALE_HOURS = max(0.0, read_float("DEMO_STALE_HOURS", 0.0))
INTERVAL = max(1.0, read_float("DEMO_INTERVAL_SECONDS", 15.0))

DURATION = Gauge(
    "pipeline_last_run_duration_seconds",
    "Duration of the most recent pipeline run in seconds",
    ["pipeline"],
)
DURATION_HIST = Histogram(
    "pipeline_run_duration_seconds",
    "Pipeline run duration distribution in seconds",
    ["pipeline"],
    buckets=(1, 5, 10, 15, 30, 45, 60, 120),
)
ROWS = Counter(
    "pipeline_rows_processed_total",
    "Rows processed by successful runs",
    ["pipeline"],
)
LAST_SUCCESS = Gauge(
    "pipeline_last_success_timestamp_seconds",
    "Unix timestamp of the last successful run",
    ["pipeline"],
)
FAILURES = Counter(
    "pipeline_failures_total",
    "Failed pipeline runs",
    ["pipeline"],
)
RUNS = Counter(
    "pipeline_runs_total",
    "Pipeline runs by outcome",
    ["pipeline", "status"],
)
UP = Gauge(
    "pipeline_up",
    "1 while the pipeline process is serving metrics",
    ["pipeline"],
)


def build_logger() -> logging.Logger:
    logger = logging.getLogger("demo-pipeline")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logger.addHandler(stream)
    path = Path(LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger


def main() -> None:
    log = build_logger()
    start_http_server(8000)
    UP.labels(PIPELINE).set(1)
    ROWS.labels(PIPELINE).inc(0)
    FAILURES.labels(PIPELINE).inc(0)
    RUNS.labels(PIPELINE, "success").inc(0)
    RUNS.labels(PIPELINE, "failure").inc(0)

    if STALE_HOURS > 0:
        LAST_SUCCESS.labels(PIPELINE).set(time.time() - (STALE_HOURS * 3600))
        log.warning(
            "freshness frozen %.1f hours in the past so DataStale can fire pipeline=%s",
            STALE_HOURS,
            PIPELINE,
        )

    log.info(
        "demo pipeline listening on :8000 pipeline=%s fail_rate=%s interval=%ss",
        PIPELINE,
        FAIL_RATE,
        INTERVAL,
    )

    while True:
        started = time.time()
        if random.random() < SLOW_RUN_CHANCE:
            work = random.uniform(DURATION_ALERT_SECONDS + 1, 45)
        else:
            work = random.uniform(2, 12)
        time.sleep(work)
        elapsed = time.time() - started
        DURATION.labels(PIPELINE).set(elapsed)
        DURATION_HIST.labels(PIPELINE).observe(elapsed)

        if random.random() < FAIL_RATE:
            FAILURES.labels(PIPELINE).inc()
            RUNS.labels(PIPELINE, "failure").inc()
            log.error(
                "pipeline run failed duration=%.2fs pipeline=%s",
                elapsed,
                PIPELINE,
            )
        else:
            processed = random.randint(100, 1000)
            ROWS.labels(PIPELINE).inc(processed)
            RUNS.labels(PIPELINE, "success").inc()
            if STALE_HOURS == 0:
                LAST_SUCCESS.labels(PIPELINE).set(time.time())
            log.info(
                "pipeline run ok rows=%s duration=%.2fs pipeline=%s",
                processed,
                elapsed,
                PIPELINE,
            )

        remaining = INTERVAL - (time.time() - started)
        if remaining > 0:
            time.sleep(remaining)


if __name__ == "__main__":
    main()
