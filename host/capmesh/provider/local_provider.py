import hashlib
import time
from typing import List, Dict, Any
from ..protocol.models import Manifest, Capability, Pricing, InvocationRequest, InvocationReceipt
from ..protocol.auth import verify_receipt, compute_hmac_sha256, DEFAULT_SECRET
from ..transport.base import TransportAdapter

class LaptopProvider(TransportAdapter):
    """Local machine capability provider running on the host laptop."""

    def __init__(self, device_id: str = "laptop-agent-01"):
        self.device_id = device_id
        self._seen_nonces = set()

    @property
    def transport_name(self) -> str:
        return "local-ipc"

    def get_manifest(self) -> Manifest:
        return Manifest(
            protocol="capmesh/0.1",
            device_id=self.device_id,
            transport="local-ipc",
            address="localhost",
            capabilities=[
                Capability(
                    id="compute.sha256",
                    description="High-speed SHA-256 computation on laptop CPU",
                    pricing=Pricing(model="fixed", amount="0.002", currency="mock-usdc"),
                    parameters={"data": {"type": "string", "required": True}}
                ),
                Capability(
                    id="storage.echo",
                    description="In-memory echo storage and round-trip verification",
                    pricing=Pricing(model="fixed", amount="0.001", currency="mock-usdc"),
                    parameters={"payload": {"type": "string", "required": True}}
                ),
            ]
        )

    async def discover(self, timeout: float = 1.0) -> List[Manifest]:
        return [self.get_manifest()]

    async def invoke(self, target: str, request: InvocationRequest, timeout: float = 5.0) -> InvocationReceipt:
        # Replay protection
        if request.nonce in self._seen_nonces:
            return InvocationReceipt(
                protocol=request.protocol,
                request_id=request.request_id,
                status="error",
                provider=self.device_id,
                error={"code": "REPLAY_DETECTED", "message": "Nonce has already been processed"}
            )
        self._seen_nonces.add(request.nonce)

        # Expiration check
        now = int(time.time())
        if request.expiration and request.expiration < now:
            return InvocationReceipt(
                protocol=request.protocol,
                request_id=request.request_id,
                status="error",
                provider=self.device_id,
                error={"code": "AUTH_EXPIRED", "message": "Request expiration timestamp is in the past"}
            )

        start_time = now
        result: Dict[str, Any] = {}

        if request.capability == "compute.sha256":
            raw = str(request.parameters.get("data", "")).encode("utf-8")
            digest = hashlib.sha256(raw).hexdigest()
            result = {"hash": digest, "bytes_hashed": len(raw)}
        elif request.capability == "storage.echo":
            result = {"echo": request.parameters.get("payload", "")}
        else:
            return InvocationReceipt(
                protocol=request.protocol,
                request_id=request.request_id,
                status="error",
                provider=self.device_id,
                error={"code": "UNKNOWN_CAPABILITY", "message": f"Unknown capability {request.capability}"}
            )

        completed_time = int(time.time())
        receipt_msg = f"receipt:{request.request_id}:{self.device_id}:{start_time}:{completed_time}"
        signature = compute_hmac_sha256(DEFAULT_SECRET, receipt_msg)

        return InvocationReceipt(
            protocol=request.protocol,
            request_id=request.request_id,
            status="success",
            provider=self.device_id,
            capability=request.capability,
            parameters=request.parameters,
            result=result,
            started_at=start_time,
            completed_at=completed_time,
            authorization_ref=f"{request.authorization.get('type')}:{request.authorization.get('token')}",
            receipt_signature=signature
        )
