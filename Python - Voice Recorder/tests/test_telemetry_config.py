#!/usr/bin/env python3
"""
Tests for telemetry configuration module
"""
import logging
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from core.telemetry_config import (
    TelemetryConfig,
    get_telemetry_config,
    initialize_telemetry,
    shutdown_telemetry
)


class TestTelemetryConfig:
    """Test telemetry configuration"""
    
    def setup_method(self):
        """Reset global state before each test"""
        import core.telemetry_config
        core.telemetry_config._telemetry_config = None
    
    def test_init_defaults(self):
        """Test initialization with default values"""
        config = TelemetryConfig()
        assert config.dsn == ''
        assert config.environment in ('development', 'staging', 'production')
        assert config.enabled is False
        assert config._initialized is False
    
    def test_init_with_params(self):
        """Test initialization with explicit parameters"""
        config = TelemetryConfig(
            dsn='https://test@sentry.io/123',
            environment='staging',
            release='2.1.0',
            enabled=True
        )
        assert config.dsn == 'https://test@sentry.io/123'
        assert config.environment == 'staging'
        assert config.release == '2.1.0'
        assert config.enabled is True
    
    def test_detect_environment_from_env_var(self):
        """Test environment detection from environment variable"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}):
            config = TelemetryConfig()
            assert config.environment == 'production'
    
    def test_detect_environment_frozen(self):
        """Test environment detection for frozen executable"""
        import sys
        original_frozen = getattr(sys, 'frozen', False)
        try:
            sys.frozen = True
            config = TelemetryConfig()
            assert config.environment == 'production'
        finally:
            if original_frozen:
                sys.frozen = original_frozen
            else:
                delattr(sys, 'frozen')
    
    def test_detect_environment_dev_indicators(self):
        """Test environment detection from dev indicators"""
        import sys
        original_argv = sys.argv[0]
        try:
            sys.argv[0] = 'pytest'
            config = TelemetryConfig()
            assert config.environment == 'development'
        finally:
            sys.argv[0] = original_argv
    
    def test_get_release_version_from_build_info(self, tmp_path):
        """Test reading version from build_info.json"""
        import json
        
        # Create mock build_info.json
        build_info = {'version': '2.1.0-test'}
        build_info_path = tmp_path / 'build_info.json'
        with open(build_info_path, 'w') as f:
            json.dump(build_info, f)
        
        # Mock Path resolution
        with patch('core.telemetry_config.Path') as mock_path:
            mock_path.return_value.parent.parent = tmp_path
            config = TelemetryConfig()
            assert config.release == '2.1.0-test'
    
    def test_get_release_version_from_version_file(self, tmp_path):
        """Test reading version from VERSION file"""
        # Create mock VERSION file
        version_path = tmp_path / 'VERSION'
        version_path.write_text('2.2.0-beta')
        
        # Mock Path resolution
        with patch('core.telemetry_config.Path') as mock_path:
            mock_path.return_value.parent.parent = tmp_path
            config = TelemetryConfig()
            assert config.release == '2.2.0-beta'
    
    def test_get_release_version_fallback(self):
        """Test version fallback when files not found"""
        with patch('core.telemetry_config.Path') as mock_path:
            # Make both build_info.json and VERSION not exist
            mock_instance = Mock()
            mock_instance.parent.parent.joinpath.return_value.exists.return_value = False
            mock_path.return_value = mock_instance
            config = TelemetryConfig()
            assert config.release == 'unknown'
    
    @patch('core.telemetry_config.sentry_sdk')
    def test_initialize_success(self, mock_sentry):
        """Test successful Sentry initialization"""
        config = TelemetryConfig(
            dsn='https://test@sentry.io/123',
            enabled=True
        )
        
        result = config.initialize()
        
        assert result is True
        assert config._initialized is True
        mock_sentry.init.assert_called_once()
        
        # Check init parameters
        call_kwargs = mock_sentry.init.call_args[1]
        assert call_kwargs['dsn'] == 'https://test@sentry.io/123'
        assert call_kwargs['send_default_pii'] is False
        assert call_kwargs['attach_stacktrace'] is True
    
    def test_initialize_disabled(self):
        """Test initialization when telemetry disabled"""
        config = TelemetryConfig(enabled=False)
        result = config.initialize()
        assert result is False
        assert config._initialized is False
    
    def test_initialize_no_dsn(self):
        """Test initialization without DSN"""
        config = TelemetryConfig(enabled=True)
        result = config.initialize()
        assert result is False
        assert config._initialized is False
    
    def test_initialize_already_initialized(self):
        """Test double initialization (should be idempotent)"""
        config = TelemetryConfig(
            dsn='https://test@sentry.io/123',
            enabled=True
        )
        config._initialized = True
        
        result = config.initialize()
        assert result is True
    
    @patch('core.telemetry_config.sentry_sdk')
    def test_initialize_exception_handling(self, mock_sentry):
        """Test initialization error handling"""
        mock_sentry.init.side_effect = Exception("Init failed")
        
        config = TelemetryConfig(
            dsn='https://test@sentry.io/123',
            enabled=True
        )
        
        result = config.initialize()
        assert result is False
        assert config._initialized is False
    
    def test_get_traces_sample_rate_production(self):
        """Test traces sample rate for production"""
        config = TelemetryConfig(environment='production')
        assert config._get_traces_sample_rate() == 0.1
    
    def test_get_traces_sample_rate_staging(self):
        """Test traces sample rate for staging"""
        config = TelemetryConfig(environment='staging')
        assert config._get_traces_sample_rate() == 0.5
    
    def test_get_traces_sample_rate_development(self):
        """Test traces sample rate for development"""
        config = TelemetryConfig(environment='development')
        assert config._get_traces_sample_rate() == 1.0
    
    def test_get_profiles_sample_rate_production(self):
        """Test profiles sample rate for production"""
        config = TelemetryConfig(environment='production')
        assert config._get_profiles_sample_rate() == 0.01
    
    def test_get_profiles_sample_rate_staging(self):
        """Test profiles sample rate for staging"""
        config = TelemetryConfig(environment='staging')
        assert config._get_profiles_sample_rate() == 0.1
    
    def test_get_profiles_sample_rate_development(self):
        """Test profiles sample rate for development"""
        config = TelemetryConfig(environment='development')
        assert config._get_profiles_sample_rate() == 0.0
    
    @patch('core.telemetry_config.sentry_sdk')
    def test_shutdown(self, mock_sentry):
        """Test graceful shutdown"""
        mock_client = Mock()
        mock_hub = Mock()
        mock_hub.client = mock_client
        mock_sentry.Hub.current = mock_hub
        
        config = TelemetryConfig()
        config._initialized = True
        
        config.shutdown(timeout=5)
        
        mock_client.close.assert_called_once_with(timeout=5)
        assert config._initialized is False
    
    @patch('core.telemetry_config.sentry_sdk')
    def test_shutdown_not_initialized(self, mock_sentry):
        """Test shutdown when not initialized"""
        config = TelemetryConfig()
        config.shutdown()  # Should not raise error
        assert config._initialized is False
    
    @patch('core.telemetry_config.sentry_sdk')
    def test_set_user_context(self, mock_sentry):
        """Test setting user context"""
        config = TelemetryConfig()
        config._initialized = True
        
        config.set_user_context("session_abc123")
        
        mock_sentry.set_user.assert_called_once_with({"id": "session_abc123"})
    
    @patch('core.telemetry_config.sentry_sdk')
    def test_set_tag(self, mock_sentry):
        """Test setting tags"""
        config = TelemetryConfig()
        config._initialized = True
        
        config.set_tag("version", "2.1.0")
        
        mock_sentry.set_tag.assert_called_once_with("version", "2.1.0")
    
    @patch('core.pii_filter.get_pii_filter')
    @patch('core.telemetry_config.sentry_sdk')
    def test_set_context(self, mock_sentry, mock_filter):
        """Test setting custom context with PII filtering"""
        mock_pii_filter = Mock()
        mock_pii_filter.filter_dict.return_value = {'filtered': 'data'}
        mock_filter.return_value = mock_pii_filter
        
        config = TelemetryConfig()
        config._initialized = True
        
        config.set_context("recording", {"file": "test.wav", "user": "john"})
        
        mock_pii_filter.filter_dict.assert_called_once()
        mock_sentry.set_context.assert_called_once_with("recording", {'filtered': 'data'})
    
    @patch('core.telemetry_config.sentry_sdk')
    def test_capture_exception(self, mock_sentry):
        """Test capturing exception"""
        mock_sentry.capture_exception.return_value = "event_123"
        
        config = TelemetryConfig()
        config._initialized = True
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            event_id = config.capture_exception(e)
        
        assert event_id == "event_123"
        mock_sentry.capture_exception.assert_called_once()
    
    @patch('core.pii_filter.get_pii_filter')
    @patch('core.telemetry_config.sentry_sdk')
    def test_capture_message(self, mock_sentry, mock_filter):
        """Test capturing message with PII filtering"""
        mock_pii_filter = Mock()
        mock_pii_filter.filter_string.return_value = "Filtered message"
        mock_filter.return_value = mock_pii_filter
        mock_sentry.capture_message.return_value = "event_456"
        
        config = TelemetryConfig()
        config._initialized = True
        
        event_id = config.capture_message("Test message with PII", level='warning')
        
        assert event_id == "event_456"
        mock_pii_filter.filter_string.assert_called_once()
        mock_sentry.capture_message.assert_called_once_with("Filtered message", level='warning')
    
    def test_capture_exception_not_initialized(self):
        """Test exception capture when not initialized"""
        config = TelemetryConfig()
        
        try:
            raise ValueError("Test")
        except ValueError as e:
            event_id = config.capture_exception(e)
        
        assert event_id is None
    
    def test_global_config_singleton(self):
        """Test global config singleton"""
        config1 = get_telemetry_config()
        config2 = get_telemetry_config()
        assert config1 is config2
    
    @patch('core.telemetry_config.sentry_sdk')
    def test_initialize_telemetry_function(self, mock_sentry):
        """Test global initialize_telemetry function"""
        result = initialize_telemetry(
            dsn='https://test@sentry.io/999',
            environment='staging',
            release='3.0.0',
            enabled=True
        )
        
        assert result is True
        config = get_telemetry_config()
        assert config.dsn == 'https://test@sentry.io/999'
        assert config.environment == 'staging'
        assert config.release == '3.0.0'
        assert config.enabled is True
    
    @patch('core.telemetry_config.sentry_sdk')
    def test_shutdown_telemetry_function(self, mock_sentry):
        """Test global shutdown_telemetry function"""
        mock_client = Mock()
        mock_hub = Mock()
        mock_hub.client = mock_client
        mock_sentry.Hub.current = mock_hub
        
        config = get_telemetry_config()
        config._initialized = True
        
        shutdown_telemetry(timeout=3)
        
        mock_client.close.assert_called_once_with(timeout=3)
    
    @patch('core.telemetry_config.sentry_sdk')
    def test_initialize_with_pii_filter(self, mock_sentry):
        """Test that initialization includes PII filter"""
        from core.pii_filter import filter_event
        
        config = TelemetryConfig(
            dsn='https://test@sentry.io/123',
            enabled=True
        )
        config.initialize()
        
        call_kwargs = mock_sentry.init.call_args[1]
        assert call_kwargs['before_send'] == filter_event
    
    @patch('core.telemetry_config.sentry_sdk')
    def test_initialize_logging_integration(self, mock_sentry):
        """Test that logging integration is configured"""
        config = TelemetryConfig(
            dsn='https://test@sentry.io/123',
            enabled=True
        )
        config.initialize()
        
        call_kwargs = mock_sentry.init.call_args[1]
        integrations = call_kwargs['integrations']
        assert len(integrations) > 0
        # First integration should be LoggingIntegration
        assert 'LoggingIntegration' in str(type(integrations[0]))
