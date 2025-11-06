"""Tests for FileManager component"""

from unittest.mock import MagicMock, patch

from cloud._file_manager import GoogleFileManager


class TestUploadFile:
    """Tests for upload_file method"""

    def test_upload_file_success(self):
        """Test successful file upload"""
        auth_manager = MagicMock()
        folder_manager = MagicMock()
        folder_manager.ensure_recordings_folder.return_value = "folder_id"
        
        service = MagicMock()
        
        # Setup the resumable media upload mock
        mock_upload = MagicMock()
        mock_upload.next_chunk.side_effect = [
            (None, {"id": "file_id"}),
        ]
        
        service.files().create.return_value = mock_upload
        
        manager = GoogleFileManager(auth_manager, folder_manager, service_provider=service)

        with patch("os.path.exists", return_value=True):
            with patch("os.path.getsize", return_value=1024):
                with patch("cloud._file_manager.build_upload_metadata", return_value={}):
                    with patch("cloud._lazy.import_http") as mock_import_http:
                        mock_media_upload = MagicMock()
                        mock_import_http.return_value = (mock_media_upload, None)
                        result = manager.upload_file("/path/to/file.wav")

        assert result == "file_id"

    def test_upload_file_not_found(self):
        """Test upload when file not found"""
        auth_manager = MagicMock()
        folder_manager = MagicMock()
        service = MagicMock()

        manager = GoogleFileManager(auth_manager, folder_manager, service_provider=service)

        with patch("os.path.exists", return_value=False):
            result = manager.upload_file("/nonexistent/file.wav")

        assert result is None

    def test_upload_file_skips_duplicate_check(self):
        """Test upload with force skips duplicate check"""
        auth_manager = MagicMock()
        folder_manager = MagicMock()
        folder_manager.ensure_recordings_folder.return_value = "folder_id"
        
        service = MagicMock()
        mock_upload = MagicMock()
        mock_upload.next_chunk.side_effect = [
            (None, {"id": "file_id"}),
        ]
        service.files().create.return_value = mock_upload

        manager = GoogleFileManager(auth_manager, folder_manager, service_provider=service)

        with patch("os.path.exists", return_value=True):
            with patch("os.path.getsize", return_value=1024):
                with patch("cloud._file_manager.build_upload_metadata", return_value={}):
                    with patch("cloud._lazy.import_http") as mock_import_http:
                        mock_media_upload = MagicMock()
                        mock_import_http.return_value = (mock_media_upload, None)
                        result = manager.upload_file("/path/to/file.wav", force=True)

        assert result == "file_id"

    def test_upload_file_duplicate_found(self):
        """Test upload skips when duplicate found"""
        auth_manager = MagicMock()
        folder_manager = MagicMock()
        service = MagicMock()

        manager = GoogleFileManager(auth_manager, folder_manager, service_provider=service)

        with patch("os.path.exists", return_value=True):
            with patch("cloud.dedupe.compute_content_sha256", return_value="abc123"):
                with patch.object(manager, "find_duplicate_by_hash", return_value={"id": "dup_id"}):
                    result = manager.upload_file("/path/to/file.wav")

        assert result == "dup_id"


class TestDownloadFile:
    """Tests for download_file method"""

    def test_download_file_success(self):
        """Test successful file download"""
        auth_manager = MagicMock()
        folder_manager = MagicMock()
        service = MagicMock()

        # Mock media download
        mock_media_download = MagicMock()
        mock_media_download.complete.side_effect = [False, True]
        mock_media_download.next_chunk.return_value = (None, b"data")

        manager = GoogleFileManager(auth_manager, folder_manager, service_provider=service)

        def http_constructor(*_: object, **__: object) -> MagicMock:
            return mock_media_download

        with patch("builtins.open", MagicMock()):
            with patch("cloud._lazy.import_http") as mock_import_http:
                mock_import_http.return_value = (None, http_constructor)
                result = manager.download_file("file_id", "/path/to/save.wav")

        assert result is True

    def test_download_file_error(self):
        """Test download error handling"""
        auth_manager = MagicMock()
        folder_manager = MagicMock()
        service = MagicMock()
        service.files().get_media.side_effect = Exception("Download error")

        manager = GoogleFileManager(auth_manager, folder_manager, service_provider=service)

        with patch("cloud._lazy.import_http", side_effect=Exception("Import error")):
            result = manager.download_file("file_id", "/path/to/save.wav")

        assert result is False


class TestListFiles:
    """Tests for list_files method"""

    def test_list_files(self):
        """Test listing files in folder"""
        auth_manager = MagicMock()
        folder_manager = MagicMock()
        service = MagicMock()

        manager = GoogleFileManager(auth_manager, folder_manager, service)

        with patch("cloud._file_manager.paginate_results") as mock_paginate:
            mock_paginate.return_value = [
                {"id": "file1", "name": "Test.wav", "size": "1024", "created": "2025-01-01"},
            ]
            result = manager.list_files("folder_id")

        assert len(result) == 1
        assert result[0]["name"] == "Test.wav"


class TestFindDuplicate:
    """Tests for find_duplicate_by_hash method"""

    def test_find_duplicate_found(self):
        """Test finding duplicate file"""
        auth_manager = MagicMock()
        folder_manager = MagicMock()
        folder_manager.ensure_recordings_folder.return_value = "folder_id"
        
        service = MagicMock()
        mock_response: dict[str, object] = {
            "files": [
                {
                    "id": "dup_id",
                    "name": "duplicate.wav",
                    "appProperties": {"content_sha256": "abc123"},
                }
            ]
        }
        service.files().list().execute.return_value = mock_response

        manager = GoogleFileManager(auth_manager, folder_manager, service)
        result = manager.find_duplicate_by_hash("abc123")

        assert result is not None
        assert result["id"] == "dup_id"

    def test_find_duplicate_not_found(self):
        """Test when no duplicate found"""
        auth_manager = MagicMock()
        folder_manager = MagicMock()
        folder_manager.ensure_recordings_folder.return_value = "folder_id"
        
        service = MagicMock()
        mock_response: dict[str, object] = {"files": []}
        service.files().list().execute.return_value = mock_response

        manager = GoogleFileManager(auth_manager, folder_manager, service)
        result = manager.find_duplicate_by_hash("different_hash")

        assert result is None


class TestDeleteFile:
    """Tests for delete_file method"""

    def test_delete_file_success(self):
        """Test successful file deletion"""
        auth_manager = MagicMock()
        folder_manager = MagicMock()
        service = MagicMock()
        service.files().delete().execute.return_value = None

        manager = GoogleFileManager(auth_manager, folder_manager, service)
        result = manager.delete_file("file_id")

        assert result is True

    def test_delete_file_error(self):
        """Test delete error handling"""
        auth_manager = MagicMock()
        folder_manager = MagicMock()
        service = MagicMock()
        service.files().delete().execute.side_effect = Exception("Delete error")

        manager = GoogleFileManager(auth_manager, folder_manager, service)
        result = manager.delete_file("file_id")

        assert result is False
