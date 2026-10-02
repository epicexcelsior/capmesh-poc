"""Configured contact selection crosses the buyer, pin loader, and gateway worker boundaries."""

import base64
from dataclasses import replace
import importlib.util
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

from capmesh.agent.observation_demo import run_observation_demo
from capmesh.observations import EvidenceError, ObservationContract, ObservationVerifier, observation_request
from capmesh.protocol.auth import receipt_message
from capmesh.protocol.identity import ReceiptPublicKey, provisioned_observation_keys
from capmesh.protocol.models import InvocationReceipt
from capmesh.provider.observation_provider import SimulatedContactProvider


def key_pin(number=7):
    key = ec.derive_private_key(number, ec.SECP256R1())
    pin = ReceiptPublicKey(key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint).hex())
    return key, pin


def signed_receipt(request, sensor="gpio18-contact", key=None):
    key = key or key_pin()[0]
    receipt = InvocationReceipt(protocol=request.protocol, request_id=request.request_id, status="success",
        provider=request.device_id, capability=request.capability, nonce=request.nonce, parameters=request.parameters,
        result={"metric": "gate.closed", "sensor": sensor, "closed": False, "stable_samples": 5, "total_samples": 5},
        started_at=request.timestamp, completed_at=request.timestamp)
    r, s = utils.decode_dss_signature(key.sign(receipt_message(receipt).encode(), ec.ECDSA(hashes.SHA256())))
    receipt.receipt_signature = "v3:" + base64.b64encode(r.to_bytes(32, "big") + s.to_bytes(32, "big")).decode()
    return receipt


def test_external_receipt_requires_the_exact_selected_sensor_and_device_pin():
    key, pin = key_pin()
    contract = ObservationContract(sensor="gpio18-contact")
    request = observation_request("second-observer", contract, now=1790860000, nonce=123)
    receipt = signed_receipt(request, key=key)
    decision = ObservationVerifier({request.device_id: pin}).verify(receipt, request, contract, now=request.timestamp)
    assert decision["decision"] == "DISPATCH"
    assert decision["receipt_identity"] == "pinned-device-p256"
    for wrong_contract in [ObservationContract(), ObservationContract(sensor="gpio9-contact"),
                           ObservationContract(sensor="gpio19-contact")]:
        with pytest.raises(EvidenceError, match="INVALID_MEASUREMENT"):
            ObservationVerifier({request.device_id: pin}).verify(receipt, request, wrong_contract, now=request.timestamp)
    with pytest.raises(EvidenceError, match="INVALID_SIGNATURE"):
        ObservationVerifier({request.device_id: key_pin(8)[1]}).verify(receipt, request, contract, now=request.timestamp)
    for wrong_request in [replace(request, nonce=124), replace(request, device_id="other-observer")]:
        with pytest.raises(EvidenceError):
            ObservationVerifier({request.device_id: pin, "other-observer": pin}).verify(
                receipt, wrong_request, contract, now=request.timestamp)


def test_explicit_gpio9_contract_preserves_the_real_recorded_paid_receipt():
    path = Path(__file__).resolve().parents[1] / "docs/evidence/device-signed-purchase.json"
    purchase = json.loads(path.read_text())["purchase"]
    receipt = InvocationReceipt.from_dict(purchase["receipt"])
    challenge = purchase["challenge"]
    contract = ObservationContract(sensor="gpio9-contact")
    request = observation_request(receipt.provider, contract, request_id=challenge["id"],
                                  nonce=challenge["nonce"], now=challenge["created_at"])
    accepted_at = receipt.completed_at + purchase["evidence_age_seconds"]
    pins = provisioned_observation_keys()
    result = ObservationVerifier(pins).verify(receipt, request, contract, now=accepted_at)
    assert result["decision"] == purchase["decision"]
    assert result["age_seconds"] == 7
    assert result["receipt_identity"] == "pinned-device-p256"
    with pytest.raises(EvidenceError, match="STALE_EVIDENCE"):
        ObservationVerifier(pins).verify(receipt, request, contract, now=receipt.completed_at + 11)
    with pytest.raises(EvidenceError, match="INVALID_MEASUREMENT"):
        ObservationVerifier(pins).verify(receipt, request, ObservationContract(sensor="gpio18-contact"), now=accepted_at)


@pytest.mark.parametrize("sensor", ["gpio4-contact", "gpio8-contact", "gpio10-contact", "gpio12-contact",
                                    "gpio15-contact", "gpio24-contact", "GPIO18", [], 18])
def test_contact_contract_rejects_unsupported_inputs(sensor):
    with pytest.raises(ValueError, match="supported GPIO"):
        ObservationContract(sensor=sensor)


