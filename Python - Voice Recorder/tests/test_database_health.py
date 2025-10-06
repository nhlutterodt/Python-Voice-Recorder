"""
Comprehensive tests for enhanced database health monitoring.
Tests health checks, monitoring system, alerts, and performance tracking.
"""

import pytest
import time
from unittest.mock import Mock, patch

# Test the enhanced database health monitoring
from core.database_health import (
    DatabaseHealthMonitor,
    HealthCheckResult,
    HealthCheckSeverity,
    HealthCheckStatus
)


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass"""
    
    def test_health_check_result_creation(self):
        """Test creating HealthCheckResult instances"""
        result = HealthCheckResult(
            name="test_check",
            status=HealthCheckStatus.PASS,
            severity=HealthCheckSeverity.INFO,
            message="Test passed",
            details={"value": 42}
        )
        
        assert result.name == "test_check"
        assert result.status == HealthCheckStatus.PASS
        assert result.severity == HealthCheckSeverity.INFO
        assert result.message == "Test passed"
        assert result.details == {"value": 42}
        assert result.timestamp is not None
    
    def test_health_check_result_defaults(self):
        """Test HealthCheckResult default values"""
        result = HealthCheckResult(
            name="simple_check",
            status=HealthCheckStatus.PASS,
            severity=HealthCheckSeverity.INFO
        )
        
        assert result.message == ""
        assert result.details == {}
    
    def test_health_check_severity_enum(self):
        """Test HealthCheckSeverity enum values"""
        assert HealthCheckSeverity.INFO.value == "info"
        assert HealthCheckSeverity.WARNING.value == "warning"
        assert HealthCheckSeverity.ERROR.value == "error"
        assert HealthCheckSeverity.CRITICAL.value == "critical"
    
    def test_health_check_status_enum(self):
        """Test HealthCheckStatus enum values"""
        assert HealthCheckStatus.PASS.value == "pass"
        assert HealthCheckStatus.WARNING.value == "warning" 
        assert HealthCheckStatus.FAIL.value == "fail"
        assert HealthCheckStatus.ERROR.value == "error"


class TestDatabaseHealthMonitor:
    """Test enhanced DatabaseHealthMonitor"""
    
    @pytest.fixture
    def health_monitor(self):
        """Create health monitor instance for testing"""
        return DatabaseHealthMonitor()
    
    @pytest.fixture
    def health_monitor_with_callback(self):
        """Create health monitor with mock alert callback"""
        callback = Mock()
        return DatabaseHealthMonitor(alert_callback=callback), callback
    
    def test_health_monitor_initialization(self, health_monitor):
        """Test health monitor initialization"""
        assert health_monitor.alert_callback is None
        assert len(health_monitor.health_history) == 0
        assert isinstance(health_monitor.health_checks, dict)
        assert len(health_monitor.health_checks) > 0  # Should have registered checks
    
    def test_health_monitor_with_callback_initialization(self, health_monitor_with_callback):
        """Test health monitor initialization with callback"""
        monitor, callback = health_monitor_with_callback
        assert monitor.alert_callback == callback
    
    def test_health_check_registry(self, health_monitor):
        """Test that health checks are properly registered"""
        expected_checks = [
            "database_connectivity",
            "query_performance", 
            "disk_space",
            "memory_usage",
            "table_integrity",
            "sqlite_integrity",
            "sqlite_wal_mode",
            "sqlite_vacuum_status"
        ]
        
        for check_name in expected_checks:
            assert check_name in health_monitor.health_checks
            assert callable(health_monitor.health_checks[check_name])
    
    @patch('core.database_context.db_context')
    def test_database_connectivity_check_success(self, mock_db_context, health_monitor):
        """Test successful database connectivity check"""
        # Mock successful database connection
        mock_session = Mock()
        mock_db_context.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value = Mock()
        
        result = health_monitor._check_database_connectivity()
        
        assert isinstance(result, HealthCheckResult)
        assert result.name == "database_connectivity"
        assert result.status == HealthCheckStatus.PASS
        assert result.severity == HealthCheckSeverity.INFO
        assert "Database connectivity successful" in result.message
    
    @patch('core.database_context.db_context')
    def test_database_connectivity_check_failure(self, mock_db_context, health_monitor):
        """Test failed database connectivity check"""
        # Mock database connection failure
        mock_db_context.get_session.side_effect = Exception("Connection failed")
        
        result = health_monitor._check_database_connectivity()
        
        assert isinstance(result, HealthCheckResult)
        assert result.name == "database_connectivity"
        assert result.status == HealthCheckStatus.ERROR
        assert result.severity == HealthCheckSeverity.CRITICAL
        assert "Database connectivity failed" in result.message
    
    @patch('core.database_context.db_context')
    @patch('time.time')
    def test_query_performance_check_fast(self, mock_time, mock_db_context, health_monitor):
        """Test query performance check with fast query"""
        # Mock fast query (50ms)
        mock_time.side_effect = [1000.0, 1000.05]  # 50ms difference
        
        mock_session = Mock()
        mock_db_context.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value = Mock()
        
        result = health_monitor._check_query_performance()
        
        assert result.status == HealthCheckStatus.PASS
        assert result.severity == HealthCheckSeverity.INFO
        assert "50.0 ms" in result.message
    
    @patch('core.database_context.db_context')
    @patch('time.time')
    def test_query_performance_check_slow(self, mock_time, mock_db_context, health_monitor):
        """Test query performance check with slow query"""
        # Mock slow query (600ms)
        mock_time.side_effect = [1000.0, 1000.6]  # 600ms difference
        
        mock_session = Mock()
        mock_db_context.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value = Mock()
        
        result = health_monitor._check_query_performance()
        
        assert result.status == HealthCheckStatus.WARNING
        assert result.severity == HealthCheckSeverity.WARNING
        assert "600.0 ms" in result.message
    
    @patch('psutil.disk_usage')
    def test_disk_space_check_sufficient(self, mock_disk_usage, health_monitor):
        """Test disk space check with sufficient space"""
        # Mock sufficient disk space (50% usage)
        mock_disk_usage.return_value = Mock(
            total=1000 * 1024 * 1024 * 1024,  # 1TB
            free=500 * 1024 * 1024 * 1024,    # 500GB free
            used=500 * 1024 * 1024 * 1024     # 500GB used
        )
        
        result = health_monitor._check_disk_space()
        
        assert result.status == HealthCheckStatus.PASS
        assert result.severity == HealthCheckSeverity.INFO
        assert "50.0%" in result.message
    
    @patch('psutil.disk_usage')
    def test_disk_space_check_warning(self, mock_disk_usage, health_monitor):
        """Test disk space check with warning level usage"""
        # Mock warning level disk space (85% usage)
        mock_disk_usage.return_value = Mock(
            total=1000 * 1024 * 1024 * 1024,  # 1TB
            free=150 * 1024 * 1024 * 1024,    # 150GB free
            used=850 * 1024 * 1024 * 1024     # 850GB used
        )
        
        result = health_monitor._check_disk_space()
        
        assert result.status == HealthCheckStatus.WARNING
        assert result.severity == HealthCheckSeverity.WARNING
        assert "85.0%" in result.message
    
    @patch('psutil.disk_usage')
    def test_disk_space_check_critical(self, mock_disk_usage, health_monitor):
        """Test disk space check with critical level usage"""
        # Mock critical disk space (95% usage)
        mock_disk_usage.return_value = Mock(
            total=1000 * 1024 * 1024 * 1024,  # 1TB
            free=50 * 1024 * 1024 * 1024,     # 50GB free
            used=950 * 1024 * 1024 * 1024     # 950GB used
        )
        
        result = health_monitor._check_disk_space()
        
        assert result.status == HealthCheckStatus.FAIL
        assert result.severity == HealthCheckSeverity.CRITICAL
        assert "95.0%" in result.message
    
    @patch('psutil.virtual_memory')
    def test_memory_usage_check_normal(self, mock_memory, health_monitor):
        """Test memory usage check with normal usage"""
        # Mock normal memory usage (60%)
        mock_memory.return_value = Mock(
            percent=60.0,
            available=8 * 1024 * 1024 * 1024,  # 8GB available
            total=20 * 1024 * 1024 * 1024      # 20GB total
        )
        
        result = health_monitor._check_memory_usage()
        
        assert result.status == HealthCheckStatus.PASS
        assert result.severity == HealthCheckSeverity.INFO
        assert "60.0%" in result.message
    
    @patch('psutil.virtual_memory')
    def test_memory_usage_check_high(self, mock_memory, health_monitor):
        """Test memory usage check with high usage"""
        # Mock high memory usage (90%)
        mock_memory.return_value = Mock(
            percent=90.0,
            available=2 * 1024 * 1024 * 1024,  # 2GB available
            total=20 * 1024 * 1024 * 1024      # 20GB total
        )
        
        result = health_monitor._check_memory_usage()
        
        assert result.status == HealthCheckStatus.WARNING
        assert result.severity == HealthCheckSeverity.WARNING
        assert "90.0%" in result.message
    
    @patch('core.database_context.db_context')
    def test_table_integrity_check_success(self, mock_db_context, health_monitor):
        """Test successful table integrity check"""
        mock_session = Mock()
        mock_db_context.get_session.return_value.__enter__.return_value = mock_session
        
        # Mock table count query result
        mock_session.execute.return_value.fetchone.return_value = (5,)  # 5 tables
        
        result = health_monitor._check_table_integrity()
        
        assert result.status == HealthCheckStatus.PASS
        assert result.severity == HealthCheckSeverity.INFO
        assert "5 tables found" in result.message
    
    @patch('core.database_context.db_context')
    def test_table_integrity_check_no_tables(self, mock_db_context, health_monitor):
        """Test table integrity check with no tables"""
        mock_session = Mock()
        mock_db_context.get_session.return_value.__enter__.return_value = mock_session
        
        # Mock no tables found
        mock_session.execute.return_value.fetchone.return_value = (0,)
        
        result = health_monitor._check_table_integrity()
        
        assert result.status == HealthCheckStatus.WARNING
        assert result.severity == HealthCheckSeverity.WARNING
        assert "No tables found" in result.message
    
    def test_run_health_checks(self, health_monitor):
        """Test running all health checks"""
        # Mock all individual health check methods
        with patch.object(health_monitor, '_check_database_connectivity') as mock_conn, \
             patch.object(health_monitor, '_check_query_performance') as mock_perf, \
             patch.object(health_monitor, '_check_disk_space') as mock_disk, \
             patch.object(health_monitor, '_check_memory_usage') as mock_memory, \
             patch.object(health_monitor, '_check_table_integrity') as mock_table, \
             patch.object(health_monitor, '_check_sqlite_integrity') as mock_sqlite, \
             patch.object(health_monitor, '_check_sqlite_wal_mode') as mock_wal, \
             patch.object(health_monitor, '_check_sqlite_vacuum_status') as mock_vacuum:
            
            # Configure mock return values
            mock_conn.return_value = HealthCheckResult("connectivity", HealthCheckStatus.PASS, HealthCheckSeverity.INFO)
            mock_perf.return_value = HealthCheckResult("performance", HealthCheckStatus.PASS, HealthCheckSeverity.INFO)
            mock_disk.return_value = HealthCheckResult("disk", HealthCheckStatus.PASS, HealthCheckSeverity.INFO)
            mock_memory.return_value = HealthCheckResult("memory", HealthCheckStatus.PASS, HealthCheckSeverity.INFO)
            mock_table.return_value = HealthCheckResult("table", HealthCheckStatus.PASS, HealthCheckSeverity.INFO)
            mock_sqlite.return_value = HealthCheckResult("sqlite", HealthCheckStatus.PASS, HealthCheckSeverity.INFO)
            mock_wal.return_value = HealthCheckResult("wal", HealthCheckStatus.PASS, HealthCheckSeverity.INFO)
            mock_vacuum.return_value = HealthCheckResult("vacuum", HealthCheckStatus.PASS, HealthCheckSeverity.INFO)
            
            results = health_monitor._run_health_checks()
            
            assert len(results) == 8  # All checks should run
            assert all(isinstance(result, HealthCheckResult) for result in results)
    
    def test_get_health_status(self, health_monitor):
        """Test getting comprehensive health status"""
        # Mock health checks to return predictable results
        with patch.object(health_monitor, '_run_health_checks') as mock_checks, \
             patch.object(health_monitor, '_get_enhanced_engine_info') as mock_engine, \
             patch.object(health_monitor, '_get_enhanced_performance_metrics') as mock_metrics, \
             patch.object(health_monitor, '_get_system_resource_status') as mock_resources:
            
            mock_checks.return_value = [
                HealthCheckResult("test1", HealthCheckStatus.PASS, HealthCheckSeverity.INFO),
                HealthCheckResult("test2", HealthCheckStatus.WARNING, HealthCheckSeverity.WARNING)
            ]
            mock_engine.return_value = {"driver": "sqlite"}
            mock_metrics.return_value = {"simple_query_ms": 50}
            mock_resources.return_value = {"memory": {"usage_percent": 60}}
            
            status = health_monitor.get_health_status()
            
            assert "health_checks" in status
            assert "engine_info" in status
            assert "performance_metrics" in status
            assert "system_resources" in status
            assert "recommendations" in status
            assert "overall_status" in status
            assert len(status["health_checks"]) == 2
    
    def test_alert_callback_triggered(self, health_monitor_with_callback):
        """Test that alert callback is triggered for critical issues"""
        monitor, callback = health_monitor_with_callback
        
        # Create a critical health check result
        critical_result = HealthCheckResult(
            "critical_check", 
            HealthCheckStatus.FAIL, 
            HealthCheckSeverity.CRITICAL,
            message="Critical failure"
        )
        
        # Mock health checks to return critical result
        with patch.object(monitor, '_run_health_checks') as mock_checks:
            mock_checks.return_value = [critical_result]
            
            monitor.get_health_status()
            
            # Verify callback was called with critical result
            callback.assert_called_once_with(critical_result)
    
    def test_alert_callback_not_triggered_for_normal_issues(self, health_monitor_with_callback):
        """Test that alert callback is not triggered for normal/info issues"""
        monitor, callback = health_monitor_with_callback
        
        # Create an info-level health check result
        info_result = HealthCheckResult(
            "info_check", 
            HealthCheckStatus.PASS, 
            HealthCheckSeverity.INFO,
            message="All good"
        )
        
        # Mock health checks to return info result
        with patch.object(monitor, '_run_health_checks') as mock_checks:
            mock_checks.return_value = [info_result]
            
            monitor.get_health_status()
            
            # Verify callback was not called
            callback.assert_not_called()
    
    def test_health_trend_analysis_insufficient_data(self, health_monitor):
        """Test health trend analysis with insufficient data"""
        trends = health_monitor._analyze_health_trends()
        assert trends["status"] == "insufficient_data"
    
    def test_health_trend_analysis_with_data(self, health_monitor):
        """Test health trend analysis with sufficient data"""
        # Add some health history
        for i in range(10):
            health_monitor.health_history.append({
                "timestamp": time.time() - (i * 60),
                "overall_status": "healthy"
            })
        
        trends = health_monitor._analyze_health_trends()
        assert "performance" in trends
        assert trends["performance"] == "stable"
    
    def test_generate_recommendations_no_issues(self, health_monitor):
        """Test recommendation generation with no issues"""
        health_status = {
            "health_checks": [
                {"status": "pass", "severity": "info"},
                {"status": "pass", "severity": "info"}
            ]
        }
        
        recommendations = health_monitor._generate_recommendations(health_status)
        
        assert len(recommendations) == 1
        assert "no immediate actions required" in recommendations[0].lower()
    
    def test_generate_recommendations_with_failures(self, health_monitor):
        """Test recommendation generation with failures"""
        health_status = {
            "health_checks": [
                {"status": "fail", "severity": "critical"},
                {"status": "error", "severity": "error"},
                {"status": "warning", "severity": "warning"}
            ]
        }
        
        recommendations = health_monitor._generate_recommendations(health_status)
        
        assert len(recommendations) >= 2
        assert any("failed health checks" in rec.lower() for rec in recommendations)
        assert any("warnings" in rec.lower() for rec in recommendations)
    
    def test_calculate_overall_status_healthy(self, health_monitor):
        """Test overall status calculation for healthy system"""
        health_status = {
            "health_checks": [
                {"status": "pass", "severity": "info"},
                {"status": "pass", "severity": "info"}
            ]
        }
        
        status = health_monitor._calculate_overall_status(health_status)
        assert status == "healthy"
    
    def test_calculate_overall_status_critical(self, health_monitor):
        """Test overall status calculation for critical system"""
        health_status = {
            "health_checks": [
                {"status": "fail", "severity": "critical"},
                {"status": "pass", "severity": "info"}
            ]
        }
        
        status = health_monitor._calculate_overall_status(health_status)
        assert status == "critical"
    
    def test_calculate_overall_status_unhealthy(self, health_monitor):
        """Test overall status calculation for unhealthy system"""
        health_status = {
            "health_checks": [
                {"status": "error", "severity": "error"},
                {"status": "pass", "severity": "info"}
            ]
        }
        
        status = health_monitor._calculate_overall_status(health_status)
        assert status == "unhealthy"
    
    def test_calculate_overall_status_degraded(self, health_monitor):
        """Test overall status calculation for degraded system"""
        health_status = {
            "health_checks": [
                {"status": "warning", "severity": "warning"},
                {"status": "warning", "severity": "warning"},
                {"status": "warning", "severity": "warning"}
            ]
        }
        
        status = health_monitor._calculate_overall_status(health_status)
        assert status == "degraded"
    
    def test_backward_compatibility_methods(self, health_monitor):
        """Test that backward compatibility methods work"""
        # Mock the enhanced methods
        with patch.object(health_monitor, '_get_enhanced_engine_info') as mock_enhanced_engine, \
             patch.object(health_monitor, '_get_enhanced_performance_metrics') as mock_enhanced_perf:
            
            mock_enhanced_engine.return_value = {"test": "data"}
            mock_enhanced_perf.return_value = {"test": "metrics"}
            
            # Test backward compatibility methods
            engine_info = health_monitor._get_engine_info()
            perf_metrics = health_monitor._get_performance_metrics()
            
            assert engine_info == {"test": "data"}
            assert perf_metrics == {"test": "metrics"}
            
            # Verify enhanced methods were called
            mock_enhanced_engine.assert_called_once()
            mock_enhanced_perf.assert_called_once()


class TestHealthMonitoringIntegration:
    """Integration tests for health monitoring scenarios"""
    
    def test_complete_health_check_cycle(self):
        """Test a complete health monitoring cycle"""
        callback_results = []
        
        def alert_callback(result: HealthCheckResult):
            callback_results.append(result)
        
        monitor = DatabaseHealthMonitor(alert_callback=alert_callback)
        
        # Mock various system states
        with patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('core.database_context.db_context') as mock_db:
            
            # Mock healthy system
            mock_disk.return_value = Mock(total=1000*1024*1024*1024, free=600*1024*1024*1024, used=400*1024*1024*1024)
            mock_memory.return_value = Mock(percent=50.0, available=8*1024*1024*1024, total=16*1024*1024*1024)
            
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__.return_value = mock_session
            mock_session.execute.return_value.fetchone.return_value = (5,)  # 5 tables
            
            # Run health check
            status = monitor.get_health_status()
            
            # Verify status structure
            assert "health_checks" in status
            assert "overall_status" in status
            assert "recommendations" in status
            
            # Should be healthy system
            assert status["overall_status"] in ["healthy", "healthy_with_warnings"]
            
            # No critical alerts should be triggered
            critical_alerts = [r for r in callback_results if r.severity == HealthCheckSeverity.CRITICAL]
            assert len(critical_alerts) == 0
    
    def test_unhealthy_system_monitoring(self):
        """Test monitoring of an unhealthy system"""
        callback_results = []
        
        def alert_callback(result: HealthCheckResult):
            callback_results.append(result)
        
        monitor = DatabaseHealthMonitor(alert_callback=alert_callback)
        
        # Mock unhealthy system
        with patch('psutil.disk_usage') as mock_disk, \
             patch('psutil.virtual_memory') as mock_memory, \
             patch('core.database_context.db_context') as mock_db:
            
            # Mock critical disk space and high memory
            mock_disk.return_value = Mock(total=1000*1024*1024*1024, free=20*1024*1024*1024, used=980*1024*1024*1024)  # 98% used
            mock_memory.return_value = Mock(percent=95.0, available=1*1024*1024*1024, total=16*1024*1024*1024)  # 95% used
            
            # Mock database connection failure
            mock_db.get_session.side_effect = Exception("Database unavailable")
            
            # Run health check
            status = monitor.get_health_status()
            
            # Should detect critical issues
            assert status["overall_status"] in ["critical", "unhealthy"]
            
            # Should have triggered critical alerts
            critical_alerts = [r for r in callback_results if r.severity == HealthCheckSeverity.CRITICAL]
            assert len(critical_alerts) > 0
            
            # Should have recommendations
            assert len(status["recommendations"]) > 0
            assert any("failed health checks" in rec.lower() for rec in status["recommendations"])


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
