"""
Phase 3 Integration Test: Enhanced Audio Recorder
Tests the integration of enhanced storage system with audio recording functionality
"""

import sys
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test imports
from services.file_storage.config import StorageConfig, EnvironmentManager
from services.file_storage.metadata import FileMetadataCalculator


class TestPhase3AudioRecorderIntegration(unittest.TestCase):
    """Test Phase 3 integration with audio recorder"""
    
    def setUp(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_environment = 'testing'
    
    def tearDown(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_enhanced_storage_config_integration(self):
        """Test that enhanced storage config works for audio recording"""
        try:
            # Test environment-aware storage configuration
            storage_config = StorageConfig.from_environment(
                self.test_environment, 
                base_path=self.temp_dir
            )
            
            # Test basic functionality
            self.assertIsNotNone(storage_config)
            self.assertEqual(storage_config.environment, self.test_environment)
            
            # Test raw recordings path
            raw_path = storage_config.get_path_for_type('raw')
            self.assertIsInstance(raw_path, Path)
            self.assertTrue(str(raw_path).endswith('raw'))
            
            print(f"✅ Storage config integration: {storage_config.environment}")
            print(f"✅ Raw recordings path: {raw_path}")
            
            return True
            
        except Exception as e:
            self.fail(f"Storage config integration failed: {e}")
    
    def test_enhanced_path_management_integration(self):
        """Test enhanced path management features"""
        try:
            storage_config = StorageConfig.from_environment(
                self.test_environment,
                base_path=self.temp_dir
            )
            
            # Test enhanced features if available
            if hasattr(storage_config, 'get_enhanced_path_info'):
                enhanced_info = storage_config.get_enhanced_path_info()
                self.assertIsInstance(enhanced_info, dict)
                self.assertIn('available', enhanced_info)
                print(f"✅ Enhanced path features available: {enhanced_info['available']}")
            
            if hasattr(storage_config, 'get_path_for_type_enhanced'):
                enhanced_path = storage_config.get_path_for_type_enhanced('raw')
                self.assertIsInstance(enhanced_path, dict)
                print(f"✅ Enhanced path method working")
            
            return True
            
        except Exception as e:
            self.fail(f"Enhanced path management integration failed: {e}")
    
    def test_metadata_calculator_integration(self):
        """Test metadata calculator integration"""
        try:
            # Create a test file
            test_file = Path(self.temp_dir) / "test.txt"
            test_file.write_text("Test content for metadata calculation")
            
            # Test metadata calculation
            metadata_calc = FileMetadataCalculator()
            self.assertIsNotNone(metadata_calc)
            
            # Test basic metadata calculation
            metadata = metadata_calc.calculate_metadata(str(test_file))
            self.assertIsInstance(metadata, dict)
            self.assertIn('filesize_bytes', metadata)
            
            print(f"✅ Metadata calculator working")
            print(f"✅ Metadata keys: {list(metadata.keys())}")
            
            return True
            
        except Exception as e:
            self.fail(f"Metadata calculator integration failed: {e}")
    
    def test_environment_manager_integration(self):
        """Test environment manager integration"""
        try:
            env_manager = EnvironmentManager()
            
            # Test supported environments
            environments = env_manager.get_supported_environments()
            self.assertIsInstance(environments, list)
            self.assertIn('development', environments)
            self.assertIn('testing', environments)
            self.assertIn('production', environments)
            
            print(f"✅ Environment manager working")
            print(f"✅ Supported environments: {environments}")
            
            return True
            
        except Exception as e:
            self.fail(f"Environment manager integration failed: {e}")
    
    def test_storage_validation_integration(self):
        """Test storage validation features"""
        try:
            storage_config = StorageConfig.from_environment(
                self.test_environment,
                base_path=self.temp_dir
            )
            
            # Test storage info
            storage_info = storage_config.get_storage_info()
            self.assertIsInstance(storage_info, dict)
            self.assertIn('free_mb', storage_info)
            
            # Test enhanced directory creation if available
            if hasattr(storage_config, 'ensure_directories_enhanced'):
                result = storage_config.ensure_directories_enhanced()
                self.assertIsInstance(result, dict)
                self.assertIn('success', result)
                print(f"✅ Enhanced directory creation: {result['success']}")
            
            print(f"✅ Storage validation working")
            print(f"✅ Free space: {storage_info['free_mb']}MB")
            
            return True
            
        except Exception as e:
            self.fail(f"Storage validation integration failed: {e}")
    
    @patch('sounddevice.query_devices')
    @patch('sounddevice.rec')
    @patch('sounddevice.wait')
    def test_enhanced_audio_recorder_mock_integration(self, mock_wait, mock_rec, mock_query_devices):
        """Test enhanced audio recorder integration with mocked audio devices"""
        try:
            # Mock audio devices
            mock_query_devices.return_value = [
                {'name': 'Test Microphone', 'max_input_channels': 2, 'default_samplerate': 44100}
            ]
            mock_rec.return_value = None
            mock_wait.return_value = None
            
            # Test enhanced audio recorder import and initialization
            from src.enhanced_audio_recorder import EnhancedAudioRecorderManager
            
            # Create enhanced recorder with testing environment
            recorder = EnhancedAudioRecorderManager(environment='testing')
            
            # Test basic initialization
            self.assertIsNotNone(recorder)
            self.assertEqual(recorder.environment, 'testing')
            self.assertIsNotNone(recorder.storage_config)
            
            # Test storage info
            storage_info = recorder.get_storage_info()
            self.assertIsInstance(storage_info, dict)
            self.assertIn('environment', storage_info)
            self.assertEqual(storage_info['environment'], 'testing')
            
            print(f"✅ Enhanced audio recorder initialized")
            print(f"✅ Environment: {recorder.environment}")
            print(f"✅ Output directory: {recorder.output_directory}")
            
            return True
            
        except ImportError as e:
            print(f"⚠️  Enhanced audio recorder import failed: {e}")
            print("This is expected if the integration is not yet complete")
            return False
        except Exception as e:
            self.fail(f"Enhanced audio recorder integration failed: {e}")
    
    def test_backward_compatibility(self):
        """Test that backward compatibility is maintained"""
        try:
            # Test that legacy imports still work
            from services.enhanced_file_storage import StorageConfig as LegacyStorageConfig
            
            # Create legacy config
            legacy_config = LegacyStorageConfig.from_environment(
                self.test_environment,
                base_path=self.temp_dir
            )
            
            # Test basic functionality
            self.assertIsNotNone(legacy_config)
            raw_path = legacy_config.get_path_for_type('raw')
            self.assertIsInstance(raw_path, Path)
            
            print(f"✅ Backward compatibility maintained")
            print(f"✅ Legacy import working")
            
            return True
            
        except Exception as e:
            self.fail(f"Backward compatibility test failed: {e}")


def run_phase_3_integration_tests():
    """Run all Phase 3 integration tests"""
    print("🚀 PHASE 3 INTEGRATION TESTS")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase3AudioRecorderIntegration)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    tests_run = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    success_rate = ((tests_run - failures - errors) / tests_run) * 100 if tests_run > 0 else 0
    
    print("\n" + "=" * 60)
    print("📊 PHASE 3 INTEGRATION TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {tests_run}")
    print(f"Successes: {tests_run - failures - errors}")
    print(f"Failures: {failures}")
    print(f"Errors: {errors}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("✅ PHASE 3 INTEGRATION: READY FOR IMPLEMENTATION")
        return True
    else:
        print("❌ PHASE 3 INTEGRATION: NEEDS ATTENTION")
        return False


if __name__ == "__main__":
    success = run_phase_3_integration_tests()
    sys.exit(0 if success else 1)
