"""Prepare public observer identity inputs offline. Never sign, connect, or activate.

Run from the repository root with python -m scripts.prepare_peaq_identity.
Optional SDK validation needs isolated peaq-os-sdk==0.10.0, plus explicit public
controller, manufacturer, and net-bond bound. It validates local inputs only.
"""

import argparse
from importlib.metadata import version
import json
from pathlib import Path
import re
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from scripts.check_peaq_readiness import ROOT, SDK_VERSION, observer_subject

BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
MACHINE_TYPE = "FieldProofContactObserverV1"


def public_multikey(key_hex):
    """Encode a validated P-256 public point with multicodec 0x1200 and base58btc."""
    point = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), bytes.fromhex(key_hex))
    compressed = point.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.CompressedPoint)
    # Unsigned varint for p256-pub (0x1200). No private key bytes enter this encoding.
    payload = b"\x80\x24" + compressed
    number = int.from_bytes(payload, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = BASE58[remainder] + encoded
    return "z" + encoded


def prepare(pins, provider="esp32-c6-96a2", sensor="gpio9-contact", *,
            controller=None, manufacturer=None, max_net_base_units=None):
    subject = observer_subject(pins, provider)
    if sensor not in {"gpio9-contact", "gpio18-contact"}:
        raise ValueError("Select gpio9-contact or gpio18-contact. This script does not verify installation.")
    supplied = (controller is not None, manufacturer is not None, max_net_base_units is not None)
    if any(supplied) and not all(supplied):
        raise ValueError("Supply controller, manufacturer, and max-net-base-units together.")
    if all(supplied):
        for name, address in (("controller", controller), ("manufacturer", manufacturer)):
            if not isinstance(address, str) or re.fullmatch(r"0x[0-9a-fA-F]{40}", address) is None:
                raise ValueError(f"Supply a public 0x-prefixed 20-byte {name} address.")
        if int(controller[2:], 16) == 0:
            raise ValueError("The controller address must not be zero.")
        if type(max_net_base_units) is not int or not 0 <= max_net_base_units < 2**256:
            raise ValueError("The net-bond bound must be an unsigned 256-bit integer.")
    key_hex = json.loads(subject)["public_key_sec1_hex"]
    # This URN names a local BLE capability. It is not an HTTPS endpoint or a registry resolver.
    endpoint = f"urn:fieldproof:ble-contact:{provider}:{sensor}:state.observe"
    return {
        "status": "offline_public_input_draft", "activated": False,
        "machine_type": MACHINE_TYPE, "credential_subject_utf8": subject.decode(),
        "controller": controller, "manufacturer": manufacturer, "tier": 0,
        "max_net_peaq_amount": str(max_net_base_units) if max_net_base_units is not None else None,
        "verification_methods": [{"id": "#receipt-key", "method_type": "Multikey",
                                  "controller": controller, "public_key_multibase": public_multikey(key_hex)}],
        "authentication": [0],
        "service_endpoints": [{"id": "#contact-observation", "service_type": "FieldProofBLEContactV1",
                               "service_endpoint": endpoint}],
        "service_contract": {"provider": provider, "sensor": sensor, "capability": "state.observe",
                             "state_measured": "electrical contact", "transport": "local BLE",
                             "installation_verified_by_this_script": False},
        "sdk_validation": "not_run",
        "remaining_gates": [
            "Review public controller, manufacturer, and service claims.",
            "Select the signing owner wallet. The signer owns the identity and pays the bond.",
            "Refresh registry ownership and full operator-specific preflight.",
            "Review bond, allowance, funding, gas bound, and permanent identity inputs.",
            "Authorize activation explicitly. Reconcile each submitted transaction before any retry.",
            "Read owner, controller, key, and service back. Compare the independent buyer pin.",
        ],
        "limits": "No wallet, network, preview, transaction, key-possession proof, site permission, or physical truth check. "
                  "The service URN is a public label for a local BLE capability. No automatic registry discovery exists. "
                  "SDK validation checks input shape, not claims or funding. A spend bound is not spending authorization.",
    }


def validate_with_sdk(draft):
    """Use published SDK input validation and DID struct encoding without a client or account."""
    if draft["controller"] is None:
        raise ValueError("SDK validation requires explicit controller, manufacturer, and net-bond bound.")
    if version("peaq-os-sdk") != SDK_VERSION:
        raise ValueError(f"Use peaq-os-sdk=={SDK_VERSION} in an isolated environment.")
    from peaq_os_sdk.tokenomics.activation_types import ActivateMachineParams, ServiceEndpointInput, VerificationMethodInput
    from peaq_os_sdk.tokenomics._internal.encode_did import encode_did_document
    from peaq_os_sdk.validation.tokenomics_activation import validate_activate_machine_params

    params = ActivateMachineParams(
        controller=draft["controller"], manufacturer=draft["manufacturer"], tier=draft["tier"],
        machine_type=draft["machine_type"], credential_subject=draft["credential_subject_utf8"].encode(),
        verification_methods=tuple(VerificationMethodInput(**entry) for entry in draft["verification_methods"]),
        authentication=tuple(draft["authentication"]),
        service_endpoints=tuple(ServiceEndpointInput(**entry) for entry in draft["service_endpoints"]),
        max_net_peaq_amount=int(draft["max_net_peaq_amount"]),
    )
    validate_activate_machine_params(params)
    return {**draft, "sdk_validation": f"peaq-os-sdk=={SDK_VERSION}: local input validation passed",
            "did_document_argument": encode_did_document(params)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default="esp32-c6-96a2")
    parser.add_argument("--sensor", choices=("gpio9-contact", "gpio18-contact"), default="gpio9-contact")
    parser.add_argument("--pins", type=Path, default=Path("host/capmesh/protocol/receipt_keys.json"))
    parser.add_argument("--controller", help="Explicit public EVM controller address. No private key.")
    parser.add_argument("--manufacturer", help="Explicit recorded manufacturer address. This claim is not verified.")
    parser.add_argument("--max-net-base-units", type=int, help="Reviewed net-bond bound, excluding gas. No spending authorization.")
    parser.add_argument("--sdk-validate", action="store_true", help="Validate and encode local inputs with isolated SDK 0.10.0.")
    args = parser.parse_args()
    try:
        pins = json.loads((ROOT / args.pins).read_text())
        draft = prepare(pins, args.provider, args.sensor, controller=args.controller,
                        manufacturer=args.manufacturer, max_net_base_units=args.max_net_base_units)
        if args.sdk_validate:
            draft = validate_with_sdk(draft)
        print(json.dumps(draft, indent=2))
    except (ValueError, OSError, ImportError) as error:
        print(f"Offline peaq input preparation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
