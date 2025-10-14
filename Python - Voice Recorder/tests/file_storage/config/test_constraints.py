"""
Tests for Storage Constraints Module - Phase 3
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from voice_recorder.services.file_storage.config.constraints import (
    ConstraintConfig,
    ConstraintValidator,
    StorageConstraints,
    create_constraints_from_environment,
)
from voice_recorder.services.file_storage.config.environment import EnvironmentConfig


class TestConstraintConfig:
    """Test ConstraintConfig dataclass"""

    def test_valid_constraint_config(self):
        """Test creating valid constraint configuration"""
        config = ConstraintConfig(
            min_disk_space_mb=50,
            max_file_size_mb=500,
            enable_disk_space_check=True,
            retention_days=30,
        )

        assert config.min_disk_space_mb == 50
        assert config.max_file_size_mb == 500
        assert config.enable_disk_space_check is True
        assert config.retention_days == 30

    def test_invalid_min_disk_space(self):
        """Test constraint config with invalid min disk space"""
        with pytest.raises(ValueError, match="min_disk_space_mb must be positive"):
            ConstraintConfig(
                min_disk_space_mb=0,
                max_file_size_mb=500,
                enable_disk_space_check=True,
                retention_days=30,
            )

    def test_invalid_max_file_size(self):
        """Test constraint config with invalid max file size"""
        with pytest.raises(ValueError, match="max_file_size_mb must be positive"):
            ConstraintConfig(
                min_disk_space_mb=50,
                max_file_size_mb=-100,
                enable_disk_space_check=True,
                retention_days=30,
            )

    def test_invalid_retention_days(self):
        """Test constraint config with invalid retention days"""
        with pytest.raises(ValueError, match="retention_days must be positive"):
            ConstraintConfig(
                min_disk_space_mb=50,
                max_file_size_mb=500,
                enable_disk_space_check=True,
                retention_days=0,
            )


class TestStorageConstraints:
    """Test StorageConstraints class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.constraint_config = ConstraintConfig(
            min_disk_space_mb=100,
            max_file_size_mb=1000,
            enable_disk_space_check=True,
            retention_days=30,
        )
        self.constraints = StorageConstraints(self.constraint_config)

    def test_initialization(self):
        """Test constraints initialization"""
        assert self.constraints.min_disk_space_mb == 100
        assert self.constraints.max_file_size_mb == 1000
        assert self.constraints.enable_disk_space_check is True
        assert self.constraints.retention_days == 30

    def test_from_environment_config(self):
        """Test creating constraints from environment config"""
        env_config = EnvironmentConfig(
            base_subdir="test",
            min_disk_space_mb=50,
            enable_disk_space_check=True,
            max_file_size_mb=500,
            enable_backup=False,
            enable_compression=False,
            retention_days=7,
        )

        constraints = StorageConstraints.from_environment_config(env_config)

        assert constraints.min_disk_space_mb == 50
        assert constraints.max_file_size_mb == 500
        assert constraints.enable_disk_space_check is True
        assert constraints.retention_days == 7

    def test_validate_constraints_configuration_valid(self):
        """Test constraint configuration validation with valid config"""
        result = self.constraints.validate_constraints_configuration()

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_constraints_configuration_warnings(self):
        """Test constraint configuration validation with warning conditions"""
        # Create constraints with values that should trigger warnings
        warning_config = ConstraintConfig(
            min_disk_space_mb=5,  # Very low
            max_file_size_mb=15000,  # Very high
            enable_disk_space_check=True,
            retention_days=5000,  # Very long
        )
        constraints = StorageConstraints(warning_config)

        result = constraints.validate_constraints_configuration()

        assert result["valid"] is True
        assert len(result["warnings"]) >= 2  # Should have multiple warnings

        warning_messages = " ".join(result["warnings"])
        assert "Very low minimum disk space" in warning_messages
        assert "Very high maximum file size" in warning_messages
        assert "Very long retention period" in warning_messages

    def test_validate_file_constraints_nonexistent_file(self):
        """Test file constraint validation with nonexistent file"""
        result = self.constraints.validate_file_constraints("/nonexistent/file.txt")

        assert result["valid"] is False
        assert "File does not exist" in result["errors"][0]
        assert result["file_path"] == "/nonexistent/file.txt"

    def test_validate_file_constraints_valid_file(self):
        """Test file constraint validation with valid file"""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Write 1MB of data
            temp_file.write(b"0" * (1024 * 1024))
            temp_file.flush()
            temp_file.close()

            try:
                result = self.constraints.validate_file_constraints(temp_file.name)

                assert result["valid"] is True
                assert result["file_size_mb"] == 1.0
                assert "file_size" in result["constraints_checked"]
                assert result["applied_constraints"]["max_file_size_mb"] == 1000

            finally:
                try:
                    os.unlink(temp_file.name)
                except (PermissionError, FileNotFoundError):
                    pass

    def test_validate_file_constraints_oversized_file(self):
        """Test file constraint validation with oversized file"""
        # Mock large file size
        with patch("os.path.exists", return_value=True):
            with patch("os.path.getsize", return_value=2000 * 1024 * 1024):  # 2000MB
                result = self.constraints.validate_file_constraints(
                    "/mock/large_file.txt"
                )

                assert result["valid"] is False
                assert "exceeds maximum" in result["errors"][0]
                assert result["file_size_mb"] == 2000.0

    def test_validate_file_constraints_approaching_limit(self):
        """Test file constraint validation with file approaching size limit"""
        # Mock file size approaching limit (80% of max)
        with patch("os.path.exists", return_value=True):
            with patch(
                "os.path.getsize", return_value=int(800 * 1024 * 1024)
            ):  # 800MB (80% of 1000MB)
                result = self.constraints.validate_file_constraints(
                    "/mock/large_file.txt"
                )

                assert result["valid"] is True
                assert len(result["warnings"]) == 1
                assert "approaching maximum" in result["warnings"][0]
                assert result["file_size_mb"] == 800.0

    @patch(
        "voice_recorder.services.file_storage.config.constraints.StorageInfoCollector"
    )
    def test_validate_disk_space_for_file_sufficient_space(self, mock_collector_class):
        """Test disk space validation with sufficient space"""
        # Mock storage info
        mock_collector = MagicMock()
        mock_collector.get_raw_storage_info.return_value = {
            "free_mb": 2000,
            "used_mb": 1000,
            "total_mb": 3000,
        }
        mock_collector_class.return_value = mock_collector

        with tempfile.NamedTemporaryFile() as temp_file:
            base_path = Path(temp_file.name).parent

            result = self.constraints.validate_disk_space_for_file(
                temp_file.name, base_path
            )

            assert result["valid"] is True
            assert result["disk_space_check_enabled"] is True
            assert result["available_space_mb"] == 2000

    @patch(
        "voice_recorder.services.file_storage.config.constraints.StorageInfoCollector"
    )
    def test_validate_disk_space_for_file_insufficient_space(
        self, mock_collector_class
    ):
        """Test disk space validation with insufficient space"""
        # Mock storage info with low space
        mock_collector = MagicMock()
        mock_collector.get_raw_storage_info.return_value = {
            "free_mb": 50,  # Less than min_disk_space_mb (100)
            "used_mb": 2950,
            "total_mb": 3000,
        }
        mock_collector_class.return_value = mock_collector

        with tempfile.NamedTemporaryFile() as temp_file:
            base_path = Path(temp_file.name).parent

            result = self.constraints.validate_disk_space_for_file(
                temp_file.name, base_path
            )

            assert result["valid"] is False
            assert "Insufficient disk space" in result["errors"][0]
            assert result["available_space_mb"] == 50

    def test_validate_disk_space_disabled(self):
        """Test disk space validation when disabled"""
        # Create constraints with disk space checking disabled
        disabled_config = ConstraintConfig(
            min_disk_space_mb=100,
            max_file_size_mb=1000,
            enable_disk_space_check=False,
            retention_days=30,
        )
        constraints = StorageConstraints(disabled_config)

        result = constraints.validate_disk_space_for_file("/any/file.txt", Path("/tmp"))

        assert result["valid"] is True
        assert result["disk_space_check_enabled"] is False
        assert "Disk space checking disabled" in result["message"]

    @patch(
        "voice_recorder.services.file_storage.config.constraints.StorageInfoCollector"
    )
    def test_validate_storage_capacity_healthy(self, mock_collector_class):
        """Test storage capacity validation with healthy storage"""
        # Mock healthy storage
        mock_collector = MagicMock()
        mock_collector.get_raw_storage_info.return_value = {
            "free_mb": 2000,
            "used_mb": 1000,
            "total_mb": 3000,
        }
        mock_collector_class.return_value = mock_collector

        result = self.constraints.validate_storage_capacity(Path("/tmp"))

        assert result["valid"] is True
        assert result["health_status"] == "healthy"
        assert result["utilization_percent"] == (1000 / 3000 * 100)

    @patch(
        "voice_recorder.services.file_storage.config.constraints.StorageInfoCollector"
    )
    def test_validate_storage_capacity_critical(self, mock_collector_class):
        """Test storage capacity validation with critical storage"""
        # Mock critical storage
        mock_collector = MagicMock()
        mock_collector.get_raw_storage_info.return_value = {
            "free_mb": 50,  # Below minimum
            "used_mb": 2950,
            "total_mb": 3000,
        }
        mock_collector_class.return_value = mock_collector

        result = self.constraints.validate_storage_capacity(Path("/tmp"))

        assert result["valid"] is False
        assert result["health_status"] == "critical"
        assert "Insufficient disk space" in result["errors"][0]

    def test_get_constraint_summary(self):
        """Test getting constraint summary"""
        summary = self.constraints.get_constraint_summary()

        assert "constraints" in summary
        assert "features" in summary
        assert "validation_info" in summary

        assert summary["constraints"]["min_disk_space_mb"] == 100
        assert summary["constraints"]["max_file_size_mb"] == 1000
        assert summary["features"]["disk_space_check_enabled"] is True


