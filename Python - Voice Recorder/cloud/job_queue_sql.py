"""SQLite-backed job queue for durable upload jobs.

Simple schema: jobs(id TEXT PRIMARY KEY, file_path TEXT, title TEXT, description TEXT, tags TEXT, status TEXT, created_iso TEXT, last_error TEXT, drive_file_id TEXT)
Worker: `run_worker(drive_manager, db_path)` which polls pending jobs and executes uploads via drive_manager.get_uploader().
"""
from __future__ import annotations

import sqlite3
import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


DEFAULT_DB = None
try:
    # Prefer the project's configured SQLAlchemy DATABASE_URL so the job queue
    # operates on the same sqlite file as the rest of the app when no
    # explicit db_path is passed. Import locally to avoid import cycles at
    # higher levels.
    from voice_recorder.models import database as _app_db

    if isinstance(_app_db.DATABASE_URL, str) and _app_db.DATABASE_URL.startswith('sqlite:///'):
        # Convert SQLAlchemy sqlite URL to a filesystem path the sqlite3
        # stdlib can open.
        DEFAULT_DB = _app_db.DATABASE_URL.replace('sqlite:///', '', 1)
    else:
        DEFAULT_DB = _app_db.DATABASE_URL
except Exception:
    # If anything goes wrong, fall back to in-memory default.
    DEFAULT_DB = None


@dataclass
class JobRow:
    id: str
    file_path: str
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    status: str = 'pending'
    attempts: int = 0
    max_attempts: int = 3
    created_iso: Optional[str] = None
    started_iso: Optional[str] = None
    finished_iso: Optional[str] = None
    uploaded_bytes: int = 0
    total_bytes: Optional[int] = None
    last_error: Optional[str] = None
    drive_file_id: Optional[str] = None
    cancel_requested: int = 0


