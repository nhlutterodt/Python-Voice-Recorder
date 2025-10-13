# Cloud integration package for Voice Recorder Pro
# Provides OAuth authentication and Google Drive integration

__version__ = "1.0.0"
__all__ = ['GoogleAuthManager', 'GoogleDriveManager', 'CloudUI', 'FeatureGate']

from voice_recorder.cloud.auth_manager import GoogleAuthManager
from voice_recorder.cloud.drive_manager import GoogleDriveManager
from voice_recorder.cloud.cloud_ui import CloudUI
from voice_recorder.cloud.feature_gate import FeatureGate

"""
Note: worker startup should not happen at import time.

We used to start a supervised job-worker here when the config enabled it.
That causes import-time side effects and makes testing and import-time
operations brittle. The worker is now started explicitly by the
application bootstrap (see `src/enhanced_main.py`) after configuration
and the DriveManager instance are available.
"""
