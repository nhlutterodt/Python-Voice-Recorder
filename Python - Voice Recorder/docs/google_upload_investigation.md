# Investigation: "Upload to Google" behavior

This document summarizes the current implementation, runtime behavior, failure modes, and recommended changes to improve the "Upload to Google" feature (Google Drive) in Voice Recorder Pro. The goal is to identify areas for abstraction, configurability, utility helpers, and effective orchestration so we can enhance reliability, testability, and expandability.

Files inspected
- `cloud/drive_manager.py` — main Google Drive upload/list/download/delete implementation.
- `cloud/auth_manager.py` — Google OAuth manager (credentials, keyring, token file, PKCE/loopback flow).
- `cloud/exceptions.py` — typed exceptions used by the cloud package (NotAuthenticatedError, APILibrariesMissingError, UploadError).
- `scripts/validate_google_oauth.py` — utility added earlier that validates client secrets and prints an auth URL (useful dev tool).

Executive summary of current behavior
- Upload entrypoint: `GoogleDriveManager.upload_recording(file_path, title=None, description=None, tags=None) -> Optional[str]`
  - Verifies file exists locally
  - Ensures user is authenticated (via `auth_manager.is_authenticated()`) and Google libraries are available
  - Ensures a recordings folder exists (searches by name, creates if missing)
  - Constructs metadata including `name`, `parents`, `description` and `properties` (source/upload_date/file_size/tags)
  - Uses `googleapiclient.http.MediaFileUpload(..., resumable=True)` and `service.files().create(..., media_body=media, fields='id, name, size, createdTime')`
  - Calls `request.next_chunk()` in a loop to drive the resumable upload and logs progress if status is returned
  - On success returns the Drive file ID (string)
  - On failures, catches broad exceptions and returns `None` (explicitly catches NotAuthenticatedError and APILibrariesMissingError to log and return None; all other Exceptions are also caught and logged and lead to returning None)

- Auth behavior: `GoogleAuthManager`
  - Lazy-loads client secrets from `config_manager` -> `VRP_CLIENT_SECRETS` env var -> `config/client_secrets.json`
  - OAuth: installed-app/loopback flow (127.0.0.1 ephemeral port) via `google_auth_oauthlib.flow.Flow`
  - On successful `authenticate()` stores credentials using either OS `keyring` (preferred) or a file `cloud/credentials/token.json` with best-effort file permission restriction and simple cross-process locking
  - Credential refresh is handled with `_refresh_if_needed()` guarded by a lock and event to avoid duplicate refreshes

- Error handling and library availability
  - Both auth and drive manager provide graceful degradation if Google API libs are missing (they detect availability with `importlib.util.find_spec` and raise/return friendly errors). The application logs this and disables cloud features.
  - `upload_recording()` intentionally returns `None` on failure to preserve backward compatibility with calling code expecting optional returns instead of exceptions.

Strengths observed
- Lazy imports for Google libraries: app can run without cloud libs installed and cloud features degrade gracefully.
- Resumable upload usage via `MediaFileUpload(..., resumable=True)` with chunked `request.next_chunk()` loop — good for large files and network glitches.
- Folder detection + create logic ensures uploaded files are grouped under a single folder.
- Metadata `properties` are used to surface searchability (source, upload_date, file_size, tags).
- Secure-ish credential storage with preference for OS keyring and fallback to token file with file locking and best-effort permission restriction.
- Concurrency-safety for credential refresh with an explicit lock and in-flight indicator.

Observed weaknesses and risks
1. Silent failure semantics
   - `upload_recording()` swallows all exceptions and returns `None`. This hides useful context from higher-level callers and makes error reporting, retries, and user-facing error messages harder to implement reliably.

2. Tight coupling to Google Drive SDK
   - The implementation directly builds `service = build('drive', 'v3', credentials=...)` and invokes Drive-specific methods. There's no small adapter/extractor surface to substitute a different backend or mock easily for integration tests.

3. Progress and cancellation API is internal-only
   - Progress is logged but not surfaced via callbacks/event hooks to UI code. There's no cancellation token to allow aborting a long upload from UI.

4. Retry behavior & backoff
   - The resumable upload handles chunking but the code doesn't implement an explicit retry/backoff strategy for `request.next_chunk()` exceptions (network failures, transient API 5xx). There is no bounded attempt count.

5. Idempotency & deduplication
   - If an upload is retried multiple times (or a file re-uploaded), the code will create duplicate files. No hashing, content-based dedupe, or idempotency keys are provided.

