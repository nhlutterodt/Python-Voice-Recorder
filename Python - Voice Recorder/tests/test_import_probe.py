import glob
import importlib
import importlib.util
import os
import sys
import traceback


def test_probe_enhanced_file_storage_import():
    """Probe which module is imported for services.enhanced_file_storage.

    Prints module.__file__, sys.path, importlib spec, and any matching files in the repo.
    This is a short, diagnostic test used only during local debugging.
    """
    name = "services.enhanced_file_storage"
    print("\n=== Import probe for:", name)
    try:
        mod = importlib.import_module(name)
        print("Imported module:", mod)
        print("module.__file__:", getattr(mod, "__file__", None))
        spec = importlib.util.find_spec(name)
        print("importlib.spec:", spec)
    except Exception as exc:
        print("Import failed:", type(exc).__name__, exc)
        traceback.print_exc()

        # List candidates in the workspace matching the filename to detect shadowing
        cwd = os.getcwd()
        print("cwd:", cwd)
        matches = glob.glob(
            os.path.join(cwd, "**", "enhanced_file_storage.py"), recursive=True
        )
        print("Found enhanced_file_storage.py matches:")
        for m in matches:
            print(" -", m)
        # Also show sys.path for debugging
        print("sys.path (first 20 entries):")
        for p in sys.path[:20]:
            print(" -", p)
        # Re-raise to make the failure visible to pytest
        raise
