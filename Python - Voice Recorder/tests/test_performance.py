#!/usr/bin/env python3
"""
Tests for performance monitoring module
"""
import time
import pytest

from core.performance import (
    track_execution_time,
    track_memory_usage,
    PerformanceTimer,
    MemoryTracker,
    get_performance_snapshot,
)
from core.structured_logging import EventCategory


class TestTrackExecutionTime:
    """Test track_execution_time decorator"""
    
    def test_decorator_basic(self):
        """Test basic decorator usage"""
        @track_execution_time()
        def sample_function():
            time.sleep(0.01)
            return "result"
        
        result = sample_function()
        assert result == "result"
    
    def test_decorator_with_exception(self):
        """Test decorator with exception"""
        @track_execution_time()
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_function()
    
    def test_decorator_with_custom_category(self):
        """Test decorator with custom category"""
        @track_execution_time(category=EventCategory.DATABASE)
        def database_function():
            return "db_result"
        
        result = database_function()
        assert result == "db_result"


class TestTrackMemoryUsage:
    """Test track_memory_usage decorator"""
    
    def test_decorator_basic(self):
        """Test basic decorator usage"""
        @track_memory_usage()
        def memory_function():
            # Allocate some memory
            data = [i for i in range(1000)]
            return len(data)
        
        result = memory_function()
        assert result == 1000
    
    def test_decorator_with_exception(self):
        """Test decorator with exception"""
        @track_memory_usage()
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_function()
    
    def test_decorator_with_custom_category(self):
        """Test decorator with custom category"""
        @track_memory_usage(category=EventCategory.EDITING)
        def editing_function():
            return "edit_result"
        
        result = editing_function()
        assert result == "edit_result"


class TestPerformanceTimer:
    """Test PerformanceTimer context manager"""
    
    def test_timer_basic(self):
        """Test basic timer usage"""
        with PerformanceTimer("test_operation", log_result=False) as timer:
            time.sleep(0.01)
        
        assert timer.duration is not None
        assert timer.duration > 0
        assert timer.start_time is not None
        assert timer.end_time is not None
    
    def test_timer_with_logging(self):
        """Test timer with logging enabled"""
        with PerformanceTimer("test_operation", log_result=True) as timer:
            time.sleep(0.01)
        
        assert timer.duration > 0
    
    def test_timer_with_exception(self):
        """Test timer with exception"""
        with pytest.raises(ValueError):
            with PerformanceTimer("test_operation", log_result=False) as timer:
                raise ValueError("Test error")
        
        # Timer should still have duration
        assert timer.duration is not None
    
    def test_timer_with_custom_category(self):
        """Test timer with custom category"""
        with PerformanceTimer("test_operation", log_result=False, 
                            category=EventCategory.EXPORT) as timer:
            time.sleep(0.01)
        
        assert timer.category == EventCategory.EXPORT
        assert timer.duration > 0


class TestMemoryTracker:
    """Test MemoryTracker context manager"""
    
    def test_tracker_basic(self):
        """Test basic memory tracker usage"""
        with MemoryTracker("test_operation", log_result=False) as tracker:
            # Allocate some memory
            data = [i for i in range(10000)]
            _ = data
        
        assert tracker.current_bytes is not None
        assert tracker.peak_bytes is not None
        assert tracker.current_mb is not None
        assert tracker.peak_mb is not None
        assert tracker.peak_bytes > 0
    
    def test_tracker_with_logging(self):
        """Test memory tracker with logging enabled"""
        with MemoryTracker("test_operation", log_result=True) as tracker:
            data = [i for i in range(10000)]
            _ = data
        
        assert tracker.peak_bytes > 0
    
    def test_tracker_with_exception(self):
        """Test memory tracker with exception"""
        with pytest.raises(ValueError):
            with MemoryTracker("test_operation", log_result=False) as tracker:
                raise ValueError("Test error")
        
        # Tracker should still have values
        assert tracker.current_bytes is not None
    
    def test_tracker_with_custom_category(self):
        """Test tracker with custom category"""
        with MemoryTracker("test_operation", log_result=False,
                          category=EventCategory.RECORDING) as tracker:
            data = [i for i in range(10000)]
            _ = data
        
        assert tracker.category == EventCategory.RECORDING
        assert tracker.peak_bytes > 0


class TestPerformanceSnapshot:
    """Test get_performance_snapshot function"""
    
    def test_snapshot_basic(self):
        """Test getting performance snapshot"""
        snapshot = get_performance_snapshot()
        
        assert "timestamp" in snapshot
        assert "memory" in snapshot
    
    def test_snapshot_with_memory_tracking(self):
        """Test snapshot with memory tracking active"""
        import tracemalloc
        
        tracemalloc.start()
        
        # Allocate some memory
        data = [i for i in range(10000)]
        _ = data
        
        snapshot = get_performance_snapshot()
        
        assert snapshot["memory"] is not None
        assert "current_bytes" in snapshot["memory"]
        assert "peak_bytes" in snapshot["memory"]
        assert "current_mb" in snapshot["memory"]
        assert "peak_mb" in snapshot["memory"]
        
        tracemalloc.stop()
    
    def test_snapshot_without_memory_tracking(self):
        """Test snapshot without memory tracking"""
        import tracemalloc
        
        if tracemalloc.is_tracing():
            tracemalloc.stop()
        
        snapshot = get_performance_snapshot()
        
        assert snapshot["memory"] is None


class TestIntegration:
    """Integration tests"""
    
    def test_nested_timers(self):
        """Test nested performance timers"""
        with PerformanceTimer("outer_operation", log_result=False) as outer:
            time.sleep(0.01)
            
            with PerformanceTimer("inner_operation", log_result=False) as inner:
                time.sleep(0.01)
            
            assert inner.duration > 0
        
        assert outer.duration > inner.duration
    
    def test_combined_decorators(self):
        """Test combining both decorators"""
        @track_execution_time()
        @track_memory_usage()
        def combined_function():
            data = [i for i in range(1000)]
            time.sleep(0.01)
            return len(data)
        
        result = combined_function()
        assert result == 1000
    
    def test_timer_and_tracker_together(self):
        """Test using timer and tracker together"""
        with PerformanceTimer("operation", log_result=False) as timer:
            with MemoryTracker("operation", log_result=False) as tracker:
                data = [i for i in range(10000)]
                time.sleep(0.01)
                _ = data
        
        assert timer.duration > 0
        assert tracker.peak_bytes > 0


class TestAccuracy:
    """Test accuracy of measurements"""
    
    def test_timer_accuracy(self):
        """Test timer measures time accurately"""
        sleep_time = 0.1  # 100ms
        
        with PerformanceTimer("test", log_result=False) as timer:
            time.sleep(sleep_time)
        
        # Should be close to sleep_time (within 50ms tolerance)
        assert abs(timer.duration - sleep_time) < 0.05
    
    def test_memory_tracker_detects_allocation(self):
        """Test memory tracker detects memory allocation"""
        with MemoryTracker("test", log_result=False) as tracker:
            # Allocate ~1MB of data
            large_data = [0] * (1024 * 128)  # 128K integers
            _ = large_data
        
        # Should have tracked some memory
        assert tracker.peak_bytes > 100000  # At least 100KB


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
