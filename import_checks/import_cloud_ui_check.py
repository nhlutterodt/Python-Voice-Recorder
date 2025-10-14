import sys
import os

# Ensure repo root and src are on sys.path
sys.path[:0] = [r"c:\Users\Owner\Voice Recorder\Python-Voice-Recorder", r"c:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder\src"]

print('sys.path[0:2]=', sys.path[0:2])

try:
    import voice_recorder.cloud.cloud_ui as m
    print('import ok:', m.__name__)
except Exception as e:
    import traceback
    traceback.print_exc()
    raise
