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


def test_owner_reads_use_the_finalized_snapshot_without_mutating_sdk_parameters():
    module = load_checker()
    sent = []

    def send(method, params):
        sent.append((method, params))
        return {"result": "fixture"}

    original = [{"to": "public contract", "data": "public call"}, "latest"]
    module.guarded_request(send, "eth_call", original, read_block=123)
    assert original[1] == "latest"
    assert sent == [("eth_call", [original[0], "0x7b"])]
    for params in [[original[0], "0x7a"], [original[0], "pending"], [original[0], "latest", {}]]:
        with pytest.raises(ValueError):
            module.guarded_request(send, "eth_call", params, read_block=123)
    assert len(sent) == 1
    with pytest.raises(PermissionError):
        module.guarded_request(send, "eth_sendRawTransaction", [], read_block=123)


class LookupError(Exception):
    def __init__(self, code, solidity_error=None):
        self.code = code
        self.solidity_error = solidity_error


def test_registry_read_distinguishes_owner_absence_foreign_home_and_failure():
    module = load_checker()
    owner = "0x" + "12" * 20
    assert module.registration_state(lambda _: owner, 123, LookupError)["owner"] == owner

    def lookup(code, solidity_error=None):
        def read(_):
            raise LookupError(code, solidity_error)
        return read

    absent = module.registration_state(lookup("MACHINE_NOT_FOUND", "ERC721NonexistentToken"), 123, LookupError)
    assert absent["status"] == "not_found_at_block" and absent["owner"] is None
    assert module.registration_state(lookup("MACHINE_HOMED_ELSEWHERE"), 123, LookupError)["status"] == "homed_elsewhere"
    for code, solidity_error in [("READ_FAILED", None), ("RPC_RATE_LIMITED", None),
                                  ("CHAIN_MISMATCH", None), ("MACHINE_NOT_FOUND", None)]:
        with pytest.raises(LookupError):
            module.registration_state(lookup(code, solidity_error), 123, LookupError)


@pytest.mark.parametrize("owner", [None, "unverified", "0x" + "00" * 20, "0x" + "zz" * 20])
def test_registry_read_rejects_invalid_owner(owner):
    module = load_checker()
    with pytest.raises(ValueError, match="invalid owner"):
        module.registration_state(lambda _: owner, 123, LookupError)


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


def test_selected_peaq_subject_binds_provider_and_key_without_discovery():
    module = load_checker()
    pins = json.loads((Path(__file__).resolve().parents[1] / "host/capmesh/protocol/receipt_keys.json").read_text())
    another = ec.derive_private_key(11, ec.SECP256R1()).public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint).hex()
    pins["providers"]["second-observer"] = another
    subject = module.observer_subject(pins, "second-observer")
    assert json.loads(subject)["provider"] == "second-observer"
    assert json.loads(subject)["public_key_sec1_hex"] == another
    assert subject != module.observer_subject(pins)
    for provider in ["unknown", "../board", None]:
        with pytest.raises(ValueError):
            module.observer_subject(pins, provider)


@pytest.mark.parametrize("key", ["04" + "00" * 64, "04" + "zz" * 64, None])
def test_identity_proposal_rejects_an_invalid_public_point(key):
    module = load_checker()
    with pytest.raises(ValueError):
        module.observer_subject({"algorithm": "ecdsa-p256-sha256",
                                "providers": {"esp32-c6-96a2": key}})


@pytest.mark.parametrize("pins", [None, [], {"providers": []}, {"providers": None}])
def test_identity_proposal_rejects_malformed_pin_containers(pins):
    with pytest.raises(ValueError, match="public pin"):
        load_checker().observer_subject(pins)