def _connect(db_path: Optional[str] = None):
    path = db_path or (DEFAULT_DB or ':memory:')
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        file_path TEXT NOT NULL,
        title TEXT,
        description TEXT,
        tags TEXT,
        status TEXT NOT NULL,
        attempts INTEGER DEFAULT 0,
        max_attempts INTEGER DEFAULT 3,
        created_iso TEXT,
        started_iso TEXT,
        finished_iso TEXT,
        uploaded_bytes INTEGER DEFAULT 0,
        total_bytes INTEGER,
        last_error TEXT,
        drive_file_id TEXT,
        cancel_requested INTEGER DEFAULT 0
    )
    ''')
    conn.commit()

    # Try to add missing columns if the table existed previously (safe no-op on newer DBs)
    try:
        cur.execute("ALTER TABLE jobs ADD COLUMN started_iso TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE jobs ADD COLUMN finished_iso TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE jobs ADD COLUMN uploaded_bytes INTEGER DEFAULT 0")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE jobs ADD COLUMN total_bytes INTEGER")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE jobs ADD COLUMN cancel_requested INTEGER DEFAULT 0")
    except Exception:
        pass
    conn.commit()
    conn.close()


def enqueue_job(job: JobRow, db_path: Optional[str] = None) -> None:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO jobs (id,file_path,title,description,tags,status,attempts,max_attempts,created_iso,started_iso,finished_iso,uploaded_bytes,total_bytes,last_error,drive_file_id,cancel_requested) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (
        job.id, job.file_path, job.title, job.description, json.dumps(job.tags) if job.tags is not None else None, job.status, job.attempts, job.max_attempts, job.created_iso or datetime.utcnow().isoformat(), job.started_iso, job.finished_iso, job.uploaded_bytes, job.total_bytes, job.last_error, job.drive_file_id, job.cancel_requested
    ))
    conn.commit()
    conn.close()


def dequeue_next(db_path: Optional[str] = None) -> Optional[JobRow]:
    conn = _connect(db_path)
    cur = conn.cursor()
    # Select jobs that are pending or failed but still under max_attempts
    cur.execute("SELECT * FROM jobs WHERE (status='pending' OR (status='failed' AND attempts<max_attempts)) ORDER BY created_iso LIMIT 1")
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    # Mark running and record start time
    started = datetime.utcnow().isoformat()
    cur.execute("UPDATE jobs SET status='running', attempts=attempts+1, started_iso=? WHERE id=?", (started, row['id']))
    conn.commit()
    conn.close()
    return JobRow(
        id=row['id'],
        file_path=row['file_path'],
        title=row['title'],
        description=row['description'],
        tags=json.loads(row['tags']) if row['tags'] else None,
        status='running',
        attempts=row['attempts'] or 0,
        max_attempts=row['max_attempts'] or 3,
        created_iso=row['created_iso'],
        started_iso=started,
        finished_iso=row.get('finished_iso'),
        uploaded_bytes=row.get('uploaded_bytes') or 0,
        total_bytes=row.get('total_bytes'),
        last_error=row['last_error'],
        drive_file_id=row['drive_file_id'],
        cancel_requested=row.get('cancel_requested') or 0,
    )


def update_job_status(job_id: str, status: str, db_path: Optional[str] = None, last_error: Optional[str] = None, drive_file_id: Optional[str] = None) -> None:
    conn = _connect(db_path)
    cur = conn.cursor()
    finished = None
    if status in ('succeeded', 'failed', 'cancelled'):
        finished = datetime.utcnow().isoformat()
    if finished is not None:
        cur.execute('UPDATE jobs SET status=?, last_error=?, drive_file_id=?, finished_iso=? WHERE id=?', (status, last_error, drive_file_id, finished, job_id))
    else:
        cur.execute('UPDATE jobs SET status=?, last_error=?, drive_file_id=? WHERE id=?', (status, last_error, drive_file_id, job_id))
    conn.commit()
    conn.close()


def update_job_progress(job_id: str, uploaded_bytes: int, total_bytes: Optional[int] = None, db_path: Optional[str] = None) -> None:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute('UPDATE jobs SET uploaded_bytes=?, total_bytes=? WHERE id=?', (uploaded_bytes, total_bytes, job_id))
    conn.commit()
    conn.close()


def set_job_cancel_requested(job_id: str, db_path: Optional[str] = None) -> None:
    """Mark a job as cancel requested so the running worker can pick it up."""
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute('UPDATE jobs SET cancel_requested=1 WHERE id=?', (job_id,))
    conn.commit()
    conn.close()


def get_all_jobs(db_path: Optional[str] = None) -> List[JobRow]:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute('SELECT * FROM jobs ORDER BY created_iso DESC')
    rows = cur.fetchall()
    jobs: List[JobRow] = []
    for row in rows:
        jobs.append(JobRow(id=row['id'], file_path=row['file_path'], title=row['title'], description=row['description'], tags=json.loads(row['tags']) if row['tags'] else None, status=row['status'], attempts=row['attempts'] or 0, max_attempts=row['max_attempts'] or 3, created_iso=row['created_iso'], last_error=row['last_error'], drive_file_id=row['drive_file_id']))
    conn.close()
    return jobs


def run_worker(drive_manager, db_path: Optional[str] = None, poll_interval: float = 2.0, stop_event: Optional[threading.Event] = None) -> None:
    """Run a simple worker loop that uploads pending jobs using the manager's uploader."""
    init_db(db_path)
    if stop_event is None:
        stop_event = threading.Event()

    while not stop_event.is_set():
        job = dequeue_next(db_path)
        if job is None:
            time.sleep(poll_interval)
            continue

        try:
            uploader = getattr(drive_manager, 'get_uploader', None)
            if callable(uploader):
                uploader = drive_manager.get_uploader()
            else:
                uploader = None

            if uploader is None:
                raise RuntimeError('No uploader available')

            # Attempt the upload; uploader.upload may raise DuplicateFoundError
            # which will be treated as success by storing the existing file id.
            # Wire progress updates from uploader back into the DB so the UI can poll
            cancel_event = threading.Event()

            def _watch_cancel():
                # Poll the DB for cancel requests and set the cancel_event when requested
                try:
                    while not cancel_event.is_set() and not stop_event.is_set():
                        conn = _connect(db_path)
                        cur = conn.cursor()
                        cur.execute('SELECT cancel_requested FROM jobs WHERE id=?', (job.id,))
                        r = cur.fetchone()
                        conn.close()
                        if r and int(r['cancel_requested'] or 0) == 1:
                            cancel_event.set()
                            break
                        time.sleep(0.5)
                except Exception:
                    return

            watcher = threading.Thread(target=_watch_cancel, daemon=True)
            watcher.start()

            def _progress_cb(progress: dict):
                try:
                    uploaded = int(progress.get('uploaded_bytes', 0) or 0)
                    total = progress.get('total_bytes')
                    update_job_progress(job.id, uploaded, total, db_path=db_path)
                except Exception:
                    pass

            try:
                result = uploader.upload(job.file_path, title=job.title, description=job.description, tags=job.tags, progress_callback=_progress_cb, cancel_event=cancel_event)
                update_job_status(job.id, 'succeeded', db_path=db_path, drive_file_id=result.get('file_id'))
            except Exception as e:
                # If the uploader raises an error, mark as failed.
                # If the cancel_event was set, report cancelled
                if cancel_event.is_set():
                    update_job_status(job.id, 'cancelled', db_path=db_path, last_error='cancelled by user')
                else:
                    update_job_status(job.id, 'failed', db_path=db_path, last_error=str(e))
        except Exception as e:
            update_job_status(job.id, 'failed', db_path=db_path, last_error=str(e))
        # Short sleep to avoid tight loop
        time.sleep(0.1)


def run_worker_with_supervisor(drive_manager, db_path: Optional[str] = None, poll_interval: float = 2.0, stop_event: Optional[threading.Event] = None) -> threading.Thread:
    """Run the worker in a supervised thread that restarts on unexpected exit."""
    if stop_event is None:
        stop_event = threading.Event()

    def _target():
        while not stop_event.is_set():
            try:
                run_worker(drive_manager, db_path=db_path, poll_interval=poll_interval, stop_event=stop_event)
            except Exception:
                # Sleep briefly before restart to avoid tight restart loops
                time.sleep(1.0)

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    return t
