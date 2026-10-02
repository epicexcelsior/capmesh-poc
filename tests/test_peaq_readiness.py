import importlib.util
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def load_checker():
    path = Path(__file__).resolve().parents[1] / "scripts/check_peaq_readiness.py"
    spec = importlib.util.spec_from_file_location("peaq_readiness", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_readiness_transport_refuses_signing_and_writes_before_network():
    module = load_checker()
    sent = []

    def send(method, params):
        sent.append((method, params))
        return {"result": "read fixture"}

    for method in ("eth_sendRawTransaction", "eth_sendTransaction", "personal_sign", "eth_sign", "eth_estimateGas"):
        with pytest.raises(PermissionError, match="refuses"):
            module.guarded_request(send, method, [])
    assert sent == []
    assert module.guarded_request(send, "eth_chainId", []) == {"result": "read fixture"}
    assert sent == [("eth_chainId", [])]


def test_identity_proposal_binds_only_the_public_pin():
    module = load_checker()
    pins = json.loads((Path(__file__).resolve().parents[1] / "host/capmesh/protocol/receipt_keys.json").read_text())
    subject = module.observer_subject(pins)
    assert module.observer_subject({**pins, "unrelated": "ignored"}) == subject
    assert json.loads(subject)["public_key_sec1_hex"] == pins["providers"]["esp32-c6-96a2"]
    other = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint).hex()
    changed = {**pins, "providers": {"esp32-c6-96a2": other}}
    assert module.observer_subject(changed) != subject
    with pytest.raises(ValueError, match="provisioned"):
        module.observer_subject({"providers": {}})


@pytest.mark.parametrize("key", ["04" + "00" * 64, "04" + "zz" * 64, None])
def test_identity_proposal_rejects_an_invalid_public_point(key):
    module = load_checker()
    with pytest.raises(ValueError):
        module.observer_subject({"algorithm": "ecdsa-p256-sha256",
                                "providers": {"esp32-c6-96a2": key}})