class TestConstraintValidator:
    """Test ConstraintValidator class"""

    def setup_method(self):
        """Set up test fixtures"""
        constraint_config = ConstraintConfig(
            min_disk_space_mb=100,
            max_file_size_mb=1000,
            enable_disk_space_check=True,
            retention_days=30,
        )
        constraints = StorageConstraints(constraint_config)
        self.validator = ConstraintValidator(constraints)

    @patch(
        "voice_recorder.services.file_storage.config.constraints.StorageInfoCollector"
    )
    def test_validate_file_complete_valid(self, mock_collector_class):
        """Test complete file validation with valid file"""
        # Mock storage info
        mock_collector = MagicMock()
        mock_collector.get_raw_storage_info.return_value = {
            "free_mb": 2000,
            "used_mb": 1000,
            "total_mb": 3000,
        }
        mock_collector_class.return_value = mock_collector

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Write 1MB of data
            temp_file.write(b"0" * (1024 * 1024))
            temp_file.flush()
            temp_file.close()

            try:
                result = self.validator.validate_file_complete(
                    temp_file.name, Path("/tmp")
                )

                assert result["overall_valid"] is True
                assert result["file_path"] == temp_file.name
                assert "file_constraints" in result["constraint_results"]
                assert "disk_space" in result["constraint_results"]
                assert "storage_capacity" in result["constraint_results"]
                assert len(result["constraint_results"]) == 3

                summary = result["summary"]
                assert summary["total_errors"] == 0
                assert summary["file_size_mb"] == 1.0
                assert len(summary["constraints_checked"]) == 3

            finally:
                try:
                    os.unlink(temp_file.name)
                except (PermissionError, FileNotFoundError):
                    pass

    @patch(
        "voice_recorder.services.file_storage.config.constraints.StorageInfoCollector"
    )
    def test_validate_before_operation_valid(self, mock_collector_class):
        """Test pre-operation validation with valid conditions"""
        # Mock healthy storage
        mock_collector = MagicMock()
        mock_collector.get_raw_storage_info.return_value = {
            "free_mb": 2000,
            "used_mb": 1000,
            "total_mb": 3000,
        }
        mock_collector_class.return_value = mock_collector

        result = self.validator.validate_before_operation("write", 50.0, Path("/tmp"))

        assert result["valid"] is True
        assert result["operation_type"] == "write"
        assert result["estimated_size_mb"] == 50.0
        assert len(result["errors"]) == 0

    @patch(
        "voice_recorder.services.file_storage.config.constraints.StorageInfoCollector"
    )
    def test_validate_before_operation_oversized(self, mock_collector_class):
        """Test pre-operation validation with oversized operation"""
        # Mock storage
        mock_collector = MagicMock()
        mock_collector.get_raw_storage_info.return_value = {
            "free_mb": 2000,
            "used_mb": 1000,
            "total_mb": 3000,
        }
        mock_collector_class.return_value = mock_collector

        result = self.validator.validate_before_operation(
            "write", 1500.0, Path("/tmp")
        )  # Exceeds 1000MB limit

        assert result["valid"] is False
        assert "exceeds maximum file size" in result["errors"][0]
        assert result["estimated_size_mb"] == 1500.0

    @patch(
        "voice_recorder.services.file_storage.config.constraints.StorageInfoCollector"
    )
    def test_validate_before_operation_approaching_limit(self, mock_collector_class):
        """Test pre-operation validation with size approaching limit"""
        # Mock storage
        mock_collector = MagicMock()
        mock_collector.get_raw_storage_info.return_value = {
            "free_mb": 2000,
            "used_mb": 1000,
            "total_mb": 3000,
        }
        mock_collector_class.return_value = mock_collector

        result = self.validator.validate_before_operation(
            "write", 850.0, Path("/tmp")
        )  # 85% of 1000MB limit

        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert "approaching maximum file size" in result["warnings"][0]

    @patch(
        "voice_recorder.services.file_storage.config.constraints.StorageInfoCollector"
    )
    def test_validate_before_operation_large_file_recommendations(
        self, mock_collector_class
    ):
        """Test pre-operation validation recommendations for large files"""
        # Mock storage
        mock_collector = MagicMock()
        mock_collector.get_raw_storage_info.return_value = {
            "free_mb": 2000,
            "used_mb": 1000,
            "total_mb": 3000,
        }
        mock_collector_class.return_value = mock_collector

        result = self.validator.validate_before_operation(
            "write", 150.0, Path("/tmp")
        )  # Large file

        assert result["valid"] is True
        assert len(result["recommendations"]) > 0
        assert any("compression" in rec for rec in result["recommendations"])


