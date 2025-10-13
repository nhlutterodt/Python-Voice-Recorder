import sys
import importlib
from pathlib import Path
repo_root = Path(r"c:\Users\Owner\Voice Recorder\Python-Voice-Recorder")
src_path = repo_root / "Python - Voice Recorder" / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(repo_root))
mod = 'voice_recorder.scripts.build.build_voice_recorder_pro'
try:
    importlib.import_module(mod)
    print(f"import ok: {mod}")
except Exception as e:
    import traceback
    traceback.print_exc()
    raise
