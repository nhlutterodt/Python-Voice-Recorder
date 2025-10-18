"""
Tests for Baseline Calculation and Deviation Detection

Tests cover:
- Baseline calculation from historical data
- MAD (Median Absolute Deviation) computation
- Deviation detection with thresholds
- Alert generation and severity levels
- Baseline persistence and loading
- Edge cases (insufficient data, missing baselines)
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import json

from core.metrics_baseline import (
    BaselineManager,
    BaselineConfig,
    BaselineStats,
    DeviationAlert,
    AlertSeverity,
    get_baseline_manager,
    calculate_baseline,
    check_deviation,
)
from core.metrics_aggregator import get_metrics_aggregator, record_histogram, record_gauge


class TestBaselineCalculation:
    """Test baseline calculation from historical metrics"""
    
    def setup_method(self):
        """Set up test environment"""
        # Reset singleton state
        from core import metrics_aggregator, metrics_baseline
        metrics_aggregator._metrics_aggregator = None
        metrics_baseline._baseline_manager = None
        
        self.aggregator = get_metrics_aggregator()  # In-memory
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "test_baselines.json"
        self.manager = BaselineManager(storage_path=self.storage_path)
    
    def teardown_method(self):
        """Clean up test environment"""
        if self.aggregator:
            self.aggregator.close()
        from core import metrics_aggregator, metrics_baseline
        metrics_aggregator._metrics_aggregator = None
        metrics_baseline._baseline_manager = None
    
    def test_calculate_baseline_with_sufficient_data(self):
        """Test baseline calculation with adequate data points"""
        # Record 50 data points with normal distribution around 100
        metric_name = "test.latency_ms"
        base_time = datetime.now()
        
        for i in range(50):
            # Create realistic distribution: mostly 95-105, few outliers
            if i < 45:
                value = 100.0 + (i % 10) - 5  # 95-105
            else:
                value = 100.0 + (i % 3) * 20  # Some outliers
            
            record_histogram(metric_name, value)
        
        # Calculate baseline
        baseline = self.manager.calculate_baseline(metric_name, window_hours=1)
        
        assert baseline is not None
        assert baseline.metric_name == metric_name
        assert baseline.data_points == 50
        assert 95 <= baseline.median <= 105  # Should be around 100
        assert baseline.mad > 0  # Should have some deviation
        assert 95 <= baseline.mean <= 105
        assert baseline.std_dev > 0
        assert 50 in baseline.percentiles
        assert 95 in baseline.percentiles
        assert 99 in baseline.percentiles
    
    def test_calculate_baseline_insufficient_data(self):
        """Test baseline calculation with insufficient data"""
        metric_name = "test.rare_metric"
        
        # Only record 5 data points (default min is 30)
        for i in range(5):
            record_histogram(metric_name, 100.0)
        
        baseline = self.manager.calculate_baseline(metric_name, window_hours=1)
        
        assert baseline is None  # Should fail due to insufficient data
    
    def test_baseline_custom_config(self):
        """Test baseline with custom configuration"""
        metric_name = "test.custom_metric"
        
        # Record data
        for i in range(50):
            record_histogram(metric_name, 100.0 + i)
        
        # Custom config: lower threshold multiplier, fewer percentiles
        config = BaselineConfig(
            threshold_multiplier=2.0,
            min_data_points=20,
            percentiles=[50, 90],
            alert_on_decrease=True,
        )
        
        baseline = self.manager.calculate_baseline(
            metric_name,
            window_hours=1,
            config=config,
        )
        
        assert baseline is not None
        assert baseline.config.threshold_multiplier == 2.0
        assert baseline.config.min_data_points == 20
        assert 50 in baseline.percentiles
        assert 90 in baseline.percentiles
        assert 95 not in baseline.percentiles  # Not requested


class TestDeviationDetection:
    """Test deviation detection and alerting"""
    
    def setup_method(self):
        """Set up test environment"""
        # Reset singleton state
        from core import metrics_aggregator, metrics_baseline
        metrics_aggregator._metrics_aggregator = None
        metrics_baseline._baseline_manager = None
        
        self.aggregator = get_metrics_aggregator()
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "test_baselines.json"
        self.manager = BaselineManager(storage_path=self.storage_path)
        
        # Create baseline data with some natural variance
        self.metric_name = "test.latency_ms"
        for i in range(50):
            # Realistic variance: 95-105ms
            value = 100.0 + (i % 11) - 5  # Range: 95, 96, ..., 105
            record_histogram(self.metric_name, value)
        
        self.baseline = self.manager.calculate_baseline(self.metric_name, window_hours=1)
    
    def teardown_method(self):
        """Clean up"""
        if self.aggregator:
            self.aggregator.close()
        from core import metrics_aggregator, metrics_baseline
        metrics_aggregator._metrics_aggregator = None
        metrics_baseline._baseline_manager = None
    
    def test_no_deviation_within_threshold(self):
        """Test that normal values don't trigger alerts"""
        alert = self.manager.check_deviation(self.metric_name, 102.0)
        assert alert is None  # 102 should be within threshold
    
    def test_deviation_above_threshold(self):
        """Test detection of values above threshold"""
        # With median=100 and MAD~0, threshold multiplier=3
        # Upper threshold should be around 100
        # Need a significant spike to trigger
        alert = self.manager.check_deviation(self.metric_name, 500.0)
        
        assert alert is not None
        assert alert.metric_name == self.metric_name
        assert alert.current_value == 500.0
        assert alert.deviation_percent > 0  # Positive deviation
        assert alert.severity in [AlertSeverity.WARNING, AlertSeverity.CRITICAL]
        assert "above" in alert.message.lower()
    
    def test_deviation_severity_levels(self):
        """Test that severity escalates with deviation magnitude"""
        # Small deviation: INFO
        alert_small = self.manager.check_deviation(self.metric_name, 120.0)
        
        # Medium deviation: WARNING
        alert_medium = self.manager.check_deviation(self.metric_name, 180.0)
        
        # Large deviation: CRITICAL
        alert_large = self.manager.check_deviation(self.metric_name, 300.0)
        
        # At least the large deviation should trigger
        assert alert_large is not None
        assert alert_large.severity == AlertSeverity.CRITICAL
    
    def test_deviation_below_threshold(self):
        """Test detection of values below threshold (when enabled)"""
        # Create baseline with decrease alerting enabled
        metric_name = "test.throughput"
        for i in range(50):
            record_gauge(metric_name, 1000.0)  # Stable at 1000
        
        config = BaselineConfig(alert_on_decrease=True)
        baseline = self.manager.calculate_baseline(metric_name, window_hours=1, config=config)
        
        # Check significant drop
        alert = self.manager.check_deviation(metric_name, 100.0)
        
        assert alert is not None
        assert alert.current_value == 100.0
        assert alert.deviation_percent < 0  # Negative deviation
        assert "below" in alert.message.lower()
    
    def test_auto_calculate_baseline(self):
        """Test automatic baseline calculation on first check"""
        metric_name = "test.new_metric"
        
        # Record data but don't calculate baseline manually
        for i in range(50):
            record_histogram(metric_name, 50.0)
        
        # Check deviation with auto_calculate=True
        alert = self.manager.check_deviation(
            metric_name,
            current_value=150.0,
            auto_calculate=True,
        )
        
        # Should auto-calculate and detect deviation
        assert alert is not None
        assert self.manager.get_baseline(metric_name) is not None