def test_public_pin_file_selects_multiple_distinct_providers(tmp_path):
    pins = {"algorithm": "ecdsa-p256-sha256", "providers": {
        "board-one": key_pin()[1].sec1_hex, "board-two": key_pin(8)[1].sec1_hex}}
    path = tmp_path / "pins.json"
    path.write_text(json.dumps(pins))
    loaded = provisioned_observation_keys(path)
    assert loaded["board-one"] != loaded["board-two"]
    for providers in [{}, {"invalid/id": key_pin()[1].sec1_hex}, {"board": None}, {"board": "04" + "00" * 64}]:
        path.write_text(json.dumps({**pins, "providers": providers}))
        with pytest.raises(ValueError):
            provisioned_observation_keys(path)


@pytest.mark.asyncio
async def test_unprovisioned_provider_fails_before_transport_discovery(monkeypatch, tmp_path):
    def no_transport():
        pytest.fail("Unprovisioned selection must fail before Bluetooth access")
    monkeypatch.setattr("capmesh.agent.observation_demo.BLETransportAdapter", no_transport)
    with pytest.raises(ValueError, match="no buyer-provisioned public key"):
        await run_observation_demo(provider="unknown", sensor="gpio18-contact", ledger_path=tmp_path / "demand.sqlite")
    assert not (tmp_path / "demand.sqlite").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("options", [{"sensor": "simulated-contact"}, {"sensor": None}, {"sensor": []},
    {"simulated": True, "sensor": "gpio18-contact"}, {"simulated": True, "sensor": []}])
async def test_demo_rejects_mixed_physical_and_simulated_terms_before_io(monkeypatch, tmp_path, options):
    monkeypatch.setattr("capmesh.agent.observation_demo.BLETransportAdapter", lambda: pytest.fail("No Bluetooth access is allowed"))
    with pytest.raises(ValueError, match="Physical mode|Simulation reports"):
        await run_observation_demo(ledger_path=tmp_path / "demand.sqlite", **options)
    assert not (tmp_path / "demand.sqlite").exists()


@pytest.mark.asyncio
async def test_custom_provider_simulation_remains_labeled_and_rejects_attacks(tmp_path):
    result = await run_observation_demo(simulated=True, provider="demo-second", closed=True,
                                       ledger_path=tmp_path / "demand.sqlite")
    assert result["mode"] == "SIMULATED"
    assert result["provider"] == "demo-second"
    assert result["receipt"]["result"]["sensor"] == "simulated-contact"
    assert result["decision"]["decision"] == "WAIT"
    assert result["attacks_passed"] is True


def load_bridge():
    path = Path(__file__).resolve().parents[1] / "gateway/bridge_call.py"
    spec = importlib.util.spec_from_file_location("contact_bridge", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_bridge_uses_the_persisted_public_pin_and_exact_external_contract(monkeypatch):
    bridge = load_bridge()
    calls = []

    class FakeBLE:
        async def discover(self, timeout):
            calls.append("discover")
            return await SimulatedContactProvider("second-observer").discover()

        async def invoke(self, target, request):
            calls.append(target)
            return signed_receipt(request)

    monkeypatch.setattr(bridge, "BLETransportAdapter", FakeBLE)
    monkeypatch.setenv("FIELDPROOF_RECEIPT_PINS", "/nonexistent/replaced-after-quote.json")
    purchase = {"id": "0123456789abcdef", "nonce": 123, "location": "demo-gate", "max_age_seconds": 10,
        "contact": {"provider": "second-observer", "sensor": "gpio18-contact"},
        "receipt_public_key": key_pin()[1].sec1_hex, "simulated": False}
    result = await bridge.run(purchase)
    assert result["decision"]["decision"] == "DISPATCH"
    assert result["receipt"]["provider"] == "second-observer"
    assert calls == ["discover", "second-observer"]
    with pytest.raises(EvidenceError, match="INVALID_MEASUREMENT"):
        await bridge.run({**purchase, "contact": {**purchase["contact"], "sensor": "gpio19-contact"}})


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [{"receipt_public_key": "04" + "00" * 64}, {"simulated": True},
    {"contact": {"provider": "second-observer", "sensor": "simulated-contact"}}])
async def test_invalid_bridge_terms_fail_before_bluetooth(monkeypatch, change):
    bridge = load_bridge()
    monkeypatch.setattr(bridge, "BLETransportAdapter", lambda: pytest.fail("No Bluetooth access is allowed"))
    purchase = {"id": "0123456789abcdef", "nonce": 123, "location": "demo-gate", "max_age_seconds": 10,
        "contact": {"provider": "second-observer", "sensor": "gpio18-contact"},
        "receipt_public_key": key_pin()[1].sec1_hex, "simulated": False}
    with pytest.raises(ValueError):
        await bridge.run({**purchase, **change})
