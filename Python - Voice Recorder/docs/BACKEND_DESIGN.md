# Backend Design & Audit — Voice Recorder Pro

Date: 2025-09-04
Branch: feature/backend-robustness

This document captures the audit, design decisions, data contracts, prioritized issues, and concrete next steps for a robust backend for Voice Recorder Pro. It mirrors the analysis performed on `models/` and `cloud/` modules and records recommended improvements so the context is preserved.

## Goals

- Provide a robust, testable backend for recordings: reliable local storage, durable metadata, explicit sync state with cloud, safe schema migrations, and clear service/repository APIs.
- Keep UI thin — tests and business logic live in services and repositories.
- Support offline-first use, resilient cloud sync, and safe schema evolution.

## Current state (brief)

- SQLAlchemy setup exists in `models/database.py` and a minimal `Recording` model in `models/recording.py`.
- Google OAuth (`cloud/auth_manager.py`) and Drive integration (`cloud/drive_manager.py`) are implemented with lazy imports and reasonable error logging.
- UI widgets in `cloud/cloud_ui.py` directly tie to managers.
- No migration tooling (Alembic) present; no repository/service layer; recording model lacks sync-mapping fields.

## Constraints & assumptions

- Desktop single-user application (not multi-tenant server).
- Large binary audio files stored in local filesystem under `recordings/`.
- Cloud sync to Google Drive is optional and must tolerate network and auth failures.

## Core components (recommended)

1. Data layer
   - SQLAlchemy models + Alembic for migrations.
   - `SessionLocal` remains, add a `get_session()` contextmanager helper.
   - Add `RecordingRepository` to centralize DB operations.

2. Expanded Recording model
   - Keep current fields and add:
     - `local_path` (str) — absolute or project-relative filepath
     - `filesize_bytes` (int)
     - `mime_type` (str)
     - `checksum` (str, sha256)
     - `drive_file_id` (Optional[str])
     - `sync_status` (enum: unsynced, syncing, synced, failed)
     - `last_synced_at` (Optional[datetime])
     - optional audio attrs: `sample_rate`, `channels`, `bit_depth`
   - Rationale: dedupe, resume uploads, map remote files to local rows.

3. Service layer
   - `RecordingService` (uses repository + filesystem utilities): create_from_file, delete, list, compute_checksum.
   - `SyncService`: queue uploads, retries, reconciliation between local DB and Drive.

4. Cloud integration improvements
   - Keep `GoogleAuthManager` and `GoogleDriveManager` but:
     - Add structured exceptions (AuthError, RateLimitError, TransientError).
     - Add retry/backoff for transient failures and handling for 429s.
     - Return result objects or raise exceptions instead of returning None/bool.
     - Persist `drive_file_id` on success.

5. Storage & file handling
   - Use deterministic recordings directory (e.g., `recordings/raw/`) and store files under UUID names; preserve original filename in metadata.
   - Compute checksum on ingest and store it.
   - Soft-delete semantics in DB; physical purge requires explicit action.

6. Migrations & tests
   - Add Alembic and an initial migration corresponding to current model.
   - Add unit tests for repository/service logic (SQLite in-memory or temp file), and mock Google APIs for cloud tests.

## Data contract — Recording (minimal)

- id: int
- filename: str (original)
- local_path: str
- title: Optional[str]
- duration: float
- filesize_bytes: int
- mime_type: str
- checksum: str
- status: enum (active, archived, deleted)
- sync_status: enum (unsynced, syncing, synced, failed)
- drive_file_id: Optional[str]
- created_at: datetime
- last_synced_at: Optional[datetime]

## API sketches (service signatures)

- RecordingService.create_from_file(path: str, title: Optional[str] = None) -> Recording
- RecordingService.get(id: int) -> Optional[Recording]
- RecordingService.delete(id: int, soft: bool = True) -> bool
- RecordingService.list(filters: dict) -> List[Recording]
- SyncService.enqueue_upload(recording_id: int) -> str  # returns task id
- SyncService.process_queue() -> None  # background worker

## Error modes & edge cases

- Disk full during copy/write
- Partial/corrupt uploads — verify checksum after download
- Google API rate limiting (429) — need retry with exponential backoff + jitter
- Auth expiration — detect and refresh or prompt user
- Filename collisions — store with UUID and track original filename
- Concurrent access to the same file — serialize through service or file locks

