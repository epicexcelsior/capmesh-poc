"""Concurrent pair collection must preserve buyer challenges and fail closed without retry."""

import asyncio
import base64
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from bleak.backends.device import BLEDevice
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

import capmesh.pair_collection as collection
import capmesh.transport.ble as ble
from capmesh.corroboration import ContactObserver, ContactPairVerifier
from capmesh.protocol.auth import receipt_message
from capmesh.protocol.identity import ReceiptPublicKey
from capmesh.protocol.models import Capability, InvocationReceipt, InvocationRequest, Manifest, Pricing

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def pair(monkeypatch):
    keys = [ec.generate_private_key(ec.SECP256R1()) for _ in range(2)]
    observers = [ContactObserver(f"fixture-{i}", f"gpio{18+i}-contact", ReceiptPublicKey(key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint).hex())) for i, key in enumerate(keys)]
    sensors = tuple(observer.sensor for observer in observers)
    monkeypatch.setattr(collection.time, "time", lambda: 100)

    def receipt(request, index, *, closed=False, completed=100):
        result = InvocationReceipt(protocol=request.protocol, request_id=request.request_id, status="success",
            provider=request.device_id, capability=request.capability, nonce=request.nonce, parameters=request.parameters,
            result={"metric": "gate.closed", "sensor": sensors[index], "closed": closed,
                    "stable_samples": 5, "total_samples": 5}, started_at=completed, completed_at=completed)
        r, s = utils.decode_dss_signature(keys[index].sign(receipt_message(result).encode(), ec.ECDSA(hashes.SHA256())))
        result.receipt_signature = "v3:" + base64.b64encode(r.to_bytes(32, "big") + s.to_bytes(32, "big")).decode()
        return result

    return observers, receipt


class FixtureTransport(ble.BLETransportAdapter):
    def __init__(self, observers, make_receipt, *, states=(False, False), failure=None, mutate=False):
        super().__init__()
        self.observers, self.make_receipt = observers, make_receipt
        self.states, self.failure, self.mutate = states, failure, mutate
        self.discovery_count = 0
        self.started = []
        self.gate = asyncio.Event()
        self.manifests = [Manifest("capmesh/0.1", observer.provider,
            capabilities=[Capability("state.observe", "Fixture contact", Pricing())]) for observer in observers]

    async def discover(self, timeout):
        self.discovery_count += 1
        return self.manifests

    async def invoke(self, target, request, timeout):
        assert self.discovery_count == 1
        self.started.append(target)
        if len(self.started) == 2:
            self.gate.set()
        await asyncio.wait_for(self.gate.wait(), timeout=0.2)
        index = next(i for i, observer in enumerate(self.observers) if observer.provider == target)
        if index == 1 and self.failure:
            raise self.failure
        if index == 1 and self.mutate:
            request.nonce += 1
        return self.make_receipt(request, index, closed=self.states[index])


@pytest.mark.asyncio
@pytest.mark.parametrize("states,decision,reason", [((False, False), "DISPATCH", "CONTACT_OPEN"),
    ((True, True), "WAIT", "CONTACT_CLOSED"), ((False, True), "WAIT", "OBSERVER_DISAGREEMENT")])
async def test_both_invocations_overlap_and_public_output_keeps_original_challenges(pair, states, decision, reason):
    observers, make = pair
    transport = FixtureTransport(observers, make, states=states)
    result = await collection.collect_contact_pair(observers, transport=transport)
    assert transport.discovery_count == 1 and len(transport.started) == 2
    assert result["pair"]["decision"] == decision and result["pair"]["reason"].startswith(reason)
    assert result["pair"]["status"] == "verified-pair"
    assert result["collection"]["invocations_started"] == 2
    assert result["collection"]["errors"] == []
    assert all(request["timestamp"] == 100 and "authorization" not in request for request in result["challenges"].values())
    assert result["payment_mode"] == "none; no funds moved"


@pytest.mark.asyncio
@pytest.mark.parametrize("discovery_problem", ["missing", "duplicate", "capability"])
async def test_failed_discovery_gate_sends_no_observation(pair, discovery_problem):
    observers, make = pair
    transport = FixtureTransport(observers, make)
    if discovery_problem == "missing":
        transport.manifests.pop()
    elif discovery_problem == "duplicate":
        transport.manifests.append(transport.manifests[0])
    else:
        transport.manifests[1].capabilities = []
    result = await collection.collect_contact_pair(observers, transport=transport)
    assert result["pair"]["decision"] == "WAIT"
    assert result["collection"]["errors"]
    assert result["collection"]["invocations_started"] == 0 and transport.started == []
    assert result["challenges"] == {}


