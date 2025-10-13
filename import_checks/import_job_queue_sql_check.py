import sys, traceback
sys.path[:0]=[r"c:\Users\Owner\Voice Recorder\Python-Voice-Recorder", r"c:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder\src"]
try:
    import voice_recorder.cloud.job_queue_sql as m
    print('import ok:', m.__name__)
except Exception:
    traceback.print_exc()
    raise
