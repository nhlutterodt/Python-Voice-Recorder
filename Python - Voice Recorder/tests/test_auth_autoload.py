from pathlib import Path

from cloud.auth_manager import GoogleAuthManager


def test_auth_manager_does_not_autoload_by_default(tmp_path: Path):
    # Create a temporary app dir with expected subfolders
    app_dir = tmp_path
    (app_dir / "cloud" / "credentials").mkdir(parents=True)
    (app_dir / "config").mkdir(parents=True)

    # Construct without providing credentials and default flags
    mgr = GoogleAuthManager(app_dir=app_dir)

    # Credentials should be None until explicitly loaded
    assert mgr.credentials is None


def test_auth_manager_use_keyring_flag_controls_loading(tmp_path: Path):
    app_dir = tmp_path
    (app_dir / "cloud" / "credentials").mkdir(parents=True)
    (app_dir / "config").mkdir(parents=True)

    # Explicitly enable keyring but do not populate it; still should not auto-load
    mgr = GoogleAuthManager(app_dir=app_dir, use_keyring=True)
    assert mgr.credentials is None
