import os
import time
import threading
import numpy as np
from unittest.mock import patch
from audio_recorder import AudioRecorderThread


def test_inputstream_raises_on_open(tmp_path, caplog):
    out = tmp_path / "rec_open_fail.wav"
    sample_rate = 8000
    channels = 1

    class RaisingInputStream:
        def __init__(self, *args, **kwargs):
            # Simulate device disappearing when attempting to open stream
            raise RuntimeError("Device disappeared on open")

    with patch('audio_recorder.sd.InputStream', new=RaisingInputStream):
        thread = AudioRecorderThread(str(out), sample_rate=sample_rate, channels=channels)
        caplog.clear()
        caplog.set_level('ERROR')

        thread.is_recording = True
        t = threading.Thread(target=thread.run)
        t.start()
        t.join(timeout=2)

    # No file should exist
    assert not os.path.exists(str(out))
    # The recorder logs an ERROR when the device disappears during open
    assert any('Recording failed' in r.message for r in caplog.records)


def test_inputstream_raises_on_exit_cleanup(tmp_path, caplog):
    out = tmp_path / "rec_exit_fail.wav"
    sample_rate = 8000
    channels = 1

    class ExitRaisingInputStream:
        def __init__(self, *args, **kwargs):
            # Accept flexible constructor signature like sd.InputStream
            self.callback = kwargs.get('callback') if 'callback' in kwargs else (args[0] if args else None)
            self.blocksize = kwargs.get('blocksize', 1024)
            self._running = False

        def __enter__(self):
            self._running = True

            def run_cb():
                # Call callback a few times, then keep running until exit
                for _ in range(3):
                    frames = self.blocksize
                    t = np.linspace(0, 1, frames, endpoint=False, dtype=np.float32)
                    chunk = 0.1 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
                    if self.callback is not None:
                        self.callback(chunk.reshape(-1, 1), frames, None, None)
                    time.sleep(0.01)
                # Stay alive until __exit__ is invoked
                while self._running:
                    time.sleep(0.01)

            self._thread = threading.Thread(target=run_cb)
            self._thread.start()
            return self

        def __exit__(self, exc_type, exc, tb):
            self._running = False
            self._thread.join()
            # Simulate device failure during context exit
            raise RuntimeError("Device disconnected during recording")

    with patch('audio_recorder.sd.InputStream', new=ExitRaisingInputStream):
        thread = AudioRecorderThread(str(out), sample_rate=sample_rate, channels=channels)
        caplog.clear()
        caplog.set_level('ERROR')

        thread.is_recording = True
        t = threading.Thread(target=thread.run)
        t.start()

        # let a few callbacks happen
        time.sleep(0.1)
        # request stop which will trigger __exit__ that raises
        thread.stop_recording()
        t.join(timeout=2)

    # Final file should not exist because finalize failed and cleanup removed partial
    assert not os.path.exists(str(out))
    # The recorder logs an ERROR when the InputStream fails on exit
    assert any('Recording failed' in r.message for r in caplog.records)