6. Metadata shape is ad-hoc
   - `properties` is a dict of stringified values (including upload_date and file_size). No canonical schema or validation is shared; this complicates searching/filtering and cross-feature reuse.

7. Tests & instrumentation
   - There are limited direct unit tests for error flows, large-upload behavior, or retry scenarios. The code relies on runtime Google SDK behaviours which complicates CI test coverage.

8. Blocking/synchronous design
   - All Drive operations are blocking in the UI thread if called directly. While the app uses a background process in the current session for the app itself, the drive manager does not present an async API or built-in worker queue.

9. Security / secrets lifecycle
   - The auth manager supports `VRP_CLIENT_SECRETS` and keyring but it's still easy for developers to accidentally place a `client_secrets.json` in the repo as we just addressed. CI patterns are not enforced in code; app expects client config in certain places and the override is env-var only.

Concrete improvement opportunities (design + prioritized plan)

0. High-level goals
- Make uploads: reliable, observable, cancellable, idempotent, testable, and pluggable.
- Avoid leaking implementation details in higher level code by introducing small, well-typed abstractions and fallbacks.

1. Introduce an uploader abstraction (priority: High)
- Create an interface / abstract class `cloud/uploader.py` with a minimal contract:
  - class UploadResult(TypedDict): file_id: str; name: str; size: int; created_time: str
  - class UploadProgress(TypedDict): uploaded_bytes: int; total_bytes: Optional[int]; percent: Optional[int]
  - class Uploader:
    - def upload(self, file_path: str, *, title: Optional[str], description: Optional[str], tags: Optional[List[str]], progress_callback: Optional[Callable[[UploadProgress], None]] = None, cancel_event: Optional[threading.Event] = None) -> UploadResult
    - def list(self, ...) -> List[...]
    - def download(...)
    - def delete(...)
- Implement the current Drive behavior as `GoogleDriveUploader(Uploader)` which adapts `GoogleDriveManager` internals. Keep the existing `GoogleDriveManager` for discovery, but introduce the adapter to present a clean surface.
- Benefits: easier to mock in tests, allows adding `DropboxUploader` or `LocalUploader` later, and keeps UI code decoupled.

2. Make failures explicit and typed (priority: High)
- Change `upload()` to raise typed exceptions from `cloud/exceptions.py` rather than returning `None` for all failures. Keep a compatibility adapter if needed (e.g., `legacy_upload_recording` wrapper that returns Optional[str]).
- Exceptions to raise: `NotAuthenticatedError`, `APILibrariesMissingError`, `UploadError` (with cause), `TransientNetworkError` (new) for retries.
- Benefits: callers can implement retries, show clear UI errors, log telemetry with failure reasons.

3. Retry/backoff + robust resumable handling (priority: High)
- Wrap the resumable chunk upload loop with a retry/backoff strategy (exponential backoff with jitter), bounded attempts (e.g., 5), and a clear transient-vs-permanent error classification.
- Detect specific http errors (429, 5xx) and treat as transient.
- On transient retry, re-initiate resumable upload if needed per Drive API recommendations.

4. Progress callbacks and cancellation (priority: High)
- Allow callers to pass a `progress_callback(progress: UploadProgress)` and a `cancel_event` (threading.Event) that is polled while uploading.
- When cancel_event is set, attempt to abort the resumable upload and return a clear cancellation exception or result.

5. Background upload orchestration & job queue (priority: Medium-High)
- Introduce a small background worker (thread pool or a lightweight queue) for uploads with persistent job state for resuming after app restart.
- Job model fields: local_path, desired_title, metadata, status (pending, running, succeeded, failed), retries, created_at, last_error, drive_file_id.
- Provide UI bindings to schedule an upload and observe job events via an event bus.

6. Idempotency and dedupe (priority: Medium)
- Create an optional content-hash-based dedupe: compute SHA256 of file (or hash of audio stream) and store it as `properties['content_sha256']`. When a file with same hash exists in the recordings folder, return existing file ID instead of creating duplicate.
- Alternatively add an `idempotency_key` property that callers can provide.

7. Metadata schema & searchability (priority: Medium)
- Define a `cloud/metadata_schema.py` module that documents the canonical keys stored in `properties` and their types (upload_date: iso8601, source, file_size:int, tags:list/string, content_sha256:string, app_version:string).
- Implement `metadata_builder` helper to validate and normalize metadata before uploading.

8. Testability: add unit & integration tests (priority: Medium)
- Unit tests: mock Google API responses using a small adapter that follows the `Uploader` interface. Test progress reporting, cancellation, retries, error propagation.
- Integration tests: a smoke test that runs only when Google libs & credentials available (CI flagged) to validate a real upload to a disposable Drive account. Use CI secrets for credentials.

