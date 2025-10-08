from pathlib import Path
import os
import tempfile
from unittest.mock import patch, Mock

from cloud.auth_manager import GoogleAuthManager


def test_save_credentials_uses_keyring_when_available(tmp_path: Path):
    mock_creds = Mock()
    mock_creds.to_json.return_value = '{"token":"abc"}'
    mgr = GoogleAuthManager(app_dir=tmp_path, credentials=mock_creds)

    fake_keyring = Mock()

    with patch("keyring.set_password", fake_keyring):
        mgr._save_credentials_securely()

    assert fake_keyring.called


def test_save_credentials_falls_back_to_file_lock(tmp_path: Path):
    mock_creds = Mock()
    mock_creds.to_json.return_value = '{"token":"xyz"}'
    mgr = GoogleAuthManager(app_dir=tmp_path, credentials=mock_creds)

    # Ensure keyring import will fail by removing keyring from sys.modules if present
    with patch.dict("sys.modules", {"keyring": None}):
        mgr._save_credentials_securely()

    # token.json should exist
    token_path = Path(tmp_path) / "cloud" / "credentials" / "token.json"
    assert token_path.exists()
    content = token_path.read_text(encoding="utf-8")
    assert '"token":"xyz"' in content
