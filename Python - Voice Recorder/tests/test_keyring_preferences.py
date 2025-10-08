import sys
import os
import importlib
from pathlib import Path

import pytest

from PySide6.QtWidgets import QApplication


def test_cli_no_keyring_overrides_config(monkeypatch):
    """When --no-keyring is passed on the CLI, enhanced_main should create the
    main window with use_keyring=False even if config_manager.prefers_keyring() is True.
    """
    # Import the module fresh to ensure globals are as expected
    enhanced_main = importlib.import_module('enhanced_main')

    # Prepare dummy QApplication and EnhancedAudioEditor to avoid real GUI creation
    class DummyApp:
        def __init__(self, args=None):
            self._args = args

        def setApplicationName(self, *a, **k):
            pass

        def setApplicationVersion(self, *a, **k):
            pass

        def setOrganizationName(self, *a, **k):
            pass

        def exec(self):
            return 0

    class DummyEditor:
        last_instance = None

        def __init__(self, *args, **kwargs):
            DummyEditor.last_instance = self
            # Capture the use_keyring kwarg if provided
            self.use_keyring = kwargs.get('use_keyring', None)

        def show(self):
            pass

    # Monkeypatch QApplication and EnhancedAudioEditor in the module under test
    monkeypatch.setattr(enhanced_main, 'QApplication', DummyApp)
    monkeypatch.setattr(enhanced_main, 'EnhancedAudioEditor', DummyEditor)

    # Ensure config_manager prefers keyring by default
    enhanced_main.config_manager.google_config.use_keyring = True

    # Simulate CLI args
    monkeypatch.setattr(sys, 'argv', ['prog', '--no-keyring'])

    # Run main and catch SystemExit (expected due to sys.exit in main)
    try:
        enhanced_main.main()
    except SystemExit:
        pass

    # Assert that the created editor instance had use_keyring explicitly False
    assert DummyEditor.last_instance is not None
    assert DummyEditor.last_instance.use_keyring is False


def test_cli_no_keyring_with_env_and_dotenv_false(tmp_path, monkeypatch):
    """When .env and environment variable indicate USE_KEYRING=false, passing
    --no-keyring should still result in use_keyring=False (inverse sanity check).
    """
    enhanced_main = importlib.import_module('enhanced_main')

    class DummyApp:
        def __init__(self, args=None):
            pass

        def setApplicationName(self, *a, **k):
            pass

        def setApplicationVersion(self, *a, **k):
            pass

        def setOrganizationName(self, *a, **k):
            pass

        def exec(self):
            return 0

    class DummyEditor:
        last_instance = None

        def __init__(self, *args, **kwargs):
            DummyEditor.last_instance = self
            self.use_keyring = kwargs.get('use_keyring', None)

        def show(self):
            pass

    monkeypatch.setattr(enhanced_main, 'QApplication', DummyApp)
    monkeypatch.setattr(enhanced_main, 'EnhancedAudioEditor', DummyEditor)

    env_path = tmp_path / '.env'
    env_path.write_text('USE_KEYRING=false\n', encoding='utf-8')

    cfg = importlib.import_module('config_manager').config_manager
    monkeypatch.setattr(cfg, 'env_file', env_path)
    monkeypatch.setenv('USE_KEYRING', 'false')

    monkeypatch.setattr(sys, 'argv', ['prog', '--no-keyring'])

    try:
        enhanced_main.main()
    except SystemExit:
        pass

    assert DummyEditor.last_instance is not None
    assert DummyEditor.last_instance.use_keyring is False


