# Login & Feature Gating — Investigation Notes

Last updated: 2025-10-07

Purpose: document every concept, code location, config artifact, runtime flag, and test that is related to enabling features based on user login (Google OAuth). This is a single-source reference we can iterate from.

## Executive summary

- The repository already contains a complete, desktop-friendly Google OAuth flow implemented in `cloud/auth_manager.py`, a central feature-gating system in `cloud/feature_gate.py`, a Google Drive wrapper in `cloud/drive_manager.py`, and UI widgets in `cloud/cloud_ui.py` that use those modules.
- The feature gating rule today is intentionally simple: authenticated users are treated as PREMIUM and therefore granted cloud features; unauthenticated users are FREE. This is implemented in `FeatureGate.get_user_tier()`.
- The codebase uses defensive checks and lazy imports so the app and tests run without the Google API packages installed. Unit tests cover auth manager, feature gate, decorator behavior, and drive manager guards.

## Key files & responsibilities

- `cloud/auth_manager.py`
  - Responsibilities: OAuth flow (desktop loopback), token storage, credential refresh, building Google API clients.
  - Public API and notable behaviors:
    - `is_authenticated() -> bool` — quick check of credential validity.
    - `get_credentials() -> Optional[Credentials]` — returns credentials only when authenticated.
    - `get_user_info() -> Optional[dict]` — queries Google OAuth2 userinfo when available.
    - `authenticate(timeout_seconds=180) -> bool` — runs loopback auth flow (opens browser), waits for callback, stores tokens.
    - `logout() -> bool` — removes stored token file and clears in-memory credentials.
    - `build_service(api, version)` — helper to construct Google API clients; raises when not authenticated or libs missing.
  - Important runtime flag: `GOOGLE_APIS_AVAILABLE` — a module-level boolean set by checking for required Google packages. When False, cloud features are disabled gracefully.
  - Token file: `cloud/credentials/token.json` (written with best-effort restricted permissions).

- `cloud/feature_gate.py`
  - Responsibilities: centralize which features are available per tier and provide user-facing restriction messages.
  - Public API:
    - `get_user_tier()` — currently returns PREMIUM for any authenticated user.
    - `is_feature_enabled(feature_name)`
    - `get_feature_value(feature_name, default)`
    - `get_restriction_message(feature_name)` — human-friendly messages used by UI.
    - `can_upload_to_cloud()` — convenience that requires both auth and the `cloud_upload` feature.
    - `FeatureDecorator.requires_feature(...)` — decorator to guard functions and optionally surface messages.

- `cloud/drive_manager.py`
  - Responsibilities: all Drive operations (upload, list, download, delete, storage info).
  - Defensive checks: `_get_service()` validates `auth_manager.is_authenticated()` and `GOOGLE_APIS_AVAILABLE` before creating a client.
  - Behavior on failures: methods generally return `None`/`False` and log errors rather than throwing wide-ranging exceptions; this keeps the UI simple but makes deterministic error handling harder.

- `cloud/cloud_ui.py`
  - UI widgets that drive the sign-in flow and present cloud features:
    - `CloudAuthWidget` — shows auth state, user info, and Sign In / Sign Out actions.
    - `CloudUploadWidget` — file selection UI and starts `GoogleDriveManager.upload_recording` via a background `CloudUploadThread`.
    - `CloudUI` — container that shows/hides upload widget and a preview/upgrade panel for unauthenticated users.
  - UI behavior: widgets call `auth_manager.authenticate()` and `logout()` directly and consult `FeatureGate` before allowing upload actions.

- `src/enhanced_editor.py`
  - Integrates cloud modules conditionally using an `_cloud_available` guard (imports wrapped in try/except). If cloud modules or Google packages are missing, the editor still runs and shows a hint about enabling cloud features.

## Configuration and repository policies

- Client secret file: `config/client_secrets.json` — required for OAuth client config (download from Google Cloud). The repo explicitly ignores this file in `.gitignore` and CI checks ensure it isn't committed.
- Token storage: `cloud/credentials/token.json` — tokens are saved here and the folder is gitignored; CI also checks for accidental commits of token.json.
- CI/workflows: `.github/workflows/ci-cd.yml` contains checks that reject committed `client_secrets.json` or `token.json`, and includes a test stub for client_secrets during CI.


## Minimal contract (for feature-gated actions)

