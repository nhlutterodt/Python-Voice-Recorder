"""
Tests for FolderManager component

Tests folder operations including creation, listing, and hierarchy management.
Uses mocking to avoid real Drive API calls.
"""

from unittest.mock import MagicMock, patch
import pytest

from cloud._folder_manager import GoogleFolderManager


class TestListFolders:
    """Tests for list_folders method"""

    def test_list_folders_in_parent(self):
        """Test listing folders in a parent folder"""
        auth_manager = MagicMock()
        service = MagicMock()

        mock_response = {
            "files": [
                {"id": "folder1", "name": "Folder 1"},
                {"id": "folder2", "name": "Folder 2"},
            ]
        }
        service.files().list().execute.return_value = mock_response

        manager = GoogleFolderManager(auth_manager, service)
        result = manager.list_folders(parent_id="parent123")

        assert len(result) == 2
        assert result[0]["id"] == "folder1"
        assert result[0]["name"] == "Folder 1"

    def test_list_folders_at_root(self):
        """Test listing folders at root"""
        auth_manager = MagicMock()
        service = MagicMock()

        mock_response = {
            "files": [
                {"id": "root1", "name": "Root Folder"},
            ]
        }
        service.files().list().execute.return_value = mock_response

        manager = GoogleFolderManager(auth_manager, service)
        result = manager.list_folders(parent_id=None)

        assert len(result) == 1
        assert result[0]["name"] == "Root Folder"

    def test_list_folders_empty(self):
        """Test listing when no folders exist"""
        auth_manager = MagicMock()
        service = MagicMock()

        mock_response = {"files": []}
        service.files().list().execute.return_value = mock_response

        manager = GoogleFolderManager(auth_manager, service)
        result = manager.list_folders()

        assert len(result) == 0

    def test_list_folders_with_custom_page_size(self):
        """Test listing with custom page size"""
        auth_manager = MagicMock()
        service = MagicMock()

        mock_response = {"files": []}
        service.files().list().execute.return_value = mock_response

        manager = GoogleFolderManager(auth_manager, service)
        result = manager.list_folders(page_size=50)

        assert isinstance(result, list)

    def test_list_folders_handles_api_error(self):
        """Test that API errors are handled gracefully"""
        auth_manager = MagicMock()
        service = MagicMock()
        service.files().list().execute.side_effect = Exception("API Error")

        manager = GoogleFolderManager(auth_manager, service)
        result = manager.list_folders()

        assert result == []


class TestCreateFolder:
    """Tests for create_folder method"""

    def test_create_folder_at_root(self):
        """Test creating folder at root"""
        auth_manager = MagicMock()
        service = MagicMock()

        mock_response = {"id": "new_folder_id"}
        service.files().create().execute.return_value = mock_response

        manager = GoogleFolderManager(auth_manager, service)
        result = manager.create_folder("New Folder")

        assert result == "new_folder_id"

    def test_create_folder_with_parent(self):
        """Test creating folder in parent"""
        auth_manager = MagicMock()
        service = MagicMock()

        mock_response = {"id": "subfolder_id"}
        service.files().create().execute.return_value = mock_response

        manager = GoogleFolderManager(auth_manager, service)
        result = manager.create_folder("Subfolder", parent_id="parent123")

        assert result == "subfolder_id"

    def test_create_folder_with_description(self):
        """Test creating folder with description"""
        auth_manager = MagicMock()
        service = MagicMock()

        mock_response = {"id": "folder_with_desc_id"}
        service.files().create().execute.return_value = mock_response

        manager = GoogleFolderManager(auth_manager, service)
        result = manager.create_folder(
            "Folder", description="This is a test folder"
        )

        assert result == "folder_with_desc_id"

    def test_create_folder_api_error(self):
        """Test create_folder handles API errors"""
        auth_manager = MagicMock()
        service = MagicMock()
        service.files().create().execute.side_effect = Exception("API Error")

        manager = GoogleFolderManager(auth_manager, service)
        result = manager.create_folder("New Folder")

        assert result is None

    def test_create_folder_returns_none_on_missing_id(self):
        """Test create_folder returns None if response has no id"""
        auth_manager = MagicMock()
        service = MagicMock()

        mock_response = {}  # No 'id' key
        service.files().create().execute.return_value = mock_response

        manager = GoogleFolderManager(auth_manager, service)
        result = manager.create_folder("New Folder")

        assert result is None