@pytest.mark.asyncio
async def test_failed_member_preserves_partial_receipt_and_never_exposes_exception_payload(pair):
    observers, make = pair
    transport = FixtureTransport(observers, make, failure=OSError("secret authorization payload"))
    result = await collection.collect_contact_pair(observers, transport=transport)
    assert result["pair"]["decision"] == "WAIT"
    assert set(result["received_receipts"]) == {"fixture-0"}
    assert result["collection"]["errors"] == [{"provider": "fixture-1", "reason": "INVOKE_FAILED: OSError"}]
    assert "secret authorization payload" not in json.dumps(result)
    assert len(transport.started) == 2  # One invocation per provider, including the failed provider.


@pytest.mark.asyncio
async def test_transport_cannot_rewrite_the_original_buyer_challenge(pair):
    observers, make = pair
    result = await collection.collect_contact_pair(observers, transport=FixtureTransport(observers, make, mutate=True))
    assert result["pair"]["decision"] == "WAIT"
    assert any("CHALLENGE_MISMATCH" in item["reason"] for item in result["pair"]["rejections"])
    assert result["challenges"]["fixture-1"]["nonce"] != result["received_receipts"]["fixture-1"]["nonce"]


@pytest.mark.asyncio
async def test_observer_selection_stays_fixed_during_discovery(pair):
    observers, make = pair
    transport = FixtureTransport(observers, make)
    discover = transport.discover
    transport.observers = tuple(observers)

    async def mutate_selection(timeout):
        found = await discover(timeout)
        observers.clear()
        return found

    transport.discover = mutate_selection
    result = await collection.collect_contact_pair(observers, transport=transport)
    assert result["pair"]["decision"] == "DISPATCH"
    assert set(result["challenges"]) == {"fixture-0", "fixture-1"}


@pytest.mark.asyncio
@pytest.mark.parametrize("malformed", [None, {"status": "success"}])
async def test_malformed_transport_response_is_explicit_unmet_evidence(pair, malformed):
    observers, make = pair
    transport = FixtureTransport(observers, make)
    invoke = transport.invoke

    async def wrong_response(target, request, timeout):
        receipt = await invoke(target, request, timeout)
        return malformed if target == "fixture-1" else receipt

    transport.invoke = wrong_response
    result = await collection.collect_contact_pair(observers, transport=transport)
    assert result["pair"]["decision"] == "WAIT"
    assert result["collection"]["errors"] == [{"provider": "fixture-1", "reason": "INVALID_RESPONSE: receipt envelope required"}]


@pytest.mark.asyncio
async def test_public_receipt_output_redacts_echoed_tokens_in_fields_and_keys(pair):
    observers, make = pair
    transport = FixtureTransport(observers, make)
    invoke = transport.invoke
    tokens = []

    async def echo_token(target, request, timeout):
        receipt = await invoke(target, request, timeout)
        token = request.authorization["token"]
        tokens.append(token)
        receipt.authorization_ref = token
        receipt.error = {"message": token, token: [token]}
        receipt.result["extra"] = token
        return receipt

    transport.invoke = echo_token
    result = await collection.collect_contact_pair(observers, transport=transport)
    encoded = json.dumps(result, allow_nan=False)
    leaked = any(token in encoded for token in tokens)
    assert leaked is False, "Command token entered public output"
    assert result["pair"]["decision"] == "DISPATCH"  # Unsigned echoes never change the signed measurement.
    assert set(result["redacted_receipts"]) == {"fixture-0", "fixture-1"}


@pytest.mark.asyncio
async def test_invalid_signature_echo_never_exposes_the_command_token(pair):
    observers, make = pair
    transport = FixtureTransport(observers, make)
    invoke = transport.invoke
    tokens = []

    async def echo_signature(target, request, timeout):
        receipt = await invoke(target, request, timeout)
        if target == "fixture-1":
            token = request.authorization["token"]
            tokens.append(token)
            receipt.receipt_signature = token
        return receipt

    transport.invoke = echo_signature
    result = await collection.collect_contact_pair(observers, transport=transport)
    leaked = any(token in json.dumps(result, allow_nan=False) for token in tokens)
    assert leaked is False, "Command token entered invalid receipt output"
    assert result["pair"]["decision"] == "WAIT"
    assert result["redacted_receipts"] == ["fixture-1"]
    assert any("INVALID_SIGNATURE" in item["reason"] for item in result["pair"]["rejections"])


