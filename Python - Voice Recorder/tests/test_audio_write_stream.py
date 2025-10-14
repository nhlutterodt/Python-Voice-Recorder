import wave

import numpy as np
from audio_recorder import AudioRecorderThread


def test_write_wave_from_float32_chunks(tmp_path):
    out = tmp_path / "out.wav"
    sample_rate = 8000
    channels = 1

    # Create three chunks of 0.1s each
    chunk_duration = 0.1
    frames = int(chunk_duration * sample_rate)

    chunks = []
    for i in range(3):
        # simple ramp signal
        t = np.linspace(0, 1, frames, endpoint=False, dtype=np.float32)
        chunk = 0.2 * (i + 1) * np.sin(2 * np.pi * 440 * t).astype(np.float32)
        chunks.append(chunk)

    duration = AudioRecorderThread.write_wave_from_float32_chunks(
        str(out), chunks, sample_rate, channels
    )

    # duration should be approximately 0.3s
    assert abs(duration - 3 * chunk_duration) < 1e-3

    # Check file exists and header matches
    assert out.exists()
    with wave.open(str(out), "rb") as wf:
        assert wf.getnchannels() == channels
        assert wf.getframerate() == sample_rate
        frames_written = wf.getnframes()
        assert frames_written == int(sample_rate * duration)
