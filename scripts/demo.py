"""Run the founder rehearsal. No payment, firmware flash, or GPIO output command exists here."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def tool(name):
    path = shutil.which(name)
    if not path:
        raise ValueError(f"{name} is unavailable. Follow the README prerequisites, then run check again.")
    return path


def run(command, *, env=None):
    return subprocess.run(command, cwd=ROOT, env=env).returncode


def port_number(value):
    port = int(value)
    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError("Use a port from 1024 to 65535.")
    return port


def require_free_port(port):
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("127.0.0.1", port))
        except OSError as error:
            raise ValueError(f"Port {port} is unavailable. Use its existing demo or choose another --port. "
                             "Stop a server only in its own terminal with Ctrl+C.") from error


def check():
    checks = [
        ("Node 22.13+ and SQLite", [tool("node"), "-e",
         "const [a,b]=process.versions.node.split('.').map(Number);"
         "if(a<22||(a===22&&b<13))process.exit(1);require('node:sqlite');"],
         "Install Node.js 22.13 or later."),
        ("Installed gateway dependencies", [tool("node"), "--input-type=module", "-e",
         "await import('express');await import('@x402/core/server');"],
         "Run npm --prefix gateway ci."),
        ("Installed Python observation CLI", [tool("uv"), "run", "--offline", "--no-sync", "--project", "host",
         "capmesh", "observe-demo", "--help"], "Run uv sync --project host."),
    ]
    failed = False
    for label, command, recovery in checks:
        try:
            result = subprocess.run(command, cwd=ROOT / "gateway" if label == "Installed gateway dependencies" else ROOT,
                                    capture_output=True, timeout=10, stdin=subprocess.DEVNULL)
            passed = result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            passed = False
        print(f"{'PASS' if passed else 'FAIL'}: {label}", flush=True)
        if not passed:
            print(recovery, flush=True)
            failed = True
    print("This check reads no radio and moves no funds. Board availability needs the separate board command.", flush=True)
    return int(failed)


def summarize_board(path, expected=None):
    events = [json.loads(line) for line in path.read_text().splitlines() if line]
    samples = [event for event in events if event.get("event") == "sample"]
    summaries = [event for event in events if event.get("event") == "summary"]
    if len(samples) != 1 or not summaries or summaries[-1].get("passed") != 1 or summaries[-1].get("failed") != 0:
        raise ValueError("The log does not contain one successful board check. Preserve it and inspect the failure.")
    result = samples[0].get("result", {})
    decision = result.get("decision", {})
    closed = decision.get("closed")
    if (samples[0].get("success") is not True or type(closed) is not bool
            or decision.get("receipt_identity") != "pinned-device-p256"):
        raise ValueError("The log does not establish a verified device input. Preserve it and inspect the failure.")
    state = "closed" if closed else "open"
    print(f"Device-signed {state.upper()} → {decision.get('decision')}. "
          f"Age: {decision.get('age_seconds')} seconds. Samples: {decision.get('sample_agreement')}.", flush=True)
    if expected and state != expected:
        raise ValueError(f"Expected {expected.upper()}, received {state.upper()}. "
                         "Check the BOOT action. No retry or simulated replacement occurred.")


def board(expected=None):
    if os.name != "posix":
        raise ValueError("The bounded board runner requires POSIX process groups. Use the documented host CLI on this system.")
    uv = tool("uv")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = Path(".local/soak") / f"founder-{stamp}-{secrets.token_hex(3)}.jsonl"
    print("ONE REAL BLE INPUT · no payment or GPIO output. Target: provisioned ESP32-C6 / GPIO9.", flush=True)
    print("Close other BLE scans. Hold BOOT for CLOSED, or release it for OPEN. Do not press Reset.", flush=True)
    code = run([uv, "run", "--no-sync", "--project", "host", "python", "scripts/soak_observations.py",
                "--count", "1", "--interval", "1", "--output", str(output)])
    if (ROOT / output).exists():
        print(f"Diagnostic log: {output}", flush=True)
    else:
        print("No diagnostic log was created. Check the runner setup.", flush=True)
    if code:
        return code
    summarize_board(ROOT / output, expected)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("check", help="Check installed prerequisites. No radio or payment.")
    guide = actions.add_parser("guide", help="Serve the HTML guide on localhost.")
    guide.add_argument("--port", type=port_number, default=8788)
    simulated = actions.add_parser("sim", help="Start simulated payment and contact. No funds or hardware.")
    simulated.add_argument("--port", type=port_number, default=4022)
    simulated.add_argument("--closed", action="store_true", help="Simulate CLOSED instead of OPEN.")
    physical = actions.add_parser("physical", help="Start simulated payment with real BLE input. No funds.")
    physical.add_argument("--port", type=port_number, default=4023)
    observed = actions.add_parser("board", help="Record one bounded real BLE input. No payment.")
    observed.add_argument("--expect", choices=("open", "closed"), help="Fail if the measured input differs from this action.")
    actions.add_parser("cases", help="Run all eight signed-fixture pair scenarios. No hardware or payment.")
    args = parser.parse_args(argv)
    try:
        if args.action == "check":
            return check()
        if args.action == "board":
            return board(args.expect)
        if args.action == "cases":
            print("SIMULATED SIGNED FIXTURES · two keys, zero physical devices, no funds.", flush=True)
            return run([tool("uv"), "run", "--no-sync", "--project", "host", "capmesh", "corroborate-demo", "--scenario", "all"])
        require_free_port(args.port)
        if args.action == "guide":
            print(f"Guide: http://127.0.0.1:{args.port}/HOW_IT_WORKS.html · Ctrl+C stops this server.", flush=True)
            return run([sys.executable, "-m", "http.server", str(args.port), "--bind", "127.0.0.1",
                        "--directory", str(ROOT / "docs")])
        npm = tool("npm")
        env = os.environ.copy()
        env["CAPMESH_GATEWAY_PORT"] = str(args.port)
        command = [npm, "--prefix", "gateway", "run", "demo"]
        if args.action == "physical":
            command += ["--", "--physical"]
        elif args.closed:
            command += ["--", "--closed"]
        print(f"{'REAL BLE INPUT' if args.action == 'physical' else 'SIMULATED CONTACT'} · "
              f"SIMULATED PAYMENT · no funds. http://127.0.0.1:{args.port}", flush=True)
        print("Ctrl+C stops this server. The launcher never pays, flashes, or drives a GPIO output.", flush=True)
        return run(command, env=env)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"STOP: {error}", file=sys.stderr, flush=True)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
