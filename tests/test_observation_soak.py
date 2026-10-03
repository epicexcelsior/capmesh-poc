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
@pytest.mark.skipif(os.name != "posix", reason="The local BLE runner uses POSIX worker process groups")
@pytest.mark.parametrize("cancel_again", [False, True])
async def test_cancellation_during_termination_reaps_worker_before_return(monkeypatch, cancel_again):
    create, killpg = asyncio.create_subprocess_exec, os.killpg
    workers, signals = [], []
    terminated = asyncio.Event()

    async def spawn(*args, **kwargs):
        worker = await create(*args, **kwargs)
        workers.append(worker)
        assert await worker.stdout.readline() == b"ready\n"
        return worker

    def record_signal(pid, sig):
        signals.append(sig)
        killpg(pid, sig)
        if sig == signal.SIGTERM:
            terminated.set()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(os, "killpg", record_signal)
    command = [sys.executable, "-c",
               "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); print('ready', flush=True); time.sleep(60)"]
    task = asyncio.create_task(soak.run_sample(0.01, command=command, cleanup_seconds=0.05))
    repeat = None
    try:
        await asyncio.wait_for(terminated.wait(), timeout=2)
        task.cancel()
        if cancel_again:
            repeat = asyncio.get_running_loop().call_later(0.01, task.cancel)
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=1)
        assert workers[0].returncode is not None
        assert signals == [signal.SIGTERM, signal.SIGKILL]
    finally:
        if repeat is not None:
            repeat.cancel()
        # Preserve the host even when the regression fails before the fix.
        for worker in workers:
            if worker.returncode is None:
                killpg(worker.pid, signal.SIGKILL)
            await worker.wait()


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
@pytest.mark.parametrize("wait_failure", ["exception", "missing_exit_status"])
async def test_completed_wait_without_confirmed_exit_reports_cleanup_failure(monkeypatch, wait_failure):
    class Worker:
        pid = 123456789
        returncode = None

        async def communicate(self):
            return b"{}", b""

        async def wait(self):
            if wait_failure == "exception":
                raise OSError("Injected wait failure")
            return None

    async def spawn(*args, **kwargs):
        return Worker()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(soak.WorkerCleanupError) as error:
        await soak.run_sample(0.1, cleanup_seconds=0.01)
    assert error.value.worker_pid == Worker.pid


@pytest.mark.asyncio
async def test_signal_error_with_confirmed_exit_preserves_the_deadline_failure(monkeypatch):
    finished = asyncio.Event()

    class Worker:
        pid = 123456789
        returncode = None

        async def communicate(self):
            await asyncio.Event().wait()

        async def wait(self):
            await finished.wait()
            self.returncode = 0
            return 0

    async def spawn(*args, **kwargs):
        return Worker()

    def signal_after_exit(*args):
        finished.set()
        raise PermissionError("Injected signal race")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(os, "killpg", signal_after_exit)
    with pytest.raises(TimeoutError):
        await soak.run_sample(0.01, cleanup_seconds=0.1)


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
