import os

import pytest
from audio_recorder import AudioRecorderManager


def test_no_input_devices(monkeypatch, tmp_path):
    """When sounddevice reports no input devices, validation should fail."""
    # Patch query_devices to return empty list (accept any args)
    monkeypatch.setattr("audio_recorder.sd.query_devices", lambda *a, **k: [])

    mgr = AudioRecorderManager()

    # Validation should return False
    assert mgr._validate_audio_devices() is False

    # get_available_devices should return an empty list
    assert mgr.get_available_devices() == []


@pytest.mark.xfail(
    condition=os.getenv("CI") is not None,
    reason="Audio device test requires actual audio hardware",
    strict=False,
)
def test_input_device_present(monkeypatch, tmp_path):
    """When an input-capable device is present, validation should succeed."""

    # Fake device list with one input device
    def fake_query_devices(*args, **kwargs):
        # When called with no args, return full device list
        if len(args) == 0 and not kwargs:
            return [
                {
                    "name": "Fake Mic",
                    "max_input_channels": 1,
                    "default_samplerate": 44100,
                }
            ]
        # When called with a device index or id, return a device info dict
        return {
            "name": "Fake Mic",
            "max_input_channels": 1,
            "default_samplerate": 44100,
            "default_low_input_latency": 0.01,
            "default_high_input_latency": 0.1,
        }

    monkeypatch.setattr("audio_recorder.sd.query_devices", fake_query_devices)

    mgr = AudioRecorderManager()

    # Validation should return True when device test passes
    assert mgr._validate_audio_devices() is True

    devices = mgr.get_available_devices()
    assert isinstance(devices, list)
    assert len(devices) == 1
    assert devices[0]["name"] == "Fake Mic"