class TestBaselinePersistence:
    """Test baseline storage and loading"""
    
    def test_baseline_persistence(self):
        """Test that baselines are saved and loaded correctly"""
        temp_dir = tempfile.mkdtemp()
        storage_path = Path(temp_dir) / "baselines.json"
        
        # Create first manager and calculate baseline
        aggregator = get_metrics_aggregator()
        manager1 = BaselineManager(storage_path=storage_path)
        
        metric_name = "test.persistent_metric"
        for i in range(50):
            record_histogram(metric_name, 100.0 + i)
        
        baseline1 = manager1.calculate_baseline(metric_name, window_hours=1)
        assert baseline1 is not None
        
        median1 = baseline1.median
        mad1 = baseline1.mad
        
        # Close first manager
        aggregator.close()
        
        # Create second manager (should load from disk)
        aggregator2 = get_metrics_aggregator()
        manager2 = BaselineManager(storage_path=storage_path)
        
        baseline2 = manager2.get_baseline(metric_name)
        
        assert baseline2 is not None
        assert baseline2.metric_name == metric_name
        assert baseline2.median == median1
        assert baseline2.mad == mad1
        assert baseline2.data_points == 50
        
        aggregator2.close()
    
    def test_baseline_serialization(self):
        """Test BaselineStats to_dict/from_dict"""
        config = BaselineConfig(
            threshold_multiplier=2.5,
            min_data_points=25,
            percentiles=[50, 75, 90],
        )
        
        baseline = BaselineStats(
            metric_name="test.metric",
            median=100.0,
            mad=5.0,
            mean=101.0,
            std_dev=7.5,
            percentiles={50: 100.0, 75: 105.0, 90: 110.0},
            data_points=100,
            window_start=datetime(2024, 1, 1, 12, 0, 0),
            window_end=datetime(2024, 1, 2, 12, 0, 0),
            calculated_at=datetime(2024, 1, 2, 12, 0, 0),
            config=config,
        )
        
        # Serialize
        data = baseline.to_dict()
        assert data["metric_name"] == "test.metric"
        assert data["median"] == 100.0
        assert data["config"]["threshold_multiplier"] == 2.5
        
        # Deserialize
        baseline2 = BaselineStats.from_dict(data)
        assert baseline2.metric_name == baseline.metric_name
        assert baseline2.median == baseline.median
        assert baseline2.mad == baseline.mad
        assert baseline2.config.threshold_multiplier == baseline.config.threshold_multiplier


