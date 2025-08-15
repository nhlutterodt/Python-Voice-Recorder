#!/usr/bin/env python3
"""
Comprehensive test suite for GoogleAuthManager

Tests core functionality, error handling, and edge cases for the OAuth authentication manager.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from cloud.auth_manager import (
    GoogleAuthManager,
    _has_module,
    _mask_email,
    _AuthCallbackServer,
    _CallbackHandler,
    GOOGLE_APIS_AVAILABLE,
    _restrict_file_permissions
)


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_has_module(self):
        """Test the _has_module function"""
        # Test with existing modules
        assert _has_module('os') is True
        assert _has_module('sys') is True
        assert _has_module('pathlib') is True
        
        # Test with non-existent module
        assert _has_module('nonexistent_module_xyz') is False
        assert _has_module('') is False
    
    def test_mask_email(self):
        """Test email masking for PII protection"""
        test_cases = [
            # (input, expected_output)
            ('user@example.com', 'us***@example.com'),
            ('ab@test.com', '***@test.com'),
            ('a@test.com', '***@test.com'),
            ('verylongusername@domain.com', 've***@domain.com'),
            ('', 'unknown'),
            (None, 'unknown'),
            ('invalid-email', 'invalid-email'),
            ('no-at-symbol', 'no-at-symbol'),
            ('@domain.com', '***@domain.com'),  # Empty username
        ]
        
        for input_email, expected in test_cases:
            result = _mask_email(input_email)
            assert result == expected, f"Failed for input '{input_email}': expected '{expected}', got '{result}'"
    
    def test_restrict_file_permissions(self):
        """Test file permission restriction"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = Path(tmp.name)
            try:
                # Should not raise an exception
                _restrict_file_permissions(tmp_path)
                
                # On POSIX systems, check permissions were actually set
                if os.name == 'posix':
                    stat_info = tmp_path.stat()
                    # Check if only owner has read/write permissions (0o600)
                    permissions = stat_info.st_mode & 0o777
                    assert permissions == 0o600, f"Expected 0o600, got {oct(permissions)}"
            finally:
                tmp_path.unlink(missing_ok=True)


class TestAuthCallbackServer:
    """Test OAuth callback server components"""
    
    def test_callback_server_initialization(self):
        """Test server initialization"""
        # Test that we can create the server class without errors
        # Note: We don't actually bind to avoid port conflicts
        assert hasattr(_AuthCallbackServer, 'auth_code')
        assert hasattr(_AuthCallbackServer, 'auth_state')
        assert hasattr(_AuthCallbackServer, 'auth_error')
    
    def test_callback_handler_class(self):
        """Test callback handler class"""
        # Verify the handler has the required methods
        assert hasattr(_CallbackHandler, 'do_GET')
        assert hasattr(_CallbackHandler, 'log_message')


