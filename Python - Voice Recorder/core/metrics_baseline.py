"""
Baseline Calculation and Deviation Detection

This module provides capabilities for calculating rolling baselines from historical
metrics and detecting when current values deviate significantly from expected patterns.

Privacy Note: All calculations use aggregated data. No individual user data is stored
or transmitted. Baseline data is stored locally and never shared.

Key Features:
- Rolling baseline calculation (median, MAD, percentiles)
- Deviation detection with configurable thresholds
- Alert generation with severity levels
- Automatic baseline updates
- Historical baseline persistence

Example Usage:
    from core.metrics_baseline import get_baseline_manager, BaselineConfig
    
    # Calculate baseline for request latency
    manager = get_baseline_manager()
    baseline = manager.calculate_baseline(
        "request.duration_ms",
        window_hours=24,
        config=BaselineConfig(threshold_multiplier=3.0)
    )
    
    # Check current value against baseline
    alert = manager.check_deviation("request.duration_ms", current_value=250.0)
    if alert:
        print(f"Alert: {alert.severity} - {alert.message}")
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
import json
import statistics

from core.logging_config import get_logger
from core.metrics_aggregator import get_metrics_aggregator, MetricQuery

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels for deviation detection"""
    INFO = "info"           # Minor deviation, informational only
    WARNING = "warning"     # Moderate deviation, investigate
    CRITICAL = "critical"   # Severe deviation, immediate action needed


@dataclass
class BaselineConfig:
    """Configuration for baseline calculation and deviation detection"""
    threshold_multiplier: float = 3.0  # MAD multiplier for deviation threshold
    min_data_points: int = 30          # Minimum samples needed for baseline
    percentiles: List[int] = field(default_factory=lambda: [50, 95, 99])
    alert_on_increase: bool = True     # Alert on values above threshold
    alert_on_decrease: bool = False    # Alert on values below threshold


