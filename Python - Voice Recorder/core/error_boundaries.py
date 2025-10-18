"""Error boundary decorators and context managers for comprehensive error handling.

This module provides reusable error boundaries that integrate:
- Sentry error tracking
- Structured logging
- Performance monitoring
- PII filtering
- Automatic context propagation

Usage:
    # Decorator for functions
    @operation_boundary(operation_name="audio_recording")
    def start_recording():
        pass
    
    # Context manager for code blocks
    with SentryContext(operation="export_audio") as ctx:
        ctx.add_breadcrumb("Starting export")
        export_file()
"""

import functools
import logging
import time
from contextlib import contextmanager
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union

from core.logging_config import get_logger
from core.performance import PerformanceTimer
from core.structured_logging import EventCategory
from core.telemetry_config import TelemetryConfig
from core.telemetry_context import TelemetryContext as BaseTelemetryContext

try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False


logger = get_logger(__name__)
F = TypeVar('F', bound=Callable[..., Any])


# Simple performance tracker using PerformanceTimer
class _PerformanceTracker:
    """Simple wrapper around PerformanceTimer for tracking operations."""
    
    def __init__(self):
        self._timers: Dict[str, PerformanceTimer] = {}
    
    def start_operation(self, operation: str) -> None:
        """Start tracking an operation."""
        if operation not in self._timers:
            self._timers[operation] = PerformanceTimer(
                operation_name=operation,
                log_result=False  # We'll handle logging ourselves
            )
        self._timers[operation].__enter__()
    
    def end_operation(self, operation: str) -> None:
        """End tracking an operation."""
        if operation in self._timers:
            timer = self._timers[operation]
            try:
                timer.__exit__(None, None, None)
            finally:
                # Clean up completed timers
                del self._timers[operation]
    
    def record_metric(self, operation: str, name: str, value: float) -> None:
        """Record a metric (logged for now)."""
        logger.debug(
            f"Metric [{operation}]: {name} = {value}",
            extra={
                "operation": operation,
                "metric_name": name,
                "metric_value": value
            }
        )


_global_tracker = _PerformanceTracker()


def get_performance_tracker() -> _PerformanceTracker:
    """Get the global performance tracker instance."""
    return _global_tracker


class ErrorSeverity(Enum):
    """Error severity classification for telemetry and handling."""
    
    INFO = "info"           # Expected errors (user cancel, validation)
    WARNING = "warning"     # Recoverable errors (network timeout, retry)
    ERROR = "error"         # Unexpected errors (invalid state, logic bugs)
    CRITICAL = "critical"   # System failures (OOM, disk full, corruption)


