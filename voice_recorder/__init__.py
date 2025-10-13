"""Package shim to make `voice_recorder` imports resolve to the existing
"Python - Voice Recorder/src" directory during local development and tests.

This file intentionally extends the package __path__ at runtime so code
that imports `voice_recorder.*` will find modules stored under the
project's src directory without requiring an editable install.
"""
from __future__ import annotations

import os
from pathlib import Path

# Compute the absolute path to the project's src directory, which is located
# under the sibling directory "Python - Voice Recorder/src" relative to the
# repository root. This works within the VS Code workspace layout used here.
_root = Path(__file__).parent.parent
# Add the project app directory (which contains the `cloud/` package and
# other modules) so imports like `voice_recorder.cloud.*` resolve to
# `Python - Voice Recorder/cloud/*` during local development.
_app_dir = _root / "Python - Voice Recorder"
if _app_dir.exists():
    __path__.insert(0, str(_app_dir))
# Also add the src directory so modules placed under src/ are discoverable
# as they would be after an editable install.
_src = _root / "Python - Voice Recorder" / "src"
if _src.exists():
    __path__.insert(0, str(_src))

__all__ = []

# Ensure common top-level modules are aliased to the package modules so the
# same module object is used whether code imports `config_manager` or
# `voice_recorder.config_manager`. This prevents duplicate-singleton issues
# during tests that import modules by different names.
try:
    import sys
    # Coalesce config_manager module objects so imports by either name refer
    # to the same module instance. Prefer the package-scoped module if it
    # exists (so voice_recorder.config_manager is authoritative).
    pkg_name = 'voice_recorder.config_manager'
    top_name = 'config_manager'
    pkg_mod = sys.modules.get(pkg_name)
    top_mod = sys.modules.get(top_name)
    if pkg_mod is not None:
        # Make top-level name point to package module (overwrite if necessary)
        sys.modules[top_name] = pkg_mod
    elif top_mod is not None:
        # Package module not loaded yet; ensure package name points to top-level module
        sys.modules[pkg_name] = top_mod
except Exception:
    # Don't fail package import for any reason here; best-effort aliasing only.
    pass