9. Secrets & configuration management improvements (priority: Medium)
- Continue to prefer OS keyring for tokens and `VRP_CLIENT_SECRETS` for client config.
- Add docs and dev scripts (we already added `scripts/validate_google_oauth.py`) and a `Makefile` target for local setup.
- In CI, write the client JSON from secret store at job runtime (example job step in `.github/workflows/ci-cd.yml`) and ensure it is cleaned up after job.

10. Observability & telemetry (priority: Medium)
- Emit structured events on upload start/complete/failure with reason codes and durations to enable measuring reliability.
- Add metrics: upload success rate, average time, retry counts, cancellations.

11. UX: upload feedback and conflict resolution (priority: Medium)
- Surface progress indicators in the UI and allow user to cancel an upload in progress.
- After upload success, show link or open Drive folder; when duplicates are detected, offer "link to existing" vs "upload again".

12. Small refactors & utilities (priority: Low)
- Extract small helpers from `drive_manager.py`:
  - `_ensure_recordings_folder()` (already present) but expose as public `ensure_folder(name)` on Uploader adapter
  - `_build_metadata(...)` helper for unit-testing metadata shapes
  - `chunked_upload_with_progress()` utility that accepts a `create_request_fn` and returns a reusable routine for other APIs (e.g., GCS)

Suggested incremental implementation plan
- Sprint 1 (3–5 days):
  1. Add `cloud/uploader.py` interface + `GoogleDriveUploader` adapter that wraps current logic, present typed exceptions and progress callback support.
  2. Change UI wiring to call new adapter (keep `GoogleDriveManager` for compatibility but mark as deprecated).
  3. Add unit tests for upload success, failures, and progress callback using mocks.

- Sprint 2 (3–7 days):
  1. Add retry/backoff utility and apply it to the chunk upload loop.
  2. Add cancellation support and test it.
  3. Add metadata builder and content-hash dedupe opt-in.

- Sprint 3 (2–5 days):
  1. Add background job queue and persistence for upload jobs.
  2. UI integration: job list, progress, cancel, retry actions.
  3. Add telemetry and CI integration for a smoke upload test.

Developer API contract (short)
- Uploader.upload(file_path, *, title, description, tags, progress_callback, cancel_event) -> UploadResult
  - Inputs: local path (must exist), optional metadata
  - Outputs: UploadResult with file_id, name, size, created_time or raises typed exceptions
  - Progress: progress_callback called with {uploaded_bytes, total_bytes, percent}
  - Errors: NotAuthenticatedError, APILibrariesMissingError, UploadError, TransientNetworkError, OperationCancelled

Edge cases & tests to include
- File missing on disk
- Not authenticated
- Google libs not installed (simulate by patching find_spec)
- Token expired during upload -> refresh race (concurrent uploads) - ensure single refresh done
- Network interruption mid-chunk and resumed upload
- Upload cancellation from UI
- Re-upload of same file (duplicate detection)
- Large files (>> memory) to ensure streaming and chunking

Migration notes & compatibility
- Keep a compatibility shim `drive_manager.upload_recording_legacy(...)` that keeps the current `Optional[str]` return shape while new callers use the typed `Uploader` interface and exceptions. This avoids breaking code paths while allowing refactor.

Security checklist
- Continue to ignore local `config/client_secrets.json` in `.gitignore` and recommend local placement in a secured folder (we put `C:\Users\Owner\secrets` in current environment).
- Rotate OAuth client secret if it was exposed in repo history; run a git-history scan to confirm.
- For CI: fetch client secrets from the secret store and write to a temporary path at job runtime; do not commit credentials.

Appendix: quick example of the proposed adapter interface (conceptual)
```python
# cloud/uploader.py (concept)
from typing import Optional, Callable, TypedDict

class UploadProgress(TypedDict):
    uploaded_bytes: int
    total_bytes: Optional[int]
    percent: Optional[int]

class UploadResult(TypedDict):
    file_id: str
    name: str
    size: int
    created_time: str

class Uploader:
    def upload(self, file_path: str, *, title: Optional[str]=None, description: Optional[str]=None,
               tags: Optional[list[str]]=None, progress_callback: Optional[Callable[[UploadProgress], None]]=None,
               cancel_event: Optional[threading.Event]=None) -> UploadResult:
        raise NotImplementedError
```

Closing summary (context: enhance feature via abstraction, configurability and orchestration)

