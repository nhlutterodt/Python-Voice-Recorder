#!/usr/bin/env python3
"""
Unit tests for build script helper functions
Demonstrates improved testability after refactoring
"""

import unittest
from unittest.mock import patch
import sys
from pathlib import Path

# Add the parent directory to path to import the build script
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from scripts.build_voice_recorder_pro import VoiceRecorderBuilder
except ImportError:
    # Fallback for different import paths
    import os
    os.chdir(Path(__file__).parent.parent)
    from scripts.build_voice_recorder_pro import VoiceRecorderBuilder


class TestBuildScriptHelpers(unittest.TestCase):
    """Test the refactored helper functions in VoiceRecorderBuilder"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.builder = VoiceRecorderBuilder()
    
    def test_check_package_import_success(self):
        """Test successful package import"""
        # Test with a standard library package that should always exist
        success, is_pydub_audioop = self.builder._check_package_import("json", "json")
        self.assertTrue(success)
        self.assertFalse(is_pydub_audioop)
    
    def test_check_package_import_failure(self):
        """Test failed package import"""
        success, is_pydub_audioop = self.builder._check_package_import("nonexistent", "nonexistent_package_12345")
        self.assertFalse(success)
        self.assertFalse(is_pydub_audioop)
    
    def test_check_package_import_pydub_audioop_issue(self):
        """Test pydub audioop special case detection"""
        # Mock ImportError with audioop message
        with patch('builtins.__import__', side_effect=ImportError("No module named 'audioop'")):
            success, is_pydub_audioop = self.builder._check_package_import("pydub", "pydub")
            self.assertFalse(success)
            self.assertTrue(is_pydub_audioop)
    
    def test_check_package_group_all_present(self):
        """Test package group checking when all packages are available"""
        packages = {"json": "json", "sys": "sys"}  # Standard library packages
        
        with patch('builtins.print') as mock_print:
            missing = self.builder._check_package_group(packages, "test", "✅", "❌")
            
            self.assertEqual(missing, [])
            # Verify success messages were printed
            mock_print.assert_any_call("   ✅ json (test)")
            mock_print.assert_any_call("   ✅ sys (test)")
    
    def test_check_package_group_some_missing(self):
        """Test package group checking with missing packages"""
        packages = {
            "json": "json",  # Available
            "missing": "nonexistent_package_12345"  # Not available
        }
        
        with patch('builtins.print') as mock_print:
            missing = self.builder._check_package_group(packages, "test", "✅", "❌")
            
            self.assertEqual(missing, ["missing"])
            mock_print.assert_any_call("   ✅ json (test)")
            mock_print.assert_any_call("   ❌ missing (test)")
    
    def test_report_missing_packages_no_missing(self):
        """Test reporting when no packages are missing"""
        with patch('builtins.print') as mock_print:
            result = self.builder._report_missing_packages([], [], [])
            
            self.assertTrue(result)
            # Should not print any error messages
            mock_print.assert_not_called()
    
    def test_report_missing_packages_required_missing(self):
        """Test reporting when required packages are missing"""
        with patch('builtins.print') as mock_print:
            result = self.builder._report_missing_packages(["pkg1", "pkg2"], [], [])
            
            self.assertFalse(result)  # Build cannot continue
            mock_print.assert_any_call("\n❌ Missing required packages: pkg1, pkg2")
            mock_print.assert_any_call("Install with: pip install pkg1 pkg2")
    
    def test_report_missing_packages_optional_missing(self):
        """Test reporting when only optional packages are missing"""
        with patch('builtins.print') as mock_print:
            result = self.builder._report_missing_packages([], ["cloud1"], ["build1"])
            
            self.assertTrue(result)  # Build can continue
            mock_print.assert_any_call("\n⚠️ Missing build packages: build1")
            mock_print.assert_any_call("EXE creation will be disabled")
            mock_print.assert_any_call("\n⚠️ Missing cloud packages: cloud1")
            mock_print.assert_any_call("Cloud features will be disabled in the build")
    
    def test_upx_detection(self):
        """Test that UPX detection is properly set during initialization"""
        # The upx_available property should be set based on shutil.which result
        self.assertIsInstance(self.builder.upx_available, bool)
        
        # Test with mocked shutil.which
        with patch('shutil.which', return_value='/usr/bin/upx'):
            builder = VoiceRecorderBuilder()
            self.assertTrue(builder.upx_available)
        
        with patch('shutil.which', return_value=None):
            builder = VoiceRecorderBuilder()
            self.assertFalse(builder.upx_available)


class TestIntegration(unittest.TestCase):
    """Integration tests for the refactored dependency checking"""
    
    def setUp(self):
        self.builder = VoiceRecorderBuilder()
    
    def test_check_dependencies_integration(self):
        """Test the main check_dependencies method works correctly"""
        with patch('builtins.print'):
            # This should not raise any exceptions
            result = self.builder.check_dependencies()
            self.assertIsInstance(result, bool)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
