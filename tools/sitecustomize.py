"""sitecustomize to run on Python startup during test runs.

It aliases legacy top-level package names (like `services`) to the canonical
package `voice_recorder.services` so tests that patch or import the old
top-level names continue to reference the same module objects when we run
with PYTHONPATH configured for the package layout.

This file is intentionally small and defensive: if voice_recorder isn't
importable yet, it silently skips aliasing.
"""
import sys

try:
    # Only enable the legacy-alias shim when explicitly requested via env var.
    # This prevents accidental inclusion in production or packaging.
    import os
    _enable_shim = os.environ.get('VOICE_RECORDER_TEST_SHIM', '').lower() in ('1', 'true', 'yes')
except Exception:
    _enable_shim = False

if _enable_shim:
    try:
        # import the canonical package and alias common legacy top-level names
        import voice_recorder.services as _vr_services
        # Only alias if not already defined or if it points somewhere else
        if 'services' not in sys.modules or sys.modules.get('services') is not _vr_services:
            sys.modules['services'] = _vr_services
            # Ensure package semantics (so submodule imports like 'services.file_storage' work)
            try:
                _vr_services.__path__
                sys.modules['services'].__path__ = _vr_services.__path__
            except Exception:
                # ignore if __path__ not present
                pass
    except Exception:
        # If anything fails (voice_recorder not importable), don't break startup
        pass

    # Map common legacy names to canonical modules so tests that import
    # 'services.file_storage...' get the same module objects and class identities.
    try:
        import sys
        # list of (legacy, canonical)
        aliases = [
            ('services.file_storage', 'voice_recorder.services.file_storage'),
            ('services.file_storage.config', 'voice_recorder.services.file_storage.config'),
            ('services.file_storage.config.environment', 'voice_recorder.services.file_storage.config.environment'),
            ('services.file_storage.config.storage_info', 'voice_recorder.services.file_storage.config.storage_info'),
            ('services.file_storage.config.constraints', 'voice_recorder.services.file_storage.config.constraints'),
            ('services.file_storage.exceptions', 'voice_recorder.services.file_storage.exceptions'),
        ]
        for legacy, canon in aliases:
            try:
                parts = canon.split('.')
                mod = __import__(canon, fromlist=[parts[-1]])
                if sys.modules.get(legacy) is not mod:
                    sys.modules[legacy] = mod
            except Exception:
                # don't fail startup if a canonical submodule isn't importable yet
                continue
    except Exception:
        pass
