import sys, traceback
sys.path[:0]=[r"c:\Users\Owner\Voice Recorder\Python-Voice-Recorder", r"c:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder\src"]
try:
    import importlib
    m = importlib.import_module('voice_recorder.scripts.smoke_record_test')
    print('import ok:', m.__name__)
except Exception:
    traceback.print_exc()
    raise
