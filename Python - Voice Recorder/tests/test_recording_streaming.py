import os
import wave
import time
import threading
import numpy as np
from unittest.mock import patch

from audio_recorder import AudioRecorderThread


def test_streaming_recording_writes_file(tmp_path):
    out = tmp_path / "rec.wav"
    sample_rate = 8000
    channels = 1

    # Prepare a fake InputStream context manager that calls the callback a few times
    class FakeInputStream:
        def __init__(self, callback, samplerate, channels, dtype, blocksize):
            self.callback = callback
            self.samplerate = samplerate
            self.channels = channels
            self.blocksize = blocksize
            self._running = False

        def __enter__(self):
            self._running = True
            # Start a thread to simulate audio callbacks
            def run_cb():
                for i in range(3):
                    # create a simple mono chunk
                    frames = self.blocksize
                    t = np.linspace(0, 1, frames, endpoint=False, dtype=np.float32)
                    chunk = 0.1 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
                    # callback signature: indata, frames, time, status
                    self.callback(chunk.reshape(-1, 1), frames, None, None)
                    time.sleep(0.01)
            self._thread = threading.Thread(target=run_cb)
            self._thread.start()
            return self

        def __exit__(self, exc_type, exc, tb):
            self._running = False
            self._thread.join()

    # Patch sounddevice.InputStream to return our FakeInputStream
    with patch('audio_recorder.sd.InputStream', new=FakeInputStream):
        thread = AudioRecorderThread(str(out), sample_rate=sample_rate, channels=channels)
        # Run the QThread.run method directly (no Qt event loop) for the test
        thread.is_recording = True
        # Run in a separate thread to mimic start/stop
        t = threading.Thread(target=thread.run)
        t.start()

        # Let the fake callbacks run
        time.sleep(0.2)

        # Stop recording
        thread.stop_recording()
        t.join()

    # Validate output file exists and has expected properties
    assert os.path.exists(str(out))
    with wave.open(str(out), 'rb') as wf:
        assert wf.getnchannels() == channels
        assert wf.getframerate() == sample_rate
        # At least some frames were written
        assert wf.getnframes() > 0