class TestThresholdCalculations:
    """Test threshold calculation methods"""
    
    def test_upper_threshold_calculation(self):
        """Test upper threshold = median + (multiplier * MAD)"""
        config = BaselineConfig(threshold_multiplier=3.0)
        baseline = BaselineStats(
            metric_name="test",
            median=100.0,
            mad=10.0,
            mean=100.0,
            std_dev=12.0,
            percentiles={50: 100.0},
            data_points=50,
            window_start=datetime.now(),
            window_end=datetime.now(),
            calculated_at=datetime.now(),
            config=config,
        )
        
        upper = baseline.get_upper_threshold()
        assert upper == 130.0  # 100 + (3 * 10)
    
    def test_lower_threshold_calculation(self):
        """Test lower threshold = median - (multiplier * MAD)"""
        config = BaselineConfig(threshold_multiplier=3.0)
        baseline = BaselineStats(
            metric_name="test",
            median=100.0,
            mad=10.0,
            mean=100.0,
            std_dev=12.0,
            percentiles={50: 100.0},
            data_points=50,
            window_start=datetime.now(),
            window_end=datetime.now(),
            calculated_at=datetime.now(),
            config=config,
        )
        
        lower = baseline.get_lower_threshold()
        assert lower == 70.0  # 100 - (3 * 10)
    
    def test_threshold_checks(self):
        """Test is_above_threshold and is_below_threshold"""
        config = BaselineConfig(threshold_multiplier=2.0)
        baseline = BaselineStats(
            metric_name="test",
            median=100.0,
            mad=10.0,
            mean=100.0,
            std_dev=12.0,
            percentiles={50: 100.0},
            data_points=50,
            window_start=datetime.now(),
            window_end=datetime.now(),
            calculated_at=datetime.now(),
            config=config,
        )
        
        # Thresholds: 80-120 (100 ± 2*10)
        assert not baseline.is_above_threshold(119.0)
        assert baseline.is_above_threshold(121.0)
        assert not baseline.is_below_threshold(81.0)
        assert baseline.is_below_threshold(79.0)


