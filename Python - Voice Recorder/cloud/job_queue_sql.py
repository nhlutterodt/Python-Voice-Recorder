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
    last_error: Optional[str] = None
    drive_file_id: Optional[str] = None


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
        last_error TEXT,
        drive_file_id TEXT
    )
    ''')
    conn.commit()
    conn.close()


def enqueue_job(job: JobRow, db_path: Optional[str] = None) -> None:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO jobs (id,file_path,title,description,tags,status,attempts,max_attempts,created_iso,last_error,drive_file_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)', (
        job.id, job.file_path, job.title, job.description, json.dumps(job.tags) if job.tags is not None else None, job.status, job.attempts, job.max_attempts, job.created_iso or datetime.utcnow().isoformat(), job.last_error, job.drive_file_id
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
    cur.execute("UPDATE jobs SET status='running', attempts=attempts+1 WHERE id=?", (row['id'],))
    conn.commit()
    conn.close()
    return JobRow(id=row['id'], file_path=row['file_path'], title=row['title'], description=row['description'], tags=json.loads(row['tags']) if row['tags'] else None, status='running', attempts=row['attempts'] or 0, max_attempts=row['max_attempts'] or 3, created_iso=row['created_iso'], last_error=row['last_error'], drive_file_id=row['drive_file_id'])


def update_job_status(job_id: str, status: str, db_path: Optional[str] = None, last_error: Optional[str] = None, drive_file_id: Optional[str] = None) -> None:
    conn = _connect(db_path)
    cur = conn.cursor()
    cur.execute('UPDATE jobs SET status=?, last_error=?, drive_file_id=? WHERE id=?', (status, last_error, drive_file_id, job_id))
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
            try:
                result = uploader.upload(job.file_path, title=job.title, description=job.description, tags=job.tags)
                update_job_status(job.id, 'succeeded', db_path=db_path, drive_file_id=result.get('file_id'))
            except Exception as e:
                # If the uploader raises an error, mark as failed.
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
