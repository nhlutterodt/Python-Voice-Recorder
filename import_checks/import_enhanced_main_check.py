# Import-check helper for voice_recorder.enhanced_main
import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parents[1]
src_root = repo_root / 'Python - Voice Recorder' / 'src'
# Add src and repo root to sys.path in the order expected by validation harness
sys.path[:0] = [str(src_root), str(repo_root)]
try:
    import importlib
    importlib.import_module('voice_recorder.enhanced_main')
    print('import ok: voice_recorder.enhanced_main')
except Exception as e:
    print('import failed:', e)
    raise
