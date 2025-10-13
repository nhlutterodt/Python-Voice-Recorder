"""Import-only check for legacy facade module services.enhanced_file_storage
This ensures the old import path continues to work and re-exports canonical components.
"""
import sys
import importlib
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
src_path = repo_root / 'Python - Voice Recorder' / 'src'
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(repo_root))

MODULE = 'services.enhanced_file_storage'

def main():
    try:
        importlib.import_module(MODULE)
        print(f"import ok: {MODULE}")
    except Exception:
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    main()
