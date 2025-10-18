"""
Tests for metrics aggregation.

Test coverage:
- Counter operations (increment, sum)
- Gauge operations (set, latest, average)
- Histogram operations (record, percentiles)
- Time-range queries
- Tag filtering
- Aggregation functions (sum, avg, percentiles)
- Database persistence
- Edge cases (empty data, invalid queries)
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from core.metrics_aggregator import (
    MetricsAggregator,
    MetricSnapshot,
    MetricType,
    MetricQuery,
    get_metrics_aggregator,
    record_counter,
    record_gauge,
    record_histogram,
)


class TestCounterOperations:
    """Test counter metric operations."""
    
    def setup_method(self):
        """Create fresh in-memory aggregator for each test."""
        self.aggregator = MetricsAggregator()
    
    def teardown_method(self):
        """Close aggregator after each test."""
        self.aggregator.close()
    
    def test_record_counter_increments(self):
        """Counter increments by default value of 1.0."""
        self.aggregator.record_counter("recordings.started")
        self.aggregator.record_counter("recordings.started")
        
        total = self.aggregator.calculate_sum("recordings.started")
        assert total == 2.0
    
    def test_record_counter_custom_increment(self):
        """Counter increments by custom value."""
        self.aggregator.record_counter("bytes.sent", increment=1024.0)
        self.aggregator.record_counter("bytes.sent", increment=2048.0)
        
        total = self.aggregator.calculate_sum("bytes.sent")
        assert total == 3072.0
    
    def test_counter_with_tags(self):
        """Counter can be filtered by tags."""
        self.aggregator.record_counter("errors", tags={"type": "network"})
        self.aggregator.record_counter("errors", tags={"type": "disk"})
        self.aggregator.record_counter("errors", tags={"type": "network"})
        
        network_errors = self.aggregator.calculate_sum(
            "errors",
            tags={"type": "network"}
        )
        assert network_errors == 2.0
        
        disk_errors = self.aggregator.calculate_sum(
            "errors",
            tags={"type": "disk"}
        )
        assert disk_errors == 1.0
    
    def test_counter_query_returns_all_increments(self):
        """Query returns all counter increment records."""
        self.aggregator.record_counter("api.requests", increment=1.0)
        self.aggregator.record_counter("api.requests", increment=1.0)
        self.aggregator.record_counter("api.requests", increment=1.0)
        
        query = MetricQuery(metric_name="api.requests")
        snapshots = self.aggregator.query_metrics(query)
        
        assert len(snapshots) == 3
        assert all(s.metric_type == MetricType.COUNTER for s in snapshots)
        assert all(s.value == 1.0 for s in snapshots)


class TestGaugeOperations:
    """Test gauge metric operations."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
    
    def teardown_method(self):
        self.aggregator.close()
    
    def test_record_gauge_value(self):
        """Gauge records current value snapshot."""
        self.aggregator.record_gauge("memory.usage", 1024.0)
        
        query = MetricQuery(metric_name="memory.usage")
        metrics = self.aggregator.query_metrics(query)
        
        assert len(metrics) == 1
        assert metrics[0].value == 1024.0
        assert metrics[0].metric_type == MetricType.GAUGE
    
    def test_gauge_multiple_snapshots(self):
        """Gauge can record multiple snapshots over time."""
        self.aggregator.record_gauge("cpu.usage", 10.0)
        self.aggregator.record_gauge("cpu.usage", 20.0)
        self.aggregator.record_gauge("cpu.usage", 15.0)
        
        query = MetricQuery(metric_name="cpu.usage")
        metrics = self.aggregator.query_metrics(query)
        
        assert len(metrics) == 3
        # Most recent first (DESC order)
        assert metrics[0].value == 15.0
        assert metrics[1].value == 20.0
        assert metrics[2].value == 10.0
    
    def test_gauge_average_over_time(self):
        """Gauge can calculate average over time period."""
        self.aggregator.record_gauge("temperature", 10.0)
        self.aggregator.record_gauge("temperature", 20.0)
        self.aggregator.record_gauge("temperature", 30.0)
        
        avg = self.aggregator.calculate_average("temperature")
        assert avg == 20.0
    
    def test_gauge_with_tags(self):
        """Gauge supports tag filtering."""
        self.aggregator.record_gauge("memory.usage", 100.0, tags={"process": "audio"})
        self.aggregator.record_gauge("memory.usage", 200.0, tags={"process": "ui"})
        
        audio_avg = self.aggregator.calculate_average(
            "memory.usage",
            tags={"process": "audio"}
        )
        assert audio_avg == 100.0


