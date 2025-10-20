"""
Unit tests for cloud._lazy module

Tests lazy import functions for Google Cloud APIs
"""

import pytest
from unittest.mock import patch, MagicMock


class TestHasModule:
    """Tests for _has_module function"""
    
    def test_has_module_builtin(self):
        """Test that builtin modules are detected"""
        from cloud._lazy import _has_module
        assert _has_module("os")
        assert _has_module("sys")
        assert _has_module("logging")
    
    def test_has_module_missing(self):
        """Test that missing modules return False"""
        from cloud._lazy import _has_module
        assert not _has_module("nonexistent_module_that_does_not_exist")
        assert not _has_module("fake.nested.module")
    
    def test_has_module_installed(self):
        """Test that installed packages are detected"""
        from cloud._lazy import _has_module
        # These should be installed based on requirements
        assert _has_module("pathlib")


class TestHasGoogleApisAvailable:
    """Tests for has_google_apis_available function"""
    
    def test_google_apis_available_all_present(self):
        """Test when all Google API modules are available"""
        from cloud._lazy import has_google_apis_available
        # This will depend on whether google-api-python-client is installed
        # The function should return without error
        result = has_google_apis_available()
        assert isinstance(result, bool)
    
    def test_google_apis_available_returns_bool(self):
        """Test that function always returns a boolean"""
        from cloud._lazy import has_google_apis_available
        result = has_google_apis_available()
        assert isinstance(result, bool)


class TestImportBuild:
    """Tests for _import_build function"""
    
    @patch("cloud._lazy._has_module")
    def test_import_build_raises_when_unavailable(self, mock_has_module):
        """Test that ImportError is raised when googleapiclient not available"""
        mock_has_module.return_value = False
        
        from cloud._lazy import _import_build
        
        with patch("importlib.util.find_spec", return_value=None):
            with pytest.raises(ImportError):
                _import_build()
    
    @patch("cloud._lazy._has_module")
    def test_import_build_error_message(self, mock_has_module):
        """Test that ImportError has helpful message"""
        mock_has_module.return_value = False
        
        from cloud._lazy import _import_build
        
        with patch("importlib.util.find_spec", return_value=None):
            with pytest.raises(ImportError) as exc_info:
                _import_build()
            
            assert "Google API client libraries not available" in str(exc_info.value)
            assert "pip install" in str(exc_info.value)


class TestImportHttp:
    """Tests for _import_http function"""
    
    def test_import_http_returns_tuple(self):
        """Test that _import_http returns a tuple when available"""
        try:
            from cloud._lazy import _import_http
            result = _import_http()
            assert isinstance(result, tuple)
            assert len(result) == 2
        except ImportError:
            # Skip test if Google APIs not available
            pytest.skip("Google API libraries not installed")
    
    def test_import_http_tuple_elements_not_none(self):
        """Test that returned tuple elements are valid"""
        try:
            from cloud._lazy import _import_http
            media_file_upload, media_io_base_download = _import_http()
            assert media_file_upload is not None
            assert media_io_base_download is not None
        except ImportError:
            pytest.skip("Google API libraries not installed")


class TestImportErrors:
    """Tests for _import_errors function"""
    
    def test_import_errors_returns_module(self):
        """Test that _import_errors returns errors module when available"""
        try:
            from cloud._lazy import _import_errors
            errors_module = _import_errors()
            assert errors_module is not None
        except ImportError:
            pytest.skip("Google API libraries not installed")


class TestLazyImportIntegration:
    """Integration tests for lazy import pattern"""
    
    def test_all_lazy_imports_consistent(self):
        """Test that lazy import functions are consistent"""
        from cloud._lazy import (
            _has_module,
            has_google_apis_available,
            _import_build,
            _import_http,
            _import_errors,
        )
        
        # All functions should be callable
        assert callable(_has_module)
        assert callable(has_google_apis_available)
        assert callable(_import_build)
        assert callable(_import_http)
        assert callable(_import_errors)
    
    def test_module_can_be_imported_safely(self):
        """Test that importing _lazy module doesn't fail even without Google APIs"""
        # The module itself should always be importable
        try:
            import cloud._lazy
            assert cloud._lazy is not None
        except ImportError as e:
            pytest.fail(f"Could not import cloud._lazy: {e}")
