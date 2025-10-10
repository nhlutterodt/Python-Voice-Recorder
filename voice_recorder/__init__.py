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
