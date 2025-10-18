from datetime import datetime

from core.metrics_aggregator import MetricsAggregator, MetricSnapshot, MetricType, MetricQuery


def test_datetime_roundtrip_in_memory_db():
    # Create a fresh aggregator with its own in-memory DB
    agg = MetricsAggregator(db_path=None)

    ts = datetime.now().replace(microsecond=0)
    snap = MetricSnapshot(metric_type=MetricType.GAUGE, name="test.datetime", value=1.23, timestamp=ts)
    agg.record_metric(snap)

    # Query back the metric and verify timestamp is a datetime and matches (iso precision)
    q = MetricQuery(metric_name="test.datetime", limit=10)
    results = agg.query_metrics(q)
    assert len(results) >= 1
    r = results[0]
    assert isinstance(r.timestamp, datetime), f"timestamp is not datetime: {type(r.timestamp)}"
    # Compare isoformat strings to avoid tiny timezone/precision differences
    assert r.timestamp.replace(microsecond=0).isoformat() == ts.isoformat()