@pytest.mark.asyncio
@pytest.mark.parametrize("closed", [float("inf"), float("-inf"), float("nan")])
async def test_nonfinite_receipt_values_leave_a_strict_json_wait_and_partial_response(pair, closed):
    observers, make = pair
    transport = FixtureTransport(observers, make)
    invoke = transport.invoke

    async def nonfinite(target, request, timeout):
        receipt = await invoke(target, request, timeout)
        if target == "fixture-1":
            receipt.result["closed"] = closed
        return receipt

    transport.invoke = nonfinite
    result = await collection.collect_contact_pair(observers, transport=transport)
    json.dumps(result, allow_nan=False)
    assert result["pair"]["decision"] == "WAIT"
    assert set(result["received_receipts"]) == {"fixture-0"}
    assert result["collection"]["errors"] == [{"provider": "fixture-1", "reason": "INVALID_RESPONSE: finite JSON receipt required"}]


@pytest.mark.asyncio
async def test_age_is_evaluated_after_all_responses_arrive(pair, monkeypatch):
    observers, make = pair
    times = iter([100, 111])
    monkeypatch.setattr(collection.time, "time", lambda: next(times))
    result = await collection.collect_contact_pair(observers, transport=FixtureTransport(observers, make))
    assert result["pair"]["decision"] == "WAIT"
    assert all("STALE_EVIDENCE" in item["reason"] for item in result["pair"]["rejections"])


@pytest.mark.asyncio
async def test_actual_ble_adapter_uses_one_scan_and_two_cached_handles_concurrently(pair, monkeypatch):
    observers, make = pair
    devices = [BLEDevice(f"AA:BB:CC:DD:EE:0{i}", f"esp32-c6-fixture-{i}", {}) for i in range(2)]
    scans, connections, writes = [], [], []
    gate = asyncio.Event()

    async def discover(**kwargs):
        scans.append(kwargs)
        return {device.address: (device, SimpleNamespace(local_name=device.name, service_uuids=[ble.SERVICE_UUID])) for device in devices}

    class Client:
        def __init__(self, target, **kwargs):
            assert isinstance(target, BLEDevice)
            self.index = devices.index(target)
            connections.append(target)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def start_notify(self, characteristic, callback):
            self.notify = callback

        async def write_gatt_char(self, characteristic, payload, **kwargs):
            self.request = InvocationRequest(**json.loads(payload))
            writes.append(self.request.device_id)
            if len(writes) == 2:
                gate.set()
            await asyncio.wait_for(gate.wait(), timeout=0.2)
            self.notify(None, b"ready")

        async def read_gatt_char(self, characteristic):
            if characteristic == ble.MANIFEST_UUID:
                return json.dumps({"protocol": "capmesh/0.1", "device_id": observers[self.index].provider,
                    "capabilities": [{"id": "state.observe", "description": "Fixture", "pricing": {}}]}).encode()
            return json.dumps(asdict(make(self.request, self.index))).encode()

    monkeypatch.setattr(ble.BleakScanner, "discover", discover)
    monkeypatch.setattr(ble, "BleakClient", Client)
    result = await collection.collect_contact_pair(observers)
    assert result["pair"]["decision"] == "DISPATCH"
    assert len(scans) == 1 and len(writes) == 2
    assert connections == [devices[0], devices[1], devices[0], devices[1]]


