import hmac
import hashlib
import secrets
import json
import base64
import binascii
from dataclasses import asdict
from typing import Dict, Any
from .models import InvocationReceipt
from .identity import ReceiptPublicKey
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils

DEFAULT_SECRET = "capmesh-secret-key-2026"

def generate_nonce() -> int:
    """Generate a random 32-bit positive integer nonce."""
    return secrets.randbelow(0x7FFFFFFF) + 1

def compute_hmac_sha256(key: str, message: str) -> str:
    """Compute HMAC-SHA256 hex digest."""
    return hmac.new(key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()

def create_auth_payload(
    request_id: str,
    capability: str,
    nonce: int,
    expiration: int,
    device_id: str = "",
    parameters: Dict[str, Any] | None = None,
    timestamp: int = 0,
    auth_type: str = "hmac-sha256",
    secret: str = DEFAULT_SECRET
) -> Dict[str, Any]:
    """Create an authorization payload for capability invocation."""
    if auth_type == "mock":
        return {"type": "mock", "token": "mock-auth-token"}
    
    if auth_type == "hmac-sha256":
        if capability == "state.observe":
            if not device_id or not parameters or not timestamp:
                raise ValueError("Observation authorization requires device, location, and timestamp")
            msg = (
                f"fieldproof-auth-v1|{request_id}|{device_id}|{capability}|"
                f"{parameters['location']}|{nonce}|{timestamp}|{expiration}"
            )
        elif capability == "led.blink":
            if not device_id or not parameters or not timestamp:
                raise ValueError("LED authorization requires device_id, parameters, and timestamp")
            msg = (
                f"capmesh-auth-v2|{request_id}|{device_id}|{capability}|"
                f"{parameters['duration']}|{parameters['count']}|{nonce}|{timestamp}|{expiration}"
            )
        else:
            msg = f"{request_id}:{capability}:{nonce}:{expiration}"
        token = compute_hmac_sha256(secret, msg)
        return {"type": "hmac-sha256-v2" if capability in ("led.blink", "state.observe") else "hmac-sha256", "token": token}
    
    raise ValueError(f"Unsupported auth_type: {auth_type}")

def receipt_message(receipt: InvocationReceipt) -> str:
    """Return the canonical receipt payload for HMAC or device signing."""
    if receipt.capability == "state.observe":
        if not receipt.parameters or not receipt.result:
            raise ValueError("Observation receipt is missing signed fields")
        result = receipt.result
        # Canonicalize only protocol Booleans. Numeric coercion can accept malformed values or raise before rejection.
        if type(result["closed"]) is not bool:
            raise ValueError("Observation contact state must be a Boolean")
        return (
            f"fieldproof-observation-v1|{receipt.protocol}|{receipt.request_id}|{receipt.provider}|"
            f"{receipt.capability}|{receipt.parameters['location']}|{receipt.nonce}|"
            f"{result['metric']}|{result['sensor']}|{int(result['closed'])}|"
            f"{result['stable_samples']}|{result['total_samples']}|"
            f"{receipt.started_at}|{receipt.completed_at}"
        )
    elif receipt.capability == "led.blink":
        if not receipt.parameters or not receipt.result or not receipt.delivery_proof:
            raise ValueError("LED receipt is missing signed fields")
        proof = receipt.delivery_proof
        return (
            f"capmesh-receipt-v2|{receipt.request_id}|{receipt.provider}|{receipt.capability}|"
            f"{receipt.parameters['duration']}|{receipt.parameters['count']}|"
            f"{receipt.result['blinks_completed']}|{proof.observer_id}|{proof.expected_state}|"
            f"{proof.observed_state}|{proof.verified_samples}|{proof.total_samples}|"
            f"{int(proof.readback_verified)}|{receipt.started_at}|{receipt.completed_at}"
        )
    else:
        return json.dumps({
            "request_id": receipt.request_id,
            "provider": receipt.provider,
            "capability": receipt.capability,
            "parameters": receipt.parameters,
            "result": receipt.result,
            "delivery_proof": asdict(receipt.delivery_proof) if receipt.delivery_proof else None,
            "started_at": receipt.started_at,
            "completed_at": receipt.completed_at,
        }, sort_keys=True, separators=(",", ":"))


def verify_receipt(receipt: InvocationReceipt, secret: str = DEFAULT_SECRET, require_delivery_proof: bool = False,
                   *, public_key: ReceiptPublicKey | None = None) -> bool:
    """Verify the signed receipt fields and optional pad readback claim."""
    if receipt.status != "success" or not isinstance(receipt.receipt_signature, str) or not receipt.receipt_signature:
        return False
    if public_key is not None:
        # A provisioned asymmetric identity never falls back to the public demo HMAC.
        if receipt.capability != "state.observe" or not receipt.receipt_signature.startswith("v3:") or require_delivery_proof:
            return False
        try:
            encoded = receipt.receipt_signature[3:]
            signature = base64.b64decode(encoded, validate=True)
            if len(signature) != 64 or base64.b64encode(signature).decode() != encoded:
                return False
            der = utils.encode_dss_signature(int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big"))
            key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), bytes.fromhex(public_key.sec1_hex))
            key.verify(der, receipt_message(receipt).encode(), ec.ECDSA(hashes.SHA256()))
            return True
        except (InvalidSignature, KeyError, TypeError, ValueError, binascii.Error):
            return False
    if not receipt.receipt_signature.startswith("v2:"):
        return False
    try:
        expected = compute_hmac_sha256(secret, receipt_message(receipt))
    except (KeyError, TypeError, ValueError):
        return False
    if not hmac.compare_digest(expected, receipt.receipt_signature[3:]):
        return False
        
    if require_delivery_proof:
        if receipt.delivery_proof is None or not receipt.delivery_proof.readback_verified:
            return False
            
    return True
