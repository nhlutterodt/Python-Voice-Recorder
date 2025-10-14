# Import-check helper for voice_recorder.audio_recorder
import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[1]
src_root = repo_root / 'Python - Voice Recorder' / 'src'
sys.path[:0] = [str(src_root), str(repo_root)]
try:
    import importlib
    importlib.import_module('voice_recorder.audio_recorder')
    print('import ok: voice_recorder.audio_recorder')
except Exception as e:
    print('import failed:', e)
    raise
