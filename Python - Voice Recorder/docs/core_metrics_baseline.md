# Metrics Baseline — Public API

Summary of `core/metrics_baseline.py`:

- `BaselineConfig` — configuration for baseline calculation
- `BaselineStats` — stats object returned by calculations
- `BaselineManager` — class with `calculate_baseline`, `check_deviation`, and other helpers
- Convenience functions: `calculate_baseline`, `check_deviation`, `get_baseline_manager`

Quick Example

```python
from core.metrics_baseline import calculate_baseline, check_deviation

baseline = calculate_baseline("request.latency_ms", window_hours=24)
alert = check_deviation("request.latency_ms", current_value=250.0)
if alert:
    print(alert.message)
```

Notes
- Baselines persist to `baselines.json` by default in the working directory.
- Baseline calculation requires sufficient historical data (configurable via `min_data_points`).
