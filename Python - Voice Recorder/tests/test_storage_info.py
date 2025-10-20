"""Tests for StorageInfo component"""

from unittest.mock import MagicMock

from cloud._storage_info import GoogleStorageInfo


class TestGetStorageQuota:
    """Tests for get_storage_quota method"""

    def test_get_storage_quota_success(self):
        """Test successful quota retrieval"""
        auth_manager = MagicMock()
        service = MagicMock()

        mock_response = {
            "storageQuota": {
                "usedBytes": "1073741824",  # 1GB
                "limit": "10737418240",  # 10GB
            }
        }
        service.about().get().execute.return_value = mock_response

        manager = GoogleStorageInfo(auth_manager, service_provider=service)
        result = manager.get_storage_quota()

        assert result is not None
        assert result["usedBytes"] == 1073741824
        assert result["limit"] == 10737418240
        assert abs(result["usedPercent"] - 10.0) < 0.01

    def test_get_storage_quota_zero_limit(self):
        """Test quota calculation with zero limit"""
        auth_manager = MagicMock()
        service = MagicMock()

        mock_response = {
            "storageQuota": {
                "usedBytes": "0",
                "limit": "0",
            }
        }
        service.about().get().execute.return_value = mock_response

        manager = GoogleStorageInfo(auth_manager, service_provider=service)
        result = manager.get_storage_quota()

        assert result is not None
        assert result["usedPercent"] == 0

    def test_get_storage_quota_api_error(self):
        """Test quota retrieval API error"""
        auth_manager = MagicMock()
        service = MagicMock()
        service.about().get().execute.side_effect = Exception("API error")

        manager = GoogleStorageInfo(auth_manager, service_provider=service)
        result = manager.get_storage_quota()

        assert result is None

    def test_get_storage_quota_not_authenticated(self):
        """Test quota retrieval when not authenticated"""
        auth_manager = MagicMock()
        auth_manager.is_authenticated.return_value = False

        manager = GoogleStorageInfo(auth_manager)
        result = manager.get_storage_quota()

        assert result is None


class TestGetStorageSummary:
    """Tests for get_storage_summary method"""

    def test_get_storage_summary_success(self):
        """Test successful summary retrieval"""
        auth_manager = MagicMock()
        service = MagicMock()

        mock_response = {
            "storageQuota": {
                "usedBytes": "1073741824",  # 1GB
                "limit": "10737418240",  # 10GB
            }
        }
        service.about().get().execute.return_value = mock_response

        manager = GoogleStorageInfo(auth_manager, service_provider=service)
        result = manager.get_storage_summary()

        assert result is not None
        assert "used" in result
        assert "limit" in result
        assert "percent" in result
        assert "available" in result
        assert "1.0 GB" in result["used"]
        assert "10.0 GB" in result["limit"]
        assert "10.0%" in result["percent"]

    def test_get_storage_summary_no_quota(self):
        """Test summary when quota retrieval fails"""
        auth_manager = MagicMock()
        service = MagicMock()
        service.about().get().execute.side_effect = Exception("API error")

        manager = GoogleStorageInfo(auth_manager, service_provider=service)
        result = manager.get_storage_summary()

        assert result is None

    def test_get_storage_summary_calculation(self):
        """Test available calculation in summary"""
        auth_manager = MagicMock()
        service = MagicMock()

        # 1GB used of 10GB = 9GB available
        mock_response = {
            "storageQuota": {
                "usedBytes": str(1 * 1024 * 1024 * 1024),
                "limit": str(10 * 1024 * 1024 * 1024),
            }
        }
        service.about().get().execute.return_value = mock_response

        manager = GoogleStorageInfo(auth_manager, service_provider=service)
        result = manager.get_storage_summary()

        assert result is not None
        assert "9.0 GB" in result["available"]


class TestStorageInfoIntegration:
    """Integration tests for StorageInfo"""

    def test_quota_and_summary_consistency(self):
        """Test that quota and summary are consistent"""
        auth_manager = MagicMock()
        service = MagicMock()

        mock_response = {
            "storageQuota": {
                "usedBytes": "5368709120",  # 5GB
                "limit": "10737418240",  # 10GB
            }
        }
        service.about().get().execute.return_value = mock_response

        manager = GoogleStorageInfo(auth_manager, service_provider=service)

        quota = manager.get_storage_quota()
        summary = manager.get_storage_summary()

        assert quota is not None
        assert summary is not None
        assert quota["usedBytes"] == 5 * 1024 * 1024 * 1024
        assert "5.0 GB" in summary["used"]
        assert abs(quota["usedPercent"] - 50.0) < 0.01
