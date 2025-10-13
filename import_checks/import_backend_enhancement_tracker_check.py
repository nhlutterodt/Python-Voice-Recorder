import sys
sys.path.insert(0, r"C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder\src")
sys.path.insert(0, r"C:\Users\Owner\Voice Recorder\Python-Voice-Recorder")
try:
    from voice_recorder.scripts.utilities.backend_enhancement_tracker import get_logger
    print('import ok: voice_recorder.scripts.utilities.backend_enhancement_tracker')
except Exception as e:
    print('import FAILED:', e)
    raise
