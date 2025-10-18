# Task #20 Day 4: Metrics Dashboard - REVISED PLAN

**Planning Date**: October 17, 2025  
**Based On**: Pattern analysis from Days 1-3 success  
**Status**: Ready for execution

---

## 📋 Executive Summary

**Original Estimate**: 1 day  
**Pattern-Based Estimate**: 2-3 hours (based on 500% efficiency trend)  
**Confidence**: 90% (proven patterns, clear scope, strong foundation)

**What Changed from Original Plan**:
- ✅ **Focused on MVP**: Removed GUI dashboard, added CLI text dashboard
- ✅ **Simplified scope**: Deferred advanced features (real-time, Grafana, ML)
- ✅ **Privacy-first**: Added local-only metrics, no external dependencies
- ✅ **Layered approach**: Three clear phases matching Days 1-3 pattern

---

## 🎯 Day 4 Goals (MVP)

### Primary Objectives

1. **Metrics Aggregation** (~1 hour)
   - Collect metrics from existing telemetry (Days 1-3)
   - Store in time-series format (SQLite or in-memory)
   - Query by time range, tags, metric type

2. **Baseline Comparison** (~1 hour)
   - Calculate rolling baseline (percentiles: p50, p95, p99)
   - Detect deviations from baseline
   - Simple threshold-based alerting

3. **Simple Dashboard** (~30-45 min)
   - Text-based CLI dashboard
   - Export to JSON/CSV
   - Summary statistics

4. **Documentation** (~15-30 min)
   - Metrics schema reference
   - Usage examples
   - Integration guide

---

## 🏗️ Architecture (Layered Approach)

```
┌─────────────────────────────────────────────────────┐
│              Voice Recorder Pro                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Day 4: Metrics & Dashboard Layer                  │
│  ┌───────────────────────────────────────────────┐ │
│  │  MetricsDashboard (CLI)                       │ │
│  │  - Display current metrics                    │ │
│  │  - Show deviations from baseline              │ │
│  │  - Export to JSON/CSV                         │ │
│  └───────────────────────────────────────────────┘ │
│                       │                             │
│                       ▼                             │
│  ┌───────────────────────────────────────────────┐ │
│  │  MetricsBaseline                              │ │
│  │  - Calculate rolling baseline                 │ │
│  │  - Detect deviations (threshold-based)        │ │
│  │  - Generate alerts                            │ │
│  └───────────────────────────────────────────────┘ │
│                       │                             │
│                       ▼                             │
│  ┌───────────────────────────────────────────────┐ │
│  │  MetricsAggregator                            │ │
│  │  - Collect metrics from telemetry             │ │
│  │  - Store in time-series format                │ │
│  │  - Query by time/tags                         │ │
│  └───────────────────────────────────────────────┘ │
│                       │                             │
└───────────────────────┼─────────────────────────────┘
                        │
                        ▼
         ┌──────────────────────────────┐
         │  Days 1-3 Telemetry          │
         │  - StructuredLogger (Day 1)  │
         │  - PerformanceTimer (Day 1)  │
         │  - ErrorBoundaries (Day 3)   │
         └──────────────────────────────┘
```

---

## 📦 Phase 1: Metrics Aggregation (~1 hour)

### Goal
Collect and aggregate metrics from existing telemetry infrastructure.

### Files to Create

#### `core/metrics_aggregator.py` (250-300 lines)

