#!/usr/bin/env python3
"""
Comprehensive test suite for GoogleAuthManager (without pytest dependency)

Tests core functionality, error handling, and edge cases for the OAuth authentication manager.
"""

import tempfile
import json
import traceback
from pathlib import Path
from unittest.mock import Mock
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

from cloud.exceptions import NotAuthenticatedError, APILibrariesMissingError


class TestRunner:
    """Simple test runner that mimics pytest functionality"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def run_test(self, test_name, test_func, *args, **kwargs):
        """Run a single test function"""
        try:
            print(f"🔍 Testing {test_name}...")
            test_func(*args, **kwargs)
            print(f"✅ {test_name} PASSED")
            self.passed += 1
            return True
        except Exception as e:
            print(f"❌ {test_name} FAILED: {e}")
            self.errors.append((test_name, str(e), traceback.format_exc()))
            self.failed += 1
            return False
    
    def assert_equal(self, actual, expected, message=""):
        """Assert two values are equal"""
        if actual != expected:
            raise AssertionError(f"{message}: Expected {expected}, got {actual}")
    
    def assert_true(self, value, message=""):
        """Assert value is True"""
        if not value:
            raise AssertionError(f"{message}: Expected True, got {value}")
    
    def assert_false(self, value, message=""):
        """Assert value is False"""  
        if value:
            raise AssertionError(f"{message}: Expected False, got {value}")
    
    def assert_is_none(self, value, message=""):
        """Assert value is None"""
        if value is not None:
            raise AssertionError(f"{message}: Expected None, got {value}")
    
    def assert_is_not_none(self, value, message=""):
        """Assert value is not None"""
        if value is None:
            raise AssertionError(f"{message}: Expected not None, got None")
    
    def assert_raises(self, exception_type, func, *args, **kwargs):
        """Assert function raises specific exception"""
        try:
            func(*args, **kwargs)
            raise AssertionError(f"Expected {exception_type.__name__} but no exception was raised")
        except exception_type:
            pass  # Expected exception was raised
        except Exception as e:
            raise AssertionError(f"Expected {exception_type.__name__} but got {type(e).__name__}: {e}")
    
    def summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"📊 TEST SUMMARY: {self.passed}/{total} tests passed")
        
        if self.failed > 0:
            print(f"\n❌ FAILED TESTS ({self.failed}):")
            for test_name, error, trace in self.errors:
                print(f"  • {test_name}: {error}")
        
        if self.passed == total:
            print("🎉 ALL TESTS PASSED!")
            return True
        else:
            print("⚠️ Some tests failed.")
            return False


def test_utility_functions(runner):
    """Test utility functions"""
    
    # Test _has_module
    runner.assert_true(_has_module('os'), "_has_module should detect 'os' module")
    runner.assert_true(_has_module('sys'), "_has_module should detect 'sys' module")
    runner.assert_false(_has_module('nonexistent_module_xyz'), "_has_module should return False for non-existent module")
    runner.assert_false(_has_module(''), "_has_module should return False for empty string")
    
    # Test _mask_email
    test_cases = [
        ('user@example.com', 'us***@example.com'),
        ('ab@test.com', '***@test.com'),
        ('a@test.com', '***@test.com'),
        ('verylongusername@domain.com', 've***@domain.com'),
        ('', 'unknown'),
        (None, 'unknown'),
        ('invalid-email', 'invalid-email'),
        ('no-at-symbol', 'no-at-symbol'),
        ('@domain.com', '***@domain.com'),
    ]
    
    for input_email, expected in test_cases:
        result = _mask_email(input_email)
        runner.assert_equal(result, expected, f"Email masking failed for '{input_email}'")


def test_file_permissions(runner):
    """Test file permission restriction"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)
        try:
            # Should not raise an exception
            _restrict_file_permissions(tmp_path)
            
            # On POSIX systems, check permissions were actually set
            if os.name == 'posix':
                stat_info = tmp_path.stat()
                permissions = stat_info.st_mode & 0o777
                runner.assert_equal(permissions, 0o600, f"File permissions should be 0o600, got {oct(permissions)}")
        finally:
            tmp_path.unlink(missing_ok=True)


