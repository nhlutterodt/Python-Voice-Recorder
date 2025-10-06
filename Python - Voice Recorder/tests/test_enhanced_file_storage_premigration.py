#!/usr/bin/env python3
"""
Pre-Migration Validation Test for Enhanced File Storage Service
Validates all functionality before refactoring to ensure zero feature loss
"""

import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from services.enhanced_file_storage import (
        EnhancedFileStorageService,
        FileMetadataCalculator,
        StorageConfig,
        StorageValidationError,
        FileMetadataError,
        DatabaseSessionError,
        FileConstraintError,
        StorageOperationError,
        StorageConfigValidationError
    )
    from core.database_context import DatabaseContextManager
    from core.database_health import DatabaseHealthMonitor
    from core.logging_config import get_logger
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("This indicates missing dependencies or path issues")
    sys.exit(1)

logger = get_logger(__name__)

class PreMigrationValidator:
    """Comprehensive validator for current enhanced file storage functionality"""
    
    def __init__(self):
        self.test_results = {
            'exceptions': {'passed': 0, 'failed': 0, 'errors': []},
            'metadata_calculator': {'passed': 0, 'failed': 0, 'errors': []},
            'storage_config': {'passed': 0, 'failed': 0, 'errors': []},
            'storage_service': {'passed': 0, 'failed': 0, 'errors': []},
            'integration': {'passed': 0, 'failed': 0, 'errors': []}
        }
        
    def validate_exceptions(self):
        """Validate all exception classes exist and can be raised"""
        print("🔍 Validating Exception Classes...")
        
        exceptions_to_test = [
            StorageValidationError,
            FileMetadataError,
            DatabaseSessionError,
            FileConstraintError,
            StorageOperationError,
            StorageConfigValidationError
        ]
        
        for exc_class in exceptions_to_test:
            try:
                # Test exception creation
                exc = exc_class("Test message")
                assert isinstance(exc, Exception)
                assert str(exc) == "Test message"
                
                # Test exception raising
                try:
                    raise exc_class("Test raise")
                except exc_class as e:
                    assert str(e) == "Test raise"
                
                self.test_results['exceptions']['passed'] += 1
                print(f"   ✅ {exc_class.__name__}")
                
            except Exception as e:
                self.test_results['exceptions']['failed'] += 1
                self.test_results['exceptions']['errors'].append(f"{exc_class.__name__}: {e}")
                print(f"   ❌ {exc_class.__name__}: {e}")
    
    def validate_file_metadata_calculator(self):
        """Validate FileMetadataCalculator functionality"""
        print("🔍 Validating FileMetadataCalculator...")
        
        # Test static methods
        try:
            # Test _format_duration
            formatted = FileMetadataCalculator._format_duration(3661.5)
            assert formatted == "01:01:01"
            self.test_results['metadata_calculator']['passed'] += 1
            print("   ✅ _format_duration")
        except Exception as e:
            self.test_results['metadata_calculator']['failed'] += 1
            self.test_results['metadata_calculator']['errors'].append(f"_format_duration: {e}")
            print(f"   ❌ _format_duration: {e}")
        
        try:
            # Test _assess_audio_quality
            metadata = {
                'frame_rate': 44100,
                'sample_width_bits': 16,
                'channels': 2
            }
            quality = FileMetadataCalculator._assess_audio_quality(metadata)
            assert quality in ['low_quality', 'standard', 'cd_quality', 'high_resolution', 'unknown']
            self.test_results['metadata_calculator']['passed'] += 1
            print("   ✅ _assess_audio_quality")
        except (Exception, AssertionError) as e:
            self.test_results['metadata_calculator']['failed'] += 1
            self.test_results['metadata_calculator']['errors'].append(f"_assess_audio_quality: {e}")
            print(f"   ❌ _assess_audio_quality: {e}")
        
        try:
            # Test _detect_mime_type_enhanced
            mime_type = FileMetadataCalculator._detect_mime_type_enhanced("test.mp3")
            assert mime_type == "audio/mpeg"
            self.test_results['metadata_calculator']['passed'] += 1
            print("   ✅ _detect_mime_type_enhanced")
        except Exception as e:
            self.test_results['metadata_calculator']['failed'] += 1
            self.test_results['metadata_calculator']['errors'].append(f"_detect_mime_type_enhanced: {e}")
            print(f"   ❌ _detect_mime_type_enhanced: {e}")
        
        # Test with a real temporary file
        try:
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
                tmp.write(b"test content for metadata calculation")
                tmp_path = tmp.name
            
            try:
                # Test basic metadata calculation (without audio)
                metadata = FileMetadataCalculator.calculate_metadata(
                    tmp_path, 
                    include_audio=False, 
                    validate_integrity=True
                )
                
                required_fields = [
                    'filename', 'file_extension', 'filesize_bytes', 
                    'mime_type', 'checksum', 'created_at'
                ]
                
                for field in required_fields:
                    assert field in metadata, f"Missing field: {field}"
                
                assert metadata['filesize_bytes'] > 0
                assert metadata['checksum'] is not None
                assert len(metadata['checksum']) == 64  # SHA256 hex length
                
                self.test_results['metadata_calculator']['passed'] += 1
                print("   ✅ calculate_metadata (basic)")
                
            finally:
                os.unlink(tmp_path)
                
        except Exception as e:
            self.test_results['metadata_calculator']['failed'] += 1
            self.test_results['metadata_calculator']['errors'].append(f"calculate_metadata: {e}")
            print(f"   ❌ calculate_metadata: {e}")
    
    def validate_storage_config(self):
        """Validate StorageConfig functionality"""
        print("🔍 Validating StorageConfig...")
        
        # Test supported environments
        try:
            environments = StorageConfig.get_supported_environments()
            expected_envs = ['development', 'testing', 'production']
            for env in expected_envs:
                assert env in environments
            self.test_results['storage_config']['passed'] += 1
            print("   ✅ get_supported_environments")
        except Exception as e:
            self.test_results['storage_config']['failed'] += 1
            self.test_results['storage_config']['errors'].append(f"get_supported_environments: {e}")
            print(f"   ❌ get_supported_environments: {e}")
        
        # Test config creation for each environment
        for env in ['development', 'testing', 'production']:
            try:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    config = StorageConfig.from_environment(env, base_path=tmp_dir)
                    
                    # Validate paths exist
                    assert config.raw_recordings_path.exists()
                    assert config.edited_recordings_path.exists()
                    assert config.temp_path.exists()
                    
                    # Validate configuration attributes
                    assert hasattr(config, 'min_disk_space_mb')
                    assert hasattr(config, 'max_file_size_mb')
                    assert hasattr(config, 'enable_disk_space_check')
                    
                    # Test storage info
                    storage_info = config.get_storage_info()
                    required_info_fields = ['free_mb', 'used_mb', 'total_mb', 'base_path']
                    for field in required_info_fields:
                        assert field in storage_info
                    
                    self.test_results['storage_config']['passed'] += 1
                    print(f"   ✅ StorageConfig for {env}")
                    
            except Exception as e:
                self.test_results['storage_config']['failed'] += 1
                self.test_results['storage_config']['errors'].append(f"StorageConfig {env}: {e}")
                print(f"   ❌ StorageConfig {env}: {e}")
        
        # Test path type validation
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                config = StorageConfig.from_environment('testing', base_path=tmp_dir)
                
                # Test valid path types
                raw_path = config.get_path_for_type('raw')
                assert raw_path == config.raw_recordings_path
                
                # Test invalid path type
                try:
                    config.get_path_for_type('invalid_type')
                    assert False, "Should have raised ValueError"
                except ValueError:
                    pass  # Expected
                
                self.test_results['storage_config']['passed'] += 1
                print("   ✅ get_path_for_type validation")
                
        except Exception as e:
            self.test_results['storage_config']['failed'] += 1
            self.test_results['storage_config']['errors'].append(f"get_path_for_type: {e}")
            print(f"   ❌ get_path_for_type: {e}")
    
    def validate_enhanced_file_storage_service(self):
        """Validate EnhancedFileStorageService functionality (mocked)"""
        print("🔍 Validating EnhancedFileStorageService...")
        
        try:
            # Mock dependencies
            mock_context_manager = Mock(spec=DatabaseContextManager)
            mock_health_monitor = Mock()  # Remove spec to allow arbitrary attributes
            
            # Mock context manager methods
            mock_context_manager.config = Mock()
            mock_context_manager.config.environment = 'testing'
            mock_context_manager.get_session_metrics.return_value = {'healthy': True}
            
            # Mock health monitor with required methods
            mock_disk_health = Mock()
            mock_disk_health.is_healthy = True
            mock_health_monitor.check_disk_space.return_value = mock_disk_health
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                storage_config = StorageConfig.from_environment('testing', base_path=tmp_dir)
                
                # Test service initialization
                service = EnhancedFileStorageService(
                    context_manager=mock_context_manager,
                    health_monitor=mock_health_monitor,
                    storage_config=storage_config,
                    enable_performance_monitoring=False
                )
                
                # Validate service attributes
                assert service.storage_config == storage_config
                assert service.context_manager == mock_context_manager
                assert service.health_monitor == mock_health_monitor
                
                # Test environment storage paths
                paths = service.get_environment_storage_paths()
                required_paths = ['raw', 'edited', 'temp', 'base']
                for path_type in required_paths:
                    assert path_type in paths
                    assert os.path.exists(paths[path_type])
                
                self.test_results['storage_service']['passed'] += 1
                print("   ✅ Service initialization")
                
        except Exception as e:
            self.test_results['storage_service']['failed'] += 1
            self.test_results['storage_service']['errors'].append(f"Service initialization: {e}")
            print(f"   ❌ Service initialization: {e}")
        
        # Test storage validation
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                storage_config = StorageConfig.from_environment('testing', base_path=tmp_dir)
                
                mock_context_manager = Mock()  # Remove spec to allow arbitrary attributes
                mock_context_manager.config = Mock()
                mock_context_manager.config.environment = 'testing'
                mock_context_manager.get_session_metrics.return_value = {'healthy': True}
                
                mock_health_monitor = Mock()  # Remove spec to allow arbitrary attributes
                mock_disk_health = Mock()
                mock_disk_health.is_healthy = True
                mock_health_monitor.check_disk_space.return_value = mock_disk_health
                
                service = EnhancedFileStorageService(
                    context_manager=mock_context_manager,
                    health_monitor=mock_health_monitor,
                    storage_config=storage_config,
                    enable_performance_monitoring=False
                )
                
                # Test validation
                validation_result = service.validate_storage_configuration()
                assert 'environment' in validation_result
                assert 'overall_valid' in validation_result
                
                self.test_results['storage_service']['passed'] += 1
                print("   ✅ Storage validation")
                
        except Exception as e:
            self.test_results['storage_service']['failed'] += 1
            self.test_results['storage_service']['errors'].append(f"Storage validation: {e}")
            print(f"   ❌ Storage validation: {e}")
    
    def validate_integration(self):
        """Validate integration between components"""
        print("🔍 Validating Component Integration...")
        
        try:
            # Test that all components can work together
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Create storage config
                storage_config = StorageConfig.from_environment('testing', base_path=tmp_dir)
                
                # Create a test file for metadata calculation
                test_file = Path(tmp_dir) / "test.txt"
                test_file.write_text("Test content for integration test")
                
                # Test metadata calculation
                FileMetadataCalculator.calculate_metadata(
                    str(test_file), 
                    include_audio=False
                )
                
                # Test file constraint validation
                constraint_result = storage_config.validate_file_constraints(str(test_file))
                assert 'valid' in constraint_result
                
                self.test_results['integration']['passed'] += 1
                print("   ✅ Component integration")
                
        except Exception as e:
            self.test_results['integration']['failed'] += 1
            self.test_results['integration']['errors'].append(f"Component integration: {e}")
            print(f"   ❌ Component integration: {e}")
    
    def run_validation(self):
        """Run complete validation suite"""
        print("🚀 Starting Pre-Migration Validation...")
        print("=" * 60)
        
        self.validate_exceptions()
        print()
        
        self.validate_file_metadata_calculator()
        print()
        
        self.validate_storage_config()
        print()
        
        self.validate_enhanced_file_storage_service()
        print()
        
        self.validate_integration()
        print()
        
        self.generate_report()
    
    def generate_report(self):
        """Generate validation report"""
        print("📊 Validation Report")
        print("=" * 60)
        
        total_passed = 0
        total_failed = 0
        
        for component, results in self.test_results.items():
            passed = results['passed']
            failed = results['failed']
            total_passed += passed
            total_failed += failed
            
            status = "✅ PASS" if failed == 0 else "❌ FAIL"
            print(f"{component.title().replace('_', ' ')}: {status} ({passed} passed, {failed} failed)")
            
            if results['errors']:
                for error in results['errors']:
                    print(f"  - {error}")
        
        print("-" * 60)
        overall_status = "✅ READY FOR MIGRATION" if total_failed == 0 else "❌ ISSUES FOUND"
        print(f"Overall: {overall_status} ({total_passed} passed, {total_failed} failed)")
        
        if total_failed > 0:
            print("\n⚠️  Please fix the above issues before proceeding with migration.")
            return False
        else:
            print("\n🎉 All validation tests passed! Ready to proceed with migration.")
            return True

def main():
    """Main validation entry point"""
    validator = PreMigrationValidator()
    success = validator.run_validation()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