```python
"""
Metrics aggregation and time-series storage.

Collects metrics from Days 1-3 telemetry and provides
query interface for dashboard and baseline calculation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from statistics import mean, median, stdev
import sqlite3
from pathlib import Path


class MetricType(Enum):
    """Type of metric collected."""
    COUNTER = "counter"       # Incremental (recording starts, errors)
    GAUGE = "gauge"           # Current value (memory, active sessions)
    HISTOGRAM = "histogram"   # Distribution (request durations)
    SUMMARY = "summary"       # Percentiles (p50, p95, p99)


@dataclass
class MetricSnapshot:
    """Single metric measurement at a point in time."""
    metric_type: MetricType
    name: str                 # e.g., "recording.duration"
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricQuery:
    """Query parameters for fetching metrics."""
    metric_name: Optional[str] = None
    metric_type: Optional[MetricType] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tags: Dict[str, str] = field(default_factory=dict)
    limit: int = 1000


class MetricsAggregator:
    """
    Aggregates metrics from telemetry and provides query interface.
    
    Features:
    - Collects metrics from structured logging, performance timers, error boundaries
    - Stores in SQLite time-series database
    - Supports counters, gauges, histograms, summaries
    - Query by time range, tags, metric type
    - Calculate aggregates (sum, avg, percentiles)
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize metrics aggregator.
        
        Args:
            db_path: Path to SQLite database (None = in-memory)
        """
        self.db_path = db_path or ":memory:"
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize SQLite schema for metrics storage."""
        # CREATE TABLE metrics (...);
        # CREATE INDEX idx_metrics_timestamp ON metrics(timestamp);
        # CREATE INDEX idx_metrics_name ON metrics(name);
        pass
    
    def record_metric(self, snapshot: MetricSnapshot) -> None:
        """
        Record a single metric snapshot.
        
        Args:
            snapshot: Metric measurement to record
        """
        pass
    
    def record_counter(self, name: str, increment: float = 1.0,
                      tags: Optional[Dict[str, str]] = None) -> None:
        """Record counter increment (e.g., recording started)."""
        pass
    
    def record_gauge(self, name: str, value: float,
                    tags: Optional[Dict[str, str]] = None) -> None:
        """Record gauge value (e.g., memory usage)."""
        pass
    
    def record_histogram(self, name: str, value: float,
                        tags: Optional[Dict[str, str]] = None) -> None:
        """Record histogram value (e.g., request duration)."""
        pass
    
    def query_metrics(self, query: MetricQuery) -> List[MetricSnapshot]:
        """
        Query metrics from storage.
        
        Args:
            query: Query parameters
            
        Returns:
            List of matching metric snapshots
        """
        pass
    
    def calculate_sum(self, metric_name: str,
                     start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None,
                     tags: Optional[Dict[str, str]] = None) -> float:
        """Calculate sum of metric values in time range."""
        pass
    
    def calculate_average(self, metric_name: str,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         tags: Optional[Dict[str, str]] = None) -> float:
        """Calculate average of metric values in time range."""
        pass
    
    def calculate_percentiles(self, metric_name: str,
                             percentiles: List[float] = [50, 95, 99],
                             start_time: Optional[datetime] = None,
                             end_time: Optional[datetime] = None,
                             tags: Optional[Dict[str, str]] = None) -> Dict[float, float]:
        """
        Calculate percentiles of metric values.
        
        Args:
            metric_name: Name of metric
            percentiles: List of percentiles to calculate (0-100)
            start_time: Start of time range
            end_time: End of time range
            tags: Tag filters
            
        Returns:
            Dict mapping percentile to value (e.g., {50: 10.5, 95: 25.3})
        """
        pass
    
    def get_metric_names(self) -> List[str]:
        """Get list of all metric names in storage."""
        pass
    
    def get_tags_for_metric(self, metric_name: str) -> Dict[str, List[str]]:
        """Get all unique tag values for a metric."""
        pass


# Global singleton instance
_metrics_aggregator: Optional[MetricsAggregator] = None


def get_metrics_aggregator() -> MetricsAggregator:
    """Get global metrics aggregator instance."""
    global _metrics_aggregator
    if _metrics_aggregator is None:
        _metrics_aggregator = MetricsAggregator()
    return _metrics_aggregator


def record_counter(name: str, increment: float = 1.0,
                  tags: Optional[Dict[str, str]] = None) -> None:
    """Convenience function to record counter."""
    get_metrics_aggregator().record_counter(name, increment, tags)


def record_gauge(name: str, value: float,
                tags: Optional[Dict[str, str]] = None) -> None:
    """Convenience function to record gauge."""
    get_metrics_aggregator().record_gauge(name, value, tags)


def record_histogram(name: str, value: float,
                    tags: Optional[Dict[str, str]] = None) -> None:
    """Convenience function to record histogram."""
    get_metrics_aggregator().record_histogram(name, value, tags)
```

#### `tests/test_metrics_aggregator.py` (250-300 lines, ~20 tests)

