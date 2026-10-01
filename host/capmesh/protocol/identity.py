"""Buyer-owned public receipt pins. Discovery cannot update this configuration."""

from dataclasses import dataclass
from importlib.resources import files
import json
import re

from cryptography.hazmat.primitives.asymmetric import ec


@dataclass(frozen=True)
class ReceiptPublicKey:
    sec1_hex: str

    def __post_init__(self):
        if not re.fullmatch(r"04[0-9a-f]{128}", self.sec1_hex):
            raise ValueError("Receipt key must contain a lowercase uncompressed P-256 point")
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), bytes.fromhex(self.sec1_hex))


def provisioned_observation_keys() -> dict[str, ReceiptPublicKey]:
    data = json.loads(files("capmesh.protocol").joinpath("receipt_keys.json").read_text())
    if data.get("algorithm") != "ecdsa-p256-sha256":
        raise ValueError("Unsupported provisioned receipt algorithm")
    return {provider: ReceiptPublicKey(key) for provider, key in data["providers"].items()}