## Security considerations

- OAuth tokens currently stored at `cloud/credentials/token.json` (best-effort 0600 on POSIX). Consider integrating OS keyring (Windows Credential Manager, macOS Keychain) for tokens.
- `config/client_secrets.json` should not be checked into repo; prefer env variables for CI secrets.

## Testing & CI

- Unit tests: repository (DB) and services (business logic) using temporary SQLite and mocks.
- Cloud tests: mock Google API calls (e.g., via pytest + responses or unittest.mock) to simulate uploads, rate limits, and failures.
- Integration smoke test: ingest a file, compute checksum, mark as uploaded with mocked Drive client, ensure `drive_file_id` persisted.

## Migration & rollout plan

1. Add Alembic and create initial migration representing the current schema.
2. Add a migration to add new Recording columns.
3. Ship migration runner script or call `alembic upgrade head` in installer step.
4. Back up DB automatically before performing destructive migration steps.

## Prioritized issues & recommended fixes

1. (High) No migration tooling — add Alembic and initial migration.
2. (High) Recording model lacks `local_path`, `checksum`, `drive_file_id`, `sync_status` — add via migration.
3. (High) Missing repository/service layer — add `services/recording_service.py` and `repositories/recording_repository.py` for centralized DB + FS logic.
4. (High) `GoogleDriveManager.upload_recording` returns None/False on failure — convert to structured results/exceptions for retryability.
5. (Medium) Credential storage on Windows not secure — consider OS keyring and document limitations.
6. (Medium) No retry/backoff for cloud operations — add exponential backoff and idempotency support.
7. (Medium) No persistent mapping between local and remote (drive_file_id) — persist it on success.
8. (Low) `filename` uniqueness may cause collisions — use UUID for stored filenames.
9. (Low) Missing unit tests for cloud manager — add tests with mocks.
10. (Low) No session helper/contextmanager — add `get_session()` to ensure consistent session lifecycle.

## Concrete next steps (pick one to start)

A) Add Alembic with initial migration + an upgrade migration for new Recording columns. Add a small `init_db.py` upgrade flag.

B Implement `RecordingService.create_from_file()` that:

   - copies file into `recordings/raw/` (UUID filename)
   - computes sha256 checksum
    - infers mime type
   - creates DB row with new fields
   - returns the created Recording
   - includes unit tests

C Harden `cloud/drive_manager.py` to raise structured exceptions and add retry/backoff (with unit tests mocking Google APIs).

D Add `repositories/recording_repository.py`, `services/recording_service.py`, and a basic integration test (in-memory DB) demonstrating create → enqueue upload with a mocked `GoogleDriveManager`.

## Cloud provider abstraction (multi-provider sync)

Goal

- Support multiple remote storage backends (Google Drive, OneDrive, SFTP, etc.) without coupling app logic to provider-specific APIs. Provide a single, testable sync surface that UI and services call.

Design summary

- Introduce a Cloud Provider Adapter interface that each provider implements. The app uses the adapter's generic API instead of provider-specific code.

Provider adapter responsibilities (ideal interface)

- authenticate() -> AuthResult
- is_authenticated() -> bool
- upload_file(local_path: str, remote_path: str, *, metadata: dict, resume: bool=False) -> UploadResult
- download_file(remote_id: str, local_path: str) -> DownloadResult
- list_files(folder_id: str | None) -> List[RemoteFile]
- delete_file(remote_id: str) -> bool
- get_storage_info() -> ProviderStorageInfo
- supports_resumable_uploads() -> bool
- normalize_remote_id(provider_id: str) -> str

Notes: return types should be simple dataclasses or TypedDicts containing standard fields (remote_id, size, mime_type, created_at, etag, resumable_url) so the SyncService can operate generically.

Provider registry & configuration

- Implement a lightweight registry that maps provider keys ("gdrive", "onedrive", "sftp") to adapter classes. Allow enabling/disabling providers via config (env/config_manager).
- Provide a factory that accepts config and returns a provider instance with credentials injected.

Provider capability matrix (example)