```python
"""
Tests for metrics aggregation.

Test coverage:
- Counter operations (increment, sum)
- Gauge operations (set, latest)
- Histogram operations (record, percentiles)
- Time-range queries
- Tag filtering
- Aggregation functions (sum, avg, percentiles)
- Edge cases (empty data, invalid queries)
"""

import pytest
from datetime import datetime, timedelta
from core.metrics_aggregator import (
    MetricsAggregator,
    MetricSnapshot,
    MetricType,
    MetricQuery,
)


class TestCounterOperations:
    """Test counter metric operations."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
    
    def test_record_counter_increments(self):
        """Counter increments by default value."""
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
        
        network_errors = self.aggregator.calculate_sum(
            "errors",
            tags={"type": "network"}
        )
        assert network_errors == 1.0


class TestGaugeOperations:
    """Test gauge metric operations."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
    
    def test_record_gauge_value(self):
        """Gauge records current value."""
        self.aggregator.record_gauge("memory.usage", 1024.0)
        
        query = MetricQuery(metric_name="memory.usage")
        metrics = self.aggregator.query_metrics(query)
        
        assert len(metrics) == 1
        assert metrics[0].value == 1024.0
    
    def test_gauge_average_over_time(self):
        """Gauge can calculate average over time."""
        self.aggregator.record_gauge("cpu.usage", 10.0)
        self.aggregator.record_gauge("cpu.usage", 20.0)
        self.aggregator.record_gauge("cpu.usage", 30.0)
        
        avg = self.aggregator.calculate_average("cpu.usage")
        assert avg == 20.0


class TestHistogramOperations:
    """Test histogram metric operations."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
    
    def test_histogram_percentiles(self):
        """Histogram calculates percentiles correctly."""
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for value in values:
            self.aggregator.record_histogram("request.duration", value)
        
        percentiles = self.aggregator.calculate_percentiles(
            "request.duration",
            percentiles=[50, 95, 99]
        )
        
        assert percentiles[50] == pytest.approx(50, abs=5)
        assert percentiles[95] >= 90
    
    def test_histogram_empty_data(self):
        """Histogram handles empty data gracefully."""
        percentiles = self.aggregator.calculate_percentiles(
            "nonexistent.metric",
            percentiles=[50, 95, 99]
        )
        
        assert percentiles == {50: 0.0, 95: 0.0, 99: 0.0}


class TestTimeRangeQueries:
    """Test time-range filtering."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
    
    def test_query_by_time_range(self):
        """Query filters metrics by time range."""
        now = datetime.now()
        
        # Record metrics at different times (mock timestamps)
        # ...
        
        query = MetricQuery(
            metric_name="test.metric",
            start_time=now - timedelta(hours=1),
            end_time=now
        )
        metrics = self.aggregator.query_metrics(query)
        
        assert len(metrics) > 0
        for metric in metrics:
            assert query.start_time <= metric.timestamp <= query.end_time


class TestTagFiltering:
    """Test tag-based filtering."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
    
    def test_filter_by_tags(self):
        """Query filters metrics by tags."""
        self.aggregator.record_counter("api.requests", tags={"endpoint": "/upload"})
        self.aggregator.record_counter("api.requests", tags={"endpoint": "/download"})
        
        upload_requests = self.aggregator.calculate_sum(
            "api.requests",
            tags={"endpoint": "/upload"}
        )
        
        assert upload_requests == 1.0
    
    def test_get_unique_tags(self):
        """Can retrieve unique tag values for metric."""
        self.aggregator.record_counter("http.requests", tags={"status": "200"})
        self.aggregator.record_counter("http.requests", tags={"status": "404"})
        self.aggregator.record_counter("http.requests", tags={"status": "500"})
        
        tags = self.aggregator.get_tags_for_metric("http.requests")
        
        assert "status" in tags
        assert set(tags["status"]) == {"200", "404", "500"}
```

### Success Criteria (Phase 1)

- ✅ Can record counters, gauges, histograms
- ✅ Can query metrics by time range and tags
- ✅ Can calculate sum, average, percentiles
- ✅ 20/20 tests passing (100%)
- ✅ Integrates with existing telemetry (Days 1-3)

---

## 📦 Phase 2: Baseline Comparison (~1 hour)

### Goal
Calculate baselines and detect deviations for alerting.

### Files to Create

#### `core/metrics_baseline.py` (150-200 lines)

