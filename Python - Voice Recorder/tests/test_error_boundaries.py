"""Tests for error boundary decorators and context managers."""

import logging
import time
from unittest.mock import MagicMock, patch

import pytest

from core.error_boundaries import (
    ErrorSeverity,
    SentryContext,
    operation_boundary,
    retry_with_telemetry,
    sentry_boundary,
)
from core.structured_logging import EventCategory


class TestOperationBoundary:
    """Test the operation_boundary decorator."""
    
    def test_successful_operation(self):
        """Test that successful operations execute normally."""
        @operation_boundary(operation_name="test_op")
        def successful_func(x, y):
            return x + y
        
        result = successful_func(2, 3)
        assert result == 5
    
    def test_exception_captured_and_reraised(self):
        """Test that exceptions are captured and reraised by default."""
        @operation_boundary(operation_name="test_op")
        def failing_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            failing_func()
    
    def test_exception_captured_with_fallback(self):
        """Test that exceptions can return fallback value instead of reraising."""
        @operation_boundary(
            operation_name="test_op",
            reraise=False,
            fallback_value="fallback"
        )
        def failing_func():
            raise ValueError("Test error")
        
        result = failing_func()
        assert result == "fallback"
    
    @patch('core.error_boundaries.TelemetryConfig')
    def test_sentry_capture_on_error(self, mock_config_class):
        """Test that errors are sent to Sentry when enabled."""
        mock_config = MagicMock()
        mock_config.enabled = True  # Use property, not method
        mock_config_class.return_value = mock_config
        
        @operation_boundary(
            operation_name="test_op",
            capture_errors=True,
            reraise=False
        )
        def failing_func():
            raise ValueError("Test error")
        
        failing_func()
        
        # Verify exception was captured
        mock_config.capture_exception.assert_called_once()
        args = mock_config.capture_exception.call_args
        assert isinstance(args[0][0], ValueError)
        assert args[1]['operation'] == 'test_op'
    
    @patch('core.error_boundaries.TelemetryConfig')
    def test_sentry_not_captured_when_disabled(self, mock_config_class):
        """Test that errors are not sent to Sentry when disabled."""
        mock_config = MagicMock()
        mock_config.enabled = False  # Use property, not method
        mock_config_class.return_value = mock_config
        
        @operation_boundary(
            operation_name="test_op",
            capture_errors=True,
            reraise=False
        )
        def failing_func():
            raise ValueError("Test error")
        
        failing_func()
        
        # Verify exception was NOT captured
        mock_config.capture_exception.assert_not_called()
    
    @patch('core.error_boundaries.get_performance_tracker')
    def test_performance_tracking(self, mock_tracker_getter):
        """Test that performance is tracked when enabled."""
        mock_tracker = MagicMock()
        mock_tracker_getter.return_value = mock_tracker
        
        @operation_boundary(
            operation_name="test_op",
            track_performance=True
        )
        def test_func():
            return "result"
        
        test_func()
        
        # Verify performance tracking
        mock_tracker.start_operation.assert_called_once_with("test_op")
        mock_tracker.end_operation.assert_called_once_with("test_op")
    
    def test_context_propagation(self):
        """Test that telemetry context is set up correctly."""
        @operation_boundary(
            operation_name="test_op",
            category=EventCategory.RECORDING,
            extra={"custom_key": "custom_value"}
        )
        def test_func():
            return "result"
        
        # Just verify it runs - context is set up via BaseTelemetryContext
        result = test_func()
        assert result == "result"


class TestRetryLogic:
    """Test retry behavior with operation_boundary."""
    
    def test_retry_on_failure(self):
        """Test that operations are retried on failure."""
        attempt_count = [0]
        
        @operation_boundary(
            operation_name="test_retry",
            retry_on_failure=True,
            max_retries=2,
            retry_delay=0.01,  # Fast retry for testing
            retry_backoff=1.0,
            reraise=False,
            fallback_value="failed"
        )
        def flaky_func():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise ValueError(f"Attempt {attempt_count[0]} failed")
            return "success"
        
        result = flaky_func()
        
        assert result == "success"
        assert attempt_count[0] == 3  # Initial + 2 retries
    
    def test_retry_exhaustion(self):
        """Test that retry gives up after max attempts."""
        attempt_count = [0]
        
        @operation_boundary(
            operation_name="test_retry",
            retry_on_failure=True,
            max_retries=2,
            retry_delay=0.01,
            reraise=False,
            fallback_value="fallback"
        )
        def always_failing_func():
            attempt_count[0] += 1
            raise ValueError(f"Attempt {attempt_count[0]} failed")
        
        result = always_failing_func()
        
        assert result == "fallback"
        assert attempt_count[0] == 3  # Initial + 2 retries
    
    def test_retry_with_specific_exceptions(self):
        """Test that only specified exceptions trigger retry."""
        attempt_count = [0]
        
        @operation_boundary(
            operation_name="test_retry",
            retry_on_failure=True,
            max_retries=2,
            retry_delay=0.01,
            retry_exceptions=(IOError, TimeoutError),
            reraise=True
        )
        def selective_retry_func():
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                raise IOError("Retry this")
            else:
                raise ValueError("Don't retry this")
        
        with pytest.raises(ValueError, match="Don't retry this"):
            selective_retry_func()
        
        assert attempt_count[0] == 2  # Initial IOError + 1 retry with ValueError
    
    def test_retry_delay_backoff(self):
        """Test that retry delay increases with backoff."""
        attempt_times = []
        
        @operation_boundary(
            operation_name="test_retry",
            retry_on_failure=True,
            max_retries=2,
            retry_delay=0.1,
            retry_backoff=2.0,
            reraise=False,
            fallback_value=None
        )
        def failing_func():
            attempt_times.append(time.time())
            raise ValueError("Test error")
        
        failing_func()
        
        assert len(attempt_times) == 3  # Initial + 2 retries
        
        # Check delays (should be ~0.1s and ~0.2s)
        delay1 = attempt_times[1] - attempt_times[0]
        delay2 = attempt_times[2] - attempt_times[1]
        
        assert 0.09 < delay1 < 0.15  # ~0.1s with tolerance
        assert 0.18 < delay2 < 0.25  # ~0.2s with tolerance


