# Metrics Aggregator — Public API

This document summarizes the public API for `core/metrics_aggregator.py` and shows quick examples.

Public functions and classes

- `MetricSnapshot` — dataclass representing a single metric sample
- `MetricQuery` — dataclass used to query metrics
- `MetricsAggregator` — main class (use `get_metrics_aggregator()` to obtain singleton)
- Convenience functions: `record_counter`, `record_gauge`, `record_histogram`

Examples

```python
from core.metrics_aggregator import record_counter, record_gauge, get_metrics_aggregator, MetricQuery

record_counter("recording.started", increment=1)
record_gauge("memory.usage", 123.0, tags={"unit": "mb"})

agg = get_metrics_aggregator()
q = MetricQuery(metric_name="memory.usage", limit=10)
samples = agg.query_metrics(q)
print(samples)
```

Notes
- The module stores samples in SQLite by default (or in-memory if no db path provided).
- Timestamps use local system time. Some sqlite3 datetime adapter warnings may appear on Python 3.12+ but are non-blocking.
