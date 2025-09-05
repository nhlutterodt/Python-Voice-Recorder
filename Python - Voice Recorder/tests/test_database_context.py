"""
Comprehensive tests for enhanced database context management.
Tests circuit breaker, disk space validation, error handling, and configuration.
"""

import pytest
import tempfile
import time
import os
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager

# Test the enhanced database context
from core.database_context import (
    DatabaseConfig, 
    DatabaseContextManager,
    DatabaseDiskSpaceError,
    DatabaseCircuitBreakerError,
    DatabaseConnectionError,
    DatabaseTimeoutError,
    DatabaseIntegrityError
)


class TestDatabaseConfig:
    """Test DatabaseConfig dataclass and environment configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = DatabaseConfig()
        
        assert config.min_disk_space_mb == 100
        assert config.connection_timeout == 30
        assert config.retry_attempts == 3
        assert config.retry_delay == 1.0
        assert config.circuit_breaker_threshold == 5
        assert config.circuit_breaker_timeout == 60
        assert config.enable_disk_space_check is True
    
    def test_environment_configurations(self):
        """Test environment-specific configurations"""
        # Test development
        dev_config = DatabaseConfig.from_environment("development")
        assert dev_config.min_disk_space_mb == 50
        assert dev_config.retry_attempts == 2
        
        # Test testing  
        test_config = DatabaseConfig.from_environment("testing")
        assert test_config.min_disk_space_mb == 10
        assert test_config.connection_timeout == 5
        assert test_config.enable_disk_space_check is False
        
        # Test production
        prod_config = DatabaseConfig.from_environment("production")
        assert prod_config.min_disk_space_mb == 500
        assert prod_config.retry_attempts == 5
        
        # Test unknown environment (should use defaults)
        unknown_config = DatabaseConfig.from_environment("unknown")
        assert unknown_config.min_disk_space_mb == 100  # default
    
    def test_config_validation(self):
        """Test configuration parameter validation"""
        # Valid config
        config = DatabaseConfig(min_disk_space_mb=100, connection_timeout=30)
        assert config.min_disk_space_mb == 100
        
        # Test with zero values (should be allowed)
        config_zero = DatabaseConfig(min_disk_space_mb=0)
        assert config_zero.min_disk_space_mb == 0


class TestDatabaseContextManager:
    """Test enhanced DatabaseContextManager with circuit breaker and disk space validation"""
    
    @pytest.fixture
    def mock_session_factory(self):
        """Mock session factory for testing"""
        mock_factory = Mock()
        mock_session = Mock()
        mock_factory.return_value = mock_session
        return mock_factory
    
    @pytest.fixture
    def config(self):
        """Test configuration"""
        return DatabaseConfig(
            min_disk_space_mb=10,
            connection_timeout=5,
            retry_attempts=2,
            circuit_breaker_threshold=2,
            circuit_breaker_timeout=10
        )
    
    @pytest.fixture
    def context_manager(self, mock_session_factory, config):
        """DatabaseContextManager instance for testing"""
        return DatabaseContextManager(mock_session_factory, config)
    
    def test_initialization(self, context_manager, config):
        """Test context manager initialization"""
        assert context_manager.config == config
        assert context_manager._circuit_breaker_failures == 0
        assert context_manager._circuit_breaker_last_failure == 0
        assert context_manager._active_sessions == 0
    
    @patch('psutil.disk_usage')
    def test_disk_space_validation_sufficient(self, mock_disk_usage, context_manager):
        """Test disk space validation when sufficient space is available"""
        # Mock sufficient disk space (100MB free)
        mock_disk_usage.return_value = Mock(free=100 * 1024 * 1024)
        
        # Should not raise exception
        context_manager._check_disk_space()
    
    @patch('psutil.disk_usage')
    def test_disk_space_validation_insufficient(self, mock_disk_usage, context_manager):
        """Test disk space validation when insufficient space"""
        # Mock insufficient disk space (5MB free, need 10MB)
        mock_disk_usage.return_value = Mock(free=5 * 1024 * 1024)
        
        with pytest.raises(DatabaseDiskSpaceError) as exc_info:
            context_manager._check_disk_space()
        
        assert "Insufficient disk space" in str(exc_info.value)
        assert "5.0 MB available" in str(exc_info.value)
    
    @patch('psutil.disk_usage')
    def test_disk_space_check_disabled(self, mock_disk_usage, mock_session_factory):
        """Test that disk space check can be disabled"""
        config = DatabaseConfig(enable_disk_space_check=False)
        context_manager = DatabaseContextManager(mock_session_factory, config)
        
        # Mock insufficient disk space
        mock_disk_usage.return_value = Mock(free=1024)  # Very low
        
        # Should not raise exception when disabled
        context_manager._check_disk_space()
    
    def test_circuit_breaker_closed_state(self, context_manager):
        """Test circuit breaker in closed state (normal operation)"""
        # Circuit breaker should be closed initially
        assert not context_manager._is_circuit_breaker_open()
    
    def test_circuit_breaker_opening(self, context_manager):
        """Test circuit breaker opening after failures"""
        # Simulate failures below threshold
        context_manager._circuit_breaker_failures = 1
        assert not context_manager._is_circuit_breaker_open()
        
        # Reach threshold
        context_manager._circuit_breaker_failures = context_manager.config.circuit_breaker_threshold
        context_manager._circuit_breaker_last_failure = time.time()
        
        assert context_manager._is_circuit_breaker_open()
    
    def test_circuit_breaker_timeout_recovery(self, context_manager):
        """Test circuit breaker automatic recovery after timeout"""
        # Open circuit breaker
        context_manager._circuit_breaker_failures = context_manager.config.circuit_breaker_threshold
        context_manager._circuit_breaker_last_failure = time.time() - (context_manager.config.circuit_breaker_timeout + 1)
        
        # Should be closed due to timeout
        assert not context_manager._is_circuit_breaker_open()
    
    def test_circuit_breaker_reset(self, context_manager):
        """Test circuit breaker reset after successful operation"""
        # Set some failures
        context_manager._circuit_breaker_failures = 3
        
        # Reset should clear failures
        context_manager._reset_circuit_breaker()
        
        assert context_manager._circuit_breaker_failures == 0
    
    @patch('psutil.disk_usage')
    def test_get_session_success(self, mock_disk_usage, context_manager):
        """Test successful session creation"""
        # Mock sufficient disk space
        mock_disk_usage.return_value = Mock(free=100 * 1024 * 1024)
        
        # Mock successful session creation
        mock_session = Mock()
        context_manager.session_factory.return_value = mock_session
        
        with context_manager.get_session() as session:
            assert session == mock_session
            assert context_manager._active_sessions == 1
        
        # Session should be closed after context exit
        assert context_manager._active_sessions == 0
        mock_session.close.assert_called_once()
    
    @patch('psutil.disk_usage')
    def test_get_session_circuit_breaker_open(self, mock_disk_usage, context_manager):
        """Test session creation when circuit breaker is open"""
        # Mock sufficient disk space
        mock_disk_usage.return_value = Mock(free=100 * 1024 * 1024)
        
        # Open circuit breaker
        context_manager._circuit_breaker_failures = context_manager.config.circuit_breaker_threshold
        context_manager._circuit_breaker_last_failure = time.time()
        
        with pytest.raises(DatabaseCircuitBreakerError) as exc_info:
            with context_manager.get_session():
                pass
        
        assert "Circuit breaker is open" in str(exc_info.value)
    
    @patch('psutil.disk_usage')
    def test_get_session_with_retry(self, mock_disk_usage, context_manager):
        """Test session creation with retry logic"""
        # Mock sufficient disk space
        mock_disk_usage.return_value = Mock(free=100 * 1024 * 1024)
        
        # Mock session factory to fail first time, succeed second time
        mock_session = Mock()
        context_manager.session_factory.side_effect = [
            Exception("Connection failed"),
            mock_session
        ]
        
        # Should succeed after retry
        with context_manager.get_session() as session:
            assert session == mock_session
    
    @patch('psutil.disk_usage')
    def test_get_session_retry_exhaustion(self, mock_disk_usage, context_manager):
        """Test session creation when all retries are exhausted"""
        # Mock sufficient disk space
        mock_disk_usage.return_value = Mock(free=100 * 1024 * 1024)
        
        # Mock session factory to always fail
        context_manager.session_factory.side_effect = Exception("Persistent connection error")
        
        with pytest.raises(DatabaseConnectionError) as exc_info:
            with context_manager.get_session():
                pass
        
        # Should have incremented circuit breaker failures
        assert context_manager._circuit_breaker_failures > 0
    
    def test_session_cleanup_on_exception(self, context_manager):
        """Test that session is properly cleaned up when exception occurs"""
        mock_session = Mock()
        context_manager.session_factory.return_value = mock_session
        
        # Mock disk space check to pass
        with patch('psutil.disk_usage') as mock_disk_usage:
            mock_disk_usage.return_value = Mock(free=100 * 1024 * 1024)
            
            # Test exception in context
            try:
                with context_manager.get_session() as session:
                    assert context_manager._active_sessions == 1
                    raise ValueError("Test exception")
            except ValueError:
                pass
            
            # Session should still be cleaned up
            assert context_manager._active_sessions == 0
            mock_session.close.assert_called_once()
    
    def test_session_metrics_tracking(self, context_manager):
        """Test that session metrics are properly tracked"""
        initial_sessions = context_manager.get_session_metrics()
        assert initial_sessions["active_sessions"] == 0
        assert initial_sessions["total_sessions_created"] == 0
        
        # Mock session creation
        with patch('psutil.disk_usage') as mock_disk_usage:
            mock_disk_usage.return_value = Mock(free=100 * 1024 * 1024)
            mock_session = Mock()
            context_manager.session_factory.return_value = mock_session
            
            with context_manager.get_session():
                metrics = context_manager.get_session_metrics()
                assert metrics["active_sessions"] == 1
                assert metrics["total_sessions_created"] == 1
            
            # After session closes
            final_metrics = context_manager.get_session_metrics()
            assert final_metrics["active_sessions"] == 0
            assert final_metrics["total_sessions_created"] == 1


class TestDatabaseExceptions:
    """Test custom database exceptions"""
    
    def test_database_disk_space_error(self):
        """Test DatabaseDiskSpaceError exception"""
        error = DatabaseDiskSpaceError("Disk full", required_mb=100, available_mb=50)
        
        assert str(error) == "Disk full"
        assert error.required_mb == 100
        assert error.available_mb == 50
    
    def test_database_circuit_breaker_error(self):
        """Test DatabaseCircuitBreakerError exception"""
        error = DatabaseCircuitBreakerError("Circuit open", failure_count=5, timeout_seconds=60)
        
        assert str(error) == "Circuit open"
        assert error.failure_count == 5
        assert error.timeout_seconds == 60
    
    def test_database_connection_error(self):
        """Test DatabaseConnectionError exception"""
        original_error = Exception("Connection refused")
        error = DatabaseConnectionError("Failed to connect", original_error, retry_count=3)
        
        assert str(error) == "Failed to connect"
        assert error.original_error == original_error
        assert error.retry_count == 3
    
    def test_database_timeout_error(self):
        """Test DatabaseTimeoutError exception"""
        error = DatabaseTimeoutError("Operation timed out", timeout_seconds=30, operation="query")
        
        assert str(error) == "Operation timed out"
        assert error.timeout_seconds == 30
        assert error.operation == "query"
    
    def test_database_integrity_error(self):
        """Test DatabaseIntegrityError exception"""
        error = DatabaseIntegrityError("Corruption detected", corruption_type="table", affected_tables=["recordings"])
        
        assert str(error) == "Corruption detected"
        assert error.corruption_type == "table"
        assert error.affected_tables == ["recordings"]


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios"""
    
    @pytest.fixture
    def temp_db_dir(self):
        """Create temporary directory for database testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_low_disk_space_scenario(self, temp_db_dir):
        """Test behavior when system is low on disk space"""
        # This test would need to actually create a filesystem with limited space
        # For now, we'll mock the disk usage
        
        config = DatabaseConfig(min_disk_space_mb=1000)  # Require 1GB
        mock_factory = Mock()
        context_manager = DatabaseContextManager(mock_factory, config)
        
        with patch('psutil.disk_usage') as mock_disk_usage:
            # Mock low disk space
            mock_disk_usage.return_value = Mock(free=100 * 1024 * 1024)  # 100MB
            
            with pytest.raises(DatabaseDiskSpaceError):
                with context_manager.get_session():
                    pass
    
    def test_database_recovery_scenario(self, temp_db_dir):
        """Test database recovery after failures"""
        config = DatabaseConfig(
            circuit_breaker_threshold=2,
            circuit_breaker_timeout=1,  # Short timeout for testing
            retry_attempts=1
        )
        mock_factory = Mock()
        context_manager = DatabaseContextManager(mock_factory, config)
        
        with patch('psutil.disk_usage') as mock_disk_usage:
            mock_disk_usage.return_value = Mock(free=1000 * 1024 * 1024)  # Sufficient space
            
            # Cause failures to open circuit breaker
            mock_factory.side_effect = Exception("Database unavailable")
            
            # First failure
            with pytest.raises(DatabaseConnectionError):
                with context_manager.get_session():
                    pass
            
            # Second failure - should open circuit breaker
            with pytest.raises(DatabaseConnectionError):
                with context_manager.get_session():
                    pass
            
            # Circuit breaker should now be open
            with pytest.raises(DatabaseCircuitBreakerError):
                with context_manager.get_session():
                    pass
            
            # Wait for circuit breaker timeout
            time.sleep(1.1)
            
            # Fix the database and test recovery
            mock_session = Mock()
            mock_factory.side_effect = None
            mock_factory.return_value = mock_session
            
            # Should succeed and reset circuit breaker
            with context_manager.get_session() as session:
                assert session == mock_session
            
            # Circuit breaker should be reset
            assert context_manager._circuit_breaker_failures == 0


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