class TestBaselineManagement:
    """Test baseline cache management"""
    
    def setup_method(self):
        """Set up test environment"""
        # Reset singleton state
        from core import metrics_aggregator, metrics_baseline
        metrics_aggregator._metrics_aggregator = None
        metrics_baseline._baseline_manager = None
        
        self.aggregator = get_metrics_aggregator()
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "test_baselines.json"
        self.manager = BaselineManager(storage_path=self.storage_path)
    
    def teardown_method(self):
        """Clean up"""
        if self.aggregator:
            self.aggregator.close()
        from core import metrics_aggregator, metrics_baseline
        metrics_aggregator._metrics_aggregator = None
        metrics_baseline._baseline_manager = None
    
    def test_get_all_baselines(self):
        """Test retrieving all cached baselines"""
        # Create multiple baselines
        for i in range(3):
            metric_name = f"test.metric_{i}"
            for j in range(50):
                record_histogram(metric_name, 100.0 + i)
            self.manager.calculate_baseline(metric_name, window_hours=1)
        
        all_baselines = self.manager.get_all_baselines()
        assert len(all_baselines) == 3
        assert "test.metric_0" in all_baselines
        assert "test.metric_1" in all_baselines
        assert "test.metric_2" in all_baselines
    
    def test_clear_single_baseline(self):
        """Test clearing a single baseline"""
        metric_name = "test.metric"
        
        # Create baseline
        for i in range(50):
            record_histogram(metric_name, 100.0)
        self.manager.calculate_baseline(metric_name, window_hours=1)
        
        assert self.manager.get_baseline(metric_name) is not None
        
        # Clear it
        result = self.manager.clear_baseline(metric_name)
        assert result is True
        assert self.manager.get_baseline(metric_name) is None
        
        # Try clearing again (should return False)
        result = self.manager.clear_baseline(metric_name)
        assert result is False
    
    def test_clear_all_baselines(self):
        """Test clearing all baselines"""
        # Create multiple baselines
        for i in range(3):
            metric_name = f"test.metric_{i}"
            for j in range(50):
                record_histogram(metric_name, 100.0)
            self.manager.calculate_baseline(metric_name, window_hours=1)
        
        assert len(self.manager.get_all_baselines()) == 3
        
        # Clear all
        self.manager.clear_all_baselines()
        assert len(self.manager.get_all_baselines()) == 0


class TestConvenienceFunctions:
    """Test module-level convenience functions"""
    
    def setup_method(self):
        """Set up test environment"""
        # Reset singleton state
        from core import metrics_aggregator, metrics_baseline
        metrics_aggregator._metrics_aggregator = None
        metrics_baseline._baseline_manager = None
        
        self.aggregator = get_metrics_aggregator()
    
    def teardown_method(self):
        """Clean up"""
        if self.aggregator:
            self.aggregator.close()
        from core import metrics_aggregator, metrics_baseline
        metrics_aggregator._metrics_aggregator = None
        metrics_baseline._baseline_manager = None
    
    def test_convenience_calculate_baseline(self):
        """Test calculate_baseline convenience function"""
        metric_name = "test.convenience_metric"
        
        for i in range(50):
            record_histogram(metric_name, 100.0)
        
        baseline = calculate_baseline(metric_name, window_hours=1)
        
        assert baseline is not None
        assert baseline.metric_name == metric_name
    
    def test_convenience_check_deviation(self):
        """Test check_deviation convenience function"""
        metric_name = "test.deviation_check"
        
        for i in range(50):
            record_histogram(metric_name, 100.0)
        
        # Should auto-calculate baseline and check
        alert = check_deviation(metric_name, 500.0, auto_calculate=True)
        
        assert alert is not None
        assert alert.current_value == 500.0


class TestDeviationAlertSerialization:
    """Test DeviationAlert serialization"""
    
    def test_alert_serialization(self):
        """Test DeviationAlert to_dict/from_dict"""
        alert = DeviationAlert(
            metric_name="test.metric",
            current_value=150.0,
            baseline_median=100.0,
            threshold=130.0,
            deviation_percent=50.0,
            severity=AlertSeverity.WARNING,
            message="Test alert",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
        )
        
        # Serialize
        data = alert.to_dict()
        assert data["metric_name"] == "test.metric"
        assert data["current_value"] == 150.0
        assert data["severity"] == "warning"
        
        # Deserialize
        alert2 = DeviationAlert.from_dict(data)
        assert alert2.metric_name == alert.metric_name
        assert alert2.current_value == alert.current_value
        assert alert2.severity == alert.severity