@dataclass
class BaselineStats:
    """Statistical baseline for a metric"""
    metric_name: str
    median: float
    mad: float                          # Median Absolute Deviation
    mean: float
    std_dev: float
    percentiles: Dict[int, float]       # {50: value, 95: value, 99: value}
    data_points: int
    window_start: datetime
    window_end: datetime
    calculated_at: datetime
    config: BaselineConfig
    
    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dictionary"""
        return {
            "metric_name": self.metric_name,
            "median": self.median,
            "mad": self.mad,
            "mean": self.mean,
            "std_dev": self.std_dev,
            "percentiles": self.percentiles,
            "data_points": self.data_points,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "calculated_at": self.calculated_at.isoformat(),
            "config": {
                "threshold_multiplier": self.config.threshold_multiplier,
                "min_data_points": self.config.min_data_points,
                "percentiles": self.config.percentiles,
                "alert_on_increase": self.config.alert_on_increase,
                "alert_on_decrease": self.config.alert_on_decrease,
            }
        }
    
    @staticmethod
    def from_dict(data: Dict) -> "BaselineStats":
        """Create from dictionary"""
        config_data = data["config"]
        config = BaselineConfig(
            threshold_multiplier=config_data["threshold_multiplier"],
            min_data_points=config_data["min_data_points"],
            percentiles=config_data["percentiles"],
            alert_on_increase=config_data["alert_on_increase"],
            alert_on_decrease=config_data["alert_on_decrease"],
        )
        
        return BaselineStats(
            metric_name=data["metric_name"],
            median=data["median"],
            mad=data["mad"],
            mean=data["mean"],
            std_dev=data["std_dev"],
            percentiles=data["percentiles"],
            data_points=data["data_points"],
            window_start=datetime.fromisoformat(data["window_start"]),
            window_end=datetime.fromisoformat(data["window_end"]),
            calculated_at=datetime.fromisoformat(data["calculated_at"]),
            config=config,
        )
    
    def get_upper_threshold(self) -> float:
        """Calculate upper deviation threshold (median + threshold * MAD)"""
        return self.median + (self.config.threshold_multiplier * self.mad)
    
    def get_lower_threshold(self) -> float:
        """Calculate lower deviation threshold (median - threshold * MAD)"""
        return self.median - (self.config.threshold_multiplier * self.mad)
    
    def is_above_threshold(self, value: float) -> bool:
        """Check if value exceeds upper threshold"""
        return value > self.get_upper_threshold()
    
    def is_below_threshold(self, value: float) -> bool:
        """Check if value is below lower threshold"""
        return value < self.get_lower_threshold()


@dataclass
class DeviationAlert:
    """Alert for metric deviation from baseline"""
    metric_name: str
    current_value: float
    baseline_median: float
    threshold: float
    deviation_percent: float
    severity: AlertSeverity
    message: str
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dictionary"""
        return {
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "baseline_median": self.baseline_median,
            "threshold": self.threshold,
            "deviation_percent": self.deviation_percent,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }
    
    @staticmethod
    def from_dict(data: Dict) -> "DeviationAlert":
        """Create from dictionary"""
        return DeviationAlert(
            metric_name=data["metric_name"],
            current_value=data["current_value"],
            baseline_median=data["baseline_median"],
            threshold=data["threshold"],
            deviation_percent=data["deviation_percent"],
            severity=AlertSeverity(data["severity"]),
            message=data["message"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class BaselineManager:
    """
    Manages baseline calculation and deviation detection for metrics
    
    This class provides methods for:
    - Calculating rolling baselines from historical data
    - Detecting deviations from expected patterns
    - Generating alerts with severity levels
    - Persisting baselines to disk
    
    Thread Safety: Not thread-safe. Use separate instances per thread.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize baseline manager
        
        Args:
            storage_path: Path to store baseline data (default: ./baselines.json)
        """
        self.storage_path = storage_path or Path("baselines.json")
        self.aggregator = get_metrics_aggregator()
        self._baselines: Dict[str, BaselineStats] = {}
        self._load_baselines()
        logger.info("BaselineManager initialized", extra={"storage_path": str(self.storage_path)})
    
    def _load_baselines(self) -> None:
        """Load baselines from disk"""
        if not self.storage_path.exists():
            logger.debug("No baseline file found, starting fresh")
            return
        
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                self._baselines = {
                    name: BaselineStats.from_dict(stats_data)
                    for name, stats_data in data.items()
                }
            logger.info(f"Loaded {len(self._baselines)} baselines from disk")
        except Exception as e:
            logger.error(f"Failed to load baselines: {e}")
            self._baselines = {}
    
    def _save_baselines(self) -> None:
        """Save baselines to disk"""
        try:
            data = {
                name: stats.to_dict()
                for name, stats in self._baselines.items()
            }
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(self._baselines)} baselines to disk")
        except Exception as e:
            logger.error(f"Failed to save baselines: {e}")
    
    def calculate_baseline(
        self,
        metric_name: str,
        window_hours: int = 24,
        config: Optional[BaselineConfig] = None,
    ) -> Optional[BaselineStats]:
        """
        Calculate baseline statistics for a metric
        
        Args:
            metric_name: Name of the metric to analyze
            window_hours: Hours of historical data to include
            config: Configuration for baseline calculation
            
        Returns:
            BaselineStats if successful, None if insufficient data
        """
        config = config or BaselineConfig()
        
        # Query historical data
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=window_hours)
        
        query = MetricQuery(
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
        )
        
        snapshots = self.aggregator.query_metrics(query)
        
        if len(snapshots) < config.min_data_points:
            logger.warning(
                f"Insufficient data for baseline: {len(snapshots)} < {config.min_data_points}",
                extra={"metric_name": metric_name}
            )
            return None
        
        # Extract values
        values = [s.value for s in snapshots]
        
        # Calculate statistics
        median = statistics.median(values)
        mean = statistics.mean(values)
        
        # Calculate MAD (Median Absolute Deviation)
        absolute_deviations = [abs(v - median) for v in values]
        mad = statistics.median(absolute_deviations)
        
        # Calculate standard deviation
        std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
        
        # Calculate percentiles
        sorted_values = sorted(values)
        percentiles = {}
        for p in config.percentiles:
            idx = int((p / 100.0) * len(sorted_values))
            idx = min(idx, len(sorted_values) - 1)
            percentiles[p] = sorted_values[idx]
        
        baseline = BaselineStats(
            metric_name=metric_name,
            median=median,
            mad=mad,
            mean=mean,
            std_dev=std_dev,
            percentiles=percentiles,
            data_points=len(values),
            window_start=start_time,
            window_end=end_time,
            calculated_at=datetime.now(),
            config=config,
        )
        
        # Cache and persist
        self._baselines[metric_name] = baseline
        self._save_baselines()
        
        logger.info(
            f"Calculated baseline for {metric_name}",
            extra={
                "median": median,
                "mad": mad,
                "data_points": len(values),
                "window_hours": window_hours,
            }
        )
        
        return baseline
    
    def get_baseline(self, metric_name: str) -> Optional[BaselineStats]:
        """
        Get cached baseline for a metric
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            BaselineStats if available, None otherwise
        """
        return self._baselines.get(metric_name)
    
    def check_deviation(
        self,
        metric_name: str,
        current_value: float,
        auto_calculate: bool = True,
        window_hours: int = 24,
    ) -> Optional[DeviationAlert]:
        """
        Check if current value deviates from baseline
        
        Args:
            metric_name: Name of the metric
            current_value: Current metric value to check
            auto_calculate: Automatically calculate baseline if not cached
            window_hours: Hours of data for auto-calculation
            
        Returns:
            DeviationAlert if deviation detected, None otherwise
        """
        baseline = self.get_baseline(metric_name)
        
        if baseline is None and auto_calculate:
            baseline = self.calculate_baseline(metric_name, window_hours)
        
        if baseline is None:
            logger.debug(f"No baseline available for {metric_name}")
            return None
        
        # Check for deviations
        is_above = baseline.is_above_threshold(current_value)
        is_below = baseline.is_below_threshold(current_value)
        
        # Determine if alert should be raised
        should_alert = False
        threshold = 0.0
        direction = ""
        
        if is_above and baseline.config.alert_on_increase:
            should_alert = True
            threshold = baseline.get_upper_threshold()
            direction = "above"
        elif is_below and baseline.config.alert_on_decrease:
            should_alert = True
            threshold = baseline.get_lower_threshold()
            direction = "below"
        
        if not should_alert:
            return None
        
        # Calculate deviation percentage
        deviation_percent = ((current_value - baseline.median) / baseline.median) * 100
        
        # Determine severity based on deviation magnitude
        abs_deviation = abs(deviation_percent)
        if abs_deviation < 50:
            severity = AlertSeverity.INFO
        elif abs_deviation < 100:
            severity = AlertSeverity.WARNING
        else:
            severity = AlertSeverity.CRITICAL
        
        message = (
            f"Metric '{metric_name}' is {direction} threshold: "
            f"current={current_value:.2f}, baseline={baseline.median:.2f}, "
            f"threshold={threshold:.2f}, deviation={deviation_percent:+.1f}%"
        )
        
        alert = DeviationAlert(
            metric_name=metric_name,
            current_value=current_value,
            baseline_median=baseline.median,
            threshold=threshold,
            deviation_percent=deviation_percent,
            severity=severity,
            message=message,
            timestamp=datetime.now(),
        )
        
        logger.warning(
            f"Deviation detected: {metric_name}",
            extra={
                "severity": severity.value,
                "current": current_value,
                "baseline": baseline.median,
                "deviation_percent": deviation_percent,
            }
        )
        
        return alert
    
    def get_all_baselines(self) -> Dict[str, BaselineStats]:
        """Get all cached baselines"""
        return self._baselines.copy()
    
    def clear_baseline(self, metric_name: str) -> bool:
        """
        Clear cached baseline for a metric
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            True if baseline was removed, False if not found
        """
        if metric_name in self._baselines:
            del self._baselines[metric_name]
            self._save_baselines()
            logger.info(f"Cleared baseline for {metric_name}")
            return True
        return False
    
    def clear_all_baselines(self) -> None:
        """Clear all cached baselines"""
        self._baselines.clear()
        self._save_baselines()
        logger.info("Cleared all baselines")