```python
"""
Metrics baseline calculation and deviation detection.

Calculates rolling baselines from historical metrics and
detects when current metrics deviate significantly.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from statistics import mean, stdev

from core.metrics_aggregator import MetricsAggregator, get_metrics_aggregator
from core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class BaselineConfig:
    """Configuration for baseline calculation."""
    window_days: int = 7              # Baseline window (7 days default)
    min_data_points: int = 10         # Minimum data points for baseline
    deviation_threshold_percent: float = 20.0  # Alert if >20% deviation
    percentile_for_baseline: float = 95.0  # Use p95 as baseline


@dataclass
class Baseline:
    """Calculated baseline for a metric."""
    metric_name: str
    baseline_value: float             # p50 or p95 value
    calculated_at: datetime
    data_points: int                  # Number of samples in baseline
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class DeviationAlert:
    """Alert when metric deviates from baseline."""
    metric_name: str
    current_value: float
    baseline_value: float
    deviation_percent: float
    severity: str                     # "info", "warning", "critical"
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsBaseline:
    """
    Manages baseline calculation and deviation detection.
    
    Features:
    - Calculate rolling baseline from historical data
    - Support for percentile-based baselines (p50, p95, p99)
    - Detect deviations beyond threshold
    - Generate alerts for significant deviations
    - Update baselines periodically
    """
    
    def __init__(self, 
                 aggregator: Optional[MetricsAggregator] = None,
                 config: Optional[BaselineConfig] = None):
        """
        Initialize baseline manager.
        
        Args:
            aggregator: Metrics aggregator (uses global if None)
            config: Baseline configuration
        """
        self.aggregator = aggregator or get_metrics_aggregator()
        self.config = config or BaselineConfig()
        self._baselines: Dict[str, Baseline] = {}
    
    def calculate_baseline(self, metric_name: str,
                          tags: Optional[Dict[str, str]] = None) -> Optional[Baseline]:
        """
        Calculate baseline for metric using historical data.
        
        Args:
            metric_name: Name of metric
            tags: Tag filters
            
        Returns:
            Baseline if sufficient data, None otherwise
        """
        # 1. Query historical data (window_days)
        # 2. Calculate percentile (config.percentile_for_baseline)
        # 3. Return Baseline object
        pass
    
    def update_baselines(self, metric_names: Optional[List[str]] = None) -> None:
        """
        Update baselines for specified metrics (or all metrics).
        
        Args:
            metric_names: List of metrics to update (None = all)
        """
        pass
    
    def get_baseline(self, metric_name: str,
                    tags: Optional[Dict[str, str]] = None) -> Optional[Baseline]:
        """
        Get cached baseline for metric.
        
        Args:
            metric_name: Name of metric
            tags: Tag filters
            
        Returns:
            Cached baseline or None
        """
        pass
    
    def check_deviation(self, metric_name: str, current_value: float,
                       tags: Optional[Dict[str, str]] = None) -> Optional[DeviationAlert]:
        """
        Check if current value deviates from baseline.
        
        Args:
            metric_name: Name of metric
            current_value: Current metric value
            tags: Tag filters
            
        Returns:
            DeviationAlert if deviation exceeds threshold, None otherwise
        """
        # 1. Get baseline for metric
        # 2. Calculate deviation percent
        # 3. Determine severity (info/warning/critical)
        # 4. Return alert if threshold exceeded
        pass
    
    def get_deviation_percent(self, current_value: float, baseline_value: float) -> float:
        """Calculate percentage deviation from baseline."""
        if baseline_value == 0:
            return 0.0
        return abs((current_value - baseline_value) / baseline_value) * 100.0
    
    def get_severity(self, deviation_percent: float) -> str:
        """Determine alert severity based on deviation."""
        if deviation_percent >= 50:
            return "critical"
        elif deviation_percent >= self.config.deviation_threshold_percent:
            return "warning"
        else:
            return "info"


# Global singleton
_metrics_baseline: Optional[MetricsBaseline] = None


def get_metrics_baseline() -> MetricsBaseline:
    """Get global metrics baseline instance."""
    global _metrics_baseline
    if _metrics_baseline is None:
        _metrics_baseline = MetricsBaseline()
    return _metrics_baseline
```

#### `tests/test_metrics_baseline.py` (150-200 lines, ~15 tests)