class TestHistogramOperations:
    """Test histogram metric operations."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
    
    def teardown_method(self):
        self.aggregator.close()
    
    def test_histogram_records_values(self):
        """Histogram records distribution of values."""
        values = [10, 20, 30, 40, 50]
        for value in values:
            self.aggregator.record_histogram("request.duration", float(value))
        
        query = MetricQuery(metric_name="request.duration")
        snapshots = self.aggregator.query_metrics(query)
        
        assert len(snapshots) == 5
        assert all(s.metric_type == MetricType.HISTOGRAM for s in snapshots)
    
    def test_histogram_percentiles(self):
        """Histogram calculates percentiles correctly."""
        # Record 0-99 (100 values)
        for i in range(100):
            self.aggregator.record_histogram("latency", float(i))
        
        percentiles = self.aggregator.calculate_percentiles(
            "latency",
            percentiles=[50, 95, 99]
        )
        
        # p50 should be around 49.5 (median of 0-99)
        assert 45 <= percentiles[50] <= 55
        
        # p95 should be around 94
        assert 90 <= percentiles[95] <= 96
        
        # p99 should be around 98
        assert 97 <= percentiles[99] <= 99
    
    def test_histogram_single_value(self):
        """Histogram handles single value correctly."""
        self.aggregator.record_histogram("single", 42.0)
        
        percentiles = self.aggregator.calculate_percentiles(
            "single",
            percentiles=[50, 95, 99]
        )
        
        assert percentiles[50] == 42.0
        assert percentiles[95] == 42.0
        assert percentiles[99] == 42.0
    
    def test_histogram_empty_data(self):
        """Histogram handles empty data gracefully."""
        percentiles = self.aggregator.calculate_percentiles(
            "nonexistent.metric",
            percentiles=[50, 95, 99]
        )
        
        assert percentiles == {50: 0.0, 95: 0.0, 99: 0.0}
    
    def test_histogram_with_tags(self):
        """Histogram supports tag filtering."""
        # Fast requests
        for i in range(10):
            self.aggregator.record_histogram(
                "response.time",
                float(i),
                tags={"endpoint": "/fast"}
            )
        
        # Slow requests
        for i in range(100, 110):
            self.aggregator.record_histogram(
                "response.time",
                float(i),
                tags={"endpoint": "/slow"}
            )
        
        fast_p95 = self.aggregator.calculate_percentiles(
            "response.time",
            percentiles=[95],
            tags={"endpoint": "/fast"}
        )[95]
        
        slow_p95 = self.aggregator.calculate_percentiles(
            "response.time",
            percentiles=[95],
            tags={"endpoint": "/slow"}
        )[95]
        
        assert fast_p95 < 20
        assert slow_p95 > 100


class TestTimeRangeQueries:
    """Test time-range filtering."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
        self.now = datetime.now()
    
    def teardown_method(self):
        self.aggregator.close()
    
    def test_query_by_time_range(self):
        """Query filters metrics by time range."""
        # Record metrics at different times (we'll use actual timestamps)
        for i in range(5):
            self.aggregator.record_counter("test.metric")
        
        # Query for recent metrics (last hour)
        query = MetricQuery(
            metric_name="test.metric",
            start_time=self.now - timedelta(hours=1),
            end_time=self.now + timedelta(hours=1)
        )
        metrics = self.aggregator.query_metrics(query)
        
        # All metrics should be within range
        assert len(metrics) == 5
        for metric in metrics:
            assert query.start_time <= metric.timestamp <= query.end_time
    
    def test_query_exclude_future_metrics(self):
        """Query correctly excludes metrics outside time range."""
        self.aggregator.record_counter("test.metric")
        
        # Query for future time range (should return nothing)
        query = MetricQuery(
            metric_name="test.metric",
            start_time=self.now + timedelta(hours=1),
            end_time=self.now + timedelta(hours=2)
        )
        metrics = self.aggregator.query_metrics(query)
        
        assert len(metrics) == 0
    
    def test_calculate_sum_with_time_range(self):
        """Calculate sum respects time range."""
        # Record some metrics
        for i in range(10):
            self.aggregator.record_counter("clicks", increment=1.0)
        
        # Sum for all time
        total = self.aggregator.calculate_sum(
            "clicks",
            start_time=self.now - timedelta(hours=1),
            end_time=self.now + timedelta(hours=1)
        )
        
        assert total == 10.0


