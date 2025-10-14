import asyncio
import threading
import time
from pathlib import Path
from unittest.mock import Mock

from cloud.auth_manager import GoogleAuthManager


def test_concurrent_refresh_only_calls_refresh_once(tmp_path: Path) -> None:
    # Arrange: create manager with injected mock credentials that appear expired
    mock_creds = Mock()
    mock_creds.expired = True
    mock_creds.refresh_token = "dummy"

    # The refresh method will sleep briefly to simulate network latency, then set expired=False
    def fake_refresh(req):
        time.sleep(0.1)
        mock_creds.expired = False

    mock_creds.refresh.side_effect = fake_refresh

    mgr = GoogleAuthManager(app_dir=tmp_path, credentials=mock_creds)

    # Act: spawn multiple threads that call _refresh_if_needed concurrently
    threads = []
    for _ in range(8):
        t = threading.Thread(target=mgr._refresh_if_needed)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Assert: refresh was called at least once but only a single active refresh should have happened
    # Depending on timing, some threads may skip because lock is held. We expect exactly 1 call.
    assert (
        mock_creds.refresh.call_count == 1
    ), f"refresh called {mock_creds.refresh.call_count} times"


def test_failed_refresh_propagates_and_allows_retry(tmp_path: Path) -> None:
    # Arrange: mock credentials where first refresh raises, second succeeds
    mock_creds = Mock()
    mock_creds.expired = True
    mock_creds.refresh_token = "dummy"

    call_count = {"n": 0}

    def fake_refresh(req):
        call_count["n"] += 1
        if call_count["n"] == 1:
            # first call fails
            raise RuntimeError("simulated refresh failure")
        # second call succeeds and marks not expired
        mock_creds.expired = False

    mock_creds.refresh.side_effect = fake_refresh

    mgr = GoogleAuthManager(app_dir=tmp_path, credentials=mock_creds)

    # Act: have multiple threads call _refresh_if_needed concurrently; they should observe the failure
    threads = []
    results = []

    def worker():
        try:
            mgr._refresh_if_needed()
            results.append((True, None))
        except Exception as e:
            results.append((False, e))

    for _ in range(4):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # At least one worker should have seen the exception (leader); others waited and then returned
    assert any(
        not ok for ok, _ in results
    ), "At least one worker should have observed the refresh failure"

    # Now mark credentials expired again and ensure a subsequent retry succeeds
    mock_creds.expired = True
    mgr._refresh_if_needed()
    assert mock_creds.expired is False


def test_async_singleflight_shares_inflight(tmp_path: Path) -> None:
    mock_creds = Mock()
    mock_creds.expired = True
    mock_creds.refresh_token = "dummy"

    # Blocking refresh function: sleep briefly then mark not expired
    def fake_refresh(req):
        time.sleep(0.05)
        mock_creds.expired = False

    mock_creds.refresh.side_effect = fake_refresh
    mgr = GoogleAuthManager(app_dir=tmp_path, credentials=mock_creds)

    async def run_concurrent():
        # Kick off multiple concurrent awaiters of the async refresh wrapper
        await asyncio.gather(*(mgr._refresh_if_needed_async() for _ in range(6)))

    asyncio.run(run_concurrent())
    assert mock_creds.expired is False
    assert mock_creds.refresh.call_count == 1
