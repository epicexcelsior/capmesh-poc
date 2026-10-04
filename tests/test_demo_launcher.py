import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/demo.py"


def load_launcher():
    spec = importlib.util.spec_from_file_location("founder_demo", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("mode,extra,expected", [
    ("sim", [], []),
    ("sim", ["--closed"], ["--", "--closed"]),
    ("physical", [], ["--", "--physical"]),
])
def test_launcher_selects_only_simulated_payment_and_propagates_child_failure(tmp_path, mode, extra, expected):
    fake = tmp_path / "npm"
    record = tmp_path / "child.json"
    fake.write_text(f"#!{sys.executable}\nimport json,os,sys\n"
                    "from pathlib import Path\n"
                    "Path(os.environ['DEMO_TEST_RECORD']).write_text(json.dumps({"
                    "'args':sys.argv[1:],'cwd':os.getcwd(),'port':os.environ['CAPMESH_GATEWAY_PORT']}))\n"
                    "raise SystemExit(7)\n")
    fake.chmod(0o755)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {**os.environ, "PATH": str(tmp_path), "DEMO_TEST_RECORD": str(record)}
    result = subprocess.run([sys.executable, str(SCRIPT), mode, "--port", str(port), *extra],
                            cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 7
    assert "SIMULATED PAYMENT" in result.stdout
    child = json.loads(record.read_text())
    assert child["args"] == ["--prefix", "gateway", "run", "demo", *expected]
    assert child["cwd"] == str(SCRIPT.parents[1])
    assert child["port"] == str(port)
    assert "start" not in child["args"]


def test_occupied_port_refuses_to_start_or_stop_any_process(monkeypatch, capsys):
    module = load_launcher()
    calls = []
    monkeypatch.setattr(module, "run", lambda *args, **kwargs: calls.append(args))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        assert module.main(["sim", "--port", str(listener.getsockname()[1])]) == 1
    assert not calls
    assert "Stop a server only in its own terminal" in capsys.readouterr().err


def test_stopped_server_connections_do_not_block_restart():
    module = load_launcher()
    with socket.socket() as listener, socket.socket() as client:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        listener.listen()
        client.connect(("127.0.0.1", port))
        connection, _ = listener.accept()
        connection.close()
        assert client.recv(1) == b""
    module.require_free_port(port)


def write_board_log(path, *, closed=False, identity="pinned-device-p256", passed=1):
    result = {"closed": closed, "receipt_identity": identity, "decision": "WAIT" if closed else "DISPATCH",
              "age_seconds": 4, "sample_agreement": "5/5"}
    events = [{"event": "sample", "success": True, "result": {"decision": result}},
              {"event": "summary", "passed": passed, "failed": 1 - passed}]
    path.write_text("\n".join(json.dumps(event) for event in events) + "\n")


def test_wrong_physical_action_fails_without_retry_or_simulation(tmp_path, monkeypatch, capsys):
    module = load_launcher()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "tool", lambda name: name)
    calls = []

    def child(command, **kwargs):
        calls.append(command)
        output = tmp_path / command[command.index("--output") + 1]
        output.parent.mkdir(parents=True)
        write_board_log(output, closed=False)
        return 0

    monkeypatch.setattr(module, "run", child)
    assert module.main(["board", "--expect", "closed"]) == 1
    assert len(calls) == 1
    assert "scripts/soak_observations.py" in calls[0]
    assert "--simulated" not in calls[0]
    assert "Expected CLOSED, received OPEN" in capsys.readouterr().err


@pytest.mark.parametrize("changes", [{"closed": "false"}, {"identity": "public-demo-hmac"}, {"passed": 0}])
def test_invalid_or_failed_board_evidence_never_reports_success(tmp_path, changes):
    module = load_launcher()
    log = tmp_path / "sample.jsonl"
    write_board_log(log, **changes)
    with pytest.raises(ValueError):
        module.summarize_board(log)


def test_verified_closed_input_is_a_successful_check_with_wait(tmp_path, capsys):
    module = load_launcher()
    log = tmp_path / "sample.jsonl"
    write_board_log(log, closed=True)
    module.summarize_board(log, expected="closed")
    assert "CLOSED → WAIT" in capsys.readouterr().out


def test_invalid_port_stops_before_any_child_action(monkeypatch):
    module = load_launcher()
    calls = []
    monkeypatch.setattr(module, "run", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(SystemExit) as failure:
        module.main(["physical", "--port", "80"])
    assert failure.value.code == 2
    assert not calls