class TestSentryBoundary:
    """Test the lightweight sentry_boundary decorator."""
    
    def test_successful_operation(self):
        """Test that successful operations work normally."""
        @sentry_boundary(operation_name="test_op")
        def successful_func(x):
            return x * 2
        
        result = successful_func(5)
        assert result == 10
    
    def test_exception_reraised(self):
        """Test that exceptions are reraised by default."""
        @sentry_boundary(operation_name="test_op")
        def failing_func():
            raise RuntimeError("Test error")
        
        with pytest.raises(RuntimeError, match="Test error"):
            failing_func()
    
    def test_fallback_value(self):
        """Test that fallback value is returned when reraise=False."""
        @sentry_boundary(
            operation_name="test_op",
            reraise=False,
            fallback_value=42
        )
        def failing_func():
            raise RuntimeError("Test error")
        
        result = failing_func()
        assert result == 42


class TestRetryWithTelemetry:
    """Test the retry_with_telemetry decorator."""
    
    def test_successful_after_retries(self):
        """Test successful operation after retries."""
        attempt_count = [0]
        
        @retry_with_telemetry(
            operation_name="test_retry",
            max_retries=3,
            retry_delay=0.01
        )
        def flaky_func():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise IOError("Temporary failure")
            return "success"
        
        result = flaky_func()
        assert result == "success"
        assert attempt_count[0] == 3
    
    def test_exception_after_max_retries(self):
        """Test that exception is raised after max retries."""
        @retry_with_telemetry(
            operation_name="test_retry",
            max_retries=2,
            retry_delay=0.01
        )
        def always_failing_func():
            raise IOError("Permanent failure")
        
        with pytest.raises(IOError, match="Permanent failure"):
            always_failing_func()
    
    def test_specific_exception_types(self):
        """Test retry only on specific exception types."""
        attempt_count = [0]
        
        @retry_with_telemetry(
            operation_name="test_retry",
            max_retries=2,
            retry_delay=0.01,
            retry_exceptions=(IOError, TimeoutError)
        )
        def selective_func():
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                raise IOError("Retry this")
            raise ValueError("Don't retry this")
        
        with pytest.raises(ValueError):
            selective_func()
        
        assert attempt_count[0] == 2


class TestSentryContext:
    """Test the SentryContext context manager."""
    
    def test_successful_context(self):
        """Test that context manager works for successful code."""
        executed = False
        
        with SentryContext(operation="test_op") as ctx:
            executed = True
            ctx.add_breadcrumb("Test breadcrumb")
        
        assert executed
    
    def test_exception_captured(self):
        """Test that exceptions are captured and reraised."""
        with pytest.raises(ValueError, match="Test error"):
            with SentryContext(operation="test_op") as ctx:
                ctx.add_breadcrumb("Before error")
                raise ValueError("Test error")
    
    @patch('core.error_boundaries.get_performance_tracker')
    def test_performance_tracking(self, mock_tracker_getter):
        """Test that performance is tracked."""
        mock_tracker = MagicMock()
        mock_tracker_getter.return_value = mock_tracker
        
        with SentryContext(operation="test_op", attach_performance=True):
            pass
        
        mock_tracker.start_operation.assert_called_once_with("test_op")
        mock_tracker.end_operation.assert_called_once_with("test_op")
    
    @patch('core.error_boundaries.get_performance_tracker')
    def test_performance_not_tracked_when_disabled(self, mock_tracker_getter):
        """Test that performance is not tracked when disabled."""
        mock_tracker = MagicMock()
        mock_tracker_getter.return_value = mock_tracker
        
        with SentryContext(operation="test_op", attach_performance=False):
            pass
        
        mock_tracker.start_operation.assert_not_called()
        mock_tracker.end_operation.assert_not_called()
    
    def test_context_setup(self):
        """Test that telemetry context is set up."""
        with SentryContext(
            operation="test_op",
            category=EventCategory.EXPORT,
            extra={"custom": "data"}
        ):
            # Just verify it runs - context is automatically set up
            pass
    
    def test_context_helper_methods(self):
        """Test that context helper methods work."""
        with SentryContext(operation="test_op") as ctx:
            # These should not raise exceptions
            ctx.add_breadcrumb("Test message", level="info", key="value")
            ctx.set_tag("test_tag", "test_value")
            ctx.set_context("test_context", {"key": "value"})
            ctx.set_metric("test_metric", 123.45, "ms")