def test_callback_server_classes(runner):
    """Test OAuth callback server components"""
    
    # Test that we can create the server class attributes
    runner.assert_true(hasattr(_AuthCallbackServer, 'auth_code'), "Server should have auth_code attribute")
    runner.assert_true(hasattr(_AuthCallbackServer, 'auth_state'), "Server should have auth_state attribute")
    runner.assert_true(hasattr(_AuthCallbackServer, 'auth_error'), "Server should have auth_error attribute")
    
    # Verify the handler has the required methods
    runner.assert_true(hasattr(_CallbackHandler, 'do_GET'), "Handler should have do_GET method")
    runner.assert_true(hasattr(_CallbackHandler, 'log_message'), "Handler should have log_message method")


def test_manager_initialization(runner):
    """Test GoogleAuthManager initialization"""
    
    # Test default initialization
    mgr = GoogleAuthManager()
    runner.assert_true(isinstance(mgr.app_dir, Path), "app_dir should be a Path instance")
    runner.assert_true(mgr.credentials_dir.exists(), "credentials_dir should exist")
    runner.assert_equal(mgr.credentials_file.name, 'token.json', "credentials file should be token.json")
    runner.assert_equal(mgr.client_secrets_file.name, 'client_secrets.json', "client secrets file should be client_secrets.json")
    runner.assert_is_none(mgr.credentials, "credentials should start as None")
    
    # Test custom app_dir
    with tempfile.TemporaryDirectory() as tmp_dir:
        custom_dir = Path(tmp_dir)
        (custom_dir / "cloud" / "credentials").mkdir(parents=True)
        (custom_dir / "config").mkdir(parents=True)
        
        mgr2 = GoogleAuthManager(app_dir=custom_dir)
        runner.assert_equal(mgr2.app_dir, custom_dir, "custom app_dir should be set correctly")
        runner.assert_true(mgr2.credentials_dir.exists(), "custom credentials_dir should exist")


def test_authentication_state(runner):
    """Test authentication state methods"""
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        app_dir = Path(tmp_dir)
        (app_dir / "cloud" / "credentials").mkdir(parents=True)
        (app_dir / "config").mkdir(parents=True)
        
        mgr = GoogleAuthManager(app_dir=app_dir)
        
        # Should start unauthenticated
        runner.assert_false(mgr.is_authenticated(), "should start unauthenticated")
        runner.assert_is_none(mgr.get_credentials(), "should return None for credentials when not authenticated")
        runner.assert_is_none(mgr.get_user_info(), "should return None for user info when not authenticated")
        
        # Test with invalid credentials
        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mgr.credentials = mock_creds
        runner.assert_false(mgr.is_authenticated(), "should be False with invalid credentials")
        
        # Test with valid credentials
        mock_creds.valid = True
        mock_creds.expired = False
        mgr.credentials = mock_creds
        runner.assert_true(mgr.is_authenticated(), "should be True with valid credentials")
        runner.assert_equal(mgr.get_credentials(), mock_creds, "should return credentials when authenticated")


def test_build_service_validation(runner):
    """Test build_service input validation and requirements"""
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        app_dir = Path(tmp_dir)
        (app_dir / "cloud" / "credentials").mkdir(parents=True)
        (app_dir / "config").mkdir(parents=True)
        mgr = GoogleAuthManager(app_dir=app_dir)

        # Test empty/None inputs
        runner.assert_raises(ValueError, mgr.build_service, '', 'v3')
        runner.assert_raises(ValueError, mgr.build_service, 'drive', '')
        runner.assert_raises((ValueError, TypeError), mgr.build_service, None, 'v3')
        runner.assert_raises((ValueError, TypeError), mgr.build_service, 'drive', None)

        # Test authentication requirement
        runner.assert_raises(NotAuthenticatedError, mgr.build_service, 'drive', 'v3')

        # Test with mocked authentication but no Google APIs
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.expired = False
        mgr.credentials = mock_creds

        # Should still fail because GOOGLE_APIS_AVAILABLE is False in test env
        runner.assert_raises(APILibrariesMissingError, mgr.build_service, 'drive', 'v3')


def test_logout_functionality(runner):
    """Test logout functionality"""
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        app_dir = Path(tmp_dir)
        (app_dir / "cloud" / "credentials").mkdir(parents=True)
        (app_dir / "config").mkdir(parents=True)
        
        mgr = GoogleAuthManager(app_dir=app_dir)
        
        # Test logout when not authenticated
        result = mgr.logout()
        runner.assert_true(result, "logout should succeed even when not authenticated")
        runner.assert_is_none(mgr.credentials, "credentials should be None after logout")
        
        # Test logout with credentials
        mgr.credentials = Mock()
        result = mgr.logout()
        runner.assert_true(result, "logout should succeed")
        runner.assert_is_none(mgr.credentials, "credentials should be None after logout")


