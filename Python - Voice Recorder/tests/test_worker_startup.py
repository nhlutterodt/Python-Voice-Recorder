import threading
import types

import importlib


def test_start_job_worker_starts_thread(monkeypatch):
    # Import the module under test
    enhanced_main = importlib.import_module('enhanced_main')

    # Prepare a fake run_worker_with_supervisor that returns a Thread instance
    def fake_run_worker_with_supervisor(drive_manager, db_path=None, poll_interval=2, stop_event=None):
        # Create a thread that will block on an Event until we signal it.
        stop_evt = threading.Event()

        def _run():
            # Block until test clears this event; simulates a long-running worker
            stop_evt.wait()

        t = threading.Thread(target=_run)
        t.daemon = True
        # attach the event to the thread so the test can stop it
        t._stop_evt = stop_evt
        t.start()
        return t

    # Monkeypatch config_manager to enable the worker
    fake_config = types.SimpleNamespace(enable_cloud_job_worker=True, cloud_jobs_db_path=None)
    monkeypatch.setattr(enhanced_main, 'config_manager', fake_config)

    # Monkeypatch the import inside the helper to return our fake function
    monkeypatch.setattr('cloud.job_queue_sql.run_worker_with_supervisor', fake_run_worker_with_supervisor, raising=False)

    # Call the helper with a dummy drive_manager
    # helper was renamed from _maybe_start_job_worker -> start_job_worker
    thread = enhanced_main.start_job_worker(object())

    assert thread is not None
    assert isinstance(thread, threading.Thread)
    assert thread.is_alive()

    # clean up the background thread started by our fake supervisor
    try:
        stop_evt = getattr(thread, '_stop_evt', None)
        if stop_evt is not None:
            stop_evt.set()
            thread.join(timeout=1.0)
    except Exception:
        pass
