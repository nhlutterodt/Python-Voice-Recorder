#!/usr/bin/env python3
"""
Tests for structured logging module
"""
import json
import logging
import tempfile
from pathlib import Path
import pytest

from core.structured_logging import (
    EventCategory,
    StructuredLogger,
    JSONFormatter,
    setup_json_logging,
    get_structured_logger,
    log_event
)


class TestEventCategory:
    """Test EventCategory enum"""
    
    def test_event_categories_exist(self):
        """Test all expected categories exist"""
        expected_categories = [
            "APP_LIFECYCLE", "RECORDING", "PLAYBACK", "EDITING",
            "EXPORT", "CLOUD_SYNC", "DATABASE", "UI",
            "ERROR", "PERFORMANCE", "SECURITY"
        ]
        
        for category in expected_categories:
            assert hasattr(EventCategory, category)
    
    def test_category_values(self):
        """Test category values are lowercase with underscores"""
        assert EventCategory.APP_LIFECYCLE.value == "app_lifecycle"
        assert EventCategory.RECORDING.value == "recording"
        assert EventCategory.ERROR.value == "error"


class TestStructuredLogger:
    """Test StructuredLogger class"""
    
    def test_logger_initialization(self):
        """Test logger can be initialized"""
        logger = StructuredLogger("TestLogger")
        assert logger.logger.name == "TestLogger"
        assert logger._context == {}
    
    def test_set_context(self):
        """Test setting context"""
        logger = StructuredLogger()
        logger.set_context(user_id="test123", session_id="abc")
        
        assert logger._context["user_id"] == "test123"
        assert logger._context["session_id"] == "abc"
    
    def test_clear_context(self):
        """Test clearing context"""
        logger = StructuredLogger()
        logger.set_context(user_id="test123")
        logger.clear_context()
        
        assert logger._context == {}
    
    def test_remove_context(self):
        """Test removing specific context keys"""
        logger = StructuredLogger()
        logger.set_context(user_id="test123", session_id="abc", request_id="xyz")
        logger.remove_context("session_id", "request_id")
        
        assert "user_id" in logger._context
        assert "session_id" not in logger._context
        assert "request_id" not in logger._context
    
    def test_create_log_entry(self):
        """Test log entry creation"""
        logger = StructuredLogger()
        logger.set_context(user_id="test123")
        
        entry = logger._create_log_entry(
            category=EventCategory.RECORDING,
            event_type="recording_started",
            message="Recording started",
            level="INFO",
            data={"duration": 60}
        )
        
        assert entry["level"] == "INFO"
        assert entry["category"] == "recording"
        assert entry["event_type"] == "recording_started"
        assert entry["message"] == "Recording started"
        assert entry["context"]["user_id"] == "test123"
        assert entry["data"]["duration"] == 60
        assert "timestamp" in entry
    
    def test_log_event(self, caplog):
        """Test logging an event"""
        logger = StructuredLogger("TestLogger")
        
        with caplog.at_level(logging.INFO):
            logger.log_event(
                category=EventCategory.APP_LIFECYCLE,
                event_type="app_started",
                message="Application started",
                level="INFO"
            )
        
        # Check that something was logged
        assert len(caplog.records) > 0
    
    def test_convenience_methods(self, caplog):
        """Test debug, info, warning, error, critical methods"""
        logger = StructuredLogger("TestLogger")
        
        with caplog.at_level(logging.DEBUG):
            logger.debug(EventCategory.PERFORMANCE, "perf_test", "Debug message")
            logger.info(EventCategory.UI, "ui_test", "Info message")
            logger.warning(EventCategory.DATABASE, "db_test", "Warning message")
            logger.error(EventCategory.ERROR, "error_test", "Error message")
            logger.critical(EventCategory.SECURITY, "security_test", "Critical message")
        
        assert len(caplog.records) >= 5


class TestJSONFormatter:
    """Test JSONFormatter class"""
    
    def test_formatter_initialization(self):
        """Test formatter can be initialized"""
        formatter = JSONFormatter()
        assert formatter is not None
    
    def test_format_structured_log(self):
        """Test formatting a structured log record"""
        formatter = JSONFormatter()
        
        # Create a log record
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            name="test",
            level=logging.INFO,
            fn="test.py",
            lno=1,
            msg='{"level": "INFO", "message": "test"}',
            args=(),
            exc_info=None
        )
        record.structured = True
        
        formatted = formatter.format(record)
        
        # Should be valid JSON
        parsed = json.loads(formatted)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "test"
    
    def test_format_regular_log(self):
        """Test formatting a regular (non-structured) log record"""
        formatter = JSONFormatter()
        
        # Create a regular log record
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            name="test",
            level=logging.INFO,
            fn="test.py",
            lno=1,
            msg="Regular log message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        
        # Should be valid JSON
        parsed = json.loads(formatted)
        assert parsed["message"] == "Regular log message"
        assert parsed["level"] == "INFO"
        assert "timestamp" in parsed


class TestSetupJsonLogging:
    """Test setup_json_logging function"""
    
    def test_setup_json_logging(self):
        """Test JSON logging setup"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            handler = setup_json_logging(log_dir=log_dir)
            
            assert handler is not None
            assert isinstance(handler.formatter, JSONFormatter)
            
            # Clean up
            handler.close()


class TestGlobalLogger:
    """Test global logger singleton"""
    
    def test_get_structured_logger(self):
        """Test getting global structured logger"""
        logger1 = get_structured_logger()
        logger2 = get_structured_logger()
        
        # Should be the same instance
        assert logger1 is logger2
    
    def test_log_event_convenience(self, caplog):
        """Test convenience log_event function"""
        with caplog.at_level(logging.INFO):
            log_event(
                category=EventCategory.RECORDING,
                event_type="test_event",
                message="Test message"
            )
        
        assert len(caplog.records) > 0


class TestIntegration:
    """Integration tests"""
    
    def test_full_logging_flow(self):
        """Test complete logging flow with context"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            handler = setup_json_logging(log_dir=log_dir)
            
            logger = get_structured_logger()
            logger.logger.addHandler(handler)
            logger.logger.setLevel(logging.DEBUG)  # Ensure DEBUG level to capture all logs
            
            # Set context
            logger.set_context(user_id="test_user", session_id="session123")
            
            # Log events
            logger.info(
                category=EventCategory.RECORDING,
                event_type="recording_started",
                message="Started recording",
                data={"filename": "test.wav"}
            )
            
            logger.error(
                category=EventCategory.ERROR,
                event_type="recording_failed",
                message="Recording failed",
                data={"error": "Device not found"}
            )
            
            # Clean up
            handler.flush()  # Flush to ensure writes
            handler.close()
            
            # Verify log file was created (.jsonl format for JSON Lines)
            log_file = log_dir / "VoiceRecorderPro_structured.jsonl"
            assert log_file.exists(), f"Log file not found at {log_file}"
            
            # Verify content
            content = log_file.read_text()
            assert "recording_started" in content or "recording_failed" in content
            assert "test_user" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
