import pytest
import sounddevice as sd
from unittest.mock import patch
from audio_recorder import AudioRecorderManager, AudioRecorderThread


def test_set_selected_device_invalid(monkeypatch):
    manager = AudioRecorderManager()

    # Make query_devices return no input devices
    with patch('audio_recorder.sd.query_devices', return_value=[]):
        ok = manager.set_selected_device(99)  # arbitrary device index
        assert ok is False


def test_set_selected_device_valid(monkeypatch):
    manager = AudioRecorderManager()

    fake_devices = [
        {'name': 'Fake Mic', 'max_input_channels': 1, 'default_samplerate': 8000},
    ]

    # Mock query_devices and InputStream context to accept a device index
    with patch('audio_recorder.sd.query_devices', return_value=fake_devices):
        class DummyStream:
            def __init__(self, samplerate, channels, dtype, blocksize, device=None, callback=None):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch('audio_recorder.sd.InputStream', new=DummyStream):
            ok = manager.set_selected_device(0)
            assert ok is True
            assert manager.get_selected_device() == 0


def test_start_recording_uses_selected_device(tmp_path):
    out_dir = tmp_path
    manager = AudioRecorderManager()
    manager.output_directory = str(out_dir)

    # Make query_devices show one device and InputStream accept device kw
    fake_devices = [
        {'name': 'Fake Mic', 'max_input_channels': 1, 'default_samplerate': 8000},
    ]

    with patch('audio_recorder.sd.query_devices', return_value=fake_devices):
        class DummyStream:
            def __init__(self, samplerate, channels, dtype, blocksize, device=None, callback=None):
                self.callback = callback

            def __enter__(self):
                # simulate a single callback then block until exit
                if self.callback:
                    import numpy as np
                    frames = 64
                    t = np.linspace(0, 1, frames, endpoint=False, dtype=np.float32)
                    chunk = 0.1 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
                    self.callback(chunk.reshape(-1, 1), frames, None, None)
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch('audio_recorder.sd.InputStream', new=DummyStream):
            manager.set_selected_device(0)
            started = manager.start_recording(filename='test.wav')
            assert started is True
            # Stop and cleanup quickly
            manager.stop_recording()
            manager.cleanup()