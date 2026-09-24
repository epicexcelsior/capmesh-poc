from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import json

@dataclass
class Pricing:
    model: str = "fixed"
    amount: str = "0.001"
    currency: str = "mock-usdc"

@dataclass
class Capability:
    id: str
    description: str
    pricing: Pricing
    parameters: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Capability:
        pricing_data = data.get("pricing", {})
        pricing = Pricing(
            model=pricing_data.get("model", "fixed"),
            amount=str(pricing_data.get("amount", "0.001")),
            currency=pricing_data.get("currency", "mock-usdc")
        )
        return cls(
            id=data["id"],
            description=data.get("description", ""),
            pricing=pricing,
            parameters=data.get("parameters")
        )

@dataclass
class Manifest:
    protocol: str
    device_id: str
    capabilities: List[Capability] = field(default_factory=list)
    transport: Optional[str] = None
    address: Optional[str] = None
    trust_tier: str = "verified"  # "verified", "untrusted", "unknown"
    attestation: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], address: Optional[str] = None, transport: Optional[str] = None) -> Manifest:
        caps = [Capability.from_dict(c) for c in data.get("capabilities", [])]
        return cls(
            protocol=data.get("protocol", "capmesh/0.1"),
            device_id=data.get("device_id", "unknown"),
            capabilities=caps,
            transport=transport,
            address=address,
            trust_tier=data.get("trust_tier", "verified"),
            attestation=data.get("attestation")
        )

    def to_json(self) -> str:
        return json.dumps({
            "protocol": self.protocol,
            "device_id": self.device_id,
            "capabilities": [
                {
                    "id": c.id,
                    "description": c.description,
                    "pricing": asdict(c.pricing),
                    "parameters": c.parameters
                } for c in self.capabilities
            ]
        })

@dataclass
class InvocationRequest:
    request_id: str
    device_id: str
    capability: str
    parameters: Dict[str, Any]
    nonce: int
    timestamp: int
    expiration: int
    authorization: Dict[str, Any]
    protocol: str = "capmesh/0.1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol": self.protocol,
            "request_id": self.request_id,
            "device_id": self.device_id,
            "capability": self.capability,
            "parameters": self.parameters,
            "nonce": self.nonce,
            "timestamp": self.timestamp,
            "expiration": self.expiration,
            "authorization": self.authorization
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

@dataclass
class DeliveryProof:
    observer_id: str
    expected_state: str
    observed_state: str
    verified_samples: int
    total_samples: int
    readback_verified: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DeliveryProof:
        return cls(
            observer_id=data.get("observer_id", "unknown"),
            expected_state=data.get("expected_state", ""),
            observed_state=data.get("observed_state", ""),
            verified_samples=int(data.get("verified_samples", 0)),
            total_samples=int(data.get("total_samples", 0)),
            readback_verified=bool(data.get("readback_verified", False))
        )

@dataclass
class InvocationReceipt:
    protocol: str
    request_id: str
    status: str
    provider: Optional[str] = None
    capability: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    started_at: Optional[int] = None
    completed_at: Optional[int] = None
    delivery_proof: Optional[DeliveryProof] = None
    authorization_ref: Optional[str] = None
    receipt_signature: Optional[str] = None
    error: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InvocationReceipt:
        dp_raw = data.get("delivery_proof")
        dp = DeliveryProof.from_dict(dp_raw) if dp_raw and isinstance(dp_raw, dict) else None
        return cls(
            protocol=data.get("protocol", "capmesh/0.1"),
            request_id=data.get("request_id", ""),
            status=data.get("status", "unknown"),
            provider=data.get("provider"),
            capability=data.get("capability"),
            parameters=data.get("parameters"),
            result=data.get("result"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            delivery_proof=dp,
            authorization_ref=data.get("authorization_ref"),
            receipt_signature=data.get("receipt_signature"),
            error=data.get("error")
        )