```python
"""
Tests for metrics baseline calculation.

Test coverage:
- Baseline calculation (percentiles)
- Deviation detection (threshold-based)
- Alert severity classification
- Baseline updates
- Edge cases (insufficient data, zero baseline)
"""

import pytest
from datetime import datetime, timedelta
from core.metrics_baseline import (
    MetricsBaseline,
    Baseline,
    BaselineConfig,
    DeviationAlert,
)
from core.metrics_aggregator import MetricsAggregator


class TestBaselineCalculation:
    """Test baseline calculation."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
        self.baseline_mgr = MetricsBaseline(self.aggregator)
    
    def test_calculate_baseline_from_historical_data(self):
        """Baseline calculated from historical percentile."""
        # Record historical data
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for value in values:
            self.aggregator.record_histogram("request.duration", value)
        
        # Calculate baseline (p95)
        baseline = self.baseline_mgr.calculate_baseline("request.duration")
        
        assert baseline is not None
        assert baseline.baseline_value >= 90  # p95 should be near top
        assert baseline.data_points == 10
    
    def test_baseline_requires_minimum_data_points(self):
        """Baseline not calculated if insufficient data."""
        # Only 5 data points (min is 10)
        for i in range(5):
            self.aggregator.record_histogram("test.metric", float(i))
        
        baseline = self.baseline_mgr.calculate_baseline("test.metric")
        
        assert baseline is None  # Insufficient data


class TestDeviationDetection:
    """Test deviation detection."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
        config = BaselineConfig(deviation_threshold_percent=20.0)
        self.baseline_mgr = MetricsBaseline(self.aggregator, config)
        
        # Create baseline data
        for i in range(100):
            self.aggregator.record_histogram("response.time", 100.0)
        self.baseline_mgr.update_baselines(["response.time"])
    
    def test_detect_deviation_above_threshold(self):
        """Deviation detected when value exceeds threshold."""
        # Current value 150ms, baseline 100ms = 50% deviation
        alert = self.baseline_mgr.check_deviation("response.time", 150.0)
        
        assert alert is not None
        assert alert.deviation_percent == pytest.approx(50.0, abs=1.0)
        assert alert.severity == "critical"  # >50% deviation
    
    def test_no_deviation_within_threshold(self):
        """No deviation if within threshold."""
        # Current value 110ms, baseline 100ms = 10% deviation (< 20% threshold)
        alert = self.baseline_mgr.check_deviation("response.time", 110.0)
        
        assert alert is None  # Within threshold
    
    def test_deviation_severity_classification(self):
        """Alert severity based on deviation magnitude."""
        # 30% deviation = warning
        alert = self.baseline_mgr.check_deviation("response.time", 130.0)
        assert alert.severity == "warning"
        
        # 60% deviation = critical
        alert = self.baseline_mgr.check_deviation("response.time", 160.0)
        assert alert.severity == "critical"


class TestBaselineUpdates:
    """Test baseline update logic."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
        self.baseline_mgr = MetricsBaseline(self.aggregator)
    
    def test_update_baselines_for_all_metrics(self):
        """Update baselines for all metrics."""
        # Record data for multiple metrics
        for i in range(20):
            self.aggregator.record_histogram("metric.a", float(i))
            self.aggregator.record_histogram("metric.b", float(i * 2))
        
        # Update all baselines
        self.baseline_mgr.update_baselines()
        
        baseline_a = self.baseline_mgr.get_baseline("metric.a")
        baseline_b = self.baseline_mgr.get_baseline("metric.b")
        
        assert baseline_a is not None
        assert baseline_b is not None
        assert baseline_b.baseline_value > baseline_a.baseline_value
```

### Success Criteria (Phase 2)

- ✅ Can calculate baseline from historical data
- ✅ Can detect deviations beyond threshold
- ✅ Can classify alert severity
- ✅ 15/15 tests passing (100%)
- ✅ Integrates with Phase 1 aggregator

---

## 📦 Phase 3: Simple Dashboard (~30-45 min)

### Goal
Provide text-based CLI dashboard for viewing metrics.

### Files to Create

#### `core/metrics_dashboard.py` (100-150 lines)

