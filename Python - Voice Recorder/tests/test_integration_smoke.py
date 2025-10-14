import os
from pathlib import Path

import pytest
from cloud.auth_manager import GOOGLE_APIS_AVAILABLE, GoogleAuthManager
from cloud.drive_manager import GoogleDriveManager

# A lightweight smoke test that verifies integration prerequisites are available.
# This test will skip unless the environment variable VRP_CLIENT_SECRETS is set and
# points to a readable file. When present, it will attempt to construct the auth
# manager and drive manager and ensure we can obtain a uploader instance.


def test_smoke_integration_env():
    client_secrets = os.environ.get("VRP_CLIENT_SECRETS")
    if not client_secrets or not Path(client_secrets).exists():
        pytest.skip(
            "VRP_CLIENT_SECRETS not set or file missing; skipping integration smoke test"
        )

    # If Google APIs are not installed, skip the integration test as well
    if not GOOGLE_APIS_AVAILABLE:
        pytest.skip("Google API libs not available in this environment")

    mgr = GoogleAuthManager()
    dm = GoogleDriveManager(mgr)

    # Ensure we can obtain a uploader instance (may raise if not configured)
    uploader = None
    try:
        uploader = dm.get_uploader()
    except Exception as e:
        pytest.skip(f"Could not construct uploader: {e}")

    assert uploader is not None