class TestEnsureRecordingsFolder:
    """Tests for ensure_recordings_folder method"""

    def test_ensure_recordings_folder_exists(self):
        """Test when recordings folder already exists"""
        auth_manager = MagicMock()
        service = MagicMock()

        mock_response = {
            "files": [{"id": "existing_recordings_id", "name": "Voice Recorder Pro"}]
        }
        service.files().list().execute.return_value = mock_response

        manager = GoogleFolderManager(auth_manager, service)
        result = manager.ensure_recordings_folder()

        assert result == "existing_recordings_id"
        assert manager.recordings_folder_id == "existing_recordings_id"

    def test_ensure_recordings_folder_creates_new(self):
        """Test creating new recordings folder when it doesn't exist"""
        auth_manager = MagicMock()
        service = MagicMock()

        # First call returns empty (folder doesn't exist)
        list_response = {"files": []}
        create_response = {"id": "new_recordings_id"}

        service.files().list().execute.return_value = list_response
        service.files().create().execute.return_value = create_response

        manager = GoogleFolderManager(auth_manager, service)
        result = manager.ensure_recordings_folder()

        assert result == "new_recordings_id"
        assert manager.recordings_folder_id == "new_recordings_id"

    def test_ensure_recordings_folder_uses_cache(self):
        """Test that cached folder ID is returned"""
        auth_manager = MagicMock()
        service = MagicMock()

        manager = GoogleFolderManager(auth_manager, service)
        manager.recordings_folder_id = "cached_id"

        result = manager.ensure_recordings_folder()

        assert result == "cached_id"
        # Service should not be called if cached
        service.files.assert_not_called()

    def test_ensure_recordings_folder_creation_fails(self):
        """Test error when folder creation fails"""
        auth_manager = MagicMock()
        service = MagicMock()

        list_response = {"files": []}  # Doesn't exist
        service.files().list().execute.return_value = list_response
        service.files().create().execute.return_value = {}  # No id

        manager = GoogleFolderManager(auth_manager, service)

        with pytest.raises(Exception):
            manager.ensure_recordings_folder()


class TestSetRecordingsFolder:
    """Tests for set_recordings_folder method"""

    def test_set_recordings_folder(self):
        """Test setting recordings folder ID"""
        auth_manager = MagicMock()
        manager = GoogleFolderManager(auth_manager)

        manager.set_recordings_folder("custom_folder_id")

        assert manager.recordings_folder_id == "custom_folder_id"

    def test_set_recordings_folder_converts_to_string(self):
        """Test that folder ID is converted to string"""
        auth_manager = MagicMock()
        manager = GoogleFolderManager(auth_manager)

        manager.set_recordings_folder(12345)

        assert manager.recordings_folder_id == "12345"
        assert isinstance(manager.recordings_folder_id, str)


class TestFolderManagerIntegration:
    """Integration tests for folder operations"""

    def test_folder_creation_and_listing(self):
        """Test creating a folder and listing its contents"""
        auth_manager = MagicMock()
        service = MagicMock()

        # Mock folder creation
        create_response = {"id": "parent_id"}
        service.files().create().execute.return_value = create_response

        # Mock folder listing (returns empty)
        list_response = {"files": []}
        service.files().list().execute.return_value = list_response

        manager = GoogleFolderManager(auth_manager, service)

        # Create folder
        parent_id = manager.create_folder("Parent")
        assert parent_id == "parent_id"

        # List contents
        contents = manager.list_folders(parent_id=parent_id)
        assert contents == []

    def test_recordings_folder_workflow(self):
        """Test typical recordings folder workflow"""
        auth_manager = MagicMock()
        service = MagicMock()

        # Mock: recordings folder doesn't exist, so create it
        list_response = {"files": []}
        create_response = {"id": "recordings_folder_id"}

        service.files().list().execute.return_value = list_response
        service.files().create().execute.return_value = create_response

        manager = GoogleFolderManager(auth_manager, service)

        # Ensure recordings folder
        folder_id = manager.ensure_recordings_folder()
        assert folder_id == "recordings_folder_id"

        # Change it
        manager.set_recordings_folder("different_id")
        assert manager.recordings_folder_id == "different_id"


class TestGetService:
    """Tests for service initialization"""

    def test_get_service_uses_provider(self):
        """Test that service_provider is used when provided"""
        auth_manager = MagicMock()
        provider_service = MagicMock()

        manager = GoogleFolderManager(auth_manager, provider_service)
        service = manager._get_service()

        assert service == provider_service

    def test_get_service_not_authenticated(self):
        """Test error when not authenticated"""
        auth_manager = MagicMock()
        auth_manager.is_authenticated.return_value = False

        manager = GoogleFolderManager(auth_manager)

        with pytest.raises(Exception):  # NotAuthenticatedError
            manager._get_service()

    def test_get_service_google_apis_unavailable(self):
        """Test error when Google APIs unavailable"""
        auth_manager = MagicMock()
        auth_manager.is_authenticated.return_value = True

        manager = GoogleFolderManager(auth_manager)

        with patch("cloud._lazy.has_google_apis_available", return_value=False):
            with pytest.raises(Exception):  # APILibrariesMissingError
                manager._get_service()