- Google Drive: resumable uploads, metadata, per-file IDs, supports partial content, rate limits (per-user), REST API.
- OneDrive (MS Graph): chunked upload (resumable), metadata, per-file IDs, quotas, supports delta API for changes.
- SFTP: simple file transfer (no resumable protocol by default), server file system semantics; may require temporary file + rename for atomicity.

Provider-agnostic sync concepts

- Idempotency: derive an idempotency key from file checksum + size to avoid duplicate uploads.
- Remote mapping: store provider key + remote_id (or single `drive_file_id` prefixed by provider key e.g. `gdrive:FILEID`) on the Recording model so the same recording can be synced to multiple providers.
- Resumable uploads: only used if provider reports support. For providers without resumable upload (SFTP), implement chunked upload via small temp files and a final rename or implement streaming with retry and checkpointing.
- Conflict resolution: use last-writer-wins, or store both remote etag and local checksum and surface conflicts to the user. Provide a reconciliation routine.
- Rate limiting / backoff: adopt a shared retry/backoff helper with exponential backoff + jitter and provider-specific retry policies (e.g., for 429/503 responses). Log and persist transient failure state.
- Quota handling: detect provider quota errors and surface a clear message to the user; mark recordings as `sync_status='quota_exceeded'` if applicable.

Provider-specific edge notes

- Google Drive:
  - Use resumable uploads for large files.
  - Metadata properties are available; store the drive file id and etag for reconciliation.
  - Scopes: `drive.file` vs broader scopes — minimize scope requested.

- OneDrive (MS Graph):
  - Use chunked upload sessions for large files; honor session expiry and re-create if needed.
  - Delta API can be used for two-way sync and change detection.

- SFTP:
  - No remote metadata API; rely on filename conventions and timestamp/size.
  - Implement atomic uploads by writing to `.part` or temporary filename then rename.
  - No native resume: implement partial-file resume by tracking bytes transferred and using remote seek if server supports it (rare). Otherwise, chunk+rename or re-upload with dedupe by checksum.

Security & credentials

- Tokens: prefer OS keyring where possible (Windows Credential Manager, macOS Keychain, Linux secret service). Fallback to encrypted local files or user profile-protected files.
- Scopes and least privilege: request minimal scopes needed for the feature (upload-only vs full drive). Document scope tradeoffs in UI and upgrade flows.
- Audit/logging: log provider operations at info/debug level with scrubbed PII; ensure token values never appear in logs.

Data model changes (multi-provider readiness)

- Recording table should support multi-provider mapping. Options:
  - Add columns `provider: str` and `remote_id: str` and store one mapping per `recording_remote` table (many-to-one). Recommended: create `recording_remote` table with columns: `id, recording_id, provider_key, remote_id, remote_etag, last_synced_at, sync_status`.

Testing & mocks

- Provide `cloud/providers/mock_provider.py` implementing the adapter interface for fast unit tests.
- Use recordings fixture + temp files for integration tests.
- For SFTP/OneDrive/Google Drive tests, mock network interactions; for OneDrive/Google use recorded response fixtures or pytest-mock.

Implementation sketch

- Add `cloud/providers/` package with per-provider adapters:
  - `cloud/providers/base.py` — the Provider ABC and shared helpers (retries, credential loader).
  - `cloud/providers/gdrive.py` — Google Drive adapter wrapping `GoogleDriveManager` or reusing its core logic but conforming to the adapter interface.
  - `cloud/providers/onedrive.py` — OneDrive adapter using MS Graph (requests or msal libraries).
  - `cloud/providers/sftp.py` — SFTP adapter using paramiko or async alternative.
- Add `services/sync_service.py` that consumes adapters by provider key and coordinates upload/download and reconciliation.

Operational concerns

- Allow background sync worker (local thread/process) with rate-limiting and concurrency controls.
- Backups: before destructive operations (deletes, migrations), keep a DB and recordings folder snapshot.
- Provide UI hints when provider capabilities differ (e.g., "Resumable uploads available" vs "Uploads may fail on network hiccups").

## Updated next steps (multi-provider)

