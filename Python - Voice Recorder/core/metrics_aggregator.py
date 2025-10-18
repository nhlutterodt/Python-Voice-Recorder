"""
Metrics aggregation and time-series storage.

This module provides functionality to collect, store, and query metrics
from the telemetry infrastructure (Days 1-3). It supports counters, gauges,
and histograms with time-series storage and query capabilities.

Privacy: No PII is collected in metrics. All data is stored locally.

Example usage:
    >>> from core.metrics_aggregator import record_counter, record_gauge
    >>> record_counter("recording.started", tags={"format": "wav"})
    >>> record_gauge("memory.usage", 1024.0, tags={"unit": "mb"})
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from statistics import mean, median, stdev, quantiles
import sqlite3
import json
from contextlib import contextmanager

from core.logging_config import get_logger

logger = get_logger(__name__)

# Register adapters/converters for datetime to avoid Python 3.12 sqlite3 deprecation warnings.
# Store datetimes as ISO-8601 strings and convert back on read. The CREATE TABLE uses TIMESTAMP,
# and connection is created with detect_types so the converter is applied when reading.
try:
    sqlite3.register_adapter(datetime, lambda val: val.isoformat())
    sqlite3.register_converter("timestamp", lambda b: datetime.fromisoformat(b.decode()))
except Exception:
    # If registration fails for any reason, fall back to default behavior. Warnings are non-blocking.
    logger.debug("Failed to register sqlite datetime adapters/converters; continuing without them")


class MetricType(Enum):
    """Type of metric being collected."""
    
    COUNTER = "counter"       # Incremental count (recording starts, errors)
    GAUGE = "gauge"           # Current value snapshot (memory, active sessions)
    HISTOGRAM = "histogram"   # Distribution of values (request durations)
    SUMMARY = "summary"       # Percentiles (p50, p95, p99)


@dataclass
class MetricSnapshot:
    """
    Single metric measurement at a point in time.
    
    Attributes:
        metric_type: Type of metric (counter, gauge, histogram)
        name: Metric name (e.g., "recording.duration", "memory.usage")
        value: Numeric value of the metric
        timestamp: When the metric was recorded
        tags: Key-value tags for filtering (e.g., {"format": "wav"})
        metadata: Additional context (not used for filtering)
    """
    
    metric_type: MetricType
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "metric_type": self.metric_type.value,
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetricSnapshot":
        """Create from dictionary (from JSON deserialization)."""
        return cls(
            metric_type=MetricType(data["metric_type"]),
            name=data["name"],
            value=data["value"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tags=data.get("tags", {}),
            metadata=data.get("metadata", {})
        )


@dataclass
class MetricQuery:
    """
    Query parameters for fetching metrics.
    
    Attributes:
        metric_name: Filter by metric name (None = all metrics)
        metric_type: Filter by metric type (None = all types)
        start_time: Start of time range (None = no lower bound)
        end_time: End of time range (None = no upper bound)
        tags: Filter by tags (must match all specified tags)
        limit: Maximum number of results (0 = no limit)
    """
    
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
    - Stores in SQLite time-series database (or in-memory)
    - Supports counters, gauges, histograms, summaries
    - Query by time range, tags, metric type
    - Calculate aggregates (sum, avg, percentiles)
    
    Thread-safety: Not thread-safe. Use from single thread or add locking.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize metrics aggregator.
        
        Args:
            db_path: Path to SQLite database file. If None, uses in-memory database.
        """
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        self._init_db()
        logger.info(f"MetricsAggregator initialized with db_path={db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection (create if needed)."""
        if self._connection is None:
            db_location = str(self.db_path) if self.db_path else ":memory:"
            self._connection = sqlite3.connect(
                db_location,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
            )
            self._connection.row_factory = sqlite3.Row
        
        try:
            yield self._connection
        except Exception as e:
            logger.error(f"Database error: {e}")
            self._connection.rollback()
            raise
    
    def _init_db(self) -> None:
        """Initialize SQLite schema for metrics storage."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    tags TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indices for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_name 
                ON metrics(name)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
                ON metrics(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_type 
                ON metrics(metric_type)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_name_timestamp 
                ON metrics(name, timestamp)
            """)
            
            conn.commit()
            logger.debug("Database schema initialized")
    
    def record_metric(self, snapshot: MetricSnapshot) -> None:
        """
        Record a single metric snapshot.
        
        Args:
            snapshot: Metric measurement to record
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO metrics (metric_type, name, value, timestamp, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                snapshot.metric_type.value,
                snapshot.name,
                snapshot.value,
                snapshot.timestamp,
                json.dumps(snapshot.tags),
                json.dumps(snapshot.metadata)
            ))
            conn.commit()
            
        logger.debug(
            f"Recorded metric: {snapshot.name}={snapshot.value} "
            f"type={snapshot.metric_type.value} tags={snapshot.tags}"
        )
    
    def record_counter(
        self,
        name: str,
        increment: float = 1.0,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record counter increment.
        
        Counters are cumulative and always increase. Use for counting events
        like "recordings started", "errors occurred", "bytes sent".
        
        Args:
            name: Metric name (e.g., "recording.started")
            increment: Amount to increment (default 1.0)
            tags: Optional tags for filtering (e.g., {"format": "wav"})
        """
        snapshot = MetricSnapshot(
            metric_type=MetricType.COUNTER,
            name=name,
            value=increment,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        self.record_metric(snapshot)
    
    def record_gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record gauge value (current state snapshot).
        
        Gauges represent a value that can go up or down. Use for metrics like
        "memory usage", "active sessions", "queue depth".
        
        Args:
            name: Metric name (e.g., "memory.usage")
            value: Current value
            tags: Optional tags for filtering (e.g., {"unit": "mb"})
        """
        snapshot = MetricSnapshot(
            metric_type=MetricType.GAUGE,
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        self.record_metric(snapshot)
    
    def record_histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record histogram value (for distribution analysis).
        
        Histograms track the distribution of values. Use for metrics like
        "request duration", "file size", "processing time".
        
        Args:
            name: Metric name (e.g., "request.duration")
            value: Observed value
            tags: Optional tags for filtering (e.g., {"endpoint": "/upload"})
        """
        snapshot = MetricSnapshot(
            metric_type=MetricType.HISTOGRAM,
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {}
        )
        self.record_metric(snapshot)
    
    def query_metrics(self, query: MetricQuery) -> List[MetricSnapshot]:
        """
        Query metrics from storage.
        
        Args:
            query: Query parameters (name, type, time range, tags, limit)
            
        Returns:
            List of matching metric snapshots, ordered by timestamp DESC
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Build SQL query dynamically based on filters
            sql = "SELECT * FROM metrics WHERE 1=1"
            params: List[Any] = []
            
            if query.metric_name:
                sql += " AND name = ?"
                params.append(query.metric_name)
            
            if query.metric_type:
                sql += " AND metric_type = ?"
                params.append(query.metric_type.value)
            
            if query.start_time:
                sql += " AND timestamp >= ?"
                params.append(query.start_time)
            
            if query.end_time:
                sql += " AND timestamp <= ?"
                params.append(query.end_time)
            
            sql += " ORDER BY timestamp DESC"
            
            if query.limit > 0:
                sql += " LIMIT ?"
                params.append(query.limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Convert rows to MetricSnapshot objects
            snapshots = []
            for row in rows:
                # Filter by tags if specified
                row_tags = json.loads(row["tags"]) if row["tags"] else {}
                if query.tags:
                    if not all(row_tags.get(k) == v for k, v in query.tags.items()):
                        continue
                
                snapshot = MetricSnapshot(
                    metric_type=MetricType(row["metric_type"]),
                    name=row["name"],
                    value=row["value"],
                    timestamp=row["timestamp"],
                    tags=row_tags,
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {}
                )
                snapshots.append(snapshot)
            
            return snapshots
    
    def calculate_sum(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> float:
        """
        Calculate sum of metric values in time range.
        
        Useful for counters to get total count.
        
        Args:
            metric_name: Name of metric
            start_time: Start of time range (None = all time)
            end_time: End of time range (None = now)
            tags: Filter by tags
            
        Returns:
            Sum of all matching metric values
        """
        query = MetricQuery(
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            tags=tags or {},
            limit=0  # No limit for aggregation
        )
        
        snapshots = self.query_metrics(query)
        return sum(s.value for s in snapshots)
    
    def calculate_average(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> float:
        """
        Calculate average of metric values in time range.
        
        Useful for gauges to get average level.
        
        Args:
            metric_name: Name of metric
            start_time: Start of time range
            end_time: End of time range
            tags: Filter by tags
            
        Returns:
            Average of all matching metric values (0.0 if no data)
        """
        query = MetricQuery(
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            tags=tags or {},
            limit=0
        )
        
        snapshots = self.query_metrics(query)
        if not snapshots:
            return 0.0
        
        return mean(s.value for s in snapshots)
    
    def calculate_percentiles(
        self,
        metric_name: str,
        percentiles: List[float] = [50, 95, 99],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Dict[float, float]:
        """
        Calculate percentiles of metric values.
        
        Useful for histograms to understand distribution (p50=median, p95, p99).
        
        Args:
            metric_name: Name of metric
            percentiles: List of percentiles to calculate (0-100)
            start_time: Start of time range
            end_time: End of time range
            tags: Filter by tags
            
        Returns:
            Dict mapping percentile to value (e.g., {50: 10.5, 95: 25.3, 99: 42.1})
            Returns {p: 0.0 for p in percentiles} if no data
        """
        query = MetricQuery(
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            tags=tags or {},
            limit=0
        )
        
        snapshots = self.query_metrics(query)
        
        # Return zeros if no data
        if not snapshots:
            return {p: 0.0 for p in percentiles}
        
        values = sorted([s.value for s in snapshots])
        
        # Calculate percentiles
        result = {}
        for p in percentiles:
            if p < 0 or p > 100:
                result[p] = 0.0
                continue
            
            # Use quantiles function from statistics (Python 3.8+)
            # quantiles() divides data into n equal-sized groups
            # For percentile p, we need position p/100
            if len(values) == 1:
                result[p] = values[0]
            else:
                # Calculate index for percentile
                index = (p / 100) * (len(values) - 1)
                lower_index = int(index)
                upper_index = min(lower_index + 1, len(values) - 1)
                fraction = index - lower_index
                
                # Linear interpolation
                result[p] = values[lower_index] + fraction * (values[upper_index] - values[lower_index])
        
        return result
    
    def get_metric_names(self) -> List[str]:
        """
        Get list of all metric names in storage.
        
        Returns:
            List of unique metric names, sorted alphabetically
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT name FROM metrics ORDER BY name")
            rows = cursor.fetchall()
            return [row["name"] for row in rows]
    
    def get_tags_for_metric(self, metric_name: str) -> Dict[str, List[str]]:
        """
        Get all unique tag values for a metric.
        
        Args:
            metric_name: Name of metric
            
        Returns:
            Dict mapping tag key to list of unique values
            Example: {"format": ["wav", "mp3"], "quality": ["high", "low"]}
        """
        query = MetricQuery(metric_name=metric_name, limit=0)
        snapshots = self.query_metrics(query)
        
        # Collect all unique tag values
        tag_values: Dict[str, set] = {}
        for snapshot in snapshots:
            for key, value in snapshot.tags.items():
                if key not in tag_values:
                    tag_values[key] = set()
                tag_values[key].add(value)
        
        # Convert sets to sorted lists
        return {key: sorted(list(values)) for key, values in tag_values.items()}
    
    def get_count(
        self,
        metric_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> int:
        """
        Get count of metric data points.
        
        Args:
            metric_name: Name of metric
            start_time: Start of time range
            end_time: End of time range
            tags: Filter by tags
            
        Returns:
            Number of data points
        """
        query = MetricQuery(
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            tags=tags or {},
            limit=0
        )
        
        snapshots = self.query_metrics(query)
        return len(snapshots)
    
    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.debug("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


# Global singleton instance
_metrics_aggregator: Optional[MetricsAggregator] = None


def get_metrics_aggregator(db_path: Optional[Path] = None) -> MetricsAggregator:
    """
    Get global metrics aggregator instance.
    
    Args:
        db_path: Path to database (only used on first call)
        
    Returns:
        Global MetricsAggregator instance
    """
    global _metrics_aggregator
    if _metrics_aggregator is None:
        _metrics_aggregator = MetricsAggregator(db_path)
    return _metrics_aggregator


def record_counter(
    name: str,
    increment: float = 1.0,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Convenience function to record counter.
    
    Args:
        name: Metric name
        increment: Amount to increment
        tags: Optional tags
    """
    get_metrics_aggregator().record_counter(name, increment, tags)


def record_gauge(
    name: str,
    value: float,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Convenience function to record gauge.
    
    Args:
        name: Metric name
        value: Current value
        tags: Optional tags
    """
    get_metrics_aggregator().record_gauge(name, value, tags)


def record_histogram(
    name: str,
    value: float,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Convenience function to record histogram.
    
    Args:
        name: Metric name
        value: Observed value
        tags: Optional tags
    """
    get_metrics_aggregator().record_histogram(name, value, tags)
