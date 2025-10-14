"""Reusable test helpers for GUI/cloud tests.

This module holds small dummy implementations used across tests so they
can be imported from a single place (keeps conftest.py small and DRY).
"""

from PySide6.QtWidgets import QWidget


class DummyAuthManager:
    """A minimal auth manager used in tests. Stores the last created
    instance on the class so tests can inspect it.
    """

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


class DummyCloudUI(QWidget):
    """A QWidget subclass so it can be inserted into tab widgets during
    tests. Simply records the auth/drive/feature_gate passed to it.
    """

    def __init__(self, auth, drive, feature_gate):
        super().__init__()
        self.auth = auth
        self.drive = drive
        self.feature_gate = feature_gate
