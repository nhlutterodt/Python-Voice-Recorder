# Widget Reference

This page describes the built-in widget types and their configuration fields. Widgets are described in dashboard JSON configs placed in `config/dashboards/`.


Widget types

- MetricWidget — shows a single metric value (sum/avg/count) for a metric name and optional tag filters.
- ChartWidget — small sparkline or bar representation of recent samples for a metric.
- AlertWidget — uses the baseline manager to show when a metric deviates beyond a threshold.
- SummaryWidget — simple aggregation summary for a metric (min/max/avg/count/sum).
- BaselineWidget — displays baseline values and deviation percentages.

Common widget fields

- `type` or `widget_type` (string) — one of the widget types above (implementations accept either key for backward compatibility).
- `title` (string) — human-friendly label shown in renderers.
- `config` (object) — widget-specific config; see examples below.

MetricWidget example

```json
{
  "widget_type": "metric",
  "title": "Recordings Today",
  "config": {
    "metric": "recordings.count",
    "aggregation": "sum",
    "window_hours": 24,
    "tags": {"format": "wav"},
    "format": "number"
  }
}
```

Fields explained:
- `metric` — metric name to query
- `aggregation` — one of `sum`, `avg`, `count`, `min`, `max`
- `window_hours` — time window for aggregation
- `tags` — optional tag filters (must match all specified tags)
- `format` — presentation format (`number`, `percent`, `duration`)

ChartWidget example (sparkline)

```json
{
  "widget_type": "chart",
  "title": "CPU Usage (24h)",
  "config": {
    "metric": "system.cpu.percent",
    "chart_type": "sparkline",
    "window_hours": 24,
    "resolution": 24
  }
}
```

AlertWidget example

```json
{
  "widget_type": "alert",
  "title": "High Latency Alerts",
  "config": {
    "metric": "request.latency_ms",
    "severity": "warning",
    "lookback_hours": 1
  }
}
```

SummaryWidget example

```json
{
  "widget_type": "summary",
  "title": "Recording Size Summary",
  "config": {
    "metric": "recording.size_kb",
    "aggregations": ["min", "max", "avg", "sum"],
    "window_hours": 168
  }
}
```

BaselineWidget example

```json
{
  "widget_type": "baseline",
  "title": "Processing Time vs Baseline",
  "config": {
    "metric": "processing.time_ms",
    "window_hours": 24
  }
}
```

Where to add widgets

Place or edit dashboard JSON files under `config/dashboards/`. Each dashboard is an array of widgets under the `widgets` key. The dashboard loader uses the filename (without extension) as the dashboard id.

Sample outputs (TextRenderer)

- MetricWidget

```text
Recordings Today
-----------------
12
```

- ChartWidget (sparkline)

```text
CPU Usage (24h)
----------------
▂▃▅▇▆▅▃▂
```

- AlertWidget

```text
High Latency Alerts
--------------------
1 warning: request.latency_ms current=350.00ms baseline=120.00ms deviation=+191.7%
```

- SummaryWidget

```text
Recording Size Summary (7d)
---------------------------
min: 45 KB
max: 1200 KB
avg: 210.5 KB
sum: 12500 KB
```

- BaselineWidget

```text
Processing Time vs Baseline
---------------------------
current: 250ms
baseline (median): 100ms
deviation: +150% (CRITICAL)
```

