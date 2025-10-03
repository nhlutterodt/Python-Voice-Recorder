"""Compatibility shim for build_voice_recorder_pro used in tests.

This provides a minimal VoiceRecorderBuilder with the small helper
methods the tests expect. It is intentionally lightweight and
does not perform actual build operations.
"""
from __future__ import annotations

import shutil
import builtins
from typing import Dict, List, Tuple


class VoiceRecorderBuilder:
    """Minimal builder shim exposing helper methods used by tests."""

    def __init__(self):
        # Detect UPX availability
        try:
            self.upx_available = bool(shutil.which("upx"))
        except Exception:
            self.upx_available = False

    def _check_package_import(self, name: str, package_name: str) -> Tuple[bool, bool]:
        """Attempt to import a package and detect pydub/audioop special-case.

        Uses builtins.__import__ directly so tests that patch __import__ are effective.
        """
        try:
            builtins.__import__(package_name)
            return True, False
        except ImportError as e:
            msg = str(e)
            return False, "audioop" in msg

    def _check_package_group(self, packages: Dict[str, str], group_name: str, ok_symbol: str, fail_symbol: str) -> List[str]:
        missing = []
        for key, pkg in packages.items():
            success, _ = self._check_package_import(key, pkg)
            if success:
                print(f"   {ok_symbol} {key} ({group_name})")
            else:
                print(f"   {fail_symbol} {key} ({group_name})")
                missing.append(key)
        return missing

    def _report_missing_packages(self, required: List[str], optional_cloud: List[str], build_only: List[str]) -> bool:
        if required:
            print(f"\n❌ Missing required packages: {', '.join(required)}")
            print(f"Install with: pip install {' '.join(required)}")
            return False
        if build_only:
            print(f"\n⚠️ Missing build packages: {', '.join(build_only)}")
            print("EXE creation will be disabled")
        if optional_cloud:
            print(f"\n⚠️ Missing cloud packages: {', '.join(optional_cloud)}")
            print("Cloud features will be disabled in the build")
        return True

    def check_dependencies(self) -> bool:
        # Minimal behavior: return True if no required packages missing
        required = {"json": "json"}
        missing = self._check_package_group(required, "required", "✅", "❌")
        return self._report_missing_packages(missing, [], [])


if __name__ == "__main__":
    builder = VoiceRecorderBuilder()
    print("UPX available:" , builder.upx_available)
    builder.check_dependencies()
