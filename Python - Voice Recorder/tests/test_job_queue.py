
from cloud.job_queue import JobQueue


def test_enqueue_and_process_once_success(tmp_path):
    db = tmp_path / "jobs.db"
    q = JobQueue(str(db))

    jid = q.enqueue('echo', {'msg': 'hello'}, max_retries=2)

    # handler that returns True
    handlers = {'echo': lambda payload: payload.get('msg') == 'hello'}
    processed = q.process_once(handlers)
    assert processed == jid

    rec = q.get_job(jid)
    assert rec is not None
    assert rec.status == 'completed'


def test_retry_and_fail(tmp_path):
    db = tmp_path / "jobs2.db"
    q = JobQueue(str(db))

    jid = q.enqueue('bad', {'count': 1}, max_retries=1)

    # handler that raises
    def bad_handler(payload):
        raise RuntimeError('boom')

    handlers = {'bad': bad_handler}

    # First attempt will requeue (attempts=1)
    q.process_once(handlers)
    rec = q.get_job(jid)
    assert rec is not None
    assert rec.attempts == 1
    assert rec.status in ('pending', 'failed')

    # Second attempt should mark failed (max_retries=1)
    q.process_once(handlers)
    rec2 = q.get_job(jid)
    assert rec2 is not None
    assert rec2.attempts >= 2
    assert rec2.status == 'failed'
