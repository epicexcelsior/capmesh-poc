"""Soak logs preserve failures and stop instead of disguising retries as passes."""

import asyncio
import importlib.util
import os
from pathlib import Path
import sys
import signal

import pytest

spec = importlib.util.spec_from_file_location("observation_soak", Path(__file__).resolve().parents[1] / "scripts/soak_observations.py")
soak = importlib.util.module_from_spec(spec)
spec.loader.exec_module(soak)


@pytest.mark.asyncio
async def test_scheduled_samples_preserve_failure_then_success():
    records, pauses = [], []
    outcomes = iter([{"decision": {"age_seconds": 4}}, RuntimeError("device unavailable"), {"decision": {"age_seconds": 5}}])

    async def sample(timeout):
        result = next(outcomes)
        if isinstance(result, Exception):
            raise result
        return result

    async def sleep(seconds):
        pauses.append(seconds)

    summary = await soak.run_samples(sample, records.append, count=3, interval=30, timeout=45, sleep=sleep)
    assert [r["success"] for r in records[:-1]] == [True, False, True]
    assert records[1]["error"] == "device unavailable"
    assert [r["number"] for r in records[:-1]] == [1, 2, 3]
    assert pauses == [30, 30]
    assert summary == {"event": "summary", "requested": 3, "completed": 3, "passed": 2, "failed": 1, "stop_reason": "completed"}


@pytest.mark.asyncio
@pytest.mark.skipif(os.name != "posix", reason="The local BLE runner uses POSIX worker process groups")
async def test_three_failed_deadlines_terminate_uncooperative_workers_and_stop():
    records = []
    command = [sys.executable, "-c", "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"]

    async def sample(timeout):
        return await soak.run_sample(timeout, command=command, cleanup_seconds=0.05)

    summary = await asyncio.wait_for(soak.run_samples(sample, records.append, count=10, interval=0, timeout=0.1), timeout=3)
    assert summary["stop_reason"] == "three_consecutive_failures"
    assert summary["completed"] == summary["failed"] == 3
    assert summary["passed"] == 0
    assert all(r["error_type"] == "TimeoutError" for r in records[:-1])


@pytest.mark.asyncio
async def test_failed_worker_cleanup_stops_before_another_sample():
    records = []

    async def sample(timeout):
        raise soak.WorkerCleanupError("Worker still active")

    summary = await soak.run_samples(sample, records.append, count=10, interval=0, timeout=45)
    assert summary["completed"] == summary["failed"] == 1
    assert summary["stop_reason"] == "worker_cleanup_failed"
    assert records[0]["error_type"] == "WorkerCleanupError"


@pytest.mark.asyncio
@pytest.mark.skipif(os.name != "posix", reason="The local BLE runner uses POSIX worker process groups")
async def test_pipe_failure_reaps_each_worker_before_another_sample(monkeypatch):
    create = asyncio.create_subprocess_exec
    workers, records = [], []

    class BrokenPipe:
        def __init__(self, worker):
            self.worker = worker
            self.pid = worker.pid

        @property
        def returncode(self):
            return self.worker.returncode

        async def communicate(self):
            raise OSError("Injected pipe read failure")

        async def wait(self):
            return await self.worker.wait()

    async def create_worker(*args, **kwargs):
        assert all(worker.returncode is not None for worker in workers)
        worker = await create(*args, **kwargs)
        workers.append(worker)
        return BrokenPipe(worker)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_worker)

    async def sample(timeout):
        return await soak.run_sample(timeout, command=[sys.executable, "-c", "import time; time.sleep(60)"], cleanup_seconds=0.1)

    summary = await asyncio.wait_for(soak.run_samples(sample, records.append, count=2, interval=0, timeout=1), timeout=3)
    assert summary["completed"] == summary["failed"] == 2
    assert all(worker.returncode is not None for worker in workers)
    assert all(record["error_type"] == "OSError" for record in records[:-1])


@pytest.mark.asyncio
@pytest.mark.skipif(os.name != "posix", reason="The local BLE runner uses POSIX worker process groups")
async def test_unreapable_worker_stops_after_one_bounded_cleanup_attempt(monkeypatch):
    signals, records = [], []

    class UnreapableWorker:
        pid = 123456789
        returncode = None

        async def communicate(self):
            await asyncio.Event().wait()

        async def wait(self):
            await asyncio.Event().wait()

    async def create_worker(*args, **kwargs):
        return UnreapableWorker()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_worker)
    monkeypatch.setattr(os, "killpg", lambda pid, sig: signals.append((pid, sig)))

    async def sample(timeout):
        return await soak.run_sample(timeout, cleanup_seconds=0.01)

    summary = await asyncio.wait_for(soak.run_samples(sample, records.append, count=3, interval=0, timeout=0.01), timeout=1)
    assert summary["stop_reason"] == "worker_cleanup_failed"
    assert summary["completed"] == 1
    assert signals == [(123456789, signal.SIGTERM), (123456789, signal.SIGKILL)]


@pytest.mark.asyncio
@pytest.mark.parametrize("count,interval,timeout", [(0, 0, 45), (241, 0, 45), (True, 0, 45),
    (1, -1, 45), (1, 301, 45), (1, 0, 0), (1, 0, 61), (1, float("nan"), 45), (1, 0, float("nan"))])
async def test_invalid_run_limits_do_not_start_a_sample(count, interval, timeout):
    async def sample(timeout):
        pytest.fail("Invalid limits must fail before hardware access")

    with pytest.raises(ValueError):
        await soak.run_samples(sample, lambda record: pytest.fail("No log expected"), count=count, interval=interval, timeout=timeout)


def test_main_refuses_an_existing_log_without_overwriting_it(tmp_path, monkeypatch):
    monkeypatch.setattr(soak, "ROOT", tmp_path)
    output = tmp_path / ".local/existing.jsonl"
    output.parent.mkdir()
    output.write_text("Preserve this run\n")
    monkeypatch.setattr(sys, "argv", ["soak", "--output", str(output)])
    with pytest.raises(FileExistsError):
        soak.main()
    assert output.read_text() == "Preserve this run\n"


def test_main_refuses_a_log_outside_ignored_local_state(tmp_path, monkeypatch):
    monkeypatch.setattr(soak, "ROOT", tmp_path)
    output = tmp_path / "tracked-result.jsonl"
    monkeypatch.setattr(sys, "argv", ["soak", "--output", str(output)])
    with pytest.raises(SystemExit) as exc:
        soak.main()
    assert exc.value.code == 2
    assert not output.exists()
