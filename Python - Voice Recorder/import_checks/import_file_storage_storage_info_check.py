"""Import check for canonical file_storage.config.storage_info module"""
import sys
from importlib import import_module

repo_root = r"c:\Users\Owner\Voice Recorder\Python-Voice-Recorder"
src_path = repo_root + r"\Python - Voice Recorder"
if src_path not in sys.path:
    sys.path.insert(0, src_path)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

try:
    m = import_module('voice_recorder.services.file_storage.config.storage_info')
    print('import ok: voice_recorder.services.file_storage.config.storage_info')
except Exception:
    import traceback
    traceback.print_exc()
    print('import failed: voice_recorder.services.file_storage.config.storage_info')
    raise
