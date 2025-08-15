from typing import Any, Dict, Optional, List

import pytest


class StubAuthManagerUnauth:
    def is_authenticated(self) -> bool:
        return False

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        return None


class StubAuthManagerAuth:
    def is_authenticated(self) -> bool:
        return True

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        return {"name": "Bob", "emailAddress": "bob@example.com"}


def test_requires_feature_allows_when_enabled():
    from cloud.feature_gate import FeatureGate, FeatureDecorator

    gate = FeatureGate(StubAuthManagerAuth())
    deco = FeatureDecorator(gate)

    calls = {"count": 0}

    @deco.requires_feature("cloud_upload")
    def do_upload(x: int, y: int) -> int:
        calls["count"] += 1
        return x + y

    result = do_upload(2, 3)
    assert result == 5
    assert calls["count"] == 1


def test_requires_feature_blocks_when_disabled_and_logs(caplog: Any):
    from cloud.feature_gate import FeatureGate, FeatureDecorator

    gate = FeatureGate(StubAuthManagerUnauth())
    messages: List[str] = []

    def collector(msg: str) -> None:
        messages.append(msg)

    deco = FeatureDecorator(gate, message_handler=collector)

    @deco.requires_feature("cloud_upload")
    def do_upload(name: str) -> str:
        return name.upper()

    with caplog.at_level("WARNING"):
        result = do_upload("abc")

    assert result is None
    assert any("Cloud upload" in m for m in messages)


def test_requires_feature_blocks_without_message_when_suppressed(caplog: Any):
    from cloud.feature_gate import FeatureGate, FeatureDecorator

    gate = FeatureGate(StubAuthManagerUnauth())
    messages: List[str] = []

    deco = FeatureDecorator(gate, message_handler=messages.append)

    @deco.requires_feature("cloud_upload", show_message=False)
    def do_upload(name: str) -> str:
        return name.upper()

    with caplog.at_level("WARNING"):
        result = do_upload("xyz")

    assert result is None
    # no messages when suppressed
    assert messages == []