class TestTagFiltering:
    """Test tag-based filtering."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
    
    def teardown_method(self):
        self.aggregator.close()
    
    def test_filter_by_single_tag(self):
        """Query filters metrics by single tag."""
        self.aggregator.record_counter("api.requests", tags={"endpoint": "/upload"})
        self.aggregator.record_counter("api.requests", tags={"endpoint": "/download"})
        self.aggregator.record_counter("api.requests", tags={"endpoint": "/upload"})
        
        upload_count = self.aggregator.calculate_sum(
            "api.requests",
            tags={"endpoint": "/upload"}
        )
        
        assert upload_count == 2.0
    
    def test_filter_by_multiple_tags(self):
        """Query filters metrics by multiple tags (AND logic)."""
        self.aggregator.record_counter(
            "http.requests",
            tags={"method": "GET", "status": "200"}
        )
        self.aggregator.record_counter(
            "http.requests",
            tags={"method": "POST", "status": "200"}
        )
        self.aggregator.record_counter(
            "http.requests",
            tags={"method": "GET", "status": "404"}
        )
        
        get_200 = self.aggregator.calculate_sum(
            "http.requests",
            tags={"method": "GET", "status": "200"}
        )
        
        assert get_200 == 1.0
    
    def test_get_unique_tags(self):
        """Can retrieve unique tag values for metric."""
        self.aggregator.record_counter("http.requests", tags={"status": "200"})
        self.aggregator.record_counter("http.requests", tags={"status": "404"})
        self.aggregator.record_counter("http.requests", tags={"status": "500"})
        self.aggregator.record_counter("http.requests", tags={"status": "200"})
        
        tags = self.aggregator.get_tags_for_metric("http.requests")
        
        assert "status" in tags
        assert set(tags["status"]) == {"200", "404", "500"}
    
    def test_get_tags_multiple_keys(self):
        """Get unique tags with multiple tag keys."""
        self.aggregator.record_counter(
            "api.calls",
            tags={"version": "v1", "region": "us"}
        )
        self.aggregator.record_counter(
            "api.calls",
            tags={"version": "v2", "region": "eu"}
        )
        
        tags = self.aggregator.get_tags_for_metric("api.calls")
        
        assert "version" in tags
        assert "region" in tags
        assert set(tags["version"]) == {"v1", "v2"}
        assert set(tags["region"]) == {"eu", "us"}


class TestAggregationFunctions:
    """Test aggregation calculations."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
    
    def teardown_method(self):
        self.aggregator.close()
    
    def test_calculate_sum_empty_data(self):
        """Sum returns 0.0 for empty data."""
        total = self.aggregator.calculate_sum("nonexistent")
        assert total == 0.0
    
    def test_calculate_average_empty_data(self):
        """Average returns 0.0 for empty data."""
        avg = self.aggregator.calculate_average("nonexistent")
        assert avg == 0.0
    
    def test_calculate_sum_multiple_values(self):
        """Sum correctly adds multiple values."""
        self.aggregator.record_counter("total", increment=10.0)
        self.aggregator.record_counter("total", increment=20.0)
        self.aggregator.record_counter("total", increment=30.0)
        
        total = self.aggregator.calculate_sum("total")
        assert total == 60.0
    
    def test_calculate_average_multiple_values(self):
        """Average correctly computes mean."""
        self.aggregator.record_gauge("value", 10.0)
        self.aggregator.record_gauge("value", 20.0)
        self.aggregator.record_gauge("value", 30.0)
        
        avg = self.aggregator.calculate_average("value")
        assert avg == 20.0
    
    def test_get_count(self):
        """Get count returns number of data points."""
        for i in range(15):
            self.aggregator.record_counter("events")
        
        count = self.aggregator.get_count("events")
        assert count == 15


