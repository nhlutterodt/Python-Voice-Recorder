# Cloud integration package for Voice Recorder Pro
# Provides OAuth authentication and Google Drive integration

__version__ = "1.0.0"
__all__ = ['GoogleAuthManager', 'GoogleDriveManager', 'CloudUI', 'FeatureGate']

from .auth_manager import GoogleAuthManager
from .drive_manager import GoogleDriveManager
from .cloud_ui import CloudUI
from .feature_gate import FeatureGate
