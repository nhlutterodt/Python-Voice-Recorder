"""voice_recorder.cloud shim package

This shim makes `voice_recorder.cloud.*` imports resolve to the existing
`Python - Voice Recorder/src/cloud` directory during local development.
"""
from __future__ import annotations

from pathlib import Path
import os

# Locate the repository root (two levels up from this file)
_root = Path(__file__).parent.parent.parent
_src_cloud = _root / "Python - Voice Recorder" / "src" / "cloud"
if _src_cloud.exists():
    __path__.insert(0, str(_src_cloud))

__all__ = []
