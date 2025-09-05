#!/usr/bin/env python3
"""
Test script for enhanced backend features:
1. Database Context Management - Proper session handling
2. Exception Handling Enhancement - Specific error types
3. Performance Monitoring Integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import tempfile
import logging
from pathlib import Path
from services.enhanced_file_storage import (
    EnhancedFileStorageService, StorageConfig, 
    DatabaseSessionError, FileConstraintError, StorageOperationError
)
from models.database import SessionLocal, db_context
from core.database_health import DatabaseHealthMonitor

# Configure logging for testing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_context_management():
    """Test enhanced database context management"""
    print("🧪 Testing Database Context Management...")
    
    try:
        # Use existing database context instance
        health_monitor = DatabaseHealthMonitor(lambda x: print(f"Database Alert: {x}"))
        
        # Create service with performance monitoring enabled
        service = EnhancedFileStorageService(
            context_manager=db_context,
            health_monitor=health_monitor,
            environment='testing',
            enable_performance_monitoring=True
        )
        
        # Test enhanced session management
        print("   ✅ Service initialized with enhanced session management")
        
        # Test storage metrics collection (uses enhanced sessions)
        metrics = service.get_storage_metrics()
        assert 'storage' in metrics
        assert 'database' in metrics
        assert 'monitoring' in metrics
        assert metrics['monitoring']['performance_enabled'] is True
        
        print("   ✅ Enhanced session management working")
        return True
        
    except Exception as e:
        print(f"   ❌ Database context management test failed: {e}")
        return False

def test_exception_handling_enhancement():
    """Test enhanced exception handling with specific error types"""
    print("🧪 Testing Exception Handling Enhancement...")
    
    try:
        # Use existing database context instance
        health_monitor = DatabaseHealthMonitor(lambda x: print(f"Database Alert: {x}"))
        
        service = EnhancedFileStorageService(
            context_manager=db_context,
            health_monitor=health_monitor,
            environment='testing'
        )
        
        # Test FileConstraintError handling
        try:
            # Create a file that's too large for testing environment
            with tempfile.NamedTemporaryFile(delete=False) as large_file:
                # Write more than the testing limit (100MB in testing env)
                large_file.write(b"x" * (101 * 1024 * 1024))  # 101MB
                large_file_path = large_file.name
            
            # This should raise FileConstraintError
            service._validate_file_constraints(large_file_path)
            print("   ❌ Expected FileConstraintError not raised")
            return False
            
        except FileConstraintError as e:
            print(f"   ✅ FileConstraintError properly raised: {e}")
            os.unlink(large_file_path)
        except Exception as e:
            print(f"   ❌ Unexpected exception type: {type(e).__name__}: {e}")
            return False
        
        # Test FileConstraintError for non-existent file
        try:
            # Try to validate constraints on non-existent file
            service._validate_file_constraints("/non/existent/file.wav")
            print("   ❌ Expected FileConstraintError not raised")
            return False
            
        except FileConstraintError as e:
            print(f"   ✅ FileConstraintError properly raised for non-existent file: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected exception type: {type(e).__name__}: {e}")
            return False
        
        print("   ✅ Enhanced exception handling working correctly")
        return True
        
    except Exception as e:
        print(f"   ❌ Exception handling test failed: {e}")
        return False

def test_performance_monitoring_integration():
    """Test performance monitoring integration"""
    print("🧪 Testing Performance Monitoring Integration...")
    
    try:
        # Use existing database context instance
        health_monitor = DatabaseHealthMonitor(lambda x: print(f"Database Alert: {x}"))
        
        # Test with performance monitoring enabled
        service_with_perf = EnhancedFileStorageService(
            context_manager=db_context,
            health_monitor=health_monitor,
            environment='testing',
            enable_performance_monitoring=True
        )
        
        # Test without performance monitoring
        service_without_perf = EnhancedFileStorageService(
            context_manager=db_context,
            health_monitor=health_monitor,
            environment='testing',
            enable_performance_monitoring=False
        )
        
        # Test that performance monitoring is properly configured
        assert service_with_perf.enable_performance_monitoring is True
        assert service_with_perf.performance_monitor is not None
        assert service_without_perf.enable_performance_monitoring is False
        assert service_without_perf.performance_monitor is None
        
        print("   ✅ Performance monitoring configuration working")
        
        # Test metrics collection with performance monitoring
        metrics_with_perf = service_with_perf.get_storage_metrics()
        metrics_without_perf = service_without_perf.get_storage_metrics()
        
        # Both should have monitoring info but different performance flags
        assert metrics_with_perf['monitoring']['performance_enabled'] is True
        assert metrics_without_perf['monitoring']['performance_enabled'] is False
        
        print("   ✅ Performance monitoring integration working")
        return True
        
    except Exception as e:
        print(f"   ❌ Performance monitoring test failed: {e}")
        return False

def test_comprehensive_integration():
    """Test all enhancements working together"""
    print("🧪 Testing Comprehensive Integration...")
    
    try:
        # Use existing database context instance
        health_monitor = DatabaseHealthMonitor(lambda x: print(f"Database Alert: {x}"))
        
        # Create service with all enhancements enabled
        service = EnhancedFileStorageService(
            context_manager=db_context,
            health_monitor=health_monitor,
            environment='testing',
            enable_performance_monitoring=True
        )
        
        # Test enhanced session management in cleanup operation
        orphaned_files = service.cleanup_orphaned_files()
        assert isinstance(orphaned_files, list)
        
        print("   ✅ Enhanced session management in cleanup working")
        
        # Test metrics collection with all enhancements
        metrics = service.get_storage_metrics()
        required_sections = ['storage', 'database', 'recordings', 'environment', 'monitoring']
        for section in required_sections:
            assert section in metrics, f"Missing metrics section: {section}"
        
        print("   ✅ Storage metrics collection with enhanced error handling working")
        print("   ✅ Comprehensive metrics collection working")
        
        print("   ✅ All enhancements working together successfully")
        return True
        
    except Exception as e:
        print(f"   ❌ Comprehensive integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all enhancement tests"""
    print("🚀 TESTING BACKEND ENHANCEMENTS")
    print("=" * 50)
    
    test_results = {
        'Database Context Management': test_database_context_management(),
        'Exception Handling Enhancement': test_exception_handling_enhancement(),
        'Performance Monitoring Integration': test_performance_monitoring_integration(),
        'Comprehensive Integration': test_comprehensive_integration()
    }
    
    print("\n📊 TEST RESULTS SUMMARY")
    print("=" * 40)
    
    all_passed = True
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if not result:
            all_passed = False
    
    overall_status = "✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED"
    print(f"\n🎯 Overall Status: {overall_status}")
    
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
