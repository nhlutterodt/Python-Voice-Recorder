# Cloud integration package for Voice Recorder Pro
# Provides OAuth authentication and Google Drive integration

__version__ = "1.0.0"
__all__ = ["GoogleAuthManager", "GoogleDriveManager", "CloudUI", "FeatureGate"]

from .auth_manager import GoogleAuthManager
from .cloud_ui import CloudUI
from .drive_manager import GoogleDriveManager
from .feature_gate import FeatureGate

"""
Note: worker startup should not happen at import time.

We used to start a supervised job-worker here when the config enabled it.
That causes import-time side effects and makes testing and import-time
operations brittle. The worker is now started explicitly by the
application bootstrap (see `src/enhanced_main.py`) after configuration
and the DriveManager instance are available.
"""
