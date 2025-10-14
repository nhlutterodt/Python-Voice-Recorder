"""Local package shim for development.

This file makes `voice_recorder` importable in-place by adding the project's
`src/` directory to the package's __path__. That mirrors the installed layout
used during packaging and lets `from voice_recorder.foo import ...` work while
running the code directly from the repo.

This is intentionally minimal and safe for development/CI. Remove once the
project is installed into the environment (or replace with an editable install).
"""
from pathlib import Path
import sys

# Calculate the sibling `src/` directory relative to this file (project root/ src)
_pkg_dir = Path(__file__).resolve().parent
_project_root = str(_pkg_dir.parent.resolve())
_src_dir = str((_pkg_dir.parent / "src").resolve())

# Prepend src first so package modules in src/ take precedence
if _src_dir not in __path__:
    __path__.insert(0, _src_dir)

# Also allow subpackages located at the project root (e.g., core/, models/)
if _project_root not in __path__:
    __path__.insert(1, _project_root)

# Expose a small helper for debugging
__all__ = []
