#!/usr/bin/env python3
"""
Performance monitoring utilities for Voice Recorder Pro
Provides timing decorators and memory tracking.
"""
import functools
import time
import tracemalloc
from typing import Callable, Any, Optional
from datetime import datetime, timezone

from .structured_logging import get_structured_logger, EventCategory


def track_execution_time(category: EventCategory = EventCategory.PERFORMANCE):
    """
    Decorator to track function execution time
    
    Args:
        category: Event category for logging
    
    Usage:
        @track_execution_time()
        def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_structured_logger()
            function_name = f"{func.__module__}.{func.__qualname__}"
            
            start_time = time.perf_counter()
            start_timestamp = datetime.now(timezone.utc)
            
            try:
                result = func(*args, **kwargs)
                
                # Log success
                duration = time.perf_counter() - start_time
                logger.log_event(
                    category=category,
                    event_type="function_completed",
                    message=f"Function {function_name} completed",
                    level="DEBUG",
                    data={
                        "function": function_name,
                        "duration_seconds": duration,
                        "duration_ms": duration * 1000,
                        "start_time": start_timestamp.isoformat(),
                    }
                )
                
                return result
                
            except Exception as e:
                # Log error with timing
                duration = time.perf_counter() - start_time
                logger.log_event(
                    category=EventCategory.ERROR,
                    event_type="function_error",
                    message=f"Function {function_name} failed after {duration:.3f}s",
                    level="ERROR",
                    data={
                        "function": function_name,
                        "duration_seconds": duration,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    }
                )
                raise
        
        return wrapper
    return decorator


def track_memory_usage(category: EventCategory = EventCategory.PERFORMANCE):
    """
    Decorator to track memory usage during function execution
    
    Args:
        category: Event category for logging
    
    Usage:
        @track_memory_usage()
        def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_structured_logger()
            function_name = f"{func.__module__}.{func.__qualname__}"
            
            # Start memory tracking
            tracemalloc.start()
            
            try:
                result = func(*args, **kwargs)
                
                # Get memory stats
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                
                # Log memory usage
                logger.log_event(
                    category=category,
                    event_type="memory_usage",
                    message=f"Function {function_name} memory usage",
                    level="DEBUG",
                    data={
                        "function": function_name,
                        "current_bytes": current,
                        "peak_bytes": peak,
                        "current_mb": current / 1024 / 1024,
                        "peak_mb": peak / 1024 / 1024,
                    }
                )
                
                return result
                
            except Exception as e:
                tracemalloc.stop()
                logger.log_event(
                    category=EventCategory.ERROR,
                    event_type="function_error",
                    message=f"Function {function_name} failed",
                    level="ERROR",
                    data={
                        "function": function_name,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    }
                )
                raise
        
        return wrapper
    return decorator


class PerformanceTimer:
    """
    Context manager for timing code blocks
    
    Usage:
        with PerformanceTimer("database_query") as timer:
            # ... code to time ...
            pass
        
        print(f"Duration: {timer.duration}s")
    """
    
    def __init__(self, operation_name: str, log_result: bool = True, 
                 category: EventCategory = EventCategory.PERFORMANCE):
        self.operation_name = operation_name
        self.log_result = log_result
        self.category = category
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration: Optional[float] = None
        self.logger = get_structured_logger()
    
    def __enter__(self):
        """Start timing"""
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Stop timing and optionally log result"""
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time
        
        if self.log_result:
            if exc_type is None:
                # Success
                self.logger.log_event(
                    category=self.category,
                    event_type="operation_completed",
                    message=f"Operation {self.operation_name} completed",
                    level="DEBUG",
                    data={
                        "operation": self.operation_name,
                        "duration_seconds": self.duration,
                        "duration_ms": self.duration * 1000,
                    }
                )
            else:
                # Error
                self.logger.log_event(
                    category=EventCategory.ERROR,
                    event_type="operation_error",
                    message=f"Operation {self.operation_name} failed",
                    level="ERROR",
                    data={
                        "operation": self.operation_name,
                        "duration_seconds": self.duration,
                        "error_type": exc_type.__name__ if exc_type else None,
                        "error_message": str(exc_val) if exc_val else None,
                    }
                )
        
        return False  # Don't suppress exceptions


class MemoryTracker:
    """
    Context manager for tracking memory usage
    
    Usage:
        with MemoryTracker("audio_processing") as tracker:
            # ... code to track ...
            pass
        
        print(f"Peak memory: {tracker.peak_mb}MB")
    """
    
    def __init__(self, operation_name: str, log_result: bool = True,
                 category: EventCategory = EventCategory.PERFORMANCE):
        self.operation_name = operation_name
        self.log_result = log_result
        self.category = category
        self.current_bytes: Optional[int] = None
        self.peak_bytes: Optional[int] = None
        self.current_mb: Optional[float] = None
        self.peak_mb: Optional[float] = None
        self.logger = get_structured_logger()
    
    def __enter__(self):
        """Start memory tracking"""
        tracemalloc.start()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Stop memory tracking and log result"""
        self.current_bytes, self.peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        self.current_mb = self.current_bytes / 1024 / 1024
        self.peak_mb = self.peak_bytes / 1024 / 1024
        
        if self.log_result:
            self.logger.log_event(
                category=self.category,
                event_type="memory_tracked",
                message=f"Memory usage for {self.operation_name}",
                level="DEBUG",
                data={
                    "operation": self.operation_name,
                    "current_bytes": self.current_bytes,
                    "peak_bytes": self.peak_bytes,
                    "current_mb": self.current_mb,
                    "peak_mb": self.peak_mb,
                }
            )
        
        return False  # Don't suppress exceptions


def get_performance_snapshot() -> dict:
    """
    Get a snapshot of current performance metrics
    
    Returns:
        Dictionary with timing and memory info
    """
    if tracemalloc.is_tracing():
        current, peak = tracemalloc.get_traced_memory()
        memory_info = {
            "current_bytes": current,
            "peak_bytes": peak,
            "current_mb": current / 1024 / 1024,
            "peak_mb": peak / 1024 / 1024,
        }
    else:
        memory_info = None
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "memory": memory_info,
    }