```python
"""
Metrics dashboard - CLI text-based view.

Displays current metrics, baselines, and deviations
in a simple, readable format.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import csv
from pathlib import Path

from core.metrics_aggregator import MetricsAggregator, get_metrics_aggregator
from core.metrics_baseline import MetricsBaseline, get_metrics_baseline
from core.logging_config import get_logger

logger = get_logger(__name__)


class MetricsDashboard:
    """
    Simple text-based metrics dashboard.
    
    Features:
    - Display current metrics
    - Show baselines and deviations
    - Export to JSON/CSV
    - Summary statistics
    """
    
    def __init__(self,
                 aggregator: Optional[MetricsAggregator] = None,
                 baseline_mgr: Optional[MetricsBaseline] = None):
        """
        Initialize dashboard.
        
        Args:
            aggregator: Metrics aggregator
            baseline_mgr: Baseline manager
        """
        self.aggregator = aggregator or get_metrics_aggregator()
        self.baseline_mgr = baseline_mgr or get_metrics_baseline()
    
    def display_summary(self, hours: int = 24) -> str:
        """
        Display metrics summary for last N hours.
        
        Args:
            hours: Time window in hours
            
        Returns:
            Formatted text summary
        """
        # 1. Get all metric names
        # 2. For each metric:
        #    - Calculate current stats (count, avg, p95)
        #    - Get baseline if available
        #    - Calculate deviation
        # 3. Format as text table
        pass
    
    def display_metric_detail(self, metric_name: str, hours: int = 24) -> str:
        """
        Display detailed view of single metric.
        
        Args:
            metric_name: Name of metric to display
            hours: Time window in hours
            
        Returns:
            Formatted text detail
        """
        pass
    
    def display_alerts(self) -> str:
        """
        Display active deviation alerts.
        
        Returns:
            Formatted text list of alerts
        """
        pass
    
    def export_to_json(self, output_path: Path, hours: int = 24) -> None:
        """
        Export metrics to JSON file.
        
        Args:
            output_path: Output file path
            hours: Time window in hours
        """
        pass
    
    def export_to_csv(self, output_path: Path, hours: int = 24) -> None:
        """
        Export metrics to CSV file.
        
        Args:
            output_path: Output file path
            hours: Time window in hours
        """
        pass
    
    def get_summary_stats(self, hours: int = 24) -> Dict:
        """
        Get summary statistics as dict (for JSON export).
        
        Returns:
            Dict with structure:
            {
                "generated_at": "2025-10-17T10:30:00",
                "time_window_hours": 24,
                "metrics": {
                    "metric.name": {
                        "count": 100,
                        "average": 50.5,
                        "p50": 50.0,
                        "p95": 95.0,
                        "p99": 99.0,
                        "baseline": 48.0,
                        "deviation_percent": 5.2
                    },
                    ...
                },
                "alerts": [...]
            }
        """
        pass


# Convenience functions
def display_dashboard(hours: int = 24) -> None:
    """Print dashboard to console."""
    dashboard = MetricsDashboard()
    print(dashboard.display_summary(hours))


def display_metric(metric_name: str, hours: int = 24) -> None:
    """Print metric detail to console."""
    dashboard = MetricsDashboard()
    print(dashboard.display_metric_detail(metric_name, hours))


def export_metrics_json(output_path: Path, hours: int = 24) -> None:
    """Export metrics to JSON file."""
    dashboard = MetricsDashboard()
    dashboard.export_to_json(output_path, hours)


def export_metrics_csv(output_path: Path, hours: int = 24) -> None:
    """Export metrics to CSV file."""
    dashboard = MetricsDashboard()
    dashboard.export_to_csv(output_path, hours)
```

#### `tests/test_metrics_dashboard.py` (100-150 lines, ~10 tests)

```python
"""
Tests for metrics dashboard.

Test coverage:
- Summary display
- Metric detail display
- Alert display
- JSON export
- CSV export
- Summary statistics calculation
"""

import pytest
from pathlib import Path
import json
import csv
from datetime import datetime, timedelta

from core.metrics_dashboard import MetricsDashboard
from core.metrics_aggregator import MetricsAggregator
from core.metrics_baseline import MetricsBaseline


class TestDashboardDisplay:
    """Test dashboard text display."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
        self.baseline_mgr = MetricsBaseline(self.aggregator)
        self.dashboard = MetricsDashboard(self.aggregator, self.baseline_mgr)
        
        # Add sample data
        for i in range(10):
            self.aggregator.record_histogram("test.metric", float(i * 10))
    
    def test_display_summary(self):
        """Summary displays all metrics."""
        summary = self.dashboard.display_summary(hours=24)
        
        assert "test.metric" in summary
        assert "count" in summary.lower()
        assert "average" in summary.lower()
    
    def test_display_metric_detail(self):
        """Metric detail shows full statistics."""
        detail = self.dashboard.display_metric_detail("test.metric", hours=24)
        
        assert "test.metric" in detail
        assert "p50" in detail.lower()
        assert "p95" in detail.lower()


class TestExportFormats:
    """Test export functionality."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
        self.dashboard = MetricsDashboard(self.aggregator)
        
        # Add sample data
        for i in range(10):
            self.aggregator.record_counter("api.requests", increment=1.0)
            self.aggregator.record_histogram("api.duration", float(i * 100))
    
    def test_export_to_json(self, tmp_path):
        """Export creates valid JSON file."""
        output_file = tmp_path / "metrics.json"
        self.dashboard.export_to_json(output_file, hours=24)
        
        assert output_file.exists()
        
        # Verify JSON structure
        with open(output_file) as f:
            data = json.load(f)
        
        assert "generated_at" in data
        assert "metrics" in data
        assert "api.requests" in data["metrics"]
        assert "api.duration" in data["metrics"]
    
    def test_export_to_csv(self, tmp_path):
        """Export creates valid CSV file."""
        output_file = tmp_path / "metrics.csv"
        self.dashboard.export_to_csv(output_file, hours=24)
        
        assert output_file.exists()
        
        # Verify CSV structure
        with open(output_file) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) > 0
        assert "metric_name" in rows[0]
        assert "value" in rows[0]


class TestSummaryStats:
    """Test summary statistics."""
    
    def setup_method(self):
        self.aggregator = MetricsAggregator()
        self.dashboard = MetricsDashboard(self.aggregator)
    
    def test_get_summary_stats(self):
        """Summary stats include all required fields."""
        # Add sample data
        for i in range(20):
            self.aggregator.record_histogram("response.time", float(i * 10))
        
        stats = self.dashboard.get_summary_stats(hours=24)
        
        assert "generated_at" in stats
        assert "time_window_hours" in stats
        assert stats["time_window_hours"] == 24
        assert "metrics" in stats
        assert "response.time" in stats["metrics"]
        
        metric_stats = stats["metrics"]["response.time"]
        assert "count" in metric_stats
        assert "average" in metric_stats
        assert "p50" in metric_stats
        assert "p95" in metric_stats
```

