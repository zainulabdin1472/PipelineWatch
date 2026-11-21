# Plug AirPulse or DeployLens into PipelineWatch

PipelineWatch already graphs any series that uses these names:

| Metric | Type | Label |
|---|---|---|
| `pipeline_last_run_duration_seconds` | gauge | `pipeline` |
| `pipeline_run_duration_seconds` | histogram | `pipeline` |
| `pipeline_rows_processed_total` | counter | `pipeline` |
| `pipeline_last_success_timestamp_seconds` | gauge | `pipeline` |
| `pipeline_failures_total` | counter | `pipeline` |
| `pipeline_runs_total` | counter | `pipeline`, `status` (`success` or `failure`) |
| `pipeline_up` | gauge | `pipeline` |

Set the `pipeline` label to `airpulse` or `deploylens`. The provisioned dashboards split series on that label, and the Prometheus rules page per series.

## While the real service is not exporting yet

From this directory:

```bash
pip install -r requirements.txt
python metrics_example.py --pipeline airpulse --port 9101
python metrics_example.py --pipeline deploylens --port 9102
```

## Scrape job

Prometheus runs in Docker, so a process on the host is `host.docker.internal`. Uncomment the matching block in `prometheus/prometheus.yml`:

```yaml
  - job_name: airpulse
    static_configs:
      - targets: ["host.docker.internal:9101"]

  - job_name: deploylens
    static_configs:
      - targets: ["host.docker.internal:9102"]
```

Then reload:

```bash
docker compose up -d prometheus
```

If the service is another compose container on the `pipelinewatch` network, use its service DNS name instead of `host.docker.internal`.

Ship its logs by writing them to the `pipeline-logs` volume, or add a Promtail `static_configs` path next to the demo job in `promtail/promtail-config.yml`. Use a `container` label so the Logs dashboard can filter on it.
