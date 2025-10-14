import sys
sys.path.insert(0, r"C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder\src")
sys.path.insert(0, r"C:\Users\Owner\Voice Recorder\Python-Voice-Recorder")
try:
    import voice_recorder.scripts.run_alembic_upgrade as mod
    print('import ok: voice_recorder.scripts.run_alembic_upgrade')
except Exception as e:
    print('import FAILED:', e)
    raise
