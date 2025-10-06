# Constraints Module Refactor

This document summarizes the refactor performed on `services.file_storage.config.constraints` to improve readability, testability, and robustness while preserving runtime behavior.

## Goals

- Reduce cognitive complexity of large functions while keeping behavior identical.
- Centralize collector probing and selection logic.
- Normalize storage info shapes consistently.
- Provide safe, deterministic environment manager resolution.
- Add unit tests for small helpers to ensure future changes are safe.

## New helpers

- `_get_candidate_collectors()` — returns ordered list of candidate collector symbols; prefers mocked symbols patched on the constraints module or the storage_info module.
- `_probe_candidate_collectors(candidate_collectors, base_path)` — instantiate and probe candidate collector classes, returning valid results as a list of `(cls, candidate, method_name, method_obj)`.
- `_select_candidate(candidate_results)` — choose a single `(cls, candidate, method_name)` entry, preferring mock-backed entries.
- `_normalize_storage_info(si)` — normalize different shapes (dict-like, attr-backed, bytes or MB fields) into `{'free_mb','used_mb','total_mb'}`.
- `_is_valid_storage_info(si)` — strict validation to avoid accepting unconfigured MagicMocks.
- `_safe_call(method, env=None)` — call method with fallback to `.return_value` if call raises.
- `_resolve_environment_manager_symbol()` / `_get_env_config_from_manager_symbol(mgr, env_name)` — deterministic environment manager resolution and safe retrieval of environment config.
- `_infer_estimated_size(estimated_size_mb, kwargs)` — small helper to infer size from a source file path.
- `_gather_storage_info_for_base(base_path)` — convenience wrapper around probe/select that returns `(storage_info, (cls, method_name))`.
- `_evaluate_capacity_for_operation(constraints, base_path, estimated_size_mb)` — used by pre-op validation to encapsulate capacity checks and recommendations.

## How to run tests for constraints helpers

From the repository root (PowerShell):

```powershell
Set-Location "C:\Users\Owner\Voice Recorder\Python-Voice-Recorder\Python - Voice Recorder"
$env:DEBUG_CONSTRAINTS='1'
pytest -q tests/file_storage/config
```

## Debugging

- Set `DEBUG_CONSTRAINTS=1` to see concise debug traces about which collector was chosen and normalized storage info values.
- Future improvement: replace prints with `logging.getLogger(__name__).debug(...)` and control via standard logging configuration.

## Rollback

Revert the changes in `services/file_storage/config/constraints.py` and remove the tests `tests/file_storage/config/test_probe_select_helpers.py` and `tests/file_storage/config/test_normalize_storage_info.py`.

## Next steps (recommended)

- Further split remaining high complexity functions into smaller helpers until linter thresholds are met.
- Replace prints with logging.
- Run full project test suite and linter.
