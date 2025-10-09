import pytest
import os

from cloud.cloud_fallback import CloudFallbackWidget


def test_cloud_fallback_instantiates(qtbot):
    # Ensure the widget can be instantiated without raising
    widget = CloudFallbackWidget(None, editor_ref=None)
    assert widget is not None


def test_cloud_fallback_buttons_exist(qtbot):
    widget = CloudFallbackWidget(None, editor_ref=None)
    # Check that the object has the key methods
    assert hasattr(widget, 'on_retry')
    assert hasattr(widget, 'on_open_requirements')
    assert hasattr(widget, 'on_open_client_secrets')