### Success Criteria (Phase 3)

- ✅ Can display summary of all metrics
- ✅ Can display detail for single metric
- ✅ Can export to JSON format
- ✅ Can export to CSV format
- ✅ 10/10 tests passing (100%)
- ✅ Integrates with Phases 1+2

---

## 📚 Phase 4: Documentation (~15-30 min)

### Files to Create/Update

#### `docs/TASK20_DAY4_COMPLETE.md`

```markdown
# Task #20 Day 4: Metrics Dashboard - COMPLETE

## Overview
Day 4 delivered metrics aggregation, baseline comparison, and a simple CLI dashboard.

## Features Implemented
1. Metrics Aggregation (counters, gauges, histograms)
2. Baseline Calculation (rolling window, percentiles)
3. Deviation Detection (threshold-based alerting)
4. CLI Dashboard (text-based display)
5. Export (JSON, CSV)

## Usage Examples
[Include code examples from implementation]

## Metrics Schema
[Document MetricType, MetricSnapshot, etc.]

## Integration Guide
[How to add metrics to existing code]
```

---

## ✅ Success Criteria (Overall Day 4)

### Functional Requirements

- ✅ **Metrics Aggregation**
  - Can record counters, gauges, histograms
  - Can query by time range and tags
  - Can calculate sum, average, percentiles

- ✅ **Baseline Comparison**
  - Can calculate baseline from historical data
  - Can detect deviations beyond threshold
  - Can generate alerts with severity levels

- ✅ **Dashboard**
  - Can display summary of all metrics
  - Can display detail for single metric
  - Can export to JSON and CSV

### Quality Requirements

- ✅ **Test Coverage**: 45/45 tests passing (100%)
- ✅ **Documentation**: Complete usage guide
- ✅ **Integration**: Works with Days 1-3 telemetry
- ✅ **Performance**: Low overhead (<5ms per metric)
- ✅ **Privacy**: No PII in metrics

### Non-Functional Requirements

- ✅ **Zero Breaking Changes**: All existing tests still pass
- ✅ **Backward Compatible**: Telemetry still works without metrics
- ✅ **Graceful Degradation**: Dashboard works without Sentry
- ✅ **Configuration**: All thresholds configurable

---

## 🚫 Out of Scope (Defer to Future)

### Deferred Features

1. **GUI Dashboard** - Use CLI or external tools
2. **Real-time Updates** - Batch queries sufficient
3. **Advanced Alerting** - Email, Slack, webhooks
4. **Grafana Integration** - Overkill for MVP
5. **Custom Visualizations** - Use JSON export + external tools
6. **ML Anomaly Detection** - Simple thresholds sufficient
7. **Multi-user Access** - Single-user CLI fine
8. **Database Optimization** - Optimize if needed later

---

## 📊 Estimated Timeline

