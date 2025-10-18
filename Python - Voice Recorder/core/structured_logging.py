#!/usr/bin/env python3
"""
Structured logging module for Voice Recorder Pro
Provides JSON-based structured logging with context tracking and event categorization.
"""
import json
import logging
import logging.handlers
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pathlib import Path


class EventCategory(Enum):
    """Categories for structured log events"""
    APP_LIFECYCLE = "app_lifecycle"
    RECORDING = "recording"
    PLAYBACK = "playback"
    EDITING = "editing"
    EXPORT = "export"
    CLOUD_SYNC = "cloud_sync"
    DATABASE = "database"
    UI = "ui"
    ERROR = "error"
    PERFORMANCE = "performance"
    SECURITY = "security"


class StructuredLogger:
    """
    Structured logger that outputs JSON-formatted log entries
    alongside standard text logs.
    """
    
    def __init__(self, logger_name: str = "VoiceRecorderPro"):
        self.logger = logging.getLogger(logger_name)
        self._context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs: Any):
        """Set context that will be included in all log entries"""
        self._context.update(kwargs)
    
    def clear_context(self):
        """Clear all context"""
        self._context.clear()
    
    def remove_context(self, *keys: str):
        """Remove specific context keys"""
        for key in keys:
            self._context.pop(key, None)
    
    def _create_log_entry(
        self,
        category: EventCategory,
        event_type: str,
        message: str,
        level: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Create a structured log entry"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "category": category.value,
            "event_type": event_type,
            "message": message,
            "context": self._context.copy(),
        }
        
        if data:
            entry["data"] = data
        
        # Add any additional fields
        if kwargs:
            entry.update(kwargs)
        
        return entry
    
    def log_event(
        self,
        category: EventCategory,
        event_type: str,
        message: str,
        level: str = "INFO",
        data: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ):
        """
        Log a structured event
        
        Args:
            category: Event category (from EventCategory enum)
            event_type: Specific event type (e.g., "recording_started")
            message: Human-readable message
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            data: Additional structured data
            **kwargs: Additional fields to include in log entry
        """
        entry = self._create_log_entry(
            category, event_type, message, level, data, **kwargs
        )
        
        # Log as JSON to the logger
        json_str = json.dumps(entry)
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(log_level, json_str, extra={"structured": True})
    
    def debug(self, category: EventCategory, event_type: str, message: str, **kwargs: Any):
        """Log debug event"""
        self.log_event(category, event_type, message, "DEBUG", **kwargs)
    
    def info(self, category: EventCategory, event_type: str, message: str, **kwargs: Any):
        """Log info event"""
        self.log_event(category, event_type, message, "INFO", **kwargs)
    
    def warning(self, category: EventCategory, event_type: str, message: str, **kwargs: Any):
        """Log warning event"""
        self.log_event(category, event_type, message, "WARNING", **kwargs)
    
    def error(self, category: EventCategory, event_type: str, message: str, **kwargs: Any):
        """Log error event"""
        self.log_event(category, event_type, message, "ERROR", **kwargs)
    
    def critical(self, category: EventCategory, event_type: str, message: str, **kwargs: Any):
        """Log critical event"""
        self.log_event(category, event_type, message, "CRITICAL", **kwargs)


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in JSON format
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        # Check if this is already a structured log entry
        if hasattr(record, "structured") and record.structured:
            # Already JSON, just return the message
            return record.getMessage()
        
        # Convert regular log to JSON
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in [
                    "name", "msg", "args", "created", "filename", "funcName",
                    "levelname", "levelno", "lineno", "module", "msecs",
                    "message", "pathname", "process", "processName",
                    "relativeCreated", "thread", "threadName", "exc_info",
                    "exc_text", "stack_info", "structured"
                ]:
                    log_entry[key] = value
        
        return json.dumps(log_entry)


def setup_json_logging(log_dir: Path, app_name: str = "VoiceRecorderPro") -> logging.Handler:
    """
    Set up a JSON log handler
    
    Args:
        log_dir: Directory for log files
        app_name: Application name for log filename
    
    Returns:
        Configured logging handler
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    
    json_handler = logging.handlers.RotatingFileHandler(
        log_dir / f"{app_name}_structured.jsonl",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    json_handler.setLevel(logging.DEBUG)
    json_handler.setFormatter(JSONFormatter())
    
    return json_handler


# Global structured logger instance
_structured_logger: Optional[StructuredLogger] = None


def get_structured_logger(name: str = "VoiceRecorderPro") -> StructuredLogger:
    """
    Get or create the global structured logger instance
    
    Args:
        name: Logger name
    
    Returns:
        StructuredLogger instance
    """
    global _structured_logger
    if _structured_logger is None:
        _structured_logger = StructuredLogger(name)
    return _structured_logger


# Convenience function for quick access
def log_event(
    category: EventCategory,
    event_type: str,
    message: str,
    level: str = "INFO",
    **kwargs: Any
):
    """
    Convenience function to log a structured event
    
    Args:
        category: Event category
        event_type: Specific event type
        message: Human-readable message
        level: Log level
        **kwargs: Additional data
    """
    logger = get_structured_logger()
    logger.log_event(category, event_type, message, level, **kwargs)