class TestCreateConstraintsFromEnvironment:
    """Test convenience function for creating constraints from environment"""

    @patch("voice_recorder.services.file_storage.config.constraints.EnvironmentManager")
    def test_create_constraints_from_environment(self, mock_env_manager_class):
        """Test creating constraints from environment name"""
        # Mock environment manager
        mock_env_manager = MagicMock()
        mock_env_config = EnvironmentConfig(
            base_subdir="test",
            min_disk_space_mb=50,
            enable_disk_space_check=True,
            max_file_size_mb=500,
            enable_backup=False,
            enable_compression=False,
            retention_days=7,
        )
        mock_env_manager.get_config.return_value = mock_env_config
        mock_env_manager_class.return_value = mock_env_manager

        constraints = create_constraints_from_environment("testing")

        assert constraints.min_disk_space_mb == 50
        assert constraints.max_file_size_mb == 500
        assert constraints.enable_disk_space_check is True
        assert constraints.retention_days == 7

        mock_env_manager.get_config.assert_called_once_with("testing")


class TestIntegrationConstraints:
    """Integration tests for constraints module"""

    def test_full_constraint_workflow(self):
        """Test complete constraint validation workflow"""
        # Create constraints for testing environment

    with patch(
        "voice_recorder.services.file_storage.config.constraints.EnvironmentManager"
    ) as mock_env_manager_class:
        # Mock environment manager
        mock_env_manager = MagicMock()
        mock_env_config = EnvironmentConfig(
            base_subdir="test",
            min_disk_space_mb=10,  # Low for testing
            enable_disk_space_check=False,  # Disabled for testing
            max_file_size_mb=100,
            enable_backup=False,
            enable_compression=True,
            retention_days=7,
        )
        mock_env_manager.get_config.return_value = mock_env_config
        mock_env_manager_class.return_value = mock_env_manager

        # Create constraints
        constraints = create_constraints_from_environment("testing")
        ConstraintValidator(constraints)

        # Test with temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Write 5MB of data
            temp_file.write(b"0" * (5 * 1024 * 1024))
            temp_file.flush()
            temp_file.close()

            try:
                # Test file constraints only (disk space checking disabled)
                file_result = constraints.validate_file_constraints(temp_file.name)
                assert file_result["valid"] is True
                assert file_result["file_size_mb"] == 5.0

                # Test constraint configuration
                config_result = constraints.validate_constraints_configuration()
                assert config_result["valid"] is True

                # Test constraint summary
                summary = constraints.get_constraint_summary()
                assert summary["constraints"]["max_file_size_mb"] == 100
                assert summary["features"]["disk_space_check_enabled"] is False

            finally:
                try:
                    os.unlink(temp_file.name)
                except (PermissionError, FileNotFoundError):
                    pass
