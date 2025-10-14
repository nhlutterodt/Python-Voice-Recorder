import sys
sys.path.insert(0, r"C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder\src")
sys.path.insert(0, r"C:\Users\Owner\Voice Recorder\Python-Voice-Recorder")
try:
    from voice_recorder.scripts.utilities.validate_implementation_completeness import main as _m
    print('import ok: voice_recorder.scripts.utilities.validate_implementation_completeness')
except Exception as e:
    print('import FAILED:', e)
    raise
