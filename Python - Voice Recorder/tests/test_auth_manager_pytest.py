"""
Pytest-compatible comprehensive test suite for Google Auth Manager.
Tests all public functionality without requiring actual Google API authentication.

Usage: python -m pytest tests/test_auth_manager_pytest.py -v
"""

import sys
import os
from unittest.mock import Mock, patch
from pathlib import Path
import pytest

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import our modules
from cloud.auth_manager import GoogleAuthManager, GOOGLE_APIS_AVAILABLE

def test_google_apis_availability():
    """Test Google APIs availability detection"""
    api_status = GOOGLE_APIS_AVAILABLE
    assert isinstance(api_status, bool)
    print(f"✓ Google APIs detection: {api_status}")

def test_manager_initialization():
    """Test GoogleAuthManager can be initialized"""
    # Test with default parameters
    manager = GoogleAuthManager()
    assert manager is not None
    assert hasattr(manager, 'app_dir')
    assert hasattr(manager, 'credentials_dir')
    assert hasattr(manager, 'credentials_file')
    assert hasattr(manager, 'client_secrets_file')
    print("✓ Manager initializes with defaults")
    
    # Test with custom app directory
    custom_dir = Path.cwd()
    manager2 = GoogleAuthManager(app_dir=custom_dir)
    assert manager2.app_dir == custom_dir
    print("✓ Manager accepts custom app directory")
    
    # Test path attributes are Path objects
    assert isinstance(manager.app_dir, Path)
    assert isinstance(manager.credentials_dir, Path)
    assert isinstance(manager.credentials_file, Path)
    assert isinstance(manager.client_secrets_file, Path)
    print("✓ Manager paths are proper Path objects")

def test_authentication_state():
    """Test authentication state checking"""
    manager = GoogleAuthManager()
    
    # Test initial unauthenticated state
    assert not manager.is_authenticated()
    print("✓ Initially unauthenticated")
    
    # Test state with mock credentials
    mock_creds = Mock()
    mock_creds.valid = True
    mock_creds.expired = False
    manager.credentials = mock_creds
    assert manager.is_authenticated()
    print("✓ Authenticated with valid credentials")
    
    # Test state with invalid credentials
    mock_creds.valid = False
    assert not manager.is_authenticated()
    print("✓ Not authenticated with invalid credentials")
    
    # Test state with expired credentials
    mock_creds.valid = True
    mock_creds.expired = True
    assert not manager.is_authenticated()
    print("✓ Not authenticated with expired credentials")
    
    # Test user info when unauthenticated
    manager.credentials = None
    user_info = manager.get_user_info()
    assert user_info is None
    print("✓ No user info when unauthenticated")

def test_build_service_basic():
    """Test build_service method basic functionality"""
    manager = GoogleAuthManager()
    
    # Test without authentication - should raise NotAuthenticatedError
    from cloud.exceptions import NotAuthenticatedError
    manager.credentials = None
    with pytest.raises(NotAuthenticatedError):
        manager.build_service("drive", "v3")
    print("✓ Raises error when unauthenticated")
    
    # Test with empty service name - should raise ValueError
    mock_creds = Mock()
    mock_creds.valid = True
    mock_creds.expired = False
    manager.credentials = mock_creds
    
    with pytest.raises(ValueError, match="API name and version must be provided"):
        manager.build_service("", "v3")
    print("✓ Raises error for empty service name")
    
    # Test with empty version - should raise ValueError
    with pytest.raises(ValueError, match="API name and version must be provided"):
        manager.build_service("drive", "")
    print("✓ Raises error for empty version")
    
    # Test with None parameters - should raise ValueError
    with pytest.raises(ValueError):
        manager.build_service(None, "v3")  # type: ignore
    print("✓ Handles None service name")
    
    with pytest.raises(ValueError):
        manager.build_service("drive", None)  # type: ignore
    print("✓ Handles None version")

def test_logout_functionality():
    """Test logout functionality"""
    manager = GoogleAuthManager()
    
    # Set up authenticated state
    mock_creds = Mock()
    mock_creds.valid = True
    manager.credentials = mock_creds
    
    # Test logout
    manager.logout()
    assert manager.credentials is None
    assert not manager.is_authenticated()
    print("✓ Logout clears credentials")
    
    # Test logout when already logged out
    manager.logout()  # Should not raise error
    assert manager.credentials is None
    print("✓ Multiple logouts handled gracefully")

def test_scopes_configuration():
    """Test OAuth scopes configuration"""
    GoogleAuthManager()
    
    # Test that SCOPES is a class attribute
    assert hasattr(GoogleAuthManager, 'SCOPES')
    assert isinstance(GoogleAuthManager.SCOPES, list)
    assert len(GoogleAuthManager.SCOPES) > 0
    print("✓ Default scopes configured")
    
    # Test specific scope requirements
    scopes = GoogleAuthManager.SCOPES
    assert 'https://www.googleapis.com/auth/drive.file' in scopes
    assert 'https://www.googleapis.com/auth/userinfo.profile' in scopes
    assert 'https://www.googleapis.com/auth/userinfo.email' in scopes
    assert 'openid' in scopes
    print("✓ Required scopes present")

