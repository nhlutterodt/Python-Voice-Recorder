import multiprocessing
import time
from pathlib import Path
from typing import Optional

from cloud.job_queue import SqliteJobQueue


def worker_main(
    db_path: str,
    out_q: multiprocessing.Queue,
    sleep_ms: float = 0.0,
    fail_dir: Optional[str] = None,
) -> None:
    """Worker process: repeatedly claim and process jobs until none left.

    The handler optionally sleeps to increase contention and may consult
    a shared filesystem directory (fail_dir) to simulate intentional
    per-job failures that decrement on each attempt.
    """
    q = SqliteJobQueue(db_path=db_path)

    def handler(payload: dict) -> bool:
        if sleep_ms:
            time.sleep(sleep_ms / 1000.0)
        if fail_dir is not None:
            f = Path(fail_dir) / str(payload.get("i"))
            if f.exists():
                try:
                    n = int(f.read_text())
                except Exception:
                    n = 0
                if n > 0:
                    # decrement and fail
                    f.write_text(str(n - 1))
                    raise RuntimeError("intentional-failure")
        return True

    handlers = {"t": handler}
    while True:
        jid = q.process_once(handlers)
        if jid is None:
            break
        out_q.put(jid)
    out_q.put(None)


def _run_workers_and_collect(
    tmp_path: Path, db_path: str, worker_count: int, **worker_kwargs
):
    ctx = multiprocessing.get_context("spawn")
    out_q: multiprocessing.Queue = ctx.Queue()
    procs = [
        ctx.Process(
            target=worker_main,
            args=(
                db_path,
                out_q,
                worker_kwargs.get("sleep_ms", 0.0),
                worker_kwargs.get("fail_dir"),
            ),
        )
        for _ in range(worker_count)
    ]
    for p in procs:
        p.start()

    received = []
    done_signals = 0
    while done_signals < worker_count:
        try:
            item = out_q.get(timeout=30)
        except Exception:
            break
        if item is None:
            done_signals += 1
        else:
            received.append(item)

    for p in procs:
        p.join(timeout=5)
        if p.is_alive():
            p.terminate()
    return received


def test_atomic_claims_under_parallel_access_stress(tmp_path: Path) -> None:
    db = tmp_path / "jobs.db"
    db_path = str(db)
    q = SqliteJobQueue(db_path=db_path)

    total = 200
    for i in range(total):
        q.enqueue("t", {"i": i}, max_retries=3)

    # 4 workers with a small sleep to increase contention
    received = _run_workers_and_collect(tmp_path, db_path, worker_count=4, sleep_ms=20)

    # handlers intentionally fail once per job, so workers will report a job
    # id more than once (failure then success). Ensure every job was seen at
    # least once and ultimately reached completed state.
    unique_ids = set(received)
    assert (
        len(unique_ids) == total
    ), f"expected {total} unique processed ids, got {len(unique_ids)}"

    # verify final state for each job is 'completed'
    q2 = SqliteJobQueue(db_path=db_path)
    for jid in unique_ids:
        rec = q2.get_job(jid)
        assert (
            rec is not None and rec.status == "completed"
        ), f"job {jid} final status is not completed"


def test_retries_under_concurrency(tmp_path: Path) -> None:
    db = tmp_path / "jobs_retry.db"
    db_path = str(db)
    q = SqliteJobQueue(db_path=db_path)

    total = 80
    # prepare a directory with per-job failure counters (1 failure each)
    fail_dir = tmp_path / "fail_counts"
    fail_dir.mkdir()
    for i in range(total):
        (fail_dir / str(i)).write_text("1")
        q.enqueue("t", {"i": i}, max_retries=2)

    # 4 workers; handlers will read and decrement files to simulate a single
    # intentional failure before success
    received = _run_workers_and_collect(
        tmp_path, db_path, worker_count=4, sleep_ms=5, fail_dir=str(fail_dir)
    )

    unique_ids = set(received)
    # Each job may be reported more than once (fail then succeed). Ensure
    # every job was eventually processed and reached completed state.
    assert (
        len(unique_ids) == total
    ), f"expected {total} unique processed ids, got {len(unique_ids)}"

    q2 = SqliteJobQueue(db_path=db_path)
    for jid in unique_ids:
        rec = q2.get_job(jid)
        assert (
            rec is not None and rec.status == "completed"
        ), f"job {jid} final status is not completed"