- Abstraction: Introduce a small `Uploader` interface and implement `GoogleDriveUploader`/adapter. This makes the upload surface testable and pluggable for other backends without changing UI wiring.

- Configurability: Move hard-coded behaviors (folder name, chunk sizes, retry policy, dedupe enabled/disabled, metadata schema) into a small `UploadConfig` structure (readable from `config_manager` or env vars). Allow per-upload overrides.

- Utilities: Extract reusable building blocks — metadata builder, chunked upload + progress & cancel utility, retry/backoff helper, content hashing helper — so logic is concise and testable.

- Orchestration: Add a background job queue for uploads with persistent job state for retries, UI visibility, and robust resume-after-restart. This will improve UX and reliability for larger uploads and intermittent networks.

If you'd like, I can next:
- Implement `cloud/uploader.py` + `cloud/google_uploader.py` (adapter) and add unit tests for the progress/exception semantics.
- Run a read-only git-history exposure check for the client_id/secret we moved.
- Add a CI example workflow snippet that writes the client JSON from a GitHub secret at runtime and runs a smoke upload in isolation.

Which of those follow-ups should I start with? I'm ready to implement the adapter + tests or run the git-history audit next.

## Analysis of existing utilities and decisions about expanding them

This section inspects the helper utilities and patterns already present in `cloud/drive_manager.py` and `cloud/auth_manager.py`, and makes explicit decisions about whether to expand, keep, or replace them. The goal is to keep changes incremental, minimise risk, and maximise reusability.

### Utilities and patterns already present

- Lazy import helpers (`_has_module`, `_import_build`, `_import_http`, `_import_flow`, etc.)
  - Purpose: allow the app to import cloud code without hard failing when Google libraries are absent.
- Folder management helper (`_ensure_recordings_folder`) in `drive_manager.py`
  - Purpose: find or create the dedicated Drive folder used for recordings.
- Chunked/resumable upload loop using `MediaFileUpload` and `request.next_chunk()`
  - Purpose: stream large files and report progress via logs.
- Metadata construction inline in `upload_recording()` (properties dict)
  - Purpose: attach searchable fields to uploaded files for later retrieval.
- Credentials storage helpers in `auth_manager.py` (`_save_credentials_securely`, `_acquire_path_lock_for_write`, `_restrict_file_permissions`, keyring fallback)
  - Purpose: try secure storage and provide a robust fallback to file-based storage with cross-process locking.
- Token refresh coordination (`_refresh_if_needed` with locks and in-flight event)
  - Purpose: avoid duplicated refreshes when multiple callers detect expired tokens.
- Small server callback helper (`_AuthCallbackServer`, `_CallbackHandler`, `_serve_until_result`) in `auth_manager.py`
  - Purpose: perform the loopback OAuth installed-app flow.

### Decision table: expand / keep / replace (with rationale)

- Lazy import helpers — KEEP & STANDARDISE
  - Rationale: This pattern is low-risk and valuable for graceful degradation. Expand slightly by centralising the pattern into a small `cloud/_lazy.py` module that exposes `require_libs(*names)` and `optional_libs(*names)` helpers. Doing so reduces duplication and makes tests easier (one place to patch). This is a small refactor with low risk.

- Folder management (`_ensure_recordings_folder`) — EXPAND & EXTRACT
  - Rationale: Keep the existing logic but extract it to the `Uploader` adapter as `ensure_folder(name)` and add unit tests. The logic is Drive-specific but should be surfaced on the public Uploader API for reuse by UI and orchestration code.

- Chunked/resumable upload loop — EXPAND (utility + retry wrapper)
  - Rationale: Keep the existing mechanism but extract a reusable `chunked_upload_with_progress()` utility that accepts a `create_request()` callback and provides progress callbacks, cancellation, and pluggable retry/backoff. Re-using the same utility for downloads (MediaIoBaseDownload) is also possible. This reduces duplicated logic and centralises retry behavior.

- Inline metadata construction — EXTRACT & STANDARDISE
  - Rationale: Metadata shape is domain-specific and should be canonicalised. Create `cloud/metadata_schema.py` and a `build_upload_metadata(...)` helper. This enables validation and consistent search semantics across the app.

- Credential-storage helpers — KEEP & DOCUMENT; ADD SAFETY LAYER
  - Rationale: Current helpers are thoughtful (keyring-first, file fallback with locking). Keep them, but extract them into `cloud/credentials.py` with the same semantics and add small integration tests that run only in dev (mocking keyring). Add clear docs on where to place `client_secrets.json` and how to rotate credentials. Also, add an optional, explicit in-app way to clear credentials.

