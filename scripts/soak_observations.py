"""Record scheduled real input checks. No payments, GPIO outputs, or automatic retries."""

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


class WorkerCleanupError(RuntimeError):
    """Stop the run when the previous worker cannot be reaped."""

    def __init__(self, message="", *, worker_pid=None):
        super().__init__(message)
        self.worker_pid = worker_pid if type(worker_pid) is int and worker_pid > 0 else None


async def run_sample(timeout, *, command=None, cleanup_seconds=2):
    # Separate processes permit termination even when BLE cancellation cleanup hangs.
    worker = await asyncio.create_subprocess_exec(
        *(command or [sys.executable, str(ROOT / "scripts/check_device_latency.py")]),
        cwd=ROOT, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, start_new_session=True)
    communication = asyncio.create_task(worker.communicate())
    reaping = asyncio.create_task(worker.wait())
    cleanup_task = None

    def confirm_reaping():
        try:
            reaping.result()
        except (Exception, asyncio.CancelledError) as error:
            raise WorkerCleanupError("The worker wait failed. Stop BLE work and inspect the process.",
                                     worker_pid=worker.pid) from error
        if worker.returncode is None:
            raise WorkerCleanupError("The worker wait returned without an exit status. Stop BLE work and inspect the process.",
                                     worker_pid=worker.pid)

    async def stop_worker():
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(worker.pid, sig)
            except ProcessLookupError:
                pass
            except OSError as error:
                done, _ = await asyncio.wait({reaping}, timeout=cleanup_seconds)
                if done:
                    confirm_reaping()
                    return
                raise WorkerCleanupError("The worker signal failed before cleanup was confirmed. Stop BLE work and inspect the process.",
                                         worker_pid=worker.pid) from error
            done, _ = await asyncio.wait({reaping}, timeout=cleanup_seconds)
            if done:
                confirm_reaping()
                return
        raise WorkerCleanupError(f"The observation worker PID {worker.pid} did not finish after termination. Stop all BLE tests and inspect the process.",
                                 worker_pid=worker.pid)

    async def finish_cleanup():
        nonlocal cleanup_task
        if cleanup_task is None:
            cleanup_task = asyncio.create_task(stop_worker())
        cancellation = None
        while True:
            try:
                await asyncio.shield(cleanup_task)
                break
            except asyncio.CancelledError as error:
                if cleanup_task.cancelled():
                    raise WorkerCleanupError("Worker cleanup was canceled before confirmation. Stop BLE work and inspect the process.",
                                             worker_pid=worker.pid) from error
                # Repeated caller cancellation cannot interrupt bounded TERM/KILL and reaping.
                cancellation = error
        if cancellation is not None:
            raise cancellation

    try:
        done, _ = await asyncio.wait({communication}, timeout=timeout)
        if not done:
            await finish_cleanup()
            raise TimeoutError("The observation deadline expired. The isolated worker was terminated.")
        output, error = communication.result()
        done, _ = await asyncio.wait({reaping}, timeout=cleanup_seconds)
        if not done:
            raise WorkerCleanupError("The observation output completed before worker cleanup. Stop the run and inspect the process.",
                                     worker_pid=worker.pid)
        confirm_reaping()
        if worker.returncode != 0:
            raise RuntimeError(error.decode(errors="replace")[-4096:] or "The real observation worker failed")
        if len(output) > 65536:
            raise ValueError("The observation worker returned an oversized result")
        return json.loads(output)
    except BaseException:
        if not reaping.done() and cleanup_task is None:
            await finish_cleanup()
        elif reaping.done():
            confirm_reaping()
        raise
    finally:
        if not reaping.done():
            reaping.cancel()
        if not communication.done():
            communication.cancel()
        elif not communication.cancelled():
            communication.exception()  # Retrieve a pipe failure after bounded worker cleanup.


