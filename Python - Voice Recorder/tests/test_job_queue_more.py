from pathlib import Path

from cloud import job_queue


def test_create_job_queue_factory_defaults_to_sqlite():
    q = job_queue.create_job_queue()
    assert isinstance(q, job_queue.SqliteJobQueue)


def test_file_job_queue_enqueue_and_process(tmp_path: Path):
    p = tmp_path / 'queue.json'
    q = job_queue.FileJobQueue(path=p)

    called = {}

    def handler(payload):
        called['payload'] = payload
        return True

    jid = q.enqueue('send', {'a': 1}, max_retries=2)
    assert isinstance(jid, int)
    processed = q.process_once({'send': handler})
    assert processed == jid
    assert called.get('payload') == {'a': 1}
