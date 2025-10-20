"""
Unit tests for cloud.storage_ops module

Tests storage and file operations utilities
"""

import pytest
from unittest.mock import MagicMock
from cloud.storage_ops import (
    paginate_results,
    format_file_size,
    create_folder_metadata,
    discover_total_bytes,
    format_storage_info,
)


class TestFormatFileSize:
    """Tests for format_file_size function"""
    
    def test_format_bytes(self):
        """Test formatting bytes"""
        assert format_file_size(512) == "512 B"
        assert format_file_size(1023) == "1023 B"
    
    def test_format_kilobytes(self):
        """Test formatting kilobytes"""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"
        assert format_file_size(1024 * 512) == "512.0 KB"
    
    def test_format_megabytes(self):
        """Test formatting megabytes"""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 5) == "5.0 MB"
        assert format_file_size(1024 * 1024 * 1.5) == "1.5 MB"
    
    def test_format_gigabytes(self):
        """Test formatting gigabytes"""
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"
        assert format_file_size(1024 * 1024 * 1024 * 10) == "10.0 GB"
    
    def test_format_none(self):
        """Test formatting None"""
        assert format_file_size(None) == "unknown"
    
    def test_format_zero(self):
        """Test formatting zero bytes"""
        assert format_file_size(0) == "0 B"


class TestCreateFolderMetadata:
    """Tests for create_folder_metadata function"""
    
    def test_basic_folder_metadata(self):
        """Test creating basic folder metadata"""
        metadata = create_folder_metadata("My Folder")
        assert metadata["name"] == "My Folder"
        assert metadata["mimeType"] == "application/vnd.google-apps.folder"
        assert "parents" not in metadata
        assert "description" not in metadata
    
    def test_folder_metadata_with_parent(self):
        """Test creating folder metadata with parent"""
        metadata = create_folder_metadata("My Folder", parent_id="parent123")
        assert metadata["name"] == "My Folder"
        assert metadata["parents"] == ["parent123"]
    
    def test_folder_metadata_with_description(self):
        """Test creating folder metadata with description"""
        metadata = create_folder_metadata(
            "My Folder",
            description="Folder for recordings"
        )
        assert metadata["description"] == "Folder for recordings"
    
    def test_folder_metadata_all_parameters(self):
        """Test creating folder metadata with all parameters"""
        metadata = create_folder_metadata(
            "My Folder",
            parent_id="parent123",
            description="Test folder"
        )
        assert metadata["name"] == "My Folder"
        assert metadata["parents"] == ["parent123"]
        assert metadata["description"] == "Test folder"
        assert metadata["mimeType"] == "application/vnd.google-apps.folder"
    
    def test_folder_metadata_parent_none(self):
        """Test that None parent is not included"""
        metadata = create_folder_metadata("My Folder", parent_id=None)
        assert "parents" not in metadata


class TestDiscoverTotalBytes:
    """Tests for discover_total_bytes function"""
    
    def test_discover_from_media_upload_size_method(self):
        """Test discovering bytes from media_upload.size() method"""
        mock_request = MagicMock()
        mock_media = MagicMock()
        mock_media.size.return_value = 1024 * 1024
        mock_request.media_upload = mock_media
        
        result = discover_total_bytes(mock_request)
        assert result == 1024 * 1024
    
    def test_discover_from_media_upload_size_string_method(self):
        """Test discovering bytes from media_upload.size_string() method"""
        mock_request = MagicMock()
        mock_media = MagicMock()
        mock_media.size.side_effect = AttributeError()  # No size method
        mock_media.size_string.return_value = str(1024 * 1024)
        mock_request.media_upload = mock_media
        
        result = discover_total_bytes(mock_request)
        assert result == 1024 * 1024
    
    def test_discover_returns_none_for_unknown(self):
        """Test that None is returned when size cannot be discovered"""
        mock_request = MagicMock(spec=[])  # No media_upload attribute
        result = discover_total_bytes(mock_request)
        assert result is None
    
    def test_discover_handles_wildcard_size_string(self):
        """Test that wildcard size strings return None"""
        mock_request = MagicMock()
        mock_media = MagicMock()
        mock_media.size.side_effect = AttributeError()
        mock_media.size_string.return_value = "*"  # Wildcard for unknown size
        mock_request.media_upload = mock_media
        
        result = discover_total_bytes(mock_request)
        assert result is None
    
    def test_discover_handles_exception(self):
        """Test that exceptions are handled gracefully"""
        mock_request = MagicMock()
        mock_request.media_upload.side_effect = Exception("Test error")
        
        # Should not raise, should return None
        result = discover_total_bytes(mock_request)
        assert result is None