- Inputs: app state, action (e.g., upload), payload (file path / metadata), feature name.
- Preconditions: feature is enabled for user tier and user is authenticated with valid credentials.
- Outputs: success result (e.g., Drive file ID) or a deterministic error/result indicating why the action did not run.
- Error modes to expose distinctly:
  - NotAuthenticated (no credentials)
  - APILibrariesMissing (GOOGLE_APIS_AVAILABLE == False)
  - TokenExpiredButRefreshFailed
  - FeatureNotAllowed (user tier doesn't allow feature)
  - Input errors (file not found, invalid metadata)
  - Transient network errors / API errors

Design goal: UI code should not need to inspect internals — service layer should raise typed exceptions or return well-known sentinel results that the UI maps to messages/prompts.

## Observed strengths

- Clear separation of concerns: auth, gate, service, and UI are cleanly separated.
- Defensive checks: service layer and UI both validate `is_authenticated()` and `GOOGLE_APIS_AVAILABLE`.
- Testability: lazy imports and many unit tests allow running tests without Google libraries or live credentials.

## Where gating checks currently occur (scan results)

I scanned the repo for auth and gating usage. These locations are the authoritative places to inspect/modify when changing gating behavior:

- Authentication manager and flags
  - `cloud/auth_manager.py` — `is_authenticated`, `authenticate`, `logout`, `get_user_info`, `build_service`, `GOOGLE_APIS_AVAILABLE`.

- Feature gate
  - `cloud/feature_gate.py` — `get_user_tier`, `is_feature_enabled`, `get_restriction_message`, `can_upload_to_cloud`, `FeatureDecorator`.

- Drive service
  - `cloud/drive_manager.py` — `_get_service()` guards, and all high-level methods call `_get_service()`.

- UI surfaces
  - `cloud/cloud_ui.py` — `CloudAuthWidget`, `CloudUploadWidget`, `CloudUI` consult auth state and feature gate; Upload widget checks `feature_gate.can_upload_to_cloud()` before starting an upload.
  - `src/enhanced_editor.py` — conditional integration and wiring of `FeatureGate` and `CloudUI`.

- Tests referencing auth/feature
  - `tests/test_auth_manager*.py`, `tests/test_feature_gate.py`, `tests/test_feature_decorator.py`, `tests/test_drive_manager_*.py`.

- Config & CI
  - `.github/workflows/ci-cd.yml` — CI checks related to `client_secrets.json` and `token.json`.
  - `config/client_secrets.json` (developer-provided)
  - `cloud/credentials/token.json` (runtime token storage)

## Missing or partial concepts discovered by scan

- Subscription validation: no server-side subscription verification exists. `get_user_tier()` uses only `is_authenticated()`.
- Deferred actions: UI does not resume attempted actions automatically after sign-in. `CloudUploadWidget` prevents upload when not authenticated and shows a message; it does not queue intent and resume after `authenticate()`.
- Typed exceptions: module code uses `RuntimeError`, `None`/`False` results, and logged errors. There's no common set of typed exceptions (e.g., `NotAuthenticatedError`) used across modules.
- Refresh locking: `_refresh_if_needed()` performs refresh without an explicit cross-thread lock; concurrent calls in multithreaded contexts could race.

## Security & privacy notes

- Token storage: `token.json` is saved under `cloud/credentials/` and the code attempts to restrict file permissions on POSIX. On Windows, it uses best-effort handle closing but does not manipulate ACLs.
- Recommendation: consider OS-provided secure storage (keyring / Credential Manager / Keychain) for long-term protection of refresh tokens on desktop platforms.

## CI safeguards

- `.gitignore` and CI workflow actively prevent committing `client_secrets.json` and `token.json`. The README and setup scripts instruct developers to place `client_secrets.json` into `config/` locally; CI injects a minimal test client_secrets during runs when needed.

## Prioritized next actions (more detailed)

1. Short (low-risk)
   - Add `cloud/exceptions.py` and define typed exceptions: `NotAuthenticatedError`, `FeatureNotAllowedError`, `APILibrariesMissingError`, `UploadError`.
   - Update `_get_service()` to raise `NotAuthenticatedError` instead of `RuntimeError` and update UI to catch it and trigger auth flow.

2. Medium (UI/UX)
   - Implement a deferred-action pattern in `CloudUploadWidget`:
     - If user attempts to upload while unauthenticated, store the upload parameters, call `authenticate()` (non-blocking), and on success resume upload automatically.
   - Add an optional confirmation toggle (ask to resume previous action) to respect user intent/privacy.

3. Medium (robustness)
   - Add a simple refresh-locking mechanism in `auth_manager` (threading.Lock) to serialize refresh attempts and avoid concurrent refresh races.
   - Convert drive manager error returns into exceptions for clearer handling; add try/except wrappers at UI boundary to present messages.

4. Long-term
   - Integrate subscription checks (if paid tiers exist) — requires back-end or third-party billing integration and a place to store user subscription state.
   - Consider keyring integration for token storage (windows credential manager, macOS keychain)

## Suggested tests to add (concrete)

- Test: when `GoogleDriveManager._get_service()` is called while `auth_manager.is_authenticated()` is False, it raises `NotAuthenticatedError` and UI handles it by prompting sign-in (mock auth_manager.authenticate()
- Test: `CloudUploadWidget` deferred upload flow — mock `auth_manager.authenticate()` (simulate success) and ensure upload thread is started with original parameters.
- Test: concurrent refresh attempts are serialized — simulate expired credentials and spawn two callers that trigger `_refresh_if_needed()` and verify only one refresh happens.

## How I verified the above

- Performed code scans for the following symbols and files: `authenticate`, `logout`, `is_authenticated`, `get_user_info`, `build_service`, `GOOGLE_APIS_AVAILABLE`, `client_secrets.json`, `token.json`, `FeatureGate`, `FeatureDecorator`, `CloudUploadWidget`, `GoogleDriveManager`.
- Opened and reviewed the relevant modules: `cloud/auth_manager.py`, `cloud/feature_gate.py`, `cloud/drive_manager.py`, `cloud/cloud_ui.py`, and `src/enhanced_editor.py`.
- Searched tests to confirm existing coverage and to identify tests to extend.

## Next step — pick one

Tell me which prioritized item above you want implemented first. I suggest starting with the small, low-risk change: add typed exceptions and update `_get_service()` + UI handling so we have a clearer contract to build on. If you confirm, I'll implement the change, update tests, and run the relevant tests.

---

If you'd like, I can also tidy the markdown formatting to satisfy repository lint rules (I kept a soft style for readability). If you prefer the file moved under `docs/architecture/` or a different name, tell me and I'll move it.


## Gaps and recommended improvements (prioritized)

1. Tier / subscription resolution
   - Right now, any authenticated user becomes PREMIUM. If you plan paid tiers, add a subscription lookup (server-side or via user metadata).

2. Deferred actions UX (medium effort, high UX value)
   - If a user clicks a gated action (Upload) while not signed in, prompt for auth and automatically resume the action when sign-in succeeds.

3. Typed exceptions & error handling (low effort)
   - Introduce a small set of typed exceptions (e.g., `NotAuthenticatedError`, `FeatureNotAllowedError`, `UploadError`) so callers can handle cases deterministically.

4. Concurrency / refresh locking (low–medium)
   - Prevent multiple concurrent refresh attempts if credentials are expired; add a refresh lock/serialization.

5. Better Windows token storage guidance (doc)
   - Current code uses best-effort permission restriction on Windows. Consider documenting this clearly or integrating OS keyring storage.

6. Apply decorator in app code (low)
   - The `FeatureDecorator` currently is used in tests. Apply it to key action handlers to centralize gating and messaging.

## Small implementation suggestions

- Add `exceptions.py` in `cloud/` with:
  - `class NotAuthenticatedError(RuntimeError): ...`
  - `class FeatureNotAllowedError(RuntimeError): ...`

- Replace broad `RuntimeError` in `_get_service()` with `NotAuthenticatedError` and adjust UI handlers to catch it and surface a login prompt.

- Implement a tiny deferred-action queue in `CloudUploadWidget.start_upload()`:
  - If not authenticated, store the intended upload payload and launch `auth_manager.authenticate()`.
  - On auth success, automatically call the stored upload function.

## Tests to add / update

- Unit test: deferred upload attempts when unauthenticated should trigger auth flow and resume upload on success (mock `authenticate()` to return True and verify upload called).
- Unit test: `NotAuthenticatedError` raised by `GoogleDriveManager._get_service()` and caught by UI
- Integration test: UI shows unlock/upgrade messages when `FeatureGate` reports feature disabled.

## Quick commands to run relevant tests locally

Run the subset of tests that already exist for auth/feature modules (from project root):

```pwsh
# Activate your venv and run tests
.\n+\venv\Scripts\Activate.ps1
pytest tests/test_auth_manager_pytest.py::test_build_service_basic -q
pytest tests/test_feature_gate.py -q
pytest tests/test_feature_decorator.py -q
```

Adjust paths/venv activation to match your environment.

## Proposed next work items (pick one or more)

1. Add typed exceptions and update `drive_manager._get_service()` to raise `NotAuthenticatedError`.
2. Implement deferred-action resume flow in `CloudUploadWidget` (UI + tests).
3. Apply `FeatureDecorator` on a couple of high-level UI handlers for consistency.
4. Add refresh-locking around credential refresh in `auth_manager._refresh_if_needed()`.

Tell me which item(s) you'd like me to implement and I'll make a focused change with tests and run the relevant test subset.

---

Notes
- I created this file automatically from a short repository scan. If you want a different filename or to move this to another folder (e.g., `docs/architecture/`), tell me and I will move it.
