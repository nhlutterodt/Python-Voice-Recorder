#!/usr/bin/env python3
"""
Tests for telemetry context module
"""
import pytest
from unittest.mock import patch

from core.telemetry_context import (
    session_id,
    request_id,
    user_id,
    operation_name,
    TelemetryContext,
    SessionManager,
    get_session_manager,
    get_current_context,
    inject_context_to_logger,
)


class TestContextVars:
    """Test context variables"""
    
    def test_context_vars_default_values(self):
        """Test context variables have correct defaults"""
        # Reset context vars
        session_id.set(None)
        request_id.set(None)
        user_id.set("anonymous")
        operation_name.set(None)
        
        assert session_id.get() is None
        assert request_id.get() is None
        assert user_id.get() == "anonymous"
        assert operation_name.get() is None


class TestTelemetryContext:
    """Test TelemetryContext context manager"""
    
    def test_context_manager_basic(self):
        """Test basic context manager usage"""
        with TelemetryContext("test_operation") as ctx:
            assert ctx.operation == "test_operation"
            assert ctx.request_id_value is not None
            assert operation_name.get() == "test_operation"
            assert request_id.get() == ctx.request_id_value
    
    def test_context_manager_restores_values(self):
        """Test context manager restores previous values"""
        # Set initial values
        operation_name.set("initial_operation")
        request_id.set("initial_request")
        
        with TelemetryContext("nested_operation"):
            assert operation_name.get() == "nested_operation"
            assert request_id.get() != "initial_request"
        
        # Should restore
        assert operation_name.get() == "initial_operation"
        assert request_id.get() == "initial_request"
    
    def test_context_manager_with_additional_context(self):
        """Test context manager with additional context"""
        with TelemetryContext("test_operation", task_id="task123") as ctx:
            assert ctx.additional_context["task_id"] == "task123"
    
    def test_context_manager_tracks_duration(self):
        """Test context manager tracks operation duration"""
        import time
        
        with TelemetryContext("test_operation") as ctx:
            time.sleep(0.01)  # Small delay
        
        assert "duration_seconds" in ctx.additional_context
        assert ctx.additional_context["duration_seconds"] > 0
    
    def test_get_context_dict(self):
        """Test getting context as dictionary"""
        session_id.set("session123")
        
        with TelemetryContext("test_operation", extra_key="extra_value") as ctx:
            context_dict = ctx.get_context_dict()
            
            assert context_dict["session_id"] == "session123"
            assert context_dict["operation"] == "test_operation"
            assert context_dict["request_id"] == ctx.request_id_value
            assert context_dict["extra_key"] == "extra_value"


class TestSessionManager:
    """Test SessionManager class"""
    
    def setup_method(self):
        """Reset session manager state before each test"""
        # Clear any existing session state
        from core.telemetry_context import session_id, user_id
        session_id.set(None)
        user_id.set("anonymous")
    
    def test_session_manager_initialization(self):
        """Test session manager can be initialized"""
        manager = SessionManager()
        
        assert manager.get_session_id() is None
        assert not manager.is_active()
    
    def test_start_session(self):
        """Test starting a session"""
        manager = SessionManager()
        session_id_value = manager.start_session()
        
        assert session_id_value is not None
        assert manager.get_session_id() == session_id_value
        assert session_id.get() == session_id_value
        assert manager.is_active()
    
    def test_start_session_with_user_id(self):
        """Test starting a session with user ID"""
        manager = SessionManager()
        manager.start_session(user_id_value="test_user")
        
        assert user_id.get() == "test_user"
    
    def test_end_session(self):
        """Test ending a session"""
        manager = SessionManager()
        manager.start_session()
        
        assert manager.is_active()
        
        manager.end_session()
        
        assert not manager.is_active()
        assert manager.get_session_id() is None
        assert session_id.get() is None
    
    def test_get_session_duration(self):
        """Test getting session duration"""
        import time
        
        manager = SessionManager()
        manager.start_session()
        
        time.sleep(0.01)  # Small delay
        
        duration = manager.get_session_duration()
        assert duration is not None
        assert duration > 0
    
    def test_session_duration_when_not_active(self):
        """Test session duration returns None when not active"""
        manager = SessionManager()
        assert manager.get_session_duration() is None


class TestGlobalSessionManager:
    """Test global session manager singleton"""
    
    def test_get_session_manager(self):
        """Test getting global session manager"""
        manager1 = get_session_manager()
        manager2 = get_session_manager()
        
        # Should be the same instance
        assert manager1 is manager2


class TestContextFunctions:
    """Test context utility functions"""
    
    def test_get_current_context(self):
        """Test getting current context"""
        session_id.set("session123")
        request_id.set("request456")
        user_id.set("user789")
        operation_name.set("test_operation")
        
        context = get_current_context()
        
        assert context["session_id"] == "session123"
        assert context["request_id"] == "request456"
        assert context["user_id"] == "user789"
        assert context["operation"] == "test_operation"
    
    def test_inject_context_to_logger(self):
        """Test injecting context for logging (filters None)"""
        session_id.set("session123")
        request_id.set(None)
        user_id.set("user789")
        operation_name.set(None)
        
        context = inject_context_to_logger()
        
        # Should include non-None values
        assert "session_id" in context
        assert "user_id" in context
        
        # Should exclude None values
        assert "request_id" not in context
        assert "operation" not in context


class TestIntegration:
    """Integration tests"""
    
    def test_session_with_operations(self):
        """Test session with multiple operations"""
        manager = get_session_manager()
        
        # Start session
        session_id_value = manager.start_session(user_id_value="test_user")
        
        # Run operations
        with TelemetryContext("operation1"):
            op1_context = get_current_context()
            assert op1_context["session_id"] == session_id_value
            assert op1_context["operation"] == "operation1"
        
        with TelemetryContext("operation2"):
            op2_context = get_current_context()
            assert op2_context["session_id"] == session_id_value
            assert op2_context["operation"] == "operation2"
        
        # End session
        manager.end_session()
        assert not manager.is_active()
    
    def test_nested_operations(self):
        """Test nested operation contexts"""
        with TelemetryContext("outer_operation"):
            outer_context = get_current_context()
            
            with TelemetryContext("inner_operation"):
                inner_context = get_current_context()
                
                # Inner operation should override
                assert inner_context["operation"] == "inner_operation"
            
            # Should restore to outer
            restored_context = get_current_context()
            assert restored_context["operation"] == "outer_operation"


class TestErrorHandling:
    """Test error handling"""
    
    def test_context_manager_with_exception(self):
        """Test context manager properly handles exceptions"""
        request_id.set("initial_request")
        
        with pytest.raises(ValueError):
            with TelemetryContext("test_operation"):
                raise ValueError("Test error")
        
        # Should still restore context
        assert request_id.get() == "initial_request"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
