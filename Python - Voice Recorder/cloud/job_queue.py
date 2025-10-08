"""A minimal file-backed job queue for long-running uploads.

This queue stores pending jobs in a JSON file and provides simple
enqueue/dequeue operations. It's intentionally synchronous and
lightweight; it's suitable for small desktop apps. A future improvement
is to add sqlite-backed durability and worker processes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional
from threading import Lock


DEFAULT_QUEUE_PATH = Path.home() / '.vrp_upload_queue.json'


@dataclass
class UploadJob:
    id: str
    file_path: str
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    created_iso: Optional[str] = None


class JobQueue:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else DEFAULT_QUEUE_PATH
        self._lock = Lock()
        self._load()

    def _load(self):
        if not self.path.exists():
            self._jobs: List[UploadJob] = []
            return
        try:
            with self.path.open('r', encoding='utf-8') as fh:
                data = json.load(fh)
            self._jobs = [UploadJob(**item) for item in data]
        except Exception:
            self._jobs = []

    def _persist(self):
        with self.path.open('w', encoding='utf-8') as fh:
            json.dump([asdict(j) for j in self._jobs], fh, ensure_ascii=False, indent=2)

    def enqueue(self, job: UploadJob) -> None:
        with self._lock:
            self._jobs.append(job)
            self._persist()

    def dequeue(self) -> Optional[UploadJob]:
        with self._lock:
            if not self._jobs:
                return None
            job = self._jobs.pop(0)
            self._persist()
            return job

    def list_jobs(self) -> List[UploadJob]:
        with self._lock:
            return list(self._jobs)
