"""Public verification must not grant authority to create device receipts."""

import base64
from dataclasses import replace

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

from capmesh.observations import EvidenceError, ObservationContract, ObservationVerifier, observation_request
from capmesh.protocol.auth import DEFAULT_SECRET, compute_hmac_sha256, receipt_message, verify_receipt
from capmesh.protocol.identity import ReceiptPublicKey
from capmesh.protocol.models import InvocationReceipt


@pytest.fixture
def signed_observation():
    key = ec.generate_private_key(ec.SECP256R1())
    pin = ReceiptPublicKey(key.public_key().public_bytes(serialization.Encoding.X962,
                                                       serialization.PublicFormat.UncompressedPoint).hex())
    request = observation_request("device-under-test", ObservationContract(), now=1790860000, nonce=123)
    receipt = InvocationReceipt(protocol=request.protocol, request_id=request.request_id, status="success",
        provider=request.device_id, capability=request.capability, nonce=request.nonce, parameters=request.parameters,
        result={"metric": "gate.closed", "sensor": "gpio9-contact", "closed": False, "stable_samples": 5, "total_samples": 5},
        started_at=request.timestamp, completed_at=request.timestamp)
    r, s = utils.decode_dss_signature(key.sign(receipt_message(receipt).encode(), ec.ECDSA(hashes.SHA256())))
    receipt.receipt_signature = "v3:" + base64.b64encode(r.to_bytes(32, "big") + s.to_bytes(32, "big")).decode()
    return receipt, request, pin


def test_device_receipt_uses_only_a_pinned_public_key(signed_observation):
    receipt, request, pin = signed_observation
    buyer = ObservationVerifier({request.device_id: pin})
    decision = buyer.verify(receipt, request, ObservationContract(), now=request.timestamp)
    assert decision["decision"] == "DISPATCH"
    assert decision["receipt_identity"] == "pinned-device-p256"
    assert not verify_receipt(receipt)  # The command HMAC cannot verify a device signature.
    with pytest.raises(EvidenceError, match="REPLAY_DETECTED"):
        buyer.verify(receipt, request, ObservationContract(), now=request.timestamp)


def test_public_demo_secret_cannot_forge_a_pinned_device_receipt(signed_observation):
    receipt, request, pin = signed_observation
    forged = replace(receipt, result={**receipt.result, "closed": True})
    forged.receipt_signature = "v2:" + compute_hmac_sha256(DEFAULT_SECRET, receipt_message(forged))
    assert verify_receipt(forged)  # Reproduces the old demonstration's forgery boundary.
    with pytest.raises(EvidenceError, match="INVALID_SIGNATURE"):
        ObservationVerifier({request.device_id: pin}).verify(forged, request, ObservationContract(), now=request.timestamp)


@pytest.mark.parametrize("field,value", [("protocol", "other/0.1"), ("request_id", "another"),
    ("provider", "impostor"), ("capability", "led.blink"), ("nonce", 124),
    ("parameters", {"location": "elsewhere"}), ("started_at", 1790859999), ("completed_at", 1790860001)])
def test_device_signature_binds_envelope_fields(signed_observation, field, value):
    receipt, _, pin = signed_observation
    assert not verify_receipt(replace(receipt, **{field: value}), public_key=pin)


@pytest.mark.parametrize("field,value", [("closed", True), ("metric", "room.occupancy"),
    ("sensor", "simulated-contact"), ("stable_samples", 4), ("total_samples", 6)])
def test_device_signature_binds_measurement_fields(signed_observation, field, value):
    receipt, _, pin = signed_observation
    assert not verify_receipt(replace(receipt, result={**receipt.result, field: value}), public_key=pin)


def test_other_key_or_malformed_signature_fails_closed(signed_observation):
    receipt, _, pin = signed_observation
    other = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint).hex()
    assert not verify_receipt(receipt, public_key=ReceiptPublicKey(other))
    for signature in [None, 123, "v3:AAAA", receipt.receipt_signature + "=", receipt.receipt_signature + "\n", "v2:deadbeef"]:
        assert not verify_receipt(replace(receipt, receipt_signature=signature), public_key=pin)
    with pytest.raises(ValueError):
        ReceiptPublicKey("04" + "00" * 64)


def test_a_valid_device_signature_does_not_override_freshness(signed_observation):
    receipt, request, pin = signed_observation
    with pytest.raises(EvidenceError, match="STALE_EVIDENCE"):
        ObservationVerifier({request.device_id: pin}).verify(receipt, request, ObservationContract(), now=request.timestamp + 11)