| Phase | Activity | Estimated Time |
|-------|----------|----------------|
| 1 | Metrics Aggregation | 60 min |
| 2 | Baseline Comparison | 60 min |
| 3 | Simple Dashboard | 30-45 min |
| 4 | Documentation | 15-30 min |
| **Total** | **All Phases** | **~3 hours** |

**Buffer**: +30 min for unexpected issues  
**Total with Buffer**: 3.5 hours

---

## 🎯 Day 4 Execution Checklist

### Phase 1: Metrics Aggregation ✅

- [ ] Create `core/metrics_aggregator.py`
  - [ ] Define MetricType enum
  - [ ] Define MetricSnapshot dataclass
  - [ ] Implement MetricsAggregator class
  - [ ] Add SQLite storage
  - [ ] Add query methods
  - [ ] Add aggregation functions

- [ ] Create `tests/test_metrics_aggregator.py`
  - [ ] Test counter operations (3 tests)
  - [ ] Test gauge operations (2 tests)
  - [ ] Test histogram operations (2 tests)
  - [ ] Test time-range queries (2 tests)
  - [ ] Test tag filtering (2 tests)
  - [ ] Test aggregation functions (3 tests)
  - [ ] Test edge cases (2 tests)

- [ ] Run tests: `pytest tests/test_metrics_aggregator.py -v`
- [ ] Verify: 20/20 tests passing

### Phase 2: Baseline Comparison ✅

- [ ] Create `core/metrics_baseline.py`
  - [ ] Define BaselineConfig dataclass
  - [ ] Define Baseline dataclass
  - [ ] Define DeviationAlert dataclass
  - [ ] Implement MetricsBaseline class
  - [ ] Add baseline calculation
  - [ ] Add deviation detection
  - [ ] Add alert generation

- [ ] Create `tests/test_metrics_baseline.py`
  - [ ] Test baseline calculation (3 tests)
  - [ ] Test deviation detection (4 tests)
  - [ ] Test alert severity (2 tests)
  - [ ] Test baseline updates (2 tests)
  - [ ] Test edge cases (2 tests)

- [ ] Run tests: `pytest tests/test_metrics_baseline.py -v`
- [ ] Verify: 15/15 tests passing

### Phase 3: Simple Dashboard ✅

- [ ] Create `core/metrics_dashboard.py`
  - [ ] Implement MetricsDashboard class
  - [ ] Add summary display
  - [ ] Add metric detail display
  - [ ] Add alert display
  - [ ] Add JSON export
  - [ ] Add CSV export

- [ ] Create `tests/test_metrics_dashboard.py`
  - [ ] Test summary display (2 tests)
  - [ ] Test metric detail (1 test)
  - [ ] Test alert display (1 test)
  - [ ] Test JSON export (2 tests)
  - [ ] Test CSV export (2 tests)
  - [ ] Test summary stats (2 tests)

- [ ] Run tests: `pytest tests/test_metrics_dashboard.py -v`
- [ ] Verify: 10/10 tests passing

### Phase 4: Documentation & Integration ✅

- [ ] Create `docs/TASK20_DAY4_COMPLETE.md`
  - [ ] Overview
  - [ ] Features implemented
  - [ ] Usage examples
  - [ ] Metrics schema
  - [ ] Integration guide

- [ ] Run all Day 4 tests:
  - [ ] `pytest tests/test_metrics_*.py -v`
  - [ ] Verify: 45/45 passing

- [ ] Run all Task #20 tests:
  - [ ] `pytest tests/test_structured_logging.py tests/test_telemetry_context.py tests/test_performance.py tests/test_pii_filter.py tests/test_telemetry_config.py tests/test_error_boundaries.py tests/test_metrics_*.py -v`
  - [ ] Verify: 179/179 passing (134 + 45)

- [ ] Verify zero breaking changes:
  - [ ] All existing tests still pass
  - [ ] No modifications to Days 1-3 code

---

## 🎓 Key Principles (From Days 1-3 Success)

1. **Layered Architecture**: Build on existing infrastructure
2. **Test-First**: Write tests alongside code
3. **Privacy-First**: No PII in metrics
4. **Configuration-Driven**: Make behaviors tunable
5. **Graceful Degradation**: Work without external services
6. **Simple First**: Optimize only when needed
7. **Clear Scope**: Focus on MVP, defer extras
8. **Document As You Go**: Usage examples in tests

---

**Plan Version**: 2.0 (Revised)  
**Created**: October 17, 2025  
**Based On**: Pattern analysis from Days 1-3  
**Status**: Ready for execution  
**Confidence**: 90%
