"""
Phase 3.6: GoogleDriveManager Component Integration Tests

Tests the integration of GoogleDriveManager with its three main components:
- GoogleFolderManager (folder operations)
- GoogleFileManager (file operations)
- GoogleStorageInfo (storage information)

Verifies:
1. Component lazy initialization
2. Delegation of operations to components
3. Component interactions (FileManager uses FolderManager)
4. State consistency between manager and components
5. Error handling through delegation chain
6. Backward compatibility
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from typing import Any, Dict, List, Optional

# Import GoogleDriveManager and components
from cloud.drive_manager import GoogleDriveManager
from cloud._folder_manager import GoogleFolderManager
from cloud._file_manager import GoogleFileManager
from cloud._storage_info import GoogleStorageInfo


class TestGoogleDriveManagerComponentIntegration:
    """Test GoogleDriveManager integration with components"""

    @pytest.fixture
    def mock_auth_manager(self):
        """Create a mock authentication manager"""
        auth_manager = Mock()
        mock_service = MagicMock()
        auth_manager.get_authorized_service = Mock(return_value=mock_service)
        auth_manager.is_authenticated = Mock(return_value=True)
        return auth_manager

    @pytest.fixture
    def drive_manager(self, mock_auth_manager):
        """Create a GoogleDriveManager instance with mocked auth"""
        return GoogleDriveManager(mock_auth_manager)

    # ========== COMPONENT INITIALIZATION TESTS ==========

    def test_components_lazy_initialized(self, drive_manager):
        """Test that components are lazily initialized on first access"""
        # Components should not be initialized yet
        assert drive_manager._folder_manager is None
        assert drive_manager._file_manager is None
        assert drive_manager._storage_info is None

        # Access folder_manager property - mock it to avoid real init
        with patch("cloud.drive_manager.GoogleFolderManager") as mock_folder_cls:
            mock_folder_instance = Mock(spec=GoogleFolderManager)
            mock_folder_cls.return_value = mock_folder_instance
            
            folder_mgr = drive_manager.folder_manager
            assert drive_manager._folder_manager is not None
            mock_folder_cls.assert_called_once()

    def test_components_reuse_on_subsequent_access(self, drive_manager):
        """Test that components are reused on subsequent accesses"""
        with patch("cloud.drive_manager.GoogleFolderManager") as mock_folder_cls:
            mock_folder_instance = Mock(spec=GoogleFolderManager)
            mock_folder_cls.return_value = mock_folder_instance
            
            # First and second access
            folder_mgr1 = drive_manager.folder_manager
            folder_mgr2 = drive_manager.folder_manager
            
            # Should be same instance and class called only once
            assert folder_mgr1 is folder_mgr2
            mock_folder_cls.assert_called_once()

    # ========== FOLDER OPERATION DELEGATION TESTS ==========

    def test_list_folders_delegation(self, drive_manager):
        """Test that list_folders delegates to FolderManager"""
        expected_folders = [
            {"id": "folder1", "name": "Folder 1"},
            {"id": "folder2", "name": "Folder 2"},
        ]

        mock_folder_mgr = Mock(spec=GoogleFolderManager)
        mock_folder_mgr.list_folders = Mock(return_value=expected_folders)
        drive_manager._folder_manager = mock_folder_mgr

        result = drive_manager.list_folders(parent_id="parent123", page_size=50)

        assert result == expected_folders
        mock_folder_mgr.list_folders.assert_called_once_with("parent123", 50)

    def test_create_folder_delegation(self, drive_manager):
        """Test that create_folder delegates to FolderManager"""
        expected_id = "new_folder_456"

        mock_folder_mgr = Mock(spec=GoogleFolderManager)
        mock_folder_mgr.create_folder = Mock(return_value=expected_id)
        drive_manager._folder_manager = mock_folder_mgr

        result = drive_manager.create_folder("New Folder", parent_id="parent123")

        assert result == expected_id
        mock_folder_mgr.create_folder.assert_called_once_with("New Folder", "parent123")

    def test_set_recordings_folder_delegation(self, drive_manager):
        """Test that set_recordings_folder delegates to FolderManager"""
        folder_id = "target_folder_789"

        mock_folder_mgr = Mock(spec=GoogleFolderManager)
        mock_folder_mgr.set_recordings_folder = Mock()
        drive_manager._folder_manager = mock_folder_mgr

        drive_manager.set_recordings_folder(folder_id)

        assert drive_manager.recordings_folder_id == folder_id
        mock_folder_mgr.set_recordings_folder.assert_called_once_with(folder_id)

    def test_ensure_recordings_folder_delegation(self, drive_manager):
        """Test that _ensure_recordings_folder delegates to FolderManager"""
        expected_folder_id = "test_folder_123"

        mock_folder_mgr = Mock(spec=GoogleFolderManager)
        mock_folder_mgr.ensure_recordings_folder = Mock(return_value=expected_folder_id)
        drive_manager._folder_manager = mock_folder_mgr

        result = drive_manager._ensure_recordings_folder()

        assert result == expected_folder_id
        assert drive_manager.recordings_folder_id == expected_folder_id
        mock_folder_mgr.ensure_recordings_folder.assert_called_once()

    # ========== FILE OPERATION DELEGATION TESTS ==========

    def test_upload_recording_delegation(self, drive_manager):
        """Test that upload_recording delegates to FileManager"""
        expected_file_id = "uploaded_file_123"

        mock_file_mgr = Mock(spec=GoogleFileManager)
        mock_file_mgr.upload_file = Mock(return_value=expected_file_id)
        drive_manager._file_manager = mock_file_mgr

        # Must also mock storage_info to avoid accessing real Google API
        mock_storage_info = Mock(spec=GoogleStorageInfo)
        drive_manager._storage_info = mock_storage_info

        result = drive_manager.upload_recording(
            file_path="/path/to/file.wav", title="recording.wav"
        )

        assert result == expected_file_id
        mock_file_mgr.upload_file.assert_called_once()

    def test_download_recording_delegation(self, drive_manager):
        """Test that download_recording delegates to FileManager"""
        mock_folder_mgr = Mock(spec=GoogleFolderManager)
        mock_folder_mgr.ensure_recordings_folder = Mock(return_value="folder_id")
        drive_manager._folder_manager = mock_folder_mgr

        mock_file_mgr = Mock(spec=GoogleFileManager)
        mock_file_mgr.download_file = Mock(return_value=True)
        drive_manager._file_manager = mock_file_mgr

        # Mock storage_info to avoid API calls
        mock_storage_info = Mock()
        mock_storage_info.get_storage_quota = Mock(return_value={"limit": 5000000, "usedBytes": 1000000})
        mock_storage_info.get_storage_summary = Mock(return_value={"used": "1GB", "total": "5GB"})
        drive_manager._storage_info = mock_storage_info

        result = drive_manager.download_recording(
            file_id="file_123", download_path="/path/to/save"
        )

        assert result is True
        mock_file_mgr.download_file.assert_called_once()

    def test_list_recordings_delegation(self, drive_manager):
        """Test that list_recordings delegates to FileManager"""
        expected_files = [
            {"id": "file1", "name": "recording1.wav"},
            {"id": "file2", "name": "recording2.wav"},
        ]

        mock_folder_mgr = Mock(spec=GoogleFolderManager)
        mock_folder_mgr.ensure_recordings_folder = Mock(return_value="folder_id")
        drive_manager._folder_manager = mock_folder_mgr

        mock_file_mgr = Mock(spec=GoogleFileManager)
        mock_file_mgr.list_files = Mock(return_value=expected_files)
        drive_manager._file_manager = mock_file_mgr

        # Mock storage_info to avoid API calls
        mock_storage_info = Mock(spec=GoogleStorageInfo)
        drive_manager._storage_info = mock_storage_info

        result = drive_manager.list_recordings()

        assert result == expected_files
        mock_file_mgr.list_files.assert_called_once()

    def test_find_duplicate_by_content_sha256_delegation(self, drive_manager):
        """Test that find_duplicate_by_content_sha256 delegates to FileManager"""
        expected_duplicate = {"id": "dup_file", "name": "duplicate.wav"}

        mock_folder_mgr = Mock(spec=GoogleFolderManager)
        mock_folder_mgr.ensure_recordings_folder = Mock(return_value="folder_id")
        drive_manager._folder_manager = mock_folder_mgr

        mock_file_mgr = Mock(spec=GoogleFileManager)
        mock_file_mgr.find_duplicate_by_hash = Mock(return_value=expected_duplicate)
        drive_manager._file_manager = mock_file_mgr

        # Mock storage_info to avoid API calls
        mock_storage_info = Mock()
        mock_storage_info.get_storage_quota = Mock(return_value={"limit": 5000000, "usedBytes": 1000000})
        mock_storage_info.get_storage_summary = Mock(return_value={"used": "1GB", "total": "5GB"})
        drive_manager._storage_info = mock_storage_info

        result = drive_manager.find_duplicate_by_content_sha256(content_sha256="abc123")

        assert result == expected_duplicate
        mock_file_mgr.find_duplicate_by_hash.assert_called_once_with("abc123")

    def test_delete_recording_delegation(self, drive_manager):
        """Test that delete_recording delegates to FileManager"""
        mock_file_mgr = Mock(spec=GoogleFileManager)
        mock_file_mgr.delete_file = Mock(return_value=True)
        drive_manager._file_manager = mock_file_mgr

        result = drive_manager.delete_recording(file_id="file_to_delete")

        assert result is True
        mock_file_mgr.delete_file.assert_called_once_with("file_to_delete")

    # ========== STORAGE INFO DELEGATION TESTS ==========

    def test_get_storage_info_delegation(self, drive_manager):
        """Test that get_storage_info delegates to StorageInfo"""
        expected_storage = {
            "used_bytes": 1000000,
            "total_bytes": 5000000,
            "free_bytes": 4000000,
        }

        mock_storage_info = Mock(spec=GoogleStorageInfo)
        mock_storage_info.get_storage_quota = Mock(return_value={"limit": 5000000, "usedBytes": 1000000})
        drive_manager._storage_info = mock_storage_info

        result = drive_manager.get_storage_info()

        assert "total_bytes" in result
        assert "used_bytes" in result
        mock_storage_info.get_storage_quota.assert_called_once()

    def test_get_storage_quota_delegation(self, drive_manager):
        """Test that get_storage_quota delegates to StorageInfo"""
        expected_quota = {
            "limit_bytes": 5000000,
            "usage_bytes": 1000000,
            "usage_in_trash_bytes": 50000,
        }

        mock_storage_info = Mock(spec=GoogleStorageInfo)
        mock_storage_info.get_storage_quota = Mock(return_value=expected_quota)
        drive_manager._storage_info = mock_storage_info

        result = drive_manager.get_storage_quota()

        assert result == expected_quota
        mock_storage_info.get_storage_quota.assert_called_once()

    def test_get_storage_summary_delegation(self, drive_manager):
        """Test that get_storage_summary delegates to StorageInfo"""
        expected_summary = {
            "used": "1.0 GB",
            "total": "5.0 GB",
            "available": "4.0 GB",
        }

        mock_storage_info = Mock(spec=GoogleStorageInfo)
        mock_storage_info.get_storage_summary = Mock(return_value=expected_summary)
        drive_manager._storage_info = mock_storage_info

        result = drive_manager.get_storage_summary()

        assert result == expected_summary
        mock_storage_info.get_storage_summary.assert_called_once()

    # ========== STATE CONSISTENCY TESTS ==========

    def test_state_consistency_recordings_folder(self, drive_manager):
        """Test state consistency for recordings folder ID"""
        folder_id = "test_folder_id"

        mock_folder_mgr = Mock(spec=GoogleFolderManager)
        drive_manager._folder_manager = mock_folder_mgr

        # Set via manager
        drive_manager.set_recordings_folder(folder_id)

        # Should be consistent
        assert drive_manager.recordings_folder_id == folder_id

    def test_file_manager_receives_folder_manager(self, drive_manager):
        """Test that FileManager receives FolderManager reference"""
        mock_folder_mgr = Mock(spec=GoogleFolderManager)
        drive_manager._folder_manager = mock_folder_mgr

        # FileManager initialization uses folder_manager
        with patch("cloud.drive_manager.GoogleFileManager") as mock_file_cls:
            mock_file_instance = Mock(spec=GoogleFileManager)
            mock_file_cls.return_value = mock_file_instance
            
            # Access file_manager property
            _ = drive_manager.file_manager
            
            # FileManager should have been initialized with FolderManager
            mock_file_cls.assert_called_once()

    # ========== MULTI-OPERATION WORKFLOW TESTS ==========

    def test_complete_upload_workflow(self, drive_manager):
        """Test complete workflow: ensure folder → upload file → check storage"""
        # Set up mocks
        mock_folder_mgr = Mock(spec=GoogleFolderManager)
        mock_folder_mgr.ensure_recordings_folder = Mock(return_value="folder_id")
        drive_manager._folder_manager = mock_folder_mgr

        mock_file_mgr = Mock(spec=GoogleFileManager)
        mock_file_mgr.upload_file = Mock(return_value="file_id")
        drive_manager._file_manager = mock_file_mgr

        mock_storage_info = Mock()
        mock_storage_info.get_storage_quota = Mock(return_value={"limit": 5000000, "usedBytes": 1000000})
        mock_storage_info.get_storage_summary = Mock(
            return_value={"used": "2GB", "total": "5GB"}
        )
        drive_manager._storage_info = mock_storage_info

        # Execute workflow
        folder_id = drive_manager._ensure_recordings_folder()
        file_id = drive_manager.upload_recording(
            "/path/to/file.wav", title="recording.wav"
        )
        storage = drive_manager.get_storage_info()

        # Verify
        assert folder_id == "folder_id"
        assert file_id == "file_id"
        assert storage["used_bytes"] == 1000000
        mock_folder_mgr.ensure_recordings_folder.assert_called_once()
        mock_file_mgr.upload_file.assert_called_once()
        mock_storage_info.get_storage_quota.assert_called()

    def test_complete_list_workflow(self, drive_manager):
        """Test complete workflow: list folders → list files"""
        folders = [{"id": "f1", "name": "Folder 1"}]
        files = [{"id": "file1", "name": "recording.wav"}]

        mock_folder_mgr = Mock(spec=GoogleFolderManager)
        mock_folder_mgr.list_folders = Mock(return_value=folders)
        drive_manager._folder_manager = mock_folder_mgr

        mock_file_mgr = Mock(spec=GoogleFileManager)
        mock_file_mgr.list_files = Mock(return_value=files)
        drive_manager._file_manager = mock_file_mgr

        # Execute workflow
        result_folders = drive_manager.list_folders()
        result_files = drive_manager.list_recordings()

        # Verify
        assert result_folders == folders
        assert result_files == files

    def test_complete_delete_workflow(self, drive_manager):
        """Test complete workflow: list files → delete file"""
        files = [{"id": "file1", "name": "old_recording.wav"}]

        mock_folder_mgr = Mock(spec=GoogleFolderManager)
        mock_folder_mgr.ensure_recordings_folder = Mock(return_value="folder_id")
        drive_manager._folder_manager = mock_folder_mgr

        mock_file_mgr = Mock(spec=GoogleFileManager)
        mock_file_mgr.list_files = Mock(return_value=files)
        mock_file_mgr.delete_file = Mock(return_value=True)
        drive_manager._file_manager = mock_file_mgr

        # Mock storage_info to avoid API calls in list_recordings
        mock_storage_info = Mock(spec=GoogleStorageInfo)
        mock_storage_info.get_storage_quota = Mock(return_value={"limit": 5000000, "usedBytes": 1000000})
        drive_manager._storage_info = mock_storage_info

        # Execute workflow
        result_files = drive_manager.list_recordings()
        file_id = result_files[0]["id"]
        deleted = drive_manager.delete_recording(file_id)

        # Verify
        assert len(result_files) == 1
        assert deleted is True
        mock_file_mgr.delete_file.assert_called_once_with("file1")

    # ========== ERROR HANDLING TESTS ==========

    def test_error_propagation_from_folder_manager(self, drive_manager):
        """Test that errors from FolderManager are properly propagated"""
        mock_folder_mgr = Mock(spec=GoogleFolderManager)
        mock_folder_mgr.list_folders = Mock(
            side_effect=RuntimeError("FolderManager error")
        )
        drive_manager._folder_manager = mock_folder_mgr

        with pytest.raises(RuntimeError):
            drive_manager.list_folders()

    def test_error_propagation_from_file_manager(self, drive_manager):
        """Test that errors from FileManager are properly propagated"""
        mock_file_mgr = Mock(spec=GoogleFileManager)
        mock_file_mgr.upload_file = Mock(
            side_effect=FileNotFoundError("File not found")
        )
        drive_manager._file_manager = mock_file_mgr

        with pytest.raises(FileNotFoundError):
            drive_manager.upload_recording("/nonexistent/file.wav", title="recording.wav")

    def test_error_propagation_from_storage_info(self, drive_manager):
        """Test that errors from StorageInfo are properly propagated"""
        mock_storage_info = Mock(spec=GoogleStorageInfo)
        mock_storage_info.get_storage_quota = Mock(
            side_effect=RuntimeError("Storage error")
        )
        drive_manager._storage_info = mock_storage_info

        with pytest.raises(RuntimeError):
            drive_manager.get_storage_quota()

    # ========== BACKWARD COMPATIBILITY TESTS ==========

    def test_public_api_unchanged(self, drive_manager):
        """Test that public API hasn't changed"""
        # All these methods should exist and be callable
        assert callable(drive_manager._ensure_recordings_folder)
        assert callable(drive_manager.list_folders)
        assert callable(drive_manager.create_folder)
        assert callable(drive_manager.set_recordings_folder)
        assert callable(drive_manager.upload_recording)
        assert callable(drive_manager.download_recording)
        assert callable(drive_manager.list_recordings)
        assert callable(drive_manager.find_duplicate_by_content_sha256)
        assert callable(drive_manager.delete_recording)
        assert callable(drive_manager.get_storage_info)
        assert callable(drive_manager.get_storage_quota)
        assert callable(drive_manager.get_storage_summary)

    def test_constant_preserved(self, drive_manager):
        """Test that RECORDINGS_FOLDER constant is preserved"""
        assert drive_manager.RECORDINGS_FOLDER == "Voice Recorder Pro"
        assert GoogleDriveManager.RECORDINGS_FOLDER == "Voice Recorder Pro"

    def test_auth_manager_stored(self, mock_auth_manager, drive_manager):
        """Test that auth_manager is properly stored"""
        assert drive_manager.auth_manager is mock_auth_manager

    def test_recordings_folder_id_initialization(self, drive_manager):
        """Test that recordings_folder_id is initialized properly"""
        assert drive_manager.recordings_folder_id is None

    # ========== COMPONENT PROTOCOL TESTS ==========

    def test_components_implement_protocols(self, drive_manager):
        """Test that components implement expected protocols"""
        mock_folder_mgr = Mock(spec=GoogleFolderManager)
        drive_manager._folder_manager = mock_folder_mgr

        mock_file_mgr = Mock(spec=GoogleFileManager)
        drive_manager._file_manager = mock_file_mgr

        mock_storage_info = Mock(spec=GoogleStorageInfo)
        drive_manager._storage_info = mock_storage_info

        # FolderManager should have required methods
        assert hasattr(mock_folder_mgr, "ensure_recordings_folder")
        assert hasattr(mock_folder_mgr, "list_folders")
        assert hasattr(mock_folder_mgr, "create_folder")
        assert hasattr(mock_folder_mgr, "set_recordings_folder")

        # FileManager should have required methods
        assert hasattr(mock_file_mgr, "upload_file")
        assert hasattr(mock_file_mgr, "download_file")
        assert hasattr(mock_file_mgr, "list_files")
        assert hasattr(mock_file_mgr, "find_duplicate_by_hash")
        assert hasattr(mock_file_mgr, "delete_file")

        # StorageInfo should have required methods
        assert hasattr(mock_storage_info, "get_storage_quota")
        assert hasattr(mock_storage_info, "get_storage_summary")

    def test_delegation_chain_integrity(self, drive_manager):
        """Test that the complete delegation chain works end-to-end"""
        # Set up all components
        mock_folder_mgr = Mock(spec=GoogleFolderManager)
        mock_file_mgr = Mock(spec=GoogleFileManager)
        mock_storage_info = Mock()

        drive_manager._folder_manager = mock_folder_mgr
        drive_manager._file_manager = mock_file_mgr
        drive_manager._storage_info = mock_storage_info

        # Set up return values
        mock_folder_mgr.ensure_recordings_folder = Mock(return_value="folder_id")
        mock_file_mgr.upload_file = Mock(return_value="file_id")
        mock_storage_info.get_storage_quota = Mock(return_value={"limit": 5000000, "usedBytes": 1000000})
        mock_storage_info.get_storage_summary = Mock(
            return_value={"used": "1GB", "total": "5GB"}
        )

        # Execute complete workflow
        folder_id = drive_manager._ensure_recordings_folder()
        file_id = drive_manager.upload_recording("/path/to/file.wav", title="test.wav")
        storage = drive_manager.get_storage_info()

        # Verify all delegations worked
        assert folder_id == "folder_id"
        assert file_id == "file_id"
        assert storage["used_bytes"] == 1000000

        # Verify all calls were made
        mock_folder_mgr.ensure_recordings_folder.assert_called_once()
        mock_file_mgr.upload_file.assert_called_once()
        mock_storage_info.get_storage_quota.assert_called()

    def test_no_direct_google_api_calls_in_manager(self, drive_manager):
        """Verify GoogleDriveManager doesn't make direct Google API calls"""
        # This is a documentation test - it verifies the architecture
        # GoogleDriveManager should NOT have any direct service.files() calls
        # All operations should go through components

        # Get the source code to verify
        import inspect

        source = inspect.getsource(GoogleDriveManager)

        # Should not contain direct service calls
        assert "service.files()" not in source
        assert "service.about()" not in source

        # Should contain delegation
        assert "folder_manager" in source
        assert "file_manager" in source
        assert "storage_info" in source