class TestMetricQueries:
    """Test query functionality."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
    
    def teardown_method(self):
        self.aggregator.close()
    
    def test_query_with_limit(self):
        """Query respects limit parameter."""
        for i in range(100):
            self.aggregator.record_counter("many")
        
        query = MetricQuery(metric_name="many", limit=10)
        metrics = self.aggregator.query_metrics(query)
        
        assert len(metrics) == 10
    
    def test_query_no_limit(self):
        """Query with limit=0 returns all results."""
        for i in range(50):
            self.aggregator.record_counter("many")
        
        query = MetricQuery(metric_name="many", limit=0)
        metrics = self.aggregator.query_metrics(query)
        
        assert len(metrics) == 50
    
    def test_query_by_metric_type(self):
        """Query filters by metric type."""
        self.aggregator.record_counter("metric")
        self.aggregator.record_gauge("metric", 10.0)
        self.aggregator.record_histogram("metric", 20.0)
        
        query = MetricQuery(metric_name="metric", metric_type=MetricType.GAUGE)
        metrics = self.aggregator.query_metrics(query)
        
        assert len(metrics) == 1
        assert metrics[0].metric_type == MetricType.GAUGE
    
    def test_get_all_metric_names(self):
        """Get all metric names returns unique sorted list."""
        self.aggregator.record_counter("zebra")
        self.aggregator.record_gauge("apple", 1.0)
        self.aggregator.record_histogram("banana", 2.0)
        self.aggregator.record_counter("zebra")  # Duplicate
        
        names = self.aggregator.get_metric_names()
        
        assert names == ["apple", "banana", "zebra"]


class TestDatabasePersistence:
    """Test database persistence."""
    
    def test_persist_to_file(self, tmp_path):
        """Metrics persist to file database."""
        db_path = tmp_path / "metrics.db"
        
        # Create aggregator, record metrics, close
        aggregator1 = MetricsAggregator(db_path)
        aggregator1.record_counter("persisted", increment=42.0)
        aggregator1.close()
        
        # Create new aggregator with same database
        aggregator2 = MetricsAggregator(db_path)
        total = aggregator2.calculate_sum("persisted")
        aggregator2.close()
        
        assert total == 42.0
    
    def test_in_memory_not_persisted(self):
        """In-memory metrics don't persist."""
        aggregator1 = MetricsAggregator()  # No path = in-memory
        aggregator1.record_counter("temporary", increment=99.0)
        aggregator1.close()
        
        aggregator2 = MetricsAggregator()  # New in-memory database
        total = aggregator2.calculate_sum("temporary")
        aggregator2.close()
        
        assert total == 0.0  # Data not persisted


class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_record_counter_convenience(self):
        """record_counter() convenience function works."""
        record_counter("test.counter", increment=5.0)
        
        aggregator = get_metrics_aggregator()
        total = aggregator.calculate_sum("test.counter")
        
        assert total == 5.0
    
    def test_record_gauge_convenience(self):
        """record_gauge() convenience function works."""
        record_gauge("test.gauge", 100.0)
        
        aggregator = get_metrics_aggregator()
        avg = aggregator.calculate_average("test.gauge")
        
        assert avg == 100.0
    
    def test_record_histogram_convenience(self):
        """record_histogram() convenience function works."""
        record_histogram("test.histogram", 50.0)
        
        aggregator = get_metrics_aggregator()
        query = MetricQuery(metric_name="test.histogram")
        metrics = aggregator.query_metrics(query)
        
        assert len(metrics) >= 1
        assert any(m.value == 50.0 for m in metrics)


class TestMetricSnapshot:
    """Test MetricSnapshot dataclass."""
    
    def test_snapshot_to_dict(self):
        """MetricSnapshot converts to dict for JSON."""
        snapshot = MetricSnapshot(
            metric_type=MetricType.COUNTER,
            name="test.metric",
            value=42.0,
            timestamp=datetime(2025, 10, 18, 12, 0, 0),
            tags={"env": "test"},
            metadata={"extra": "info"}
        )
        
        data = snapshot.to_dict()
        
        assert data["metric_type"] == "counter"
        assert data["name"] == "test.metric"
        assert data["value"] == 42.0
        assert data["timestamp"] == "2025-10-18T12:00:00"
        assert data["tags"] == {"env": "test"}
        assert data["metadata"] == {"extra": "info"}
    
    def test_snapshot_from_dict(self):
        """MetricSnapshot creates from dict (from JSON)."""
        data = {
            "metric_type": "gauge",
            "name": "test.metric",
            "value": 100.0,
            "timestamp": "2025-10-18T12:00:00",
            "tags": {"env": "prod"},
            "metadata": {"source": "api"}
        }
        
        snapshot = MetricSnapshot.from_dict(data)
        
        assert snapshot.metric_type == MetricType.GAUGE
        assert snapshot.name == "test.metric"
        assert snapshot.value == 100.0
        assert snapshot.timestamp == datetime(2025, 10, 18, 12, 0, 0)
        assert snapshot.tags == {"env": "prod"}
        assert snapshot.metadata == {"source": "api"}


class TestContextManager:
    """Test context manager interface."""
    
    def test_context_manager(self, tmp_path):
        """MetricsAggregator works as context manager."""
        db_path = tmp_path / "context.db"
        
        with MetricsAggregator(db_path) as aggregator:
            aggregator.record_counter("context.test")
            total = aggregator.calculate_sum("context.test")
            assert total == 1.0
        
        # Connection should be closed after context
        # Verify by opening new aggregator and checking data persisted
        with MetricsAggregator(db_path) as aggregator:
            total = aggregator.calculate_sum("context.test")
            assert total == 1.0