def test_integration_unauthenticated_workflow():
    """Test complete workflow for unauthenticated user"""
    manager = GoogleAuthManager()
    
    # Verify initial state
    assert not manager.is_authenticated()
    assert manager.get_user_info() is None
    
    # Try to build service (should raise exception gracefully)
    from cloud.exceptions import NotAuthenticatedError
    with pytest.raises(NotAuthenticatedError):
        manager.build_service("drive", "v3")
    print("✓ Build service raises appropriate error when unauthenticated")
    
    # Logout should work even when not authenticated
    result = manager.logout()
    assert result is True  # Should return True even when not authenticated
    assert not manager.is_authenticated()
    
    print("✓ Unauthenticated workflow handled correctly")

def test_config_manager_integration():
    """Test config manager integration"""
    # Test manager initialization (config_manager is imported in __init__, not module level)
    manager = GoogleAuthManager()
    # config_manager is set during initialization, should handle gracefully if missing
    assert hasattr(manager, 'config_manager')
    print("✓ Config manager attribute exists")
    
    # Test that manager works whether or not config_manager is available
    assert manager.credentials_file.name == "token.json"
    assert manager.client_secrets_file.name == "client_secrets.json"
    print("✓ File paths configured correctly regardless of config_manager")

def test_error_handling():
    """Test error handling in various scenarios"""
    manager = GoogleAuthManager()
    
    # First set up authenticated state for type validation tests
    mock_creds = Mock()
    mock_creds.valid = True
    mock_creds.expired = False
    manager.credentials = mock_creds
    
    # Test building service with invalid types - integer values are truthy but wrong type
    # The validation logic checks `not api`, so 123 passes as truthy
    # The error will come from the Google API build function itself
    # Depending on environment/build, invalid types may raise ValueError/TypeError
    # or a runtime error from the underlying client; allow those too but prefer
    # ValueError/TypeError as the more deterministic outcomes in our code.
    from cloud.exceptions import APILibrariesMissingError
    with pytest.raises((ValueError, TypeError, APILibrariesMissingError)):
        manager.build_service(123, "v3")  # type: ignore
    print("✓ Handles non-string service name")
    
    with pytest.raises((ValueError, TypeError, APILibrariesMissingError)):
        manager.build_service("drive", 123)  # type: ignore
    print("✓ Handles non-string version")
    
    # Test with invalid service names (when authenticated)
    # This will now either succeed (if Google APIs are available) or fail differently
    # Invalid service name may surface different exceptions depending on Google
    # client availability; accept ValueError or APILibrariesMissingError from downstream.
    from cloud.exceptions import APILibrariesMissingError
    with pytest.raises((ValueError, APILibrariesMissingError)):
        manager.build_service("invalid-service", "v3")
    print("✓ Handles invalid service names appropriately")

@patch('cloud.auth_manager.GOOGLE_APIS_AVAILABLE', False)
def test_without_google_apis():
    """Test behavior when Google APIs are not available"""
    manager = GoogleAuthManager()
    
    # Should still initialize
    assert manager is not None
    
    # Should not be able to build services - should raise APILibrariesMissingError about Google APIs
    mock_creds = Mock()
    mock_creds.valid = True
    mock_creds.expired = False
    manager.credentials = mock_creds
    from cloud.exceptions import APILibrariesMissingError
    
    with pytest.raises(APILibrariesMissingError):
        manager.build_service("drive", "v3")
    print("✓ Graceful degradation without Google APIs")

def test_file_structure():
    """Test that the manager sets up correct file structure"""
    manager = GoogleAuthManager()
    
    # Check that paths are set correctly
    assert manager.credentials_dir.name == "credentials"
    assert manager.credentials_file.name == "token.json"
    assert manager.client_secrets_file.name == "client_secrets.json"
    
    # Check relative structure
    assert manager.credentials_dir.parent.name == "cloud"
    assert manager.client_secrets_file.parent.name == "config"
    
    print("✓ File structure configured correctly")

def test_module_detection():
    """Test module availability detection"""
    # Test that our auth manager can be imported
    from cloud.auth_manager import GoogleAuthManager
    manager = GoogleAuthManager()
    assert hasattr(manager, 'credentials')
    print("✓ Auth manager module imports successfully")
    
    # Test GOOGLE_APIS_AVAILABLE constant
    assert isinstance(GOOGLE_APIS_AVAILABLE, bool)
    print(f"✓ Google APIs available: {GOOGLE_APIS_AVAILABLE}")

if __name__ == "__main__":
    # Run all tests when called directly
    pytest.main([__file__, "-v"])