def test_reinit_cloud_components_uses_updated_preference(monkeypatch, tmp_path, qapp):
    """Ensure that when preferences change and the editor re-initializes cloud
    components, the new GoogleAuthManager is created with the updated use_keyring.
    """
    # Import the module under test
    ee = importlib.import_module('enhanced_editor')
    cfg = importlib.import_module('config_manager').config_manager

    # Point config_manager.env_file to temp to avoid touching repo .env
    monkeypatch.setattr(cfg, 'env_file', tmp_path / '.env')

    # Ensure cloud is considered available
    monkeypatch.setattr(ee, '_cloud_available', True)

    # Dummy classes to capture use_keyring
    class DummyAuthManager:
        last_instance = None

        def __init__(self, use_keyring=True, *a, **kw):
            DummyAuthManager.last_instance = self
            self.use_keyring = use_keyring

    class DummyDriveManager:
        def __init__(self, auth):
            self.auth = auth

    class DummyFeatureGate:
        def __init__(self, auth):
            self.auth = auth

    class DummyCloudUI:
            def __init__(self, auth, drive, feature_gate):
                from PySide6.QtWidgets import QWidget
                QWidget.__init__(self)
                self.auth = auth
                self.drive = drive
                self.feature_gate = feature_gate

    # Patch the cloud classes in enhanced_editor module
    monkeypatch.setattr(ee, 'GoogleAuthManager', DummyAuthManager)
    monkeypatch.setattr(ee, 'GoogleDriveManager', DummyDriveManager)
    monkeypatch.setattr(ee, 'FeatureGate', DummyFeatureGate)
    monkeypatch.setattr(ee, 'CloudUI', DummyCloudUI)

    # Start with preference True
    cfg.google_config.use_keyring = True

    # Create an editor instance; it should initialize cloud components with True
    editor = ee.EnhancedAudioEditor(use_keyring=True)
    assert DummyAuthManager.last_instance is not None
    assert DummyAuthManager.last_instance.use_keyring is True

    # Create a dummy SettingsDialog that flips the preference to False when exec() is called
    class DummySettingsDialog:
        def __init__(self, parent=None):
            pass

        def exec(self):
            # Simulate user toggling setting to False and saving
            cfg.set_use_keyring(False)
            return True

    # Patch the dialog used by EnhancedAudioEditor.open_preferences
    monkeypatch.setattr(ee, 'SettingsDialog', DummySettingsDialog)

    # Call open_preferences which should trigger re-init with the new preference
    editor.open_preferences()

    # After re-init, the auth manager should have been recreated with use_keyring False
    assert DummyAuthManager.last_instance is not None
    assert DummyAuthManager.last_instance.use_keyring is False


@pytest.fixture(scope='session')
def qapp():
    """Provide a headless Qt QApplication for widget tests.

    Uses the offscreen platform so tests don't require a display.
    """
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_settings_dialog_on_save_updates_env_and_pref(tmp_path, monkeypatch, qapp):
    """Instantiate the real SettingsDialog in a headless QApplication,
    toggle the checkbox, save, and verify .env and config_manager update.
    """
    settings_ui = importlib.import_module('settings_ui')
    config_manager = importlib.import_module('config_manager').config_manager

    # Point the config manager's env_file to a temp .env in tmp_path
    env_path = tmp_path / '.env'
    monkeypatch.setattr(config_manager, 'env_file', env_path)

    # Start with USE_KEYRING True
    config_manager.google_config.use_keyring = True

    # Create the real dialog (parent None is fine under QApplication fixture)
    dlg = settings_ui.SettingsDialog(parent=None)

    # Simulate user unchecking the keyring option
    dlg.keyring_checkbox.setChecked(False)

    # Click Save by calling the handler
    dlg.on_save()

    # After saving, config_manager should reflect the change
    assert config_manager.prefers_keyring() is False

    # .env file should exist and contain USE_KEYRING=false
    assert env_path.exists()
    contents = env_path.read_text(encoding='utf-8')
    assert 'USE_KEYRING=false' in contents


def test_cli_no_keyring_precedence_over_env_and_dotenv(tmp_path, monkeypatch):
    """Ensure that the CLI --no-keyring flag takes precedence over both the
    environment variable USE_KEYRING and the project's .env file.
    """
    enhanced_main = importlib.import_module('enhanced_main')

    # Dummy QApplication and EnhancedAudioEditor to capture the passed kwarg
    class DummyApp:
        def __init__(self, args=None):
            pass

        def setApplicationName(self, *a, **k):
            pass

        def setApplicationVersion(self, *a, **k):
            pass

        def setOrganizationName(self, *a, **k):
            pass

        def exec(self):
            return 0

    class DummyEditor:
        last_instance = None

        def __init__(self, *args, **kwargs):
            DummyEditor.last_instance = self
            self.use_keyring = kwargs.get('use_keyring', None)

        def show(self):
            pass

    monkeypatch.setattr(enhanced_main, 'QApplication', DummyApp)
    monkeypatch.setattr(enhanced_main, 'EnhancedAudioEditor', DummyEditor)

    # Create a real .env file containing USE_KEYRING=true
    env_path = tmp_path / '.env'
    env_path.write_text('USE_KEYRING=true\n', encoding='utf-8')

    # Point config_manager.env_file to our temp .env and ensure environment variable is set to true
    cfg = importlib.import_module('config_manager').config_manager
    monkeypatch.setattr(cfg, 'env_file', env_path)
    monkeypatch.setenv('USE_KEYRING', 'true')

    # Simulate CLI args with --no-keyring
    monkeypatch.setattr(sys, 'argv', ['prog', '--no-keyring'])

    try:
        enhanced_main.main()
    except SystemExit:
        pass

    # The created editor should have use_keyring explicitly False
    assert DummyEditor.last_instance is not None
    assert DummyEditor.last_instance.use_keyring is False