# Singleton instance
_baseline_manager: Optional[BaselineManager] = None


def get_baseline_manager(storage_path: Optional[Path] = None) -> BaselineManager:
    """
    Get or create singleton baseline manager
    
    Args:
        storage_path: Path to store baseline data (only used on first call)
        
    Returns:
        Singleton BaselineManager instance
    """
    global _baseline_manager
    if _baseline_manager is None:
        _baseline_manager = BaselineManager(storage_path)
    return _baseline_manager


# Convenience functions

def calculate_baseline(
    metric_name: str,
    window_hours: int = 24,
    config: Optional[BaselineConfig] = None,
) -> Optional[BaselineStats]:
    """
    Calculate baseline for a metric (convenience function)
    
    Args:
        metric_name: Name of the metric
        window_hours: Hours of historical data
        config: Baseline configuration
        
    Returns:
        BaselineStats if successful, None otherwise
    """
    manager = get_baseline_manager()
    return manager.calculate_baseline(metric_name, window_hours, config)


def check_deviation(
    metric_name: str,
    current_value: float,
    auto_calculate: bool = True,
) -> Optional[DeviationAlert]:
    """
    Check if value deviates from baseline (convenience function)
    
    Args:
        metric_name: Name of the metric
        current_value: Current value to check
        auto_calculate: Auto-calculate baseline if missing
        
    Returns:
        DeviationAlert if deviation detected, None otherwise
    """
    manager = get_baseline_manager()
    return manager.check_deviation(metric_name, current_value, auto_calculate)
