"""Job queue implementation with robust SQLite backend and a file adapter.

This module provides:
- SqliteJobQueue: WAL-enabled SQLite backend with atomic-claim semantics
  (BEGIN IMMEDIATE + conditional UPDATE) to safely claim work across
  processes.
- FileJobQueue: a small JSON-file backed adapter kept for legacy
  compatibility.
- create_job_queue(): factory selecting between backends.
- migrate_file_queue_to_sqlite(): helper to migrate existing file-queue
  entries into the SQLite DB.

The public symbol `JobQueue` is an alias to `SqliteJobQueue` to preserve
existing imports that expect `from cloud.job_queue import JobQueue`.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

DEFAULT_DB = ":memory:"
DEFAULT_FILE_QUEUE = Path.home() / ".vrp_upload_queue.json"


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


@dataclass
class JobRecord:
    id: int
    job_type: str
    payload: Dict[str, Any]
    status: str
    attempts: int
    max_retries: int
    last_error: Optional[str]
    created_at: str
    updated_at: str


class SqliteJobQueue:
    """SQLite-backed durable job queue with atomic-claim semantics."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB
        # isolation_level=None to allow explicit BEGIN/COMMIT
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path, timeout=10, check_same_thread=False, isolation_level=None
        )
        conn.row_factory = sqlite3.Row
        # pragmas for durability and concurrency
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=10000;")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_type TEXT NOT NULL,
                    payload TEXT,
                    status TEXT NOT NULL CHECK (status IN ('pending','running','completed','failed')),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at);"
            )

    def enqueue(
        self, job_type: str, payload: Dict[str, Any], max_retries: int = 3
    ) -> int:
        now = _utc_now_iso()
        payload_txt = json.dumps(payload, ensure_ascii=False)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("BEGIN;")
            cur.execute(
                "INSERT INTO jobs(job_type, payload, status, attempts, max_retries, created_at, updated_at) VALUES (?, ?, 'pending', 0, ?, ?, ?)",
                (job_type, payload_txt, max_retries, now, now),
            )
            lid = cur.lastrowid
            cur.execute("COMMIT;")
        if lid is None:
            raise RuntimeError("failed to insert job")
        return int(lid)

    def get_job(self, job_id: int) -> Optional[JobRecord]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, job_type, payload, status, attempts, max_retries, last_error, created_at, updated_at FROM jobs WHERE id = ?",
                (job_id,),
            )
            row = cur.fetchone()
            return self._row_to_record(row) if row else None

    def _row_to_record(self, row: sqlite3.Row) -> JobRecord:
        payload = {}
        if row["payload"]:
            try:
                payload = json.loads(row["payload"])
            except Exception:
                payload = {}
        return JobRecord(
            id=int(row["id"]),
            job_type=row["job_type"],
            payload=payload,
            status=row["status"],
            attempts=int(row["attempts"]),
            max_retries=int(row["max_retries"]),
            last_error=row["last_error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _claim_next_pending(self) -> Optional[JobRecord]:
        """Atomically claim the next pending job.

        Uses BEGIN IMMEDIATE + conditional UPDATE to avoid races across
        processes.
        """
        with self._connect() as conn:
            cur = conn.cursor()
            # Start an immediate transaction to acquire a RESERVED lock
            cur.execute("BEGIN IMMEDIATE;")
            cur.execute(
                "SELECT id FROM jobs WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1;"
            )
            row = cur.fetchone()
            if not row:
                cur.execute("ROLLBACK;")
                return None

            job_id = int(row[0])
            now = _utc_now_iso()
            # Attempt to mark running only if still pending
            cur.execute(
                "UPDATE jobs SET status = 'running', updated_at = ? WHERE id = ? AND status = 'pending';",
                (now, job_id),
            )
            if cur.rowcount != 1:
                cur.execute("ROLLBACK;")
                return None

            cur.execute(
                "SELECT id, job_type, payload, status, attempts, max_retries, last_error, created_at, updated_at FROM jobs WHERE id = ?;",
                (job_id,),
            )
            job_row = cur.fetchone()
            cur.execute("COMMIT;")
            return self._row_to_record(job_row) if job_row else None

    def _update_job(self, job_id: int, **fields: Any) -> None:
        if not fields:
            return
        set_cols = ", ".join(f"{k} = ?" for k in fields.keys())
        params = list(fields.values())
        now = _utc_now_iso()
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE jobs SET {set_cols}, updated_at = ? WHERE id = ?",
                (*params, now, job_id),
            )

    def process_once(
        self, handlers: Dict[str, Callable[[Dict[str, Any]], bool]]
    ) -> Optional[int]:
        job = self._claim_next_pending()
        if job is None:
            return None

        handler = handlers.get(job.job_type)
        if handler is None:
            # No handler: mark failed without incrementing attempts
            self._update_job(
                job.id, last_error=f"no handler for {job.job_type}", status="failed"
            )
            return job.id

        try:
            ok = handler(job.payload)
            if ok:
                self._update_job(job.id, status="completed")
            else:
                attempts = job.attempts + 1
                if attempts > job.max_retries:
                    self._update_job(
                        job.id,
                        attempts=attempts,
                        last_error="handler returned false",
                        status="failed",
                    )
                else:
                    self._update_job(
                        job.id,
                        attempts=attempts,
                        last_error="handler returned false",
                        status="pending",
                    )
        except Exception as e:
            attempts = job.attempts + 1
            if attempts > job.max_retries:
                self._update_job(
                    job.id, attempts=attempts, last_error=str(e), status="failed"
                )
            else:
                self._update_job(
                    job.id, attempts=attempts, last_error=str(e), status="pending"
                )

        return job.id


@dataclass
class _FileJobRow:
    id: int
    job_type: str
    payload: Dict[str, Any]
    status: str = "pending"
    attempts: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class FileJobQueue:
    """Legacy JSON file-backed compatibility adapter."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else DEFAULT_FILE_QUEUE
        self._lock = Lock()
        self._load()

    def _load(self) -> None:
        self._jobs: List[_FileJobRow] = []
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            mapped: List[_FileJobRow] = []
            for item in raw:
                mapped.append(_FileJobRow(**item))
            self._jobs = mapped
        except Exception:
            self._jobs = []

    def _persist(self) -> None:
        data = [asdict(j) for j in self._jobs]
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def enqueue(
        self, job_type: str, payload: Dict[str, Any], max_retries: int = 3
    ) -> int:
        with self._lock:
            new_id = (self._jobs[-1].id + 1) if self._jobs else 1
            now = _utc_now_iso()
            row = _FileJobRow(
                id=new_id,
                job_type=job_type,
                payload=payload,
                max_retries=max_retries,
                created_at=now,
                updated_at=now,
            )
            self._jobs.append(row)
            self._persist()
            return new_id

    def get_job(self, job_id: int) -> Optional[JobRecord]:
        with self._lock:
            row = next((j for j in self._jobs if j.id == job_id), None)
            if not row:
                return None
            return JobRecord(
                id=row.id,
                job_type=row.job_type,
                payload=row.payload,
                status=row.status,
                attempts=row.attempts,
                max_retries=row.max_retries,
                last_error=row.last_error,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    def process_once(
        self, handlers: Dict[str, Callable[[Dict[str, Any]], bool]]
    ) -> Optional[int]:
        with self._lock:
            row = next((j for j in self._jobs if j.status == "pending"), None)
            if not row:
                return None
            row.status = "running"
            row.updated_at = _utc_now_iso()
            self._persist()

        handler = handlers.get(row.job_type)
        if handler is None:
            with self._lock:
                row.last_error = f"no handler for {row.job_type}"
                row.status = "failed"
                self._persist()
            return row.id

        try:
            ok = handler(row.payload)
            with self._lock:
                if ok:
                    row.status = "completed"
                else:
                    row.attempts += 1
                    row.status = (
                        "failed" if row.attempts >= row.max_retries else "pending"
                    )
                row.updated_at = _utc_now_iso()
                self._persist()
        except Exception as e:
            with self._lock:
                row.attempts += 1
                row.last_error = str(e)
                row.status = "failed" if row.attempts >= row.max_retries else "pending"
                row.updated_at = _utc_now_iso()
                self._persist()
        return row.id


def create_job_queue(
    db_path: Optional[str] = None,
    backend: Optional[str] = None,
    file_queue_path: Optional[Path] = None,
):
    """Factory for job queues. backend can be 'sqlite' (default) or 'file'."""
    if backend == "file":
        return FileJobQueue(path=file_queue_path)
    # default to sqlite
    return SqliteJobQueue(db_path=db_path)


def migrate_file_queue_to_sqlite(file_path: Optional[Path], sqlite_db: str) -> int:
    """Migrate jobs from a file-backed queue into a sqlite DB.

    Returns the number of migrated jobs.
    """
    path = Path(file_path) if file_path else DEFAULT_FILE_QUEUE
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    q = SqliteJobQueue(db_path=sqlite_db)
    migrated = 0
    for item in raw:
        try:
            job_type = item.get("job_type")
            payload = item.get("payload") or {}
            max_retries = item.get("max_retries") or 3
            q.enqueue(job_type, payload, max_retries=max_retries)
            migrated += 1
        except Exception:
            continue
    return migrated


# Backwards-compatible alias expected by tests/imports
JobQueue = SqliteJobQueue
