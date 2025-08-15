from typing import Any, Dict, Optional, List, cast
import pytest


class StubAuthManagerUnauth:
    def is_authenticated(self) -> bool:
        return False

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        return None


class StubAuthManagerAuth:
    def __init__(self, name: str = "Alice", email: str = "alice@example.com") -> None:
        self._name = name
        self._email = email

    def is_authenticated(self) -> bool:
        return True

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        return {"name": self._name, "emailAddress": self._email}


def test_free_tier_features_and_limits():
    from cloud.feature_gate import FeatureGate, UserTier

    gate = FeatureGate(StubAuthManagerUnauth())

    assert gate.get_user_tier() == UserTier.FREE
    assert gate.is_feature_enabled("cloud_upload") is False
    assert gate.get_feature_value("cloud_upload") is False

    # Defaults for FREE tier
    assert gate.get_feature_value("export_formats") == ["wav"]
    assert gate.get_format_options() == ["wav"]
    assert gate.get_cloud_storage_limit() == 0

    # Recording limit: 5 minutes (300s)
    assert gate.check_recording_limit(60) is True
    assert gate.check_recording_limit(300) is True
    assert gate.check_recording_limit(301) is False

    # Messaging
    text = gate.get_tier_status_text()
    assert "Free" in text

    benefits = gate.get_upgrade_benefits()
    assert isinstance(benefits, list) and len(benefits) > 0

    msg = gate.get_restriction_message("cloud_upload")
    assert msg is not None and "Cloud upload" in msg


def test_premium_tier_features_and_limits():
    from cloud.feature_gate import FeatureGate, UserTier

    gate = FeatureGate(StubAuthManagerAuth())

    assert gate.get_user_tier() == UserTier.PREMIUM
    assert gate.is_feature_enabled("cloud_upload") is True
    assert gate.get_feature_value("cloud_upload") is True

    # Premium values
    formats = gate.get_format_options()
    assert isinstance(formats, list)
    assert "mp3" in formats and "flac" in formats and "wav" in formats

    # Recording limit: 1 hour (3600s)
    assert gate.check_recording_limit(1800) is True
    assert gate.check_recording_limit(3600) is True
    assert gate.check_recording_limit(3601) is False

    assert gate.get_cloud_storage_limit() == 15

    text = gate.get_tier_status_text()
    assert "Premium" in text and "Alice" in text


def test_get_all_features_and_types():
    from cloud.feature_gate import FeatureGate

    free_gate = FeatureGate(StubAuthManagerUnauth())
    prem_gate = FeatureGate(StubAuthManagerAuth())

    free_features = free_gate.get_all_features()
    prem_features = prem_gate.get_all_features()

    # Basic shape checks
    for features in (free_features, prem_features):
        assert isinstance(features, dict)
        assert "cloud_upload" in features
        assert "export_formats" in features

    # Value differences
    assert free_features["cloud_upload"] is False
    assert prem_features["cloud_upload"] is True

    # Types for export formats
    free_formats_any = cast(List[Any], free_features["export_formats"])  # type: ignore[index]
    assert isinstance(free_formats_any, list)
    assert all(isinstance(x, str) for x in free_formats_any)


@pytest.mark.parametrize("auth_manager,expected_tier,cloud_upload,formats,storage_limit", [
    (StubAuthManagerUnauth(), "free", False, ["wav"], 0),
    (StubAuthManagerAuth(), "premium", True, ["wav", "mp3", "flac"], 15),
])
def test_tier_matrix_parameterized(auth_manager, expected_tier, cloud_upload, formats, storage_limit):
    from cloud.feature_gate import FeatureGate, UserTier
    gate = FeatureGate(auth_manager)
    assert gate.get_user_tier().value == expected_tier
    assert gate.is_feature_enabled("cloud_upload") is cloud_upload
    assert all(fmt in gate.get_format_options() for fmt in formats)
    assert gate.get_cloud_storage_limit() == storage_limit


def test_unknown_feature_name_returns_safe_defaults():
    from cloud.feature_gate import FeatureGate
    gate = FeatureGate(StubAuthManagerUnauth())
    # Unknown feature returns False for is_feature_enabled
    assert gate.is_feature_enabled("nonexistent_feature") is False
    # Returns default for get_feature_value
    assert gate.get_feature_value("nonexistent_feature", default=123) == 123
    # Restriction message is generic
    msg = gate.get_restriction_message("nonexistent_feature")
    assert msg is not None and "requires premium access" in msg


def test_tier_status_text_fallback_to_email():
    from cloud.feature_gate import FeatureGate, UserTier
    class EmailOnlyAuth:
        def is_authenticated(self) -> bool:
            return True
        def get_user_info(self) -> Optional[Dict[str, Any]]:
            return {"emailAddress": "user@example.com"}
    gate = FeatureGate(EmailOnlyAuth())
    text = gate.get_tier_status_text()
    assert "Premium" in text and "user@example.com" in text


def test_tier_status_text_fallback_to_user():
    from cloud.feature_gate import FeatureGate, UserTier
    class NoInfoAuth:
        def is_authenticated(self) -> bool:
            return True
        def get_user_info(self) -> Optional[Dict[str, Any]]:
            return None
    gate = FeatureGate(NoInfoAuth())
    text = gate.get_tier_status_text()
    assert "Premium Account" in text