class ErrorBoundaryConfig:
    """Configuration for error boundary behavior."""
    
    def __init__(
        self,
        operation_name: str,
        category: EventCategory = EventCategory.ERROR,
        capture_errors: bool = True,
        track_performance: bool = True,
        retry_on_failure: bool = False,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        retry_backoff: float = 2.0,
        retry_exceptions: Optional[tuple] = None,
        fallback_value: Any = None,
        reraise: bool = True,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        critical: bool = False,
        tags: Optional[Dict[str, str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """Initialize error boundary configuration.
        
        Args:
            operation_name: Name of the operation for telemetry
            category: Event category for structured logging
            capture_errors: Whether to send errors to Sentry
            track_performance: Whether to track performance metrics
            retry_on_failure: Whether to retry on failure
            max_retries: Maximum retry attempts
            retry_delay: Initial delay between retries (seconds)
            retry_backoff: Backoff multiplier for retry delay
            retry_exceptions: Tuple of exception types to retry (None = all)
            fallback_value: Value to return on error (if not reraising)
            reraise: Whether to reraise exception after handling
            severity: Error severity level
            critical: Whether this is a critical operation (affects alerting)
            tags: Additional tags for Sentry events
            extra: Additional context for Sentry events
        """
        self.operation_name = operation_name
        self.category = category
        self.capture_errors = capture_errors
        self.track_performance = track_performance
        self.retry_on_failure = retry_on_failure
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_backoff = retry_backoff
        self.retry_exceptions = retry_exceptions
        self.fallback_value = fallback_value
        self.reraise = reraise
        self.severity = severity
        self.critical = critical
        self.tags = tags or {}
        self.extra = extra or {}


def operation_boundary(
    operation_name: str,
    category: EventCategory = EventCategory.ERROR,
    capture_errors: bool = True,
    track_performance: bool = True,
    retry_on_failure: bool = False,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    retry_backoff: float = 2.0,
    retry_exceptions: Optional[tuple] = None,
    fallback_value: Any = None,
    reraise: bool = True,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    critical: bool = False,
    tags: Optional[Dict[str, str]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Callable[[F], F]:
    """Decorator that creates a comprehensive error boundary around a function.
    
    Integrates Sentry error tracking, structured logging, performance monitoring,
    and automatic retry logic.
    
    Args:
        operation_name: Name of the operation for telemetry
        category: Event category for structured logging
        capture_errors: Whether to send errors to Sentry
        track_performance: Whether to track performance metrics
        retry_on_failure: Whether to retry on failure
        max_retries: Maximum retry attempts
        retry_delay: Initial delay between retries (seconds)
        retry_backoff: Backoff multiplier for retry delay
        retry_exceptions: Tuple of exception types to retry (None = all)
        fallback_value: Value to return on error (if not reraising)
        reraise: Whether to reraise exception after handling
        severity: Error severity level
        critical: Whether this is a critical operation
        tags: Additional tags for Sentry events
        extra: Additional context for Sentry events
    
    Returns:
        Decorated function with error boundary
    
    Example:
        @operation_boundary(
            operation_name="audio_recording",
            category=EventCategory.RECORDING,
            critical=True
        )
        def start_recording():
            # Automatic error handling and telemetry
            pass
    """
    config = ErrorBoundaryConfig(
        operation_name=operation_name,
        category=category,
        capture_errors=capture_errors,
        track_performance=track_performance,
        retry_on_failure=retry_on_failure,
        max_retries=max_retries,
        retry_delay=retry_delay,
        retry_backoff=retry_backoff,
        retry_exceptions=retry_exceptions,
        fallback_value=fallback_value,
        reraise=reraise,
        severity=severity,
        critical=critical,
        tags=tags,
        extra=extra,
    )
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return _execute_with_boundary(func, config, args, kwargs)
        return wrapper  # type: ignore
    
    return decorator


def _execute_with_boundary(
    func: Callable,
    config: ErrorBoundaryConfig,
    args: tuple,
    kwargs: dict,
) -> Any:
    """Execute function with error boundary and retry logic."""
    performance_tracker = get_performance_tracker()
    telemetry_config = TelemetryConfig()
    
    # Set up telemetry context
    with BaseTelemetryContext(
        operation=config.operation_name,
        category=config.category.value,
        **config.extra
    ):
        attempt = 0
        current_delay = config.retry_delay
        last_exception = None
        
        while attempt <= (config.max_retries if config.retry_on_failure else 0):
            try:
                # Start performance tracking
                if config.track_performance:
                    performance_tracker.start_operation(config.operation_name)
                
                # Start Sentry transaction if enabled
                transaction = None
                if config.capture_errors and telemetry_config.enabled and SENTRY_AVAILABLE:
                    transaction = sentry_sdk.start_transaction(
                        name=config.operation_name,
                        op=config.category.value
                    )
                    transaction.set_tag("attempt", attempt + 1)
                    for key, value in config.tags.items():
                        transaction.set_tag(key, value)
                    transaction.__enter__()
                
                try:
                    # Execute the function
                    result = func(*args, **kwargs)
                    
                    # Success - log and return
                    if attempt > 0:
                        logger.info(
                            f"Operation '{config.operation_name}' succeeded after {attempt + 1} attempts",
                            extra={
                                "category": config.category.value,
                                "operation": config.operation_name,
                                "attempts": attempt + 1
                            }
                        )
                    
                    return result
                
                finally:
                    # End Sentry transaction
                    if transaction:
                        transaction.__exit__(None, None, None)
                    
                    # End performance tracking
                    if config.track_performance:
                        performance_tracker.end_operation(config.operation_name)
            
            except Exception as exc:
                last_exception = exc
                
                # Check if we should retry
                should_retry = (
                    config.retry_on_failure
                    and attempt < config.max_retries
                    and (config.retry_exceptions is None or isinstance(exc, config.retry_exceptions))
                )
                
                # Log the error
                log_level = {
                    ErrorSeverity.INFO: logging.INFO,
                    ErrorSeverity.WARNING: logging.WARNING,
                    ErrorSeverity.ERROR: logging.ERROR,
                    ErrorSeverity.CRITICAL: logging.CRITICAL,
                }.get(config.severity, logging.ERROR)
                
                logger.log(
                    log_level,
                    f"Error in operation '{config.operation_name}'"
                    + (f" (attempt {attempt + 1}/{config.max_retries + 1})" if should_retry else ""),
                    exc_info=exc,
                    extra={
                        "category": config.category.value,
                        "operation": config.operation_name,
                        "error_type": type(exc).__name__,
                        "severity": config.severity.value,
                        "critical": config.critical,
                        "will_retry": should_retry,
                        "attempt": attempt + 1
                    }
                )
                
                # Capture in Sentry if enabled and severity warrants it
                if (
                    config.capture_errors
                    and config.severity in (ErrorSeverity.ERROR, ErrorSeverity.CRITICAL)
                    and telemetry_config.enabled
                ):
                    telemetry_config.capture_exception(
                        exc,
                        **{
                            "operation": config.operation_name,
                            "category": config.category.value,
                            "severity": config.severity.value,
                            "critical": config.critical,
                            "attempt": attempt + 1,
                            "will_retry": should_retry,
                            **config.extra
                        }
                    )
                
                # Retry or fail
                if should_retry:
                    attempt += 1
                    logger.info(
                        f"Retrying operation '{config.operation_name}' in {current_delay}s",
                        extra={
                            "category": config.category.value,
                            "operation": config.operation_name,
                            "retry_delay": current_delay,
                            "attempt": attempt
                        }
                    )
                    time.sleep(current_delay)
                    current_delay *= config.retry_backoff
                    continue
                else:
                    # Final failure
                    if config.reraise:
                        raise
                    else:
                        logger.warning(
                            f"Returning fallback value for failed operation '{config.operation_name}'",
                            extra={
                                "category": config.category.value,
                                "operation": config.operation_name,
                                "fallback_value": config.fallback_value
                            }
                        )
                        return config.fallback_value
        
        # Should never reach here, but for type safety
        if config.reraise and last_exception:
            raise last_exception
        return config.fallback_value


@contextmanager
def SentryContext(
    operation: str,
    category: EventCategory = EventCategory.ERROR,
    tags: Optional[Dict[str, str]] = None,
    extra: Optional[Dict[str, Any]] = None,
    attach_performance: bool = True,
    capture_errors: bool = True,
):
    """Context manager for scoped error and performance tracking.
    
    Provides a context for code blocks that automatically:
    - Creates a Sentry scope with tags and context
    - Tracks performance metrics
    - Captures exceptions
    - Manages structured logging context
    
    Args:
        operation: Name of the operation
        category: Event category
        tags: Additional Sentry tags
        extra: Additional context data
        attach_performance: Whether to track performance
        capture_errors: Whether to capture exceptions
    
    Yields:
        SentryContextManager instance with helper methods
    
    Example:
        with SentryContext(
            operation="export_audio",
            tags={"format": "wav"}
        ) as ctx:
            ctx.add_breadcrumb("Starting export")
            export_file()
            ctx.set_metric("file_size_mb", size / 1024 / 1024)
    """
    performance_tracker = get_performance_tracker()
    telemetry_config = TelemetryConfig()
    
    # Start performance tracking
    if attach_performance:
        performance_tracker.start_operation(operation)
    
    # Create Sentry scope if enabled
    scope_stack = []
    transaction = None
    
    if telemetry_config.enabled and SENTRY_AVAILABLE:
        # Push new scope
        scope = sentry_sdk.push_scope()
        scope_stack.append(scope)
        
        # Set tags
        if tags:
            for key, value in tags.items():
                sentry_sdk.set_tag(key, value)
        
        # Set context
        if extra:
            sentry_sdk.set_context("operation_context", extra)
        
        # Start transaction
        if attach_performance:
            transaction = sentry_sdk.start_transaction(
                name=operation,
                op=category.value
            )
            transaction.__enter__()
    
    # Create context manager helper
    class ContextHelper:
        """Helper methods for the context manager."""
        
        def add_breadcrumb(self, message: str, level: str = "info", **data: Any) -> None:
            """Add a breadcrumb to Sentry."""
            logger.debug(f"[{operation}] {message}", extra=data)
            if telemetry_config.enabled and SENTRY_AVAILABLE:
                sentry_sdk.add_breadcrumb(
                    message=message,
                    level=level,
                    category=category.value,
                    data=data
                )
        
        def set_tag(self, key: str, value: str) -> None:
            """Set a tag in the current Sentry scope."""
            if telemetry_config.enabled and SENTRY_AVAILABLE:
                sentry_sdk.set_tag(key, value)
        
        def set_context(self, name: str, data: Dict[str, Any]) -> None:
            """Set context data in Sentry."""
            if telemetry_config.enabled and SENTRY_AVAILABLE:
                sentry_sdk.set_context(name, data)
        
        def set_metric(self, name: str, value: float, unit: str = "none") -> None:
            """Record a metric."""
            logger.info(
                f"Metric: {name} = {value} {unit}",
                extra={
                    "metric_name": name,
                    "metric_value": value,
                    "metric_unit": unit,
                    "operation": operation
                }
            )
            performance_tracker.record_metric(operation, name, value)
    
    helper = ContextHelper()
    
    try:
        yield helper
    except Exception as exc:
        # Log the error
        logger.error(
            f"Error in context '{operation}'",
            exc_info=exc,
            extra={
                "category": category.value,
                "operation": operation
            }
        )
        
        # Capture in Sentry if enabled
        if capture_errors and telemetry_config.enabled:
            telemetry_config.capture_exception(
                exc,
                **{
                    "operation": operation,
                    "category": category.value,
                    **(extra or {})
                }
            )
        
        raise
    finally:
        # End transaction
        if transaction:
            transaction.__exit__(None, None, None)
        
        # Pop Sentry scope
        while scope_stack:
            scope_stack.pop()
            sentry_sdk.pop_scope()
        
        # End performance tracking
        if attach_performance:
            performance_tracker.end_operation(operation)


def sentry_boundary(
    operation_name: str,
    reraise: bool = True,
    fallback_value: Any = None,
    tags: Optional[Dict[str, str]] = None,
) -> Callable[[F], F]:
    """Lightweight decorator for basic Sentry error capture.
    
    Use this for simple error capture without retry logic or performance tracking.
    For more advanced features, use @operation_boundary.
    
    Args:
        operation_name: Name of the operation
        reraise: Whether to reraise the exception
        fallback_value: Value to return on error (if not reraising)
        tags: Additional Sentry tags
    
    Returns:
        Decorated function
    
    Example:
        @sentry_boundary(operation_name="validate_file")
        def validate_recording(file_path):
            # Simple error capture
            pass
    """
    return operation_boundary(
        operation_name=operation_name,
        capture_errors=True,
        track_performance=False,
        retry_on_failure=False,
        reraise=reraise,
        fallback_value=fallback_value,
        tags=tags,
    )


def retry_with_telemetry(
    operation_name: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    retry_backoff: float = 2.0,
    retry_exceptions: Optional[tuple] = None,
    reraise: bool = True,
) -> Callable[[F], F]:
    """Decorator for retry logic with telemetry tracking.
    
    Args:
        operation_name: Name of the operation
        max_retries: Maximum retry attempts
        retry_delay: Initial delay between retries (seconds)
        retry_backoff: Backoff multiplier for retry delay
        retry_exceptions: Tuple of exception types to retry (None = all)
        reraise: Whether to reraise exception after max retries
    
    Returns:
        Decorated function with retry logic
    
    Example:
        @retry_with_telemetry(
            operation_name="upload_recording",
            max_retries=3,
            retry_exceptions=(IOError, TimeoutError)
        )
        def upload_to_cloud(file_path):
            # Automatic retry on network errors
            pass
    """
    return operation_boundary(
        operation_name=operation_name,
        capture_errors=True,
        track_performance=True,
        retry_on_failure=True,
        max_retries=max_retries,
        retry_delay=retry_delay,
        retry_backoff=retry_backoff,
        retry_exceptions=retry_exceptions,
        reraise=reraise,
        severity=ErrorSeverity.WARNING,  # Retryable errors are typically warnings
    )


# Export public API
__all__ = [
    'ErrorSeverity',
    'ErrorBoundaryConfig',
    'operation_boundary',
    'SentryContext',
    'sentry_boundary',
    'retry_with_telemetry',
]
