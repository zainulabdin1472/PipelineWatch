"""Tiny exporter showing the PipelineWatch metric shape.

Copy these definitions into AirPulse or DeployLens, or run this process and
scrape it while those services are still being wired up.

    python metrics_example.py --pipeline airpulse --port 9101
    python metrics_example.py --pipeline deploylens --port 9102
"""

from __future__ import annotations

import argparse
import random
import time

from prometheus_client import Counter, Gauge, Histogram, start_http_server

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Sample pipeline exporter")
    parser.add_argument("--pipeline", required=True, choices=("airpulse", "deploylens"))
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()

    start_http_server(args.port)
    UP.labels(args.pipeline).set(1)
    FAILURES.labels(args.pipeline).inc(0)
    print(f"{args.pipeline} exporter on :{args.port}/metrics", flush=True)

    while True:
        elapsed = random.uniform(1.0, 8.0)
        time.sleep(elapsed)
        DURATION.labels(args.pipeline).set(elapsed)
        DURATION_HIST.labels(args.pipeline).observe(elapsed)
        ROWS.labels(args.pipeline).inc(random.randint(10, 200))
        RUNS.labels(args.pipeline, "success").inc()
        LAST_SUCCESS.labels(args.pipeline).set(time.time())


if __name__ == "__main__":
    main()
