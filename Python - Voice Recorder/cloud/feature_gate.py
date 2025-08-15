"""
Feature Gating System for Voice Recorder Pro

Controls access to premium features based on authentication status
and provides user tier management for cloud-enabled functionality.
"""

import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable, TypeVar, cast

try:
    from typing import ParamSpec  # Python 3.10+
except Exception:  # pragma: no cover
    from typing_extensions import ParamSpec  # type: ignore

P = ParamSpec("P")
R = TypeVar("R")


class UserTier(Enum):
    """User subscription tiers"""

    FREE = "free"
    PREMIUM = "premium"
    PRO = "pro"


@runtime_checkable
class AuthManagerProtocol(Protocol):
    """Minimal contract expected from an authentication manager."""

    def is_authenticated(self) -> bool:
        ...

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        ...


class FeatureGate:
    """Manages feature access based on authentication and subscription status"""

    def __init__(self, auth_manager: AuthManagerProtocol):
        """
        Initialize feature gate

        Args:
            auth_manager: GoogleAuthManager-like instance
        """
        self.auth_manager = auth_manager

        # Map of user tier to feature configuration values
        self.feature_matrix: Dict[UserTier, Dict[str, Any]] = {
            UserTier.FREE: {
                "cloud_upload": False,
                "cloud_download": False,
                "cloud_sync": False,
                "unlimited_recordings": False,
                "export_formats": ["wav"],
                "max_recording_length": 300,  # 5 minutes
                "concurrent_recordings": 1,
                "cloud_storage_gb": 0,
                "audio_quality": "standard",
                "advanced_editing": False,
                "batch_operations": False,
                "custom_presets": False,
            },
            UserTier.PREMIUM: {
                "cloud_upload": True,
                "cloud_download": True,
                "cloud_sync": True,
                "unlimited_recordings": True,
                "export_formats": ["wav", "mp3", "flac"],
                "max_recording_length": 3600,  # 1 hour
                "concurrent_recordings": 3,
                "cloud_storage_gb": 15,  # Google Drive free tier
                "audio_quality": "high",
                "advanced_editing": True,
                "batch_operations": True,
                "custom_presets": True,
            },
        }

    def get_user_tier(self) -> UserTier:
        """
        Determine user's current tier

        Returns:
            UserTier: Current user tier
        """
        if self.auth_manager.is_authenticated():
            # For now, authenticated users get Premium
            # In the future, this could check subscription status
            return UserTier.PREMIUM
        return UserTier.FREE

    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Check if a specific feature is enabled for the current user

        Args:
            feature_name (str): Name of the feature to check

        Returns:
            bool: True if feature is enabled, False otherwise
        """
        user_tier = self.get_user_tier()
        features: Dict[str, Any] = self.feature_matrix.get(user_tier, {})
        return bool(features.get(feature_name, False))

    def get_feature_value(self, feature_name: str, default: Optional[Any] = None) -> Any:
        """
        Get the value of a feature for the current user

        Args:
            feature_name (str): Name of the feature
            default: Default value if feature not found

        Returns:
            Feature value or default
        """
        user_tier = self.get_user_tier()
        features: Dict[str, Any] = self.feature_matrix.get(user_tier, {})
        return features.get(feature_name, default)

    def get_all_features(self) -> Dict[str, Any]:
        """
        Get all features for the current user tier

        Returns:
            Dict: All features and their values/status
        """
        user_tier = self.get_user_tier()
        return self.feature_matrix.get(user_tier, {})

    def get_upgrade_benefits(self) -> List[str]:
        """
        Get list of benefits when upgrading from current tier

        Returns:
            List[str]: List of upgrade benefits
        """
        current_tier = self.get_user_tier()
        if current_tier == UserTier.FREE:
            return [
                "☁️ Upload recordings to Google Drive",
                "📥 Access recordings from any device",
                "🔄 Automatic cloud synchronization",
                "🎵 Export to MP3 and FLAC formats",
                "⏱️ Unlimited recording length",
                "🎛️ Advanced audio editing tools",
                "📁 Batch file operations",
                "⚙️ Custom recording presets",
                "🎧 High-quality audio recording",
                "💾 15GB cloud storage",
            ]
        return []  # Already at highest tier

    def get_tier_status_text(self) -> str:
        """
        Get human-readable tier status

        Returns:
            str: Status text for UI display
        """
        user_tier = self.get_user_tier()
        if user_tier == UserTier.FREE:
            return "Free Version - Sign in for Premium Features"
        if user_tier == UserTier.PREMIUM:
            user_info = self.auth_manager.get_user_info()
            if user_info:
                name = user_info.get("name") or user_info.get("emailAddress") or "User"
                return f"Premium Account - {name}"
            return "Premium Account"
        return "Unknown Status"

    def get_restriction_message(self, feature_name: str) -> Optional[str]:
        """
        Get restriction message for a disabled feature

        Args:
            feature_name (str): Name of the feature

        Returns:
            str: Message explaining the restriction, or None if feature is enabled
        """
        if self.is_feature_enabled(feature_name):
            return None
        messages: Dict[str, str] = {
            "cloud_upload": "☁️ Cloud upload requires Google authentication. Sign in to enable premium features.",
            "cloud_download": "📥 Cloud access requires Google authentication. Sign in to access your recordings.",
            "cloud_sync": "🔄 Cloud sync is a premium feature. Sign in with Google to enable synchronization.",
            "unlimited_recordings": "📝 Free version limited to basic recordings. Upgrade for unlimited access.",
            "advanced_editing": "🎛️ Advanced editing requires premium access. Sign in to unlock professional tools.",
            "batch_operations": "📁 Batch operations are premium-only. Sign in to process multiple files.",
            "custom_presets": "⚙️ Custom presets require premium account. Sign in to create personalized settings.",
        }
        return messages.get(feature_name, f"🔒 {feature_name} requires premium access.")

    def check_recording_limit(self, current_length: int) -> bool:
        """
        Check if recording length is within limits

        Args:
            current_length (int): Current recording length in seconds

        Returns:
            bool: True if within limits, False otherwise
        """
        max_length: int = int(self.get_feature_value("max_recording_length", 300))
        return current_length <= max_length

    def get_format_options(self) -> List[str]:
        """
        Get available export formats for current tier

        Returns:
            List[str]: Available format options
        """
        value = self.get_feature_value("export_formats", ["wav"])
        if isinstance(value, list):
            value_list = cast(List[Any], value)
            try:
                return [str(v) for v in value_list]
            except Exception:
                return ["wav"]
        return ["wav"]

    def can_upload_to_cloud(self) -> bool:
        """
        Check if user can upload to cloud storage

        Returns:
            bool: True if cloud upload is available
        """
        return self.auth_manager.is_authenticated() and self.is_feature_enabled("cloud_upload")

    def get_cloud_storage_limit(self) -> int:
        """
        Get cloud storage limit in GB

        Returns:
            int: Storage limit in gigabytes
        """
        return int(self.get_feature_value("cloud_storage_gb", 0))


class FeatureDecorator:
    """Decorator for feature-gated methods"""

    def __init__(self, feature_gate: FeatureGate, message_handler: Optional[Callable[[str], None]] = None):
        self.feature_gate = feature_gate
        if message_handler is not None:
            self.message_handler = message_handler
        else:
            def _default_handler(msg: str) -> None:
                logging.warning(msg)
                print(msg)
            self.message_handler = _default_handler

    def requires_feature(self, feature_name: str, show_message: bool = True) -> Callable[[Callable[P, R]], Callable[P, Optional[R]]]:
        """
        Decorator that checks if a feature is enabled before execution

        Args:
            feature_name (str): Required feature name
            show_message (bool): Whether to show restriction message
        """

        def decorator(func: Callable[P, R]) -> Callable[P, Optional[R]]:
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> Optional[R]:
                if self.feature_gate.is_feature_enabled(feature_name):
                    return func(*args, **kwargs)
                if show_message:
                    message = self.feature_gate.get_restriction_message(feature_name)
                    if message:
                        self.message_handler(f"🚫 {message}")
                return None

            return wrapper

        return decorator


# Example usage
if __name__ == "__main__":
    from cloud.auth_manager import GoogleAuthManager

    # Initialize feature gate
    auth_manager = GoogleAuthManager()
    feature_gate = FeatureGate(auth_manager)

    # Check current tier
    tier = feature_gate.get_user_tier()
    print(f"👤 Current tier: {tier.value}")
    print(f"📊 Status: {feature_gate.get_tier_status_text()}")

    # Check specific features
    features_to_check = ["cloud_upload", "advanced_editing", "unlimited_recordings"]

    print("\n🔍 Feature availability:")
    for feature in features_to_check:
        enabled = feature_gate.is_feature_enabled(feature)
        status = "✅ Enabled" if enabled else "🔒 Restricted"
        print(f"  {feature}: {status}")

        if not enabled:
            message = feature_gate.get_restriction_message(feature)
            print(f"    💬 {message}")

    # Show upgrade benefits if on free tier
    if tier == UserTier.FREE:
        print("\n⭐ Upgrade benefits:")
        benefits = feature_gate.get_upgrade_benefits()
        for benefit in benefits[:5]:  # Show first 5 benefits
            print(f"  {benefit}")

    # Show format options
    formats = feature_gate.get_format_options()
    print(f"\n💾 Available formats: {', '.join(formats)}")