async def run_samples(sample, emit, *, count, interval, timeout, sleep=asyncio.sleep):
    if type(count) is not int or not 1 <= count <= 240:
        raise ValueError("Sample count must be 1–240")
    if not 0 <= interval <= 300 or not 0 < timeout <= 60:
        raise ValueError("Interval must be 0–300 seconds. Timeout must be greater than 0 and at most 60 seconds")
    passed = failed = consecutive_failures = 0
    stop_reason = "completed"
    for number in range(1, count + 1):
        started = time.monotonic()
        record = {"event": "sample", "number": number,
                  "captured_at_utc": datetime.now(timezone.utc).isoformat()}
        try:
            record["result"] = await sample(timeout)
            record["success"] = True
            passed += 1
            consecutive_failures = 0
        except Exception as exc:
            record.update(success=False, error_type=type(exc).__name__, error=str(exc))
            failed += 1
            consecutive_failures += 1
            if isinstance(exc, WorkerCleanupError):
                stop_reason = "worker_cleanup_failed"
        record["elapsed_seconds"] = round(time.monotonic() - started, 3)
        emit(record)
        if stop_reason == "worker_cleanup_failed":
            break
        if consecutive_failures == 3:
            stop_reason = "three_consecutive_failures"
            break
        if number < count:
            await sleep(interval)
    summary = {"event": "summary", "requested": count, "completed": passed + failed,
               "passed": passed, "failed": failed,
               "stop_reason": stop_reason}
    emit(summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--interval", type=float, default=30, help="Seconds between completed samples")
    parser.add_argument("--timeout", type=float, default=45, help="Deadline for each complete observation")
    parser.add_argument("--output", type=Path, required=True, help="New ignored .local JSONL file")
    args = parser.parse_args()
    if os.name != "posix":
        parser.error("The unattended BLE runner requires POSIX process groups")
    output = args.output.resolve()
    if not output.is_relative_to((ROOT / ".local").resolve()):
        parser.error("Keep raw diagnostic logs inside the repository's ignored .local directory")
    if not 1 <= args.count <= 240 or not 0 <= args.interval <= 300 or not 0 < args.timeout <= 60:
        parser.error("Use 1–240 samples, a 0–300 second interval, and a timeout greater than 0 and at most 60 seconds")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as log:
        def emit(record):
            log.write(json.dumps(record) + "\n")
            log.flush()
            os.fsync(log.fileno())
            if record["event"] == "sample":
                age = record.get("result", {}).get("decision", {}).get("age_seconds")
                print(f"Sample {record['number']}: {'PASS' if record['success'] else 'FAIL'}; age={age}; elapsed={record['elapsed_seconds']}s", flush=True)
            elif record["event"] == "summary":
                print(json.dumps(record), flush=True)

        emit({"event": "start", "captured_at_utc": datetime.now(timezone.utc).isoformat(),
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "versions": {"python": sys.version.split()[0], "bleak": importlib.metadata.version("bleak"),
                           "cryptography": importlib.metadata.version("cryptography")},
              "tracked_changes_present": bool(subprocess.check_output(["git", "diff", "HEAD", "--name-only"], cwd=ROOT, text=True).strip()),
              "source_files_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
                  "host/capmesh/transport/ble.py", "host/capmesh/observations.py",
                  "host/capmesh/protocol/auth.py", "host/capmesh/protocol/receipt_keys.json",
                  "host/capmesh/protocol/identity.py", "host/capmesh/protocol/models.py",
                  "host/uv.lock", "scripts/check_device_latency.py")},
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "count": args.count, "interval_seconds": args.interval, "timeout_seconds": args.timeout,
              "worker_cleanup_seconds": 4,
              "mode": "Real BLE input only. No payment or GPIO output. Each sample uses a new challenge."})
        try:
            summary = asyncio.run(run_samples(run_sample, emit, count=args.count, interval=args.interval, timeout=args.timeout))
        except KeyboardInterrupt:
            emit({"event": "interrupted", "captured_at_utc": datetime.now(timezone.utc).isoformat()})
            return 130
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