- Token refresh coordination — KEEP
  - Rationale: The singleflight-like pattern is correct and should be kept. Expand tests around this area (concurrent refresh scenario) rather than replacing the approach.

- Local OAuth callback server helpers — KEEP but harden
  - Rationale: The one-shot server is appropriate for installed-app flows. Hardening includes explicit port/timeouts and better logging, but the structure should remain. Extract into `cloud/oauth_server.py` for clarity and testing.

### Implementation notes and risk mitigation

- Make small, testable refactors: extract utilities into new small modules (`cloud/_lazy.py`, `cloud/credentials.py`, `cloud/metadata_schema.py`, `cloud/upload_utils.py`, `cloud/oauth_server.py`). Keep existing public entrypoints working while migrating internal references.
- Add unit tests that patch the lazy import helpers so CI doesn't need cloud libraries for coverage of logic paths.
- When introducing the `Uploader` interface, provide a `GoogleDriveUploader` that delegates to the extracted utilities. Keep `GoogleDriveManager` as a compatibility layer for the short term and mark it deprecated.
- Use feature flags or a migration period for behavior that changes return semantics (None vs exceptions). Provide a `legacy_upload_recording_compat()` wrapper while refactors land.

### Practical next tasks (short checklist)

1. Create `cloud/_lazy.py` and update imports to use it (small safe refactor).
2. Add `cloud/metadata_schema.py` and move metadata assembly into `build_upload_metadata()`.
3. Extract `chunked_upload_with_progress()` into `cloud/upload_utils.py` and wire it into `GoogleDriveUploader`.
4. Add `cloud/credentials.py` that encapsulates keyring + file fallback storage and provide a small CLI helper to clear stored credentials.
5. Implement `cloud/uploader.py` interface and `cloud/google_uploader.py` adapter (unit tests).

Each step is intentionally small so it can be code-reviewed and reverted if anything breaks.

### Concluding recommendation

The current implementation contains many of the right building blocks. The effort should focus on extracting and consolidating utilities (lazy imports, metadata builder, chunked upload, credentials storage), introducing a small typed uploader abstraction, and improving error semantics and observability. These changes will unlock better testability and allow richer orchestration (background jobs, dedupe, retries) without a large upfront rewrite.

If you'd like, I will start with implementing `cloud/uploader.py` and `cloud/upload_utils.py` and add unit tests for progress, cancellation, and retry behavior. Otherwise I can proceed with adding the small utility modules in the practical checklist above.
 
## Lasting context — what I implemented in this session

- Added a small typed uploader interface in `cloud/uploader.py` (abstract contract for upload/list/download/delete).
- Implemented `cloud/google_uploader.py` — a GoogleDriveUploader adapter that:
  - wraps the existing `GoogleDriveManager` behaviour,
  - uses a shared chunked upload helper for resumable uploads,
  - accepts a `progress_callback` and a `cancel_event`, and
  - returns a typed `UploadResult` or raises typed exceptions from `cloud/exceptions.py`.
- Hardened and expanded the chunked upload helper in `cloud/upload_utils.py`:
  - added transient error classification heuristics,
  - implemented exponential backoff with jitter,
  - improved attempts/ retry semantics, and
  - improved how total bytes are discovered and reported to progress callbacks.
- Added unit tests:
  - `tests/test_upload_utils.py` — coverage for progress reporting, cancellation, and retry behavior in the upload helper.
  - `tests/test_google_uploader.py` — adapter unit test that mocks a minimal Drive service and validates progress and returned result.

## Test results (unit)

- I ran the unit tests for the upload helper and the new adapter locally in the repository venv. They exercised the helper + adapter mechanics.
- If you want, I can run the full test suite next; these files are intentionally small and mock-based so they run quickly.

## CI workflow example (safe secret handling)

Below is an example GitHub Actions workflow that I will add to the repository (file: `.github/workflows/ci-google-upload.yml`). It runs unit tests and a detect-secrets check for accidental secrets. The integration job only runs when the repository has a GitHub secret named `VRP_CLIENT_SECRETS_JSON` (the job writes it to a temporary file and cleans it up).

Usage notes:
- Create a repository secret `VRP_CLIENT_SECRETS_JSON` containing the JSON content of the OAuth client file. Only set this for private repositories or dedicated integration branches. Do NOT commit the client JSON.
- The integration job is gated with `if: secrets.VRP_CLIENT_SECRETS_JSON != ''` so it will be skipped unless the secret is present.

I will add the workflow file to the repo now.