class TestFormatStorageInfo:
    """Tests for format_storage_info function"""
    
    def test_format_both_values_known(self):
        """Test formatting when both values are known"""
        info = format_storage_info(5368709120, 107374182400)  # 5GB / 100GB
        assert info["used"] == "5.0 GB"
        assert info["limit"] == "100.0 GB"
        assert abs(info["percent"] - 5.0) < 0.1
    
    def test_format_used_none(self):
        """Test formatting when used is None"""
        info = format_storage_info(None, 107374182400)
        assert info["used"] == "unknown"
        assert info["limit"] == "100.0 GB"
        assert info["percent"] is None
    
    def test_format_limit_none(self):
        """Test formatting when limit is None"""
        info = format_storage_info(5368709120, None)
        assert info["used"] == "5.0 GB"
        assert info["limit"] == "unknown"
        assert info["percent"] is None
    
    def test_format_both_none(self):
        """Test formatting when both are None"""
        info = format_storage_info(None, None)
        assert info["used"] == "unknown"
        assert info["limit"] == "unknown"
        assert info["percent"] is None
    
    def test_format_full_storage(self):
        """Test formatting when storage is full"""
        info = format_storage_info(107374182400, 107374182400)  # 100GB / 100GB
        assert abs(info["percent"] - 100.0) < 0.1
    
    def test_format_zero_limit(self):
        """Test formatting with zero limit (no division by zero)"""
        info = format_storage_info(1024, 0)
        assert info["used"] == "1.0 KB"
        assert info["limit"] == "0 B"
        assert info["percent"] is None


class TestPaginateResults:
    """Tests for paginate_results function"""
    
    def test_single_page_results(self):
        """Test pagination with single page"""
        mock_service = MagicMock()
        mock_files_api = MagicMock()
        mock_service.files.return_value = mock_files_api
        
        # Single page response
        mock_files_api.list.return_value.execute.return_value = {
            "files": [
                {"id": "file1", "name": "File 1"},
                {"id": "file2", "name": "File 2"},
            ],
            "nextPageToken": None,
        }
        
        results = paginate_results(mock_service, "query")
        assert len(results) == 2
        assert results[0]["id"] == "file1"
        assert results[1]["id"] == "file2"
    
    def test_multiple_page_results(self):
        """Test pagination with multiple pages"""
        mock_service = MagicMock()
        mock_files_api = MagicMock()
        mock_service.files.return_value = mock_files_api
        
        # Mock multiple pages
        mock_list_call = mock_files_api.list.return_value
        mock_list_call.execute.side_effect = [
            {
                "files": [
                    {"id": "file1", "name": "File 1"},
                ],
                "nextPageToken": "page2_token",
            },
            {
                "files": [
                    {"id": "file2", "name": "File 2"},
                ],
                "nextPageToken": None,
            },
        ]
        
        results = paginate_results(mock_service, "query")
        assert len(results) == 2
    
    def test_max_results_limit(self):
        """Test that max_results parameter limits results"""
        mock_service = MagicMock()
        mock_files_api = MagicMock()
        mock_service.files.return_value = mock_files_api
        
        # Single page with more than max_results
        mock_files_api.list.return_value.execute.return_value = {
            "files": [
                {"id": f"file{i}", "name": f"File {i}"}
                for i in range(100)
            ],
            "nextPageToken": None,
        }
        
        results = paginate_results(mock_service, "query", max_results=10)
        assert len(results) == 10
    
    def test_empty_results(self):
        """Test pagination with no results"""
        mock_service = MagicMock()
        mock_files_api = MagicMock()
        mock_service.files.return_value = mock_files_api
        
        mock_files_api.list.return_value.execute.return_value = {
            "files": [],
            "nextPageToken": None,
        }
        
        results = paginate_results(mock_service, "query")
        assert len(results) == 0
    
    def test_custom_page_size(self):
        """Test that custom page size is passed to API"""
        mock_service = MagicMock()
        mock_files_api = MagicMock()
        mock_service.files.return_value = mock_files_api
        
        mock_files_api.list.return_value.execute.return_value = {
            "files": [],
            "nextPageToken": None,
        }
        
        paginate_results(mock_service, "query", page_size=50)
        
        # Verify pageSize was passed
        call_args = mock_files_api.list.call_args
        assert call_args is not None
        assert "pageSize" in call_args[1]
        assert call_args[1]["pageSize"] == 50
    
    def test_custom_fields(self):
        """Test that custom fields are passed to API"""
        mock_service = MagicMock()
        mock_files_api = MagicMock()
        mock_service.files.return_value = mock_files_api
        
        mock_files_api.list.return_value.execute.return_value = {
            "files": [],
            "nextPageToken": None,
        }
        
        paginate_results(mock_service, "query", fields="files(id, name, size)")
        
        # Verify fields includes nextPageToken
        call_args = mock_files_api.list.call_args
        assert call_args is not None
        assert "fields" in call_args[1]
        assert "nextPageToken" in call_args[1]["fields"]
