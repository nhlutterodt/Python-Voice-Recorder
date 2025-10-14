"""
Phase 2 Integration Tests: Path Management Module
Test integration of enhanced path management with StorageConfig
"""

import tempfile
from pathlib import Path

from services.file_storage.config import StorageConfig


class TestPhase2Integration:
    """Integration tests for Phase 2 path management features"""

    def test_storage_config_with_enhanced_path_management(self):
        """Test that StorageConfig integrates enhanced path management"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StorageConfig.from_environment("testing", base_path=temp_dir)

            # Test that path_manager is available (Phase 2 feature)
            assert hasattr(config, "path_manager")

            # Test basic path functionality still works (backward compatibility)
            raw_path = config.get_path_for_type("raw")
            assert isinstance(raw_path, Path)
            assert str(temp_dir) in str(raw_path)

    def test_enhanced_path_info_feature(self):
        """Test enhanced path info feature (Phase 2 addition)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StorageConfig.from_environment("development", base_path=temp_dir)

            # Test enhanced path info method (new in Phase 2)
            enhanced_info = config.get_enhanced_path_info()

            # Should always return a result (enhanced or fallback)
            assert "available" in enhanced_info

            if enhanced_info["available"]:
                # Enhanced path management is working
                assert "enhanced_info" in enhanced_info
                assert "validation_results" in enhanced_info
                assert "supported_types" in enhanced_info
            else:
                # Fallback info should be provided
                assert "fallback_info" in enhanced_info
                assert "base_path" in enhanced_info["fallback_info"]

    def test_enhanced_directory_creation_feature(self):
        """Test enhanced directory creation feature (Phase 2 addition)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StorageConfig.from_environment("production", base_path=temp_dir)

            # Test enhanced directory creation method (new in Phase 2)
            result = config.ensure_directories_enhanced()

            # Should always succeed (enhanced or basic)
            assert "success" in result
            assert result["success"]

            # Verify directories exist
            assert config.raw_recordings_path.exists()
            assert config.edited_recordings_path.exists()
            assert config.temp_path.exists()
            if config.backup_path:
                assert config.backup_path.exists()

    def test_enhanced_path_validation_feature(self):
        """Test enhanced path validation feature (Phase 2 addition)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StorageConfig.from_environment("testing", base_path=temp_dir)

            # Create directories first
            config.ensure_directories_enhanced()

            # Test enhanced path validation method (new in Phase 2)
            validation_result = config.validate_path_permissions()

            # Should always return a result
            assert "enhanced" in validation_result

            if validation_result["enhanced"]:
                # Enhanced validation worked
                assert (
                    "valid" in validation_result or "paths_checked" in validation_result
                )
            else:
                # Fallback message should be provided
                assert "message" in validation_result

    def test_enhanced_path_for_type_feature(self):
        """Test enhanced path for type feature (Phase 2 addition)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StorageConfig.from_environment("development", base_path=temp_dir)

            # Test enhanced path getter method (new in Phase 2)
            for path_type in ["raw", "edited", "temp"]:
                result = config.get_path_for_type_enhanced(path_type)

                # Should always return a result
                assert "path" in result or "error" in result
                assert "storage_type" in result
                assert "enhanced" in result

                if "path" in result:
                    # Basic path should work
                    assert isinstance(result["path"], Path)

                    # Enhanced features might be available
                    if result["enhanced"]:
                        assert "enhanced_path" in result
                        assert "validation" in result

    def test_backward_compatibility_preservation(self):
        """Test that all existing StorageConfig functionality still works"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StorageConfig.from_environment("testing", base_path=temp_dir)

            # All original methods should work unchanged
            assert config.environment == "testing"
            assert config.base_path == Path(temp_dir)

            # Original path methods should work
            raw_path = config.get_path_for_type("raw")
            assert isinstance(raw_path, Path)

            # Original validation should work
            storage_info = config.get_storage_info()
            assert "free_mb" in storage_info

            # Original file validation should work
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test")
            validation = config.validate_file_constraints(str(test_file))
            assert "valid" in validation

    def test_phase2_feature_graceful_degradation(self):
        """Test that Phase 2 features degrade gracefully if they fail"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StorageConfig.from_environment("production", base_path=temp_dir)

            # Even if enhanced features fail, basic functionality should work

            # Test enhanced path info with potential failure
            enhanced_info = config.get_enhanced_path_info()
            if not enhanced_info["available"]:
                # Should provide fallback information
                assert "fallback_info" in enhanced_info
                assert enhanced_info["fallback_info"]["base_path"] == str(temp_dir)

            # Test enhanced directory creation with potential failure
            dir_result = config.ensure_directories_enhanced()
            # Should succeed either way
            assert dir_result["success"]

            # Basic path access should always work
            assert config.get_path_for_type("raw") == config.raw_recordings_path

    def test_environment_integration_with_path_management(self):
        """Test that Phase 1 environment features work with Phase 2 path features"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test all environments work with enhanced path management
            for environment in ["development", "testing", "production"]:
                config = StorageConfig.from_environment(environment, base_path=temp_dir)

                # Environment should be properly set (Phase 1 feature)
                assert config.environment == environment

                # Enhanced path features should work (Phase 2 feature)
                enhanced_info = config.get_enhanced_path_info()
                assert "available" in enhanced_info

                # Directory creation should work
                dir_result = config.ensure_directories_enhanced()
                assert dir_result["success"]

    def test_feature_addition_not_removal(self):
        """Verify that Phase 2 is a feature addition, not a removal"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StorageConfig.from_environment("development", base_path=temp_dir)

            # Original functionality should be PRESERVED
            original_methods = [
                "get_path_for_type",
                "get_storage_info",
                "validate_file_constraints",
                "get_configuration_summary",
            ]

            for method_name in original_methods:
                assert hasattr(
                    config, method_name
                ), f"Original method {method_name} was removed!"

            # NEW functionality should be ADDED
            new_methods = [
                "get_enhanced_path_info",
                "ensure_directories_enhanced",
                "validate_path_permissions",
                "get_path_for_type_enhanced",
            ]

            for method_name in new_methods:
                assert hasattr(
                    config, method_name
                ), f"New method {method_name} was not added!"

            # Test that both old and new work
            old_path = config.get_path_for_type("raw")
            new_path_info = config.get_path_for_type_enhanced("raw")

            assert isinstance(old_path, Path)
            assert "path" in new_path_info or "error" in new_path_info
