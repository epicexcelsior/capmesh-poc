"""Buyer-owned public receipt pins. Discovery cannot update this configuration."""

from dataclasses import dataclass
from importlib.resources import files
import json
from pathlib import Path
import re

from cryptography.hazmat.primitives.asymmetric import ec


@dataclass(frozen=True)
class ReceiptPublicKey:
    sec1_hex: str

    def __post_init__(self):
        if not isinstance(self.sec1_hex, str) or not re.fullmatch(r"04[0-9a-f]{128}", self.sec1_hex):
            raise ValueError("Receipt key must contain a lowercase uncompressed P-256 point")
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), bytes.fromhex(self.sec1_hex))


def provisioned_observation_keys(path=None) -> dict[str, ReceiptPublicKey]:
    source = Path(path) if path is not None else files("capmesh.protocol").joinpath("receipt_keys.json")
    data = json.loads(source.read_text())
    if not isinstance(data, dict) or data.get("algorithm") != "ecdsa-p256-sha256":
        raise ValueError("Unsupported provisioned receipt algorithm")
    providers = data.get("providers")
    if not isinstance(providers, dict) or not providers:
        raise ValueError("Provision at least one device public key")
    if any(not re.fullmatch(r"[A-Za-z0-9_-]{1,31}", provider) for provider in providers):
        raise ValueError("Provider IDs must contain 1–31 letters, digits, hyphens, or underscores")
    return {provider: ReceiptPublicKey(key) for provider, key in data["providers"].items()}