class TestGoogleAuthManager:
    """Test main GoogleAuthManager class"""
    
    @pytest.fixture
    def temp_app_dir(self):
        """Create a temporary app directory for testing"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            app_dir = Path(tmp_dir)
            # Create required subdirectories
            (app_dir / "cloud" / "credentials").mkdir(parents=True)
            (app_dir / "config").mkdir(parents=True)
            yield app_dir
    
    @pytest.fixture
    def auth_manager(self, temp_app_dir):
        """Create an auth manager instance for testing"""
        return GoogleAuthManager(app_dir=temp_app_dir)
    
    def test_initialization_default(self):
        """Test default initialization"""
        mgr = GoogleAuthManager()
        
        assert isinstance(mgr.app_dir, Path)
        assert mgr.credentials_dir.exists()
        assert mgr.credentials_file.name == 'token.json'
        assert mgr.client_secrets_file.name == 'client_secrets.json'
        assert mgr.credentials is None
        assert mgr.config_manager is None  # Should be None if not available
    
    def test_initialization_custom_dir(self, temp_app_dir):
        """Test initialization with custom directory"""
        mgr = GoogleAuthManager(app_dir=temp_app_dir)
        
        assert mgr.app_dir == temp_app_dir
        assert mgr.credentials_dir == temp_app_dir / "cloud" / "credentials"
        assert mgr.credentials_dir.exists()
    
    def test_is_authenticated_unauthenticated(self, auth_manager):
        """Test is_authenticated when not authenticated"""
        assert auth_manager.is_authenticated() is False
    
    def test_is_authenticated_with_invalid_credentials(self, auth_manager):
        """Test is_authenticated with invalid credentials"""
        # Mock invalid credentials
        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        auth_manager.credentials = mock_creds
        
        assert auth_manager.is_authenticated() is False
    
    def test_is_authenticated_with_valid_credentials(self, auth_manager):
        """Test is_authenticated with valid credentials"""
        # Mock valid credentials
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        auth_manager.credentials = mock_creds
        
        assert auth_manager.is_authenticated() is True
    
    def test_get_credentials_unauthenticated(self, auth_manager):
        """Test get_credentials when not authenticated"""
        assert auth_manager.get_credentials() is None
    
    def test_get_credentials_authenticated(self, auth_manager):
        """Test get_credentials when authenticated"""
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        auth_manager.credentials = mock_creds
        
        result = auth_manager.get_credentials()
        assert result is mock_creds
    
    def test_get_user_info_unauthenticated(self, auth_manager):
        """Test get_user_info when not authenticated"""
        assert auth_manager.get_user_info() is None
    
    def test_get_user_info_no_google_apis(self, auth_manager):
        """Test get_user_info when Google APIs not available"""
        # Mock authenticated state but no APIs
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        auth_manager.credentials = mock_creds
        
        # The actual GOOGLE_APIS_AVAILABLE is False in test environment
        assert auth_manager.get_user_info() is None
    
    def test_logout_success(self, auth_manager):
        """Test successful logout"""
        # Set up some credentials
        auth_manager.credentials = Mock()
        
        result = auth_manager.logout()
        
        assert result is True
        assert auth_manager.credentials is None
    
    def test_logout_no_credentials_file(self, auth_manager):
        """Test logout when no credentials file exists"""
        # Ensure file doesn't exist
        if auth_manager.credentials_file.exists():
            auth_manager.credentials_file.unlink()
        
        result = auth_manager.logout()
        assert result is True
    
    def test_build_service_validation_errors(self, auth_manager):
        """Test build_service input validation"""
        # Test empty API name
        with pytest.raises(ValueError, match="API name and version must be provided"):
            auth_manager.build_service('', 'v3')
        
        # Test empty version
        with pytest.raises(ValueError, match="API name and version must be provided"):
            auth_manager.build_service('drive', '')
        
        # Test None values
        with pytest.raises(ValueError, match="API name and version must be provided"):
            auth_manager.build_service(None, 'v3')
        
        with pytest.raises(ValueError, match="API name and version must be provided"):
            auth_manager.build_service('drive', None)
    
    def test_build_service_not_authenticated(self, auth_manager):
        """Test build_service when not authenticated"""
        with pytest.raises(RuntimeError, match="Authentication required"):
            auth_manager.build_service('drive', 'v3')
    
    def test_build_service_no_google_apis(self, auth_manager):
        """Test build_service when Google APIs not available"""
        # Mock authenticated state
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        auth_manager.credentials = mock_creds
        
        # GOOGLE_APIS_AVAILABLE is False in test environment
        with pytest.raises(RuntimeError, match="Google APIs client library not available"):
            auth_manager.build_service('drive', 'v3')
    
    def test_authenticate_no_google_apis(self, auth_manager):
        """Test authenticate when Google APIs not available"""
        result = auth_manager.authenticate()
        assert result is False
    
    def test_get_client_config_no_config(self, auth_manager):
        """Test _get_client_config when no configuration available"""
        result = auth_manager._get_client_config()
        assert result is None
    
    def test_get_client_config_with_file(self, auth_manager):
        """Test _get_client_config with client_secrets.json"""
        # Create a mock client secrets file
        config_data = {
            "installed": {
                "client_id": "test_client_id",
                "client_secret": "test_secret",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }
        
        auth_manager.client_secrets_file.write_text(json.dumps(config_data))
        
        result = auth_manager._get_client_config()
        assert result == config_data
    
    def test_get_client_config_invalid_json(self, auth_manager):
        """Test _get_client_config with invalid JSON"""
        # Create invalid JSON file
        auth_manager.client_secrets_file.write_text("invalid json content")
        
        result = auth_manager._get_client_config()
        assert result is None
    
    def test_load_credentials_if_present_no_file(self, auth_manager):
        """Test _load_credentials_if_present when no file exists"""
        # Ensure no credentials file
        if auth_manager.credentials_file.exists():
            auth_manager.credentials_file.unlink()
        
        auth_manager._load_credentials_if_present()
        assert auth_manager.credentials is None
    
    def test_load_credentials_if_present_no_google_apis(self, auth_manager):
        """Test _load_credentials_if_present when Google APIs not available"""
        # Create a dummy credentials file
        auth_manager.credentials_file.write_text('{"dummy": "data"}')
        
        # GOOGLE_APIS_AVAILABLE is False in test environment
        auth_manager._load_credentials_if_present()
        assert auth_manager.credentials is None
    
    def test_scopes_defined(self):
        """Test that required OAuth scopes are defined"""
        expected_scopes = [
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "openid",
        ]
        
        assert GoogleAuthManager.SCOPES == expected_scopes


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_full_unauthenticated_workflow(self):
        """Test complete workflow for unauthenticated user"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            app_dir = Path(tmp_dir)
            (app_dir / "cloud" / "credentials").mkdir(parents=True)
            (app_dir / "config").mkdir(parents=True)
            
            mgr = GoogleAuthManager(app_dir=app_dir)
            
            # Should start unauthenticated
            assert mgr.is_authenticated() is False
            assert mgr.get_credentials() is None
            assert mgr.get_user_info() is None
            
            # Should handle logout gracefully
            assert mgr.logout() is True
            
            # Should fail to build services
            with pytest.raises((ValueError, RuntimeError)):
                mgr.build_service('drive', 'v3')
    
    def test_file_permission_security(self):
        """Test that file permissions are handled securely"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = Path(tmp.name)
            try:
                # Test permission restriction
                _restrict_file_permissions(tmp_path)
                
                # Should not raise an exception
                assert tmp_path.exists()
                
                # On POSIX, check actual permissions
                if os.name == 'posix':
                    stat_info = tmp_path.stat()
                    permissions = stat_info.st_mode & 0o777
                    assert permissions == 0o600
                    
            finally:
                tmp_path.unlink(missing_ok=True)


def test_module_detection():
    """Test module detection functionality"""
    # This should work in any environment
    assert GOOGLE_APIS_AVAILABLE is not None
    assert isinstance(GOOGLE_APIS_AVAILABLE, bool)


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