@pytest.fixture
def diagnostic(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    spec = importlib.util.spec_from_file_location("contact_pair_diagnostic", ROOT / "scripts/check_contact_pair.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def profile_for(observers):
    return {"observers": [{"provider": observer.provider, "sensor": observer.sensor,
        "public_key_sec1_hex": observer.public_key.sec1_hex} for observer in observers]}


@pytest.mark.asyncio
async def test_parent_sends_only_snapshotted_public_configuration_and_keeps_unmet_result(pair, diagnostic, monkeypatch):
    import scripts.soak_observations as soak
    observers, _ = pair
    profile = profile_for(observers)
    calls = []
    expected = {"payment_mode": "none; no funds moved", "pair": ContactPairVerifier(observers).verify({}, now=100)}

    async def sample(timeout, *, command):
        calls.append((timeout, command))
        assert json.loads(command[-1]) == profile and "--pins" not in command
        return expected.copy()

    monkeypatch.setattr(soak, "run_sample", sample)
    result = await diagnostic.run_diagnostic(profile)
    assert result["pair"]["reason"].startswith("MISSING_OBSERVER")
    assert result["worker_cleanup_confirmed"] is True and len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["timeout", "cleanup", "worker"])
async def test_parent_timeout_or_cleanup_failure_is_visible_wait_without_retry(pair, diagnostic, monkeypatch, failure):
    import scripts.soak_observations as soak
    observers, _ = pair
    calls = []
    error = {"timeout": TimeoutError(), "cleanup": soak.WorkerCleanupError(),
             "worker": RuntimeError("secret authorization payload")}[failure]

    async def sample(*args, **kwargs):
        calls.append(kwargs)
        raise error

    monkeypatch.setattr(soak, "run_sample", sample)
    result = await diagnostic.run_diagnostic(profile_for(observers))
    assert result["pair"]["decision"] == "WAIT" and len(calls) == 1
    assert result["worker_cleanup_confirmed"] is (failure != "cleanup")
    assert "secret authorization payload" not in json.dumps(result)
    if failure == "cleanup":
        assert "Stop BLE work" in result["collection"]["errors"][0]["action"]


@pytest.mark.asyncio
async def test_real_process_helper_signal_failure_reports_unconfirmed_cleanup_and_worker_pid(pair, diagnostic, monkeypatch):
    import scripts.soak_observations as soak
    observers, _ = pair

    class Worker:
        pid = 123456789
        returncode = None

        async def communicate(self):
            await asyncio.Event().wait()

        async def wait(self):
            await asyncio.Event().wait()

    async def spawn(*args, **kwargs):
        return Worker()

    def deny_signal(*args):
        raise PermissionError("signal denied")

    actual_sample = soak.run_sample
    async def sample(*args, **kwargs):
        return await actual_sample(0.01, cleanup_seconds=0.01, **kwargs)

    monkeypatch.setattr(soak.asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(soak.os, "killpg", deny_signal)
    monkeypatch.setattr(soak, "run_sample", sample)
    result = await diagnostic.run_diagnostic(profile_for(observers))
    assert result["pair"]["decision"] == "WAIT"
    assert result["worker_cleanup_confirmed"] is False
    assert result["collection"]["errors"][0]["worker_pid"] == Worker.pid


def test_worker_returns_unmet_policy_as_json_with_successful_transport_exit(pair, diagnostic, monkeypatch, capsys):
    observers, _ = pair
    async def collect(_):
        return {"pair": ContactPairVerifier(observers).verify({}, now=100)}
    monkeypatch.setattr(diagnostic, "collect_contact_pair", collect)
    monkeypatch.setattr(sys, "argv", ["check_contact_pair", "--worker-profile", json.dumps(profile_for(observers))])
    assert diagnostic.main() == 0
    assert json.loads(capsys.readouterr().out)["pair"]["decision"] == "WAIT"


def test_public_profile_refuses_unknown_provider_duplicate_key_or_unsupported_input_before_worker(pair, diagnostic, tmp_path):
    observers, _ = pair
    path = tmp_path / "pins.json"
    path.write_text(json.dumps({"algorithm": "ecdsa-p256-sha256", "providers": {
        observer.provider: observer.public_key.sec1_hex for observer in observers}}))
    valid = [f"{observer.provider}:{observer.sensor}" for observer in observers]
    assert diagnostic.public_profile(valid, path) == profile_for(observers)
    for selections in [[], [valid[0]], [valid[0], valid[0]], [valid[0], "missing:gpio18-contact"],
                       [valid[0], "fixture-1:gpio12-contact"], [valid[0], "fixture-1:simulated-contact"]]:
        with pytest.raises(ValueError):
            diagnostic.public_profile(selections, path)
    duplicate = profile_for(observers)
    duplicate["observers"][1]["public_key_sec1_hex"] = duplicate["observers"][0]["public_key_sec1_hex"]
    with pytest.raises(ValueError, match="distinct public"):
        diagnostic.observers_from_profile(duplicate)
