#!/usr/bin/env python3
"""
Simple repository check to find legacy imports like
`from models import ...` or `import models.something`.

Exits with code 1 when any matches are found so CI can fail early.
Ignores common vendor/venv directories.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


DEFAULT_EXCLUDES = [
    ".git",
    "venv",
    "venv_test",
    "build",
    "dist",
    "__pycache__",
    "node_modules",
    "Python-Voice-Recorder/venv",
]


IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+models(?:\b|[.])")


def should_skip(path: Path, excludes: list[str]) -> bool:
    for ex in excludes:
        if ex and ex in path.parts:
            return True
    return False


def scan(root: Path, excludes: list[str]) -> list[tuple[Path, int, str]]:
    findings: list[tuple[Path, int, str]] = []
    for p in root.rglob("*.py"):
        if should_skip(p, excludes):
            continue
        try:
            text = p.read_text(encoding="utf8")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if IMPORT_RE.search(line):
                findings.append((p, i, line.strip()))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Check repo for legacy `models` imports")
    ap.add_argument("root", nargs="?", default=".", help="Repository root to scan")
    ap.add_argument("--exclude", "-e", action="append", default=[], help="Additional path parts to exclude")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    excludes = DEFAULT_EXCLUDES + args.exclude

    findings = scan(root, excludes)
    if not findings:
        print("No legacy `models` imports found.")
        return 0

    print("Found legacy `models` imports:")
    for p, lineno, line in findings:
        print(f"{p.relative_to(root)}:{lineno}: {line}")

    print(f"\nTotal: {len(findings)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
