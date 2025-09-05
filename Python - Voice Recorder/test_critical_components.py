"""
Comprehensive integration tests for all critical enhanced components.
This script validates that all enhanced database context management components work together.
"""

import sys
import time
import traceback
from pathlib import Path
from typing import List, Dict, Any

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import all critical enhanced components
try:
    from core.database_context import DatabaseConfig, DatabaseContextManager
    from core.database_health import DatabaseHealthMonitor, HealthCheckResult, HealthCheckSeverity
    from models.database import SessionLocal, engine
    print("✅ All critical enhanced components imported successfully")
except ImportError as e:
    print(f"❌ Failed to import critical components: {e}")
    sys.exit(1)


class CriticalComponentsTester:
    """Comprehensive tester for all critical enhanced components"""
    
    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.passed_tests = 0
        self.failed_tests = 0
    
    def log_test(self, test_name: str, success: bool, details: str = "", error: str = ""):
        """Log test result"""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "error": error,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        
        if success:
            self.passed_tests += 1
            print(f"✅ {test_name}: {details}")
        else:
            self.failed_tests += 1
            print(f"❌ {test_name}: {error}")
    
    def test_database_config_environments(self):
        """Test DatabaseConfig with different environments"""
        try:
            # Test development environment
            dev_config = DatabaseConfig.from_environment("development")
            assert hasattr(dev_config, 'min_disk_space_mb')
            assert hasattr(dev_config, 'circuit_breaker_threshold')
            
            # Test production environment  
            prod_config = DatabaseConfig.from_environment("production")
            assert hasattr(prod_config, 'retry_attempts')
            assert hasattr(prod_config, 'connection_timeout')
            
            # Test testing environment
            test_config = DatabaseConfig.from_environment("testing")
            assert hasattr(test_config, 'enable_disk_space_check')
            
            self.log_test(
                "DatabaseConfig Environment Configurations",
                True,
                f"Dev: {dev_config.min_disk_space_mb}MB, Prod: {prod_config.min_disk_space_mb}MB, Test: {test_config.enable_disk_space_check}"
            )
            
        except Exception as e:
            self.log_test("DatabaseConfig Environment Configurations", False, error=str(e))
    
    def test_database_context_manager_initialization(self):
        """Test DatabaseContextManager initialization and basic functionality"""
        try:
            config = DatabaseConfig.from_environment("testing")
            context_manager = DatabaseContextManager(SessionLocal, config)
            
            # Test initialization
            assert context_manager.config == config
            assert context_manager._circuit_breaker_failures == 0
            assert context_manager._active_sessions == 0
            
            # Test metrics
            metrics = context_manager.get_session_metrics()
            assert "active_sessions" in metrics
            assert "total_sessions_created" in metrics
            assert metrics["active_sessions"] == 0
            
            self.log_test(
                "DatabaseContextManager Initialization",
                True,
                f"Config: {config.min_disk_space_mb}MB disk space, {config.circuit_breaker_threshold} CB threshold"
            )
            
        except Exception as e:
            self.log_test("DatabaseContextManager Initialization", False, error=str(e))
    
    def test_database_context_session_creation(self):
        """Test database session creation and cleanup"""
        try:
            config = DatabaseConfig.from_environment("testing")  # Disable disk space check for testing
            context_manager = DatabaseContextManager(SessionLocal, config)
            
            # Test session creation and cleanup
            initial_metrics = context_manager.get_session_metrics()
            
            with context_manager.get_session() as session:
                # Verify session is active
                active_metrics = context_manager.get_session_metrics()
                assert active_metrics["active_sessions"] == 1
                assert active_metrics["total_sessions_created"] == 1
                
                # Test basic session functionality
                result = session.execute("SELECT 1").fetchone()
                assert result is not None
            
            # Verify session cleanup
            final_metrics = context_manager.get_session_metrics()
            assert final_metrics["active_sessions"] == 0
            assert final_metrics["total_sessions_created"] == 1
            
            self.log_test(
                "Database Session Creation and Cleanup",
                True,
                f"Created and cleaned up 1 session, final active: {final_metrics['active_sessions']}"
            )
            
        except Exception as e:
            self.log_test("Database Session Creation and Cleanup", False, error=str(e))
    
    def test_circuit_breaker_functionality(self):
        """Test circuit breaker pattern functionality"""
        try:
            config = DatabaseConfig(
                circuit_breaker_threshold=2,
                circuit_breaker_timeout=1,
                enable_disk_space_check=False  # Disable for testing
            )
            context_manager = DatabaseContextManager(SessionLocal, config)
            
            # Test circuit breaker is initially closed
            assert not context_manager._is_circuit_breaker_open()
            
            # Simulate failures to open circuit breaker
            context_manager._circuit_breaker_failures = config.circuit_breaker_threshold
            context_manager._circuit_breaker_last_failure = time.time()
            
            # Circuit breaker should be open
            assert context_manager._is_circuit_breaker_open()
            
            # Test timeout recovery
            context_manager._circuit_breaker_last_failure = time.time() - (config.circuit_breaker_timeout + 1)
            assert not context_manager._is_circuit_breaker_open()
            
            # Test reset
            context_manager._circuit_breaker_failures = 3
            context_manager._reset_circuit_breaker()
            assert context_manager._circuit_breaker_failures == 0
            
            self.log_test(
                "Circuit Breaker Functionality",
                True,
                f"Threshold: {config.circuit_breaker_threshold}, Timeout: {config.circuit_breaker_timeout}s"
            )
            
        except Exception as e:
            self.log_test("Circuit Breaker Functionality", False, error=str(e))
    
    def test_health_monitor_initialization(self):
        """Test DatabaseHealthMonitor initialization and basic functionality"""
        try:
            # Test without callback
            health_monitor = DatabaseHealthMonitor()
            assert health_monitor.alert_callback is None
            assert len(health_monitor.health_history) == 0
            assert isinstance(health_monitor.health_checks, dict)
            assert len(health_monitor.health_checks) > 0
            
            # Test with callback
            callback_calls = []
            def test_callback(result):
                callback_calls.append(result)
            
            health_monitor_with_callback = DatabaseHealthMonitor(alert_callback=test_callback)
            assert health_monitor_with_callback.alert_callback == test_callback
            
            self.log_test(
                "Health Monitor Initialization",
                True,
                f"Registered {len(health_monitor.health_checks)} health checks"
            )
            
        except Exception as e:
            self.log_test("Health Monitor Initialization", False, error=str(e))
    
    def test_health_check_registry(self):
        """Test that all expected health checks are registered"""
        try:
            health_monitor = DatabaseHealthMonitor()
            
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
            
            missing_checks = []
            for check_name in expected_checks:
                if check_name not in health_monitor.health_checks:
                    missing_checks.append(check_name)
            
            if missing_checks:
                raise AssertionError(f"Missing health checks: {missing_checks}")
            
            # Verify all checks are callable
            non_callable_checks = []
            for check_name, check_func in health_monitor.health_checks.items():
                if not callable(check_func):
                    non_callable_checks.append(check_name)
            
            if non_callable_checks:
                raise AssertionError(f"Non-callable health checks: {non_callable_checks}")
            
            self.log_test(
                "Health Check Registry",
                True,
                f"All {len(expected_checks)} expected health checks registered and callable"
            )
            
        except Exception as e:
            self.log_test("Health Check Registry", False, error=str(e))
    
    def test_health_status_generation(self):
        """Test comprehensive health status generation"""
        try:
            health_monitor = DatabaseHealthMonitor()
            
            # Get health status
            status = health_monitor.get_health_status()
            
            # Verify status structure
            required_keys = [
                "health_checks",
                "engine_info", 
                "performance_metrics",
                "system_resources",
                "recommendations",
                "overall_status"
            ]
            
            missing_keys = []
            for key in required_keys:
                if key not in status:
                    missing_keys.append(key)
            
            if missing_keys:
                raise AssertionError(f"Missing status keys: {missing_keys}")
            
            # Verify health checks structure
            health_checks = status["health_checks"]
            if not isinstance(health_checks, list):
                raise AssertionError("health_checks should be a list")
            
            if len(health_checks) == 0:
                raise AssertionError("No health checks were executed")
            
            # Verify recommendations
            recommendations = status["recommendations"]
            if not isinstance(recommendations, list):
                raise AssertionError("recommendations should be a list")
            
            self.log_test(
                "Health Status Generation",
                True,
                f"Generated status with {len(health_checks)} checks, overall: {status['overall_status']}"
            )
            
        except Exception as e:
            self.log_test("Health Status Generation", False, error=str(e))
    
    def test_integration_database_context_and_health(self):
        """Test integration between database context and health monitoring"""
        try:
            # Create components
            config = DatabaseConfig.from_environment("testing")
            context_manager = DatabaseContextManager(SessionLocal, config)
            health_monitor = DatabaseHealthMonitor()
            
            # Test database connectivity through context manager
            with context_manager.get_session() as session:
                result = session.execute("SELECT 1").fetchone()
                assert result is not None
            
            # Test health monitoring
            status = health_monitor.get_health_status()
            
            # Verify integration points
            assert "database_connectivity" in [check.get("name", "") for check in status["health_checks"]]
            assert status["overall_status"] in ["healthy", "healthy_with_warnings", "degraded", "unhealthy", "critical"]
            
            self.log_test(
                "Database Context and Health Integration",
                True,
                f"Context manager and health monitor working together, status: {status['overall_status']}"
            )
            
        except Exception as e:
            self.log_test("Database Context and Health Integration", False, error=str(e))
    
    def test_error_handling_and_exceptions(self):
        """Test custom error handling and exception classes"""
        try:
            from core.database_context import (
                DatabaseDiskSpaceError,
                DatabaseCircuitBreakerError, 
                DatabaseConnectionError,
                DatabaseTimeoutError,
                DatabaseIntegrityError
            )
            
            # Test exception creation and attributes
            disk_error = DatabaseDiskSpaceError("Disk full", required_mb=100, available_mb=50)
            assert disk_error.required_mb == 100
            assert disk_error.available_mb == 50
            
            cb_error = DatabaseCircuitBreakerError("Circuit open", failure_count=5, timeout_seconds=60)
            assert cb_error.failure_count == 5
            assert cb_error.timeout_seconds == 60
            
            conn_error = DatabaseConnectionError("Connection failed", Exception("Original"), retry_count=3)
            assert conn_error.retry_count == 3
            assert conn_error.original_error is not None
            
            timeout_error = DatabaseTimeoutError("Timeout", timeout_seconds=30, operation="query")
            assert timeout_error.timeout_seconds == 30
            assert timeout_error.operation == "query"
            
            integrity_error = DatabaseIntegrityError("Corruption", corruption_type="table", affected_tables=["test"])
            assert integrity_error.corruption_type == "table"
            assert integrity_error.affected_tables == ["test"]
            
            self.log_test(
                "Error Handling and Custom Exceptions",
                True,
                "All custom exception classes created and tested successfully"
            )
            
        except Exception as e:
            self.log_test("Error Handling and Custom Exceptions", False, error=str(e))
    
    def test_backward_compatibility(self):
        """Test that backward compatibility is maintained"""
        try:
            # Test that original database functionality still works
            from models.database import SessionLocal, engine
            
            # Test basic session creation (original way)
            session = SessionLocal()
            result = session.execute("SELECT 1").fetchone()
            session.close()
            assert result is not None
            
            # Test that enhanced components don't break existing functionality
            config = DatabaseConfig.from_environment("testing")
            context_manager = DatabaseContextManager(SessionLocal, config)
            health_monitor = DatabaseHealthMonitor()
            
            # Test enhanced functionality doesn't interfere with basic operations
            with context_manager.get_session() as enhanced_session:
                enhanced_result = enhanced_session.execute("SELECT 1").fetchone()
                assert enhanced_result is not None
            
            self.log_test(
                "Backward Compatibility",
                True,
                "Original database functionality preserved alongside enhanced features"
            )
            
        except Exception as e:
            self.log_test("Backward Compatibility", False, error=str(e))
    
    def run_all_tests(self):
        """Run all critical component tests"""
        print("🧪 Starting comprehensive critical components testing...")
        print("=" * 60)
        
        # Run all tests
        self.test_database_config_environments()
        self.test_database_context_manager_initialization()
        self.test_database_context_session_creation()
        self.test_circuit_breaker_functionality()
        self.test_health_monitor_initialization()
        self.test_health_check_registry()
        self.test_health_status_generation()
        self.test_integration_database_context_and_health()
        self.test_error_handling_and_exceptions()
        self.test_backward_compatibility()
        
        print("=" * 60)
        print(f"🎯 Testing Complete: {self.passed_tests} passed, {self.failed_tests} failed")
        
        if self.failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   • {result['test_name']}: {result['error']}")
        
        return self.failed_tests == 0
    
    def generate_test_report(self) -> str:
        """Generate comprehensive test report"""
        report = []
        report.append("# Critical Components Testing Report")
        report.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        report.append("## Summary")
        report.append(f"- Total Tests: {len(self.test_results)}")
        report.append(f"- Passed: {self.passed_tests}")
        report.append(f"- Failed: {self.failed_tests}")
        report.append(f"- Success Rate: {(self.passed_tests / len(self.test_results) * 100):.1f}%")
        report.append("")
        
        report.append("## Test Results")
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            report.append(f"### {result['test_name']} - {status}")
            
            if result["success"]:
                report.append(f"**Details:** {result['details']}")
            else:
                report.append(f"**Error:** {result['error']}")
            
            report.append("")
        
        return "\n".join(report)


def main():
    """Main testing function"""
    try:
        tester = CriticalComponentsTester()
        success = tester.run_all_tests()
        
        # Generate and save test report
        report = tester.generate_test_report()
        report_path = Path("docs/CRITICAL_COMPONENTS_TEST_REPORT.md")
        report_path.write_text(report, encoding="utf-8")
        print(f"\n📊 Test report saved to: {report_path}")
        
        if success:
            print("\n🎉 All critical components are working correctly!")
            return 0
        else:
            print("\n⚠️  Some critical components have issues that need attention.")
            return 1
            
    except Exception as e:
        print(f"\n💥 Critical testing error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
