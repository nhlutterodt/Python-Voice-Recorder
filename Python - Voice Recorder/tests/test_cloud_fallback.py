import os

import pytest

from cloud.cloud_fallback import CloudFallbackWidget


@pytest.mark.xfail(
    condition=os.getenv("CI") is not None,
    reason="Qt requires display in headless CI environment",
    strict=False,
)
def test_cloud_fallback_instantiates(qtbot):
    # Ensure the widget can be instantiated without raising
    widget = CloudFallbackWidget(None, editor_ref=None)
    assert widget is not None


@pytest.mark.xfail(
    condition=os.getenv("CI") is not None,
    reason="Qt requires display in headless CI environment",
    strict=False,
)
def test_cloud_fallback_buttons_exist(qtbot):
    widget = CloudFallbackWidget(None, editor_ref=None)
    # Check that the object has the key methods
    assert hasattr(widget, "on_retry")
    assert hasattr(widget, "on_open_requirements")
    assert hasattr(widget, "on_open_client_secrets")
