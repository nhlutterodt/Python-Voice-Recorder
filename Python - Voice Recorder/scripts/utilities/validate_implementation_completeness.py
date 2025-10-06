#!/usr/bin/env python3
"""
Comprehensive Implementation Validation Script
Double-check that all backend enhancements are perfectly implemented
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from models.database import db_context
from core.database_health import DatabaseHealthMonitor
from services.enhanced_file_storage import (
    EnhancedFileStorageService, DatabaseSessionError, FileConstraintError, StorageOperationError,
    StorageValidationError
)
from core.logging_config import setup_application_logging
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from performance_monitor import PerformanceBenchmark

# Setup logging
logger = setup_application_logging("INFO")

def validate_logging_configuration():
    """Validate that logging is properly configured across all modules"""
    print("🔍 Validating Logging Configuration...")
    
    # Check that application-wide logging is configured
    import logging
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0, "Root logger has no handlers configured"
    
    # Check that VoiceRecorderPro namespace is being used
    test_logger = logging.getLogger("VoiceRecorderPro.test")
    assert test_logger.parent.name == "VoiceRecorderPro", "Logger hierarchy not properly configured"
    
    print("   ✅ Application-wide logging properly configured")
    print("   ✅ Logger hierarchy using VoiceRecorderPro namespace")
    
    return True

def validate_database_context_management():
    """Validate enhanced database context management"""
    print("🔍 Validating Database Context Management...")
    
    # Test that db_context uses proper session factory
    assert hasattr(db_context, 'session_factory'), "DatabaseContextManager missing session_factory"
    assert callable(db_context.session_factory), "session_factory is not callable"
    
    # Create service and test _managed_session
    health_monitor = DatabaseHealthMonitor(lambda x: print(f"Alert: {x}"))
    service = EnhancedFileStorageService(
        context_manager=db_context,
        health_monitor=health_monitor,
        environment='testing'
    )
    
    # Test that _managed_session works
    with service._managed_session("validation_test") as session:
        assert session is not None, "Session is None"
        assert hasattr(session, 'query'), "Session missing query method"
        assert hasattr(session, 'add'), "Session missing add method"
        assert hasattr(session, 'commit'), "Session missing commit method"
    
    print("   ✅ DatabaseContextManager properly initialized")
    print("   ✅ _managed_session context manager working")
    print("   ✅ Session has all required methods")
    
    return True

def validate_exception_handling():
    """Validate specific exception handling implementation"""
    print("🔍 Validating Exception Handling Enhancement...")
    
    # Test that all exception classes exist and inherit from Exception
    assert issubclass(DatabaseSessionError, Exception), "DatabaseSessionError not Exception subclass"
    assert issubclass(FileConstraintError, Exception), "FileConstraintError not Exception subclass"
    assert issubclass(StorageOperationError, Exception), "StorageOperationError not Exception subclass"
    assert issubclass(StorageValidationError, Exception), "StorageValidationError not Exception subclass"
    
    # Test exception raising with file constraints
    health_monitor = DatabaseHealthMonitor(lambda x: print(f"Alert: {x}"))
    service = EnhancedFileStorageService(
        context_manager=db_context,
        health_monitor=health_monitor,
        environment='testing'
    )
    
    # Test file size constraint exception
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as large_file:
            # Write more than the testing limit (100MB)
            large_file.write(b"x" * (101 * 1024 * 1024))  # 101MB
            large_file_path = large_file.name
        
        service._validate_file_constraints(large_file_path)
        assert False, "Expected FileConstraintError not raised"
    except FileConstraintError as e:
        assert "File size" in str(e) and "exceeds maximum" in str(e), "Incorrect error message"
        os.unlink(large_file_path)
    
    # Test non-existent file exception
    try:
        service._validate_file_constraints("/absolutely/non/existent/file.wav")
        assert False, "Expected FileConstraintError not raised"
    except FileConstraintError as e:
        assert "does not exist" in str(e), "Incorrect error message for non-existent file"
    
    print("   ✅ All exception classes properly defined")
    print("   ✅ FileConstraintError properly raised for size violations")
    print("   ✅ FileConstraintError properly raised for non-existent files")
    
    return True

def validate_performance_monitoring():
    """Validate performance monitoring integration"""
    print("🔍 Validating Performance Monitoring Integration...")
    
    # Test PerformanceBenchmark functionality
    benchmark = PerformanceBenchmark()
    
    # Test measure_operation context manager
    with benchmark.measure_operation("test_operation", test_param="value"):
        import time
        time.sleep(0.1)  # Small delay to measure
    
    # Check that metric was recorded
    assert len(benchmark.metrics) > 0, "No metrics recorded"
    metric = benchmark.metrics[0]
    assert metric.operation_name == "test_operation", "Incorrect operation name"
    assert metric.duration > 0.05, "Duration measurement seems incorrect"
    
    # Test service with performance monitoring enabled
    health_monitor = DatabaseHealthMonitor(lambda x: print(f"Alert: {x}"))
    service_with_perf = EnhancedFileStorageService(
        context_manager=db_context,
        health_monitor=health_monitor,
        environment='testing',
        enable_performance_monitoring=True
    )
    
    # Test service without performance monitoring  
    service_without_perf = EnhancedFileStorageService(
        context_manager=db_context,
        health_monitor=health_monitor,
        environment='testing',
        enable_performance_monitoring=False
    )
    
    assert service_with_perf.enable_performance_monitoring is True, "Performance monitoring not enabled"
    assert service_with_perf.performance_monitor is not None, "Performance monitor not initialized"
    assert service_without_perf.enable_performance_monitoring is False, "Performance monitoring incorrectly enabled"
    assert service_without_perf.performance_monitor is None, "Performance monitor incorrectly initialized"
    
    print("   ✅ PerformanceBenchmark measure_operation working")
    print("   ✅ Performance monitoring configurable in service")
    print("   ✅ Performance metrics properly recorded")
    
    return True

def validate_comprehensive_integration():
    """Validate that all enhancements work together"""
    print("🔍 Validating Comprehensive Integration...")
    
    # Create service with all enhancements enabled
    health_monitor = DatabaseHealthMonitor(lambda x: print(f"Alert: {x}"))
    service = EnhancedFileStorageService(
        context_manager=db_context,
        health_monitor=health_monitor,
        environment='testing',
        enable_performance_monitoring=True
    )
    
    # Test that enhanced session management works with performance monitoring
    test_passed = False
    with service._managed_session("integration_test") as session:
        # Session should be functional
        assert session is not None
        # Performance monitoring should be active
        assert service.performance_monitor is not None
        test_passed = True
    
    assert test_passed, "Integrated session management failed"
    
    # Test storage metrics collection (uses all enhancements)
    metrics = service.get_storage_metrics()
    required_sections = ['storage', 'database', 'recordings', 'environment', 'monitoring']
    for section in required_sections:
        assert section in metrics, f"Missing metrics section: {section}"
    
    # Verify monitoring section has performance data
    monitoring_data = metrics['monitoring']
    assert 'performance_enabled' in monitoring_data, "Performance status not in monitoring"
    assert monitoring_data['performance_enabled'] is True, "Performance monitoring not enabled in metrics"
    
    print("   ✅ Enhanced session management working with performance monitoring")
    print("   ✅ Storage metrics collection working with all enhancements")
    print("   ✅ All three enhancements properly integrated")
    
    return True

def main():
    """Run comprehensive validation"""
    print("🚀 COMPREHENSIVE IMPLEMENTATION VALIDATION")
    print("=" * 50)
    
    tests = [
        ("Logging Configuration", validate_logging_configuration),
        ("Database Context Management", validate_database_context_management),
        ("Exception Handling Enhancement", validate_exception_handling),
        ("Performance Monitoring Integration", validate_performance_monitoring),
        ("Comprehensive Integration", validate_comprehensive_integration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "✅ PASSED" if result else "❌ FAILED"
            print()
        except Exception as e:
            results[test_name] = f"❌ FAILED: {e}"
            print(f"   ❌ {test_name} failed: {e}")
            print()
    
    print("📊 VALIDATION RESULTS SUMMARY")
    print("=" * 40)
    for test_name, result in results.items():
        print(f"  {test_name}: {result}")
    
    # Overall status
    failed_tests = [name for name, result in results.items() if result.startswith("❌")]
    if failed_tests:
        print(f"\n🎯 Overall Status: ❌ {len(failed_tests)} VALIDATION(S) FAILED")
        return 1
    else:
        print("\n🎯 Overall Status: ✅ ALL VALIDATIONS PASSED")
        print("\n🎉 Implementation is PERFECT and COMPLETE!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
