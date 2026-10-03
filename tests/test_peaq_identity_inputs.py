import importlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

@pytest.fixture
def preparer(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    return importlib.import_module("scripts.prepare_peaq_identity")


def pins():
    return json.loads((Path(__file__).resolve().parents[1] / "host/capmesh/protocol/receipt_keys.json").read_text())


def decode_public_multikey(value):
    # Independent base58btc decoding, used only to inspect the public wire format.
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    assert value.startswith("z")
    number = 0
    for char in value[1:]:
        number = number * 58 + alphabet.index(char)
    return number.to_bytes((number.bit_length() + 7) // 8, "big")


def test_key_binding_preserves_public_point_and_existing_permanent_subject(preparer):
    trusted = pins()
    draft = preparer.prepare(trusted)
    assert draft["credential_subject_utf8"].encode() == preparer.observer_subject(trusted)
    encoded = decode_public_multikey(draft["verification_methods"][0]["public_key_multibase"])
    assert encoded[:2] == b"\x80\x24" and len(encoded) == 35
    point = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), encoded[2:])
    assert point.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint).hex() == trusted["providers"]["esp32-c6-96a2"]
    assert draft["controller"] is None and draft["activated"] is False
    assert draft["sdk_validation"] == "not_run"
    with pytest.raises(ValueError, match="requires explicit"):
        preparer.validate_with_sdk(draft)


def test_published_w3c_p256_multikey_example_reencodes_exactly(preparer):
    # W3C ECDSA Cryptosuites v1.0, section 2.1.1, Example 1 (May 15, 2025).
    example = "zDnaerx9CtbPJ1q36T5Ln5wYt3MQYeGRG5ehnPAmxcf5mDZpv"
    encoded = decode_public_multikey(example)
    assert encoded[:2] == b"\x80\x24" and len(encoded) == 35
    public = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), encoded[2:])
    uncompressed = public.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    assert preparer.public_multikey(uncompressed.hex()) == example


def test_service_selection_binds_provider_and_supported_sensor_without_changing_identity(preparer):
    trusted = pins()
    trusted["providers"]["second-observer"] = trusted["providers"]["esp32-c6-96a2"]
    draft = preparer.prepare(trusted, "second-observer", "gpio18-contact")
    assert draft["service_endpoints"][0]["service_endpoint"] == "urn:fieldproof:ble-contact:second-observer:gpio18-contact:state.observe"
    assert draft["credential_subject_utf8"].encode() == preparer.observer_subject(trusted, "second-observer")
    assert draft["credential_subject_utf8"] == preparer.prepare(trusted, "second-observer", "gpio9-contact")["credential_subject_utf8"]
    assert draft["service_contract"]["installation_verified_by_this_script"] is False
    with pytest.raises(ValueError):
        preparer.prepare(trusted, "../untrusted")
    with pytest.raises(ValueError):
        preparer.prepare(trusted, sensor="gpio20-output")


@pytest.mark.parametrize("overrides", [
    {"manufacturer": None},
    {"controller": "private-key"},
    {"controller": "0x" + "00" * 20},
    {"manufacturer": "not-an-address"},
    {"max_net_base_units": -1}, {"max_net_base_units": True}, {"max_net_base_units": 2**256},
])
def test_invalid_or_incomplete_public_activation_inputs_fail_locally(preparer, overrides):
    args = {"controller": "0x" + "11" * 20, "manufacturer": "0x" + "00" * 20,
            "max_net_base_units": 400000000000000000}
    args.update(overrides)
    with pytest.raises(ValueError):
        preparer.prepare(pins(), **args)


def test_explicit_claims_remain_a_draft_without_spending_authorization(preparer):
    draft = preparer.prepare(pins(), controller="0x" + "11" * 20, manufacturer="0x" + "00" * 20,
                    max_net_base_units=400000000000000000)
    assert draft["max_net_peaq_amount"] == "400000000000000000"
    assert draft["authentication"] == [0] and draft["activated"] is False
    assert draft["verification_methods"][0]["controller"] == draft["controller"]
    assert "not spending authorization" in draft["limits"]
