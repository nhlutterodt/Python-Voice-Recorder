import wave
from pathlib import Path

import uuid

def make_sine_wav(path: Path, duration_s: float = 0.5, sample_rate: int = 22050):
    import math
    import struct

    n_frames = int(duration_s * sample_rate)
    amplitude = 16000
    freq = 440.0

    with wave.open(str(path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(n_frames):
            t = i / sample_rate
            v = int(amplitude * math.sin(2 * math.pi * freq * t))
            wf.writeframes(struct.pack('<h', v))


def test_recording_service_ingest(tmp_path, tmp_db_context, recordings_dir):
    # Create a small temporary recordings directory and WAV (use unique name)
    rec_dir = tmp_path / 'recordings' / 'raw'
    rec_dir.mkdir(parents=True)
    fname = f"test_headless_{uuid.uuid4().hex}.wav"
    wav_path = rec_dir / fname
    make_sine_wav(wav_path, duration_s=0.3, sample_rate=22050)

    # Use fixtures: tmp_db_context provides a DatabaseContextManager with tables created
    test_db_context = tmp_db_context

    # Use the recordings_dir fixture for where the service stores copied files
    store_dir = recordings_dir

    # Import the service and instantiate it with injected dependencies
    from services.recording_service import RecordingService
    svc = RecordingService(db_ctx=test_db_context, recordings_dir=store_dir)
    _rec = svc.create_from_file(str(wav_path), title='headless-test')

    # Verify DB row exists using a session from the tmp_db_context
    from sqlalchemy import text
    with test_db_context.get_session() as session:
        rows = session.execute(text('SELECT id, filename, stored_filename FROM recordings')).fetchall()
        assert len(rows) == 1
        assert rows[0][1] == fname
