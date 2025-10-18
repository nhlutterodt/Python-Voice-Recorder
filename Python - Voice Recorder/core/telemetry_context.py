#!/usr/bin/env python3
"""
Telemetry context management for Voice Recorder Pro
Provides session tracking and context propagation across operations.
"""
import uuid
from contextvars import ContextVar
from typing import Any, Optional
from datetime import datetime, timezone


# Context variables for tracking
session_id: ContextVar[Optional[str]] = ContextVar("session_id", default=None)
request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id: ContextVar[str] = ContextVar("user_id", default="anonymous")
operation_name: ContextVar[Optional[str]] = ContextVar("operation_name", default=None)


class TelemetryContext:
    """
    Context manager for telemetry operations
    Automatically tracks session and request IDs
    """
    
    def __init__(self, operation: str, **additional_context: Any):
        self.operation = operation
        self.additional_context = additional_context
        self.request_id_value = str(uuid.uuid4())
        self.start_time = None
        self._previous_request_id = None
        self._previous_operation = None
    
    def __enter__(self):
        """Enter context - set request ID and operation name"""
        self._previous_request_id = request_id.get(None)
        self._previous_operation = operation_name.get(None)
        
        request_id.set(self.request_id_value)
        operation_name.set(self.operation)
        self.start_time = datetime.now(timezone.utc)
        
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Exit context - restore previous values"""
        request_id.set(self._previous_request_id)
        operation_name.set(self._previous_operation)
        
        # Calculate duration
        if self.start_time:
            duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()
            self.additional_context["duration_seconds"] = duration
        
        return False  # Don't suppress exceptions
    
    def get_context_dict(self) -> dict[str, Any]:
        """Get current context as dictionary"""
        ctx = {
            "session_id": session_id.get(None),
            "request_id": request_id.get(None),
            "user_id": user_id.get("anonymous"),
            "operation": operation_name.get(None),
        }
        ctx.update(self.additional_context)
        return {k: v for k, v in ctx.items() if v is not None}


class SessionManager:
    """
    Manages application session lifecycle
    """
    
    def __init__(self):
        self._session_id: Optional[str] = None
        self._session_start: Optional[datetime] = None
    
    def start_session(self, user_id_value: str = "anonymous") -> str:
        """
        Start a new session
        
        Args:
            user_id_value: User identifier (default: "anonymous")
        
        Returns:
            Session ID
        """
        self._session_id = str(uuid.uuid4())
        self._session_start = datetime.now(timezone.utc)
        
        session_id.set(self._session_id)
        user_id.set(user_id_value)
        
        return self._session_id
    
    def end_session(self):
        """End the current session"""
        session_id.set(None)
        user_id.set("anonymous")
        self._session_id = None
        self._session_start = None
    
    def get_session_id(self) -> Optional[str]:
        """Get current session ID"""
        return session_id.get(None)
    
    def get_session_duration(self) -> Optional[float]:
        """Get session duration in seconds"""
        if self._session_start:
            return (datetime.now(timezone.utc) - self._session_start).total_seconds()
        return None
    
    def is_active(self) -> bool:
        """Check if session is active"""
        return self._session_id is not None


# Global session manager
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create global session manager"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def get_current_context() -> dict[str, Any]:
    """
    Get current telemetry context as dictionary
    
    Returns:
        Dictionary with session_id, request_id, user_id, operation
    """
    return {
        "session_id": session_id.get(None),
        "request_id": request_id.get(None),
        "user_id": user_id.get("anonymous"),
        "operation": operation_name.get(None),
    }


def inject_context_to_logger() -> dict[str, Any]:
    """
    Get context dict suitable for logging
    Filters out None values
    """
    ctx = get_current_context()
    return {k: v for k, v in ctx.items() if v is not None}