class TestErrorSeverity:
    """Test error severity classification."""
    
    @patch('core.error_boundaries.TelemetryConfig')
    def test_info_severity_not_captured(self, mock_config_class):
        """Test that INFO severity errors are not sent to Sentry."""
        mock_config = MagicMock()
        mock_config.enabled = True
        mock_config_class.return_value = mock_config
        
        @operation_boundary(
            operation_name="test_op",
            severity=ErrorSeverity.INFO,
            capture_errors=True,
            reraise=False
        )
        def info_error_func():
            raise ValueError("User cancelled")
        
        info_error_func()
        
        # INFO errors should not be captured in Sentry
        mock_config.capture_exception.assert_not_called()
    
    @patch('core.error_boundaries.TelemetryConfig')
    def test_warning_severity_not_captured(self, mock_config_class):
        """Test that WARNING severity errors are not sent to Sentry."""
        mock_config = MagicMock()
        mock_config.enabled = True
        mock_config_class.return_value = mock_config
        
        @operation_boundary(
            operation_name="test_op",
            severity=ErrorSeverity.WARNING,
            capture_errors=True,
            reraise=False
        )
        def warning_error_func():
            raise IOError("Network timeout")
        
        warning_error_func()
        
        # WARNING errors should not be captured in Sentry
        mock_config.capture_exception.assert_not_called()
    
    @patch('core.error_boundaries.TelemetryConfig')
    def test_error_severity_captured(self, mock_config_class):
        """Test that ERROR severity errors are sent to Sentry."""
        mock_config = MagicMock()
        mock_config.enabled = True
        mock_config_class.return_value = mock_config
        
        @operation_boundary(
            operation_name="test_op",
            severity=ErrorSeverity.ERROR,
            capture_errors=True,
            reraise=False
        )
        def error_func():
            raise RuntimeError("Unexpected error")
        
        error_func()
        
        # ERROR severity should be captured
        mock_config.capture_exception.assert_called_once()
    
    @patch('core.error_boundaries.TelemetryConfig')
    def test_critical_severity_captured(self, mock_config_class):
        """Test that CRITICAL severity errors are sent to Sentry."""
        mock_config = MagicMock()
        mock_config.enabled = True
        mock_config_class.return_value = mock_config
        
        @operation_boundary(
            operation_name="test_op",
            severity=ErrorSeverity.CRITICAL,
            capture_errors=True,
            critical=True,
            reraise=False
        )
        def critical_error_func():
            raise MemoryError("Out of memory")
        
        critical_error_func()
        
        # CRITICAL severity should be captured with critical flag
        mock_config.capture_exception.assert_called_once()
        call_kwargs = mock_config.capture_exception.call_args[1]
        assert call_kwargs['severity'] == 'critical'
        assert call_kwargs['critical'] is True


class TestTagsAndExtra:
    """Test tags and extra context propagation."""
    
    @patch('core.error_boundaries.TelemetryConfig')
    def test_tags_in_error_capture(self, mock_config_class):
        """Test that tags are included in error capture."""
        mock_config = MagicMock()
        mock_config.enabled = True
        mock_config_class.return_value = mock_config
        
        @operation_boundary(
            operation_name="test_op",
            tags={"env": "test", "feature": "audio"},
            reraise=False
        )
        def tagged_func():
            raise ValueError("Test error")
        
        tagged_func()
        
        # Tags should be in the extra context (not directly visible in mock)
        mock_config.capture_exception.assert_called_once()
    
    @patch('core.error_boundaries.TelemetryConfig')
    def test_extra_context_in_error_capture(self, mock_config_class):
        """Test that extra context is included in error capture."""
        mock_config = MagicMock()
        mock_config.enabled = True
        mock_config_class.return_value = mock_config
        
        @operation_boundary(
            operation_name="test_op",
            extra={"file_path": "/test/file.wav", "size_mb": 5.2},
            reraise=False
        )
        def context_func():
            raise ValueError("Test error")
        
        context_func()
        
        # Extra context should be passed through
        mock_config.capture_exception.assert_called_once()
        call_kwargs = mock_config.capture_exception.call_args[1]
        assert call_kwargs['file_path'] == '/test/file.wav'
        assert call_kwargs['size_mb'] == 5.2
