"""Import-only check for voice_recorder.services.file_storage.config package"""
import sys
import traceback
from pathlib import Path
repo_root = Path(r"c:\Users\Owner\Voice Recorder\Python-Voice-Recorder")
src_dir = repo_root / "Python - Voice Recorder" / "src"
for p in (repo_root, src_dir):
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

module_name = 'voice_recorder.services.file_storage.config'
try:
    import importlib
    importlib.invalidate_caches()
    importlib.import_module(module_name)
    print(f"import ok: {module_name}")
except Exception:
    print(f"import failed: {module_name}")
    traceback.print_exc()
    sys.exit(2)
