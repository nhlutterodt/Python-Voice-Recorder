import multiprocessing
from pathlib import Path

from cloud.job_queue import SqliteJobQueue


def worker_main(db_path: str, out_q: multiprocessing.Queue) -> None:
    """Worker process: repeatedly claim and process jobs until none left."""
    q = SqliteJobQueue(db_path=db_path)
    handlers = {"t": lambda p: True}
    while True:
        jid = q.process_once(handlers)
        if jid is None:
            break
        out_q.put(jid)
    # signal finished
    out_q.put(None)


def test_atomic_claims_under_parallel_access(tmp_path: Path) -> None:
    db = tmp_path / "jobs.db"
    db_path = str(db)
    q = SqliteJobQueue(db_path=db_path)

    total = 50
    for i in range(total):
        q.enqueue("t", {"i": i})

    ctx = multiprocessing.get_context("spawn")
    out_q: multiprocessing.Queue = ctx.Queue()
    p1 = ctx.Process(target=worker_main, args=(db_path, out_q))
    p2 = ctx.Process(target=worker_main, args=(db_path, out_q))
    p1.start()
    p2.start()

    received = []
    done_signals = 0
    # Collect results until both workers signal completion
    while done_signals < 2:
        try:
            item = out_q.get(timeout=10)
        except Exception:
            break
        if item is None:
            done_signals += 1
        else:
            received.append(item)

    p1.join(timeout=5)
    p2.join(timeout=5)
    if p1.is_alive():
        p1.terminate()
    if p2.is_alive():
        p2.terminate()

    # Ensure every job was processed once and only once
    assert len(received) == total, f"expected {total} processed ids, got {len(received)}"
    assert len(set(received)) == total, "duplicate job ids were processed"
