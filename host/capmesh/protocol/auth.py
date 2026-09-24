import hmac
import hashlib
import time
import random
from typing import Dict, Any
from .models import InvocationReceipt

DEFAULT_SECRET = "capmesh-secret-key-2026"

def generate_nonce() -> int:
    """Generate a random 32-bit positive integer nonce."""
    return random.randint(1, 0x7FFFFFFF)

def compute_hmac_sha256(key: str, message: str) -> str:
    """Compute HMAC-SHA256 hex digest."""
    return hmac.new(key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()

def create_auth_payload(
    request_id: str,
    capability: str,
    nonce: int,
    expiration: int,
    auth_type: str = "hmac-sha256",
    secret: str = DEFAULT_SECRET
) -> Dict[str, Any]:
    """Create an authorization payload for capability invocation."""
    if auth_type == "mock":
        return {"type": "mock", "token": "mock-auth-token"}
    
    if auth_type == "hmac-sha256":
        msg = f"{request_id}:{capability}:{nonce}:{expiration}"
        token = compute_hmac_sha256(secret, msg)
        return {"type": "hmac-sha256", "token": token}
    
    raise ValueError(f"Unsupported auth_type: {auth_type}")

def verify_receipt(receipt: InvocationReceipt, secret: str = DEFAULT_SECRET) -> bool:
    """Verify provider's cryptographic signature on receipt."""
    if receipt.status != "success" or not receipt.receipt_signature:
        return False
    
    msg = f"receipt:{receipt.request_id}:{receipt.provider}:{receipt.started_at}:{receipt.completed_at}"
    expected = compute_hmac_sha256(secret, msg)
    return hmac.compare_digest(expected, receipt.receipt_signature)