1. Add `cloud/providers/base.py` and `cloud/providers/mock_provider.py` (adapter and mock) and wire a simple registry.
2. Add `recording_remote` table migration (Alembic) to store per-provider mapping.
3. Implement a thin `gdrive` adapter that delegates to existing `GoogleDriveManager` but returns unified results.
4. Add unit tests for the registry + mock provider and a service-level test showing an upload flow using the mock provider.

## Metadata & Logging

A robust metadata model and a consistent logging strategy are essential for searchability, diagnostics, audits, and safe cloud sync.

Metadata concepts

- Canonical metadata stored on the `Recording` row (or related tables):
  - `id`, `original_filename`, `stored_filename` (UUID), `local_path` (str)
  - `title`, `description`, `tags` (array / normalized table)
  - `duration`, `filesize_bytes`, `mime_type`, `sample_rate`, `channels`, `bit_depth`
  - `checksum` (sha256), `waveform_peaks` (serialized summary), `spectrogram_preview` (path/reference)
  - `created_by_app_version` (app version string), `created_at`, `modified_at`
  - `status` (active/archived/deleted) and `retention_policy` (enum or reference)
  - `provenance` / `ingest_source` (local, import, cloud:gdrive, cloud:onedrive, sftp)

- Remote mapping table (`recording_remote`) to store per-provider metadata:
  - `id, recording_id, provider_key, remote_id, remote_etag, remote_path, last_synced_at, sync_status`

- Indexes & search
  - Index `created_at`, `checksum`, `title`, and `tags` for quick queries.
  - Provide a lightweight full-text search (FTS) index for `title` and `description` (SQLite FTS or an optional small search index) if the app needs quick local search.

- Derived assets
  - Store derived artifacts (waveform images, spectrograms, compressed versions, transcriptions) alongside the recording record with pointers to local path and optional remote mapping.
  - Maintain lifecycle metadata (e.g., `derived_generated_at`, `derived_version`) so artifacts can be safely regenerated or invalidated when source changes.

- Data integrity
  - Compute and store `checksum` on ingest. Validate checksum after downloads from remote providers where possible.
  - Add a lightweight verification job that periodically re-hashes files to detect silent corruption (configurable frequency).

- Retention & GDPR
  - Store `consent`/`data_subject` flags if required and provide a way to purge personal data per user request.
  - When deleting recordings, implement soft-delete + a configurable retention/purge policy. Provide export of user data where applicable.

Logging strategy

- Structured logging
  - Use Python `logging` with a single app-wide logger configured to emit structured JSON logs in production builds. Include fields: `timestamp`, `level`, `logger`, `message`, `module`, `func`, `lineno`, `correlation_id`, `user_email_masked`, and `context` (dict).

- Correlation & tracing
  - Generate a `correlation_id` for high-level operations (e.g., ingest → upload → finalize). Pass this ID through service calls and include it in logs, telemetry, and any cloud requests (where safe).
  - Optionally integrate with an open-source tracing system (OpenTelemetry) for distributed traces when the app interacts with remote services.

- Audit logs
  - For security-relevant operations (auth changes, upload, download, delete, permission changes), write audit entries to a separate append-only store (or a DB table) with: `timestamp, user_masked, operation, target_recording_id, provider, success, meta`.
  - Ensure audit log entries do not contain secrets or full tokens.

- Error telemetry & metrics
  - Count and export metrics for: upload attempts, upload failures, auth failures, retry attempts, and sync latency. Expose these as local metrics consumable by CI/diagnostics, and optionally send anonymized telemetry when user opts in.

- PII handling
  - Mask or omit sensitive fields in logs (emails should be masked; access tokens must never be logged).
  - Respect user opt-out for telemetry and provide a clear privacy policy in the app.

- Local log management
  - Rotate logs and limit retention (e.g., keep logs for 30 days) to avoid disk growth.
  - For the distributed/executable build, provide an option to upload logs when debugging (user-initiated) instead of automatically sending them.

- Operational notes
  - Ensure cloud adapter errors include structured error codes (e.g., `ERR_UPLOAD_RATE_LIMIT`, `ERR_AUTH_EXPIRED`) so UI and retry logic can act deterministically.
  - On failure paths, store failure metadata on the `recording_remote` row so the sync worker can resume or surface actionable messages to users.

---

If you want, I can start implementing: A (migrations) or B (ingest & service) next. Tell me which and I will begin on this branch and commit changes.
