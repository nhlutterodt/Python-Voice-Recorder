# Login & Feature Gating — Investigation Notes

Last updated: 2025-10-07

Purpose: document concepts, code locations, config artifacts, runtime flags, and tests related to enabling features based on user login (Google OAuth). This file is a single-source reference we can iterate from.

## Executive summary

- The repository contains a desktop-friendly Google OAuth flow (`cloud/auth_manager.py`), a central feature-gating system (`cloud/feature_gate.py`), a Google Drive wrapper (`cloud/drive_manager.py`), and UI widgets (`cloud/cloud_ui.py`).
- The feature gating rule is simple today: authenticated users are treated as PREMIUM and therefore granted cloud features; unauthenticated users are FREE (see `FeatureGate.get_user_tier()`).
- The codebase uses defensive checks and lazy imports so the app and tests run without the Google API packages installed.
- Status update: a small, low-risk robustness change was implemented (typed exceptions at the service boundary and proactive UI handling). The full test suite was executed and is currently passing.

## Key files & responsibilities

- `cloud/auth_manager.py`
  - Responsibilities: OAuth loopback flow, token storage, credential refresh, and building Google API clients.
  - Public API (high level): `is_authenticated()`, `get_credentials()`, `get_user_info()`, `authenticate()`, `logout()`, `build_service()`.

- `cloud/feature_gate.py`
  - Responsibilities: centralize which features are available per tier and provide user-facing restriction messages.
  - Public API: `get_user_tier()`, `is_feature_enabled()`, `get_feature_value()`, `get_restriction_message()`, `can_upload_to_cloud()`, `FeatureDecorator`.

- `cloud/drive_manager.py`
  - Responsibilities: Drive operations (upload, list, download, delete, storage info).
  - Defensive checks: `_get_service()` validates `auth_manager.is_authenticated()` and `GOOGLE_APIS_AVAILABLE`.
  - Recent change: `_get_service()` now raises typed exceptions for auth/library issues; higher-level methods preserve backward-compatible sentinel returns (None/False).

- `cloud/cloud_ui.py`
  - Responsibilities: UI widgets that expose sign-in, sign-out, and cloud actions.
  - Recent change: upload flow was updated to catch `NotAuthenticatedError`, prompt the user to authenticate, and resume the upload automatically on successful sign-in (basic resume implementation).

- Token file: `cloud/credentials/token.json` (runtime storage — gitignored). Client secrets: `config/client_secrets.json` (developer-provided, ignored in repo).

## Minimal contract (for feature-gated actions)

- Inputs: app state, action (e.g., upload), payload (file path / metadata), feature name.
- Preconditions: feature is enabled for the user tier and user has valid credentials.
- Outputs: success result (e.g., Drive file ID) or a deterministic error/result describing why the action did not run.

Error modes to expose distinctly:

- NotAuthenticated (no credentials)
- APILibrariesMissing (GOOGLE_APIS_AVAILABLE == False)
- TokenExpiredButRefreshFailed
- FeatureNotAllowed (user tier doesn't allow feature)
- Input errors (file not found, invalid metadata)
- Transient network/API errors

Design goal: UI code should not need to parse generic error messages — service layers raise typed exceptions or return well-known sentinel values that UI maps to messages/prompts.

## Observed strengths

- Clear separation of concerns: auth, gate, service, and UI are cleanly separated.
- Defensive checks: both service layer and UI validate `is_authenticated()` and `GOOGLE_APIS_AVAILABLE`.
- Testability: lazy imports and many unit tests allow running tests without Google libraries or live credentials.

## Where gating checks occur (authoritative list)

- `cloud/auth_manager.py` — `is_authenticated`, `authenticate`, `logout`, `get_user_info`, `build_service`, `GOOGLE_APIS_AVAILABLE`.
- `cloud/feature_gate.py` — `get_user_tier`, `is_feature_enabled`, `get_restriction_message`, `can_upload_to_cloud`, `FeatureDecorator`.
- `cloud/drive_manager.py` — `_get_service()` guards and high-level helpers.
- `cloud/cloud_ui.py` and `src/enhanced_editor.py` — UI wiring and conditional cloud integration.
- Tests referencing auth/feature: `tests/test_auth_manager*.py`, `tests/test_feature_gate.py`, `tests/test_feature_decorator.py`, `tests/test_drive_manager_*.py`.

## Changes implemented in this pass

- Added `cloud/exceptions.py` with typed exceptions used across cloud modules:
  - `NotAuthenticatedError`, `APILibrariesMissingError`, `FeatureNotAllowedError`, `UploadError`.
- `cloud/drive_manager.py` — `_get_service()` updated to raise `NotAuthenticatedError` / `APILibrariesMissingError` instead of generic RuntimeError.
- `cloud/auth_manager.py` — `build_service()` updated to raise typed exceptions on auth/library problems.
- `cloud/cloud_ui.py` — upload flow updated to prompt for auth on `NotAuthenticatedError` and resume the upload after successful authentication (basic resume implemented).
- Tests updated to use the new typed exceptions where applicable.
- Full test suite run: all tests passed after changes.

## Missing or partial concepts still to address

- Subscription validation: `get_user_tier()` uses only `is_authenticated()`; if paid tiers are required, add server-side subscription checks or user metadata.
- Refresh locking: `_refresh_if_needed()` should serialize refresh attempts (add a threading.Lock) to avoid races in multithreaded contexts.
- Deferred-action UX: current resume flow is basic — consider adding a user confirmation toggle and queueing for multiple pending intents.

## Prioritized next actions

1) Short (low-risk) — (done)
   - Typed exceptions and `_get_service()` change (done).

2) Medium (UI/UX)
   - Improve deferred-action resume (confirmation, queueing multiple intents).

3) Medium (robustness)
   - Add refresh-locking to `auth_manager`.
   - Consider converting more drive-manager internals to raise typed exceptions instead of returning sentinels.

4) Long-term
   - Integrate subscription checks if paid tiers are required.
   - Consider keyring integration for token storage.

## Suggested tests to add or extend

- Test: `GoogleDriveManager._get_service()` raises `NotAuthenticatedError` when unauthenticated (covered/updated in drive-manager tests).
- Test: `CloudUploadWidget` deferred upload flow — mock `auth_manager.authenticate()` to simulate success and verify the upload resumes with the original parameters.
- Test: concurrent refresh attempts are serialized — add a test after adding refresh-locking.

## How I verified the change

- Updated code and tests locally.
- Ran the full pytest suite from the project root with PYTHONPATH set; all tests passed.

## Quick commands (examples)

```pwsh
# From project root (example)
.\venv\Scripts\Activate.ps1
pytest -q tests/test_auth_manager_pytest.py
pytest -q tests/test_drive_manager_not_authenticated.py
```

## Next step

Tell me which prioritized item you want me to implement next (I recommend adding refresh-locking next, then further improving the deferred-action UX). I can implement any of the items above, update tests, and run the relevant test subset.