def test_config_loading(runner):
    """Test configuration loading methods"""
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        app_dir = Path(tmp_dir)
        (app_dir / "cloud" / "credentials").mkdir(parents=True)
        (app_dir / "config").mkdir(parents=True)
        
        mgr = GoogleAuthManager(app_dir=app_dir)
        
        # Test with no config file
        result = mgr._get_client_config()
        runner.assert_is_none(result, "should return None when no config available")
        
        # Test with valid config file
        config_data = {
            "installed": {
                "client_id": "test_client_id",
                "client_secret": "test_secret",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }
        
        mgr.client_secrets_file.write_text(json.dumps(config_data))
        result = mgr._get_client_config()
        runner.assert_equal(result, config_data, "should return config data from file")
        
        # Test with invalid JSON
        mgr.client_secrets_file.write_text("invalid json content")
        result = mgr._get_client_config()
        runner.assert_is_none(result, "should return None for invalid JSON")


def test_credentials_loading(runner):
    """Test credential file loading"""
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        app_dir = Path(tmp_dir)
        (app_dir / "cloud" / "credentials").mkdir(parents=True)
        (app_dir / "config").mkdir(parents=True)
        
        mgr = GoogleAuthManager(app_dir=app_dir)
        
        # Test with no credentials file
        mgr._load_credentials_if_present()
        runner.assert_is_none(mgr.credentials, "should be None when no credentials file")
        
        # Test with credentials file but no Google APIs
        mgr.credentials_file.write_text('{"dummy": "data"}')
        mgr._load_credentials_if_present()
        # Should still be None because GOOGLE_APIS_AVAILABLE is False
        runner.assert_is_none(mgr.credentials, "should be None when Google APIs not available")


def test_scopes_configuration(runner):
    """Test that OAuth scopes are properly configured"""
    
    expected_scopes = [
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/userinfo.profile", 
        "https://www.googleapis.com/auth/userinfo.email",
        "openid",
    ]
    
    runner.assert_equal(GoogleAuthManager.SCOPES, expected_scopes, "OAuth scopes should be properly defined")


def test_integration_unauthenticated_workflow(runner):
    """Test complete workflow for unauthenticated user"""
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        app_dir = Path(tmp_dir)
        (app_dir / "cloud" / "credentials").mkdir(parents=True)
        (app_dir / "config").mkdir(parents=True)
        
        mgr = GoogleAuthManager(app_dir=app_dir)
        
        # Complete unauthenticated workflow
        runner.assert_false(mgr.is_authenticated(), "should start unauthenticated")
        runner.assert_is_none(mgr.get_credentials(), "should have no credentials")
        runner.assert_is_none(mgr.get_user_info(), "should have no user info")
        
        # Should handle logout gracefully
        runner.assert_true(mgr.logout(), "logout should work even when not authenticated")
        
    # Should fail to build services with appropriate errors
    # depending on whether inputs are invalid or the user is unauthenticated
    runner.assert_raises((ValueError, NotAuthenticatedError), mgr.build_service, 'drive', 'v3')


def test_module_detection(runner):
    """Test module detection functionality"""
    
    runner.assert_is_not_none(GOOGLE_APIS_AVAILABLE, "GOOGLE_APIS_AVAILABLE should not be None")
    runner.assert_true(isinstance(GOOGLE_APIS_AVAILABLE, bool), "GOOGLE_APIS_AVAILABLE should be boolean")


def main():
    """Run all tests"""
    print("🧪 COMPREHENSIVE AUTH MANAGER TEST SUITE")
    print("=" * 60)
    
    runner = TestRunner()
    
    # Define all tests
    tests = [
        ("Utility Functions", test_utility_functions),
        ("File Permissions", test_file_permissions),
        ("Callback Server Classes", test_callback_server_classes),
        ("Manager Initialization", test_manager_initialization),
        ("Authentication State", test_authentication_state),
        ("Build Service Validation", test_build_service_validation),
        ("Logout Functionality", test_logout_functionality),
        ("Config Loading", test_config_loading),
        ("Credentials Loading", test_credentials_loading),
        ("Scopes Configuration", test_scopes_configuration),
        ("Integration Workflow", test_integration_unauthenticated_workflow),
        ("Module Detection", test_module_detection),
    ]
    
    # Run all tests
    for test_name, test_func in tests:
        runner.run_test(test_name, test_func, runner)
    
    # Print summary
    return runner.summary()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
