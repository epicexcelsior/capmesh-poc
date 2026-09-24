from typing import List
from ..protocol.models import Manifest, Capability, Pricing, InvocationRequest, InvocationReceipt
from ..transport.base import TransportAdapter

class UntrustedRogueProvider(TransportAdapter):
    """
    Rogue capability provider used in adversarial demos and security policy verification.
    Under-cuts honest providers on price (0.002 vs 0.004) but fails cryptographic trust verification.
    """

    def __init__(self, device_id: str = "rogue-signal-node-99"):
        self.device_id = device_id

    @property
    def transport_name(self) -> str:
        return "wifi-http"

    def get_manifest(self) -> Manifest:
        return Manifest(
            protocol="capmesh/0.1",
            device_id=self.device_id,
            transport="wifi-http",
            address="192.168.1.199:8080",
            trust_tier="untrusted",
            attestation="forged-sig:0xdeadbeef",
            capabilities=[
                Capability(
                    id="visible_signal",
                    description="Cheap rogue optical pulse (unverified provider)",
                    pricing=Pricing(model="fixed", amount="0.002", currency="mock-usdc"),
                    parameters={"duration": {"type": "integer", "default": 3}}
                ),
                Capability(
                    id="led.blink",
                    description="Rogue LED flasher with zero hardware attestation",
                    pricing=Pricing(model="fixed", amount="0.002", currency="mock-usdc"),
                    parameters={"duration": {"type": "integer", "default": 3}}
                )
            ]
        )

    async def discover(self, timeout: float = 1.0) -> List[Manifest]:
        return [self.get_manifest()]

    async def invoke(self, target: str, request: InvocationRequest, timeout: float = 5.0) -> InvocationReceipt:
        return InvocationReceipt(
            protocol=request.protocol,
            request_id=request.request_id,
            status="error",
            provider=self.device_id,
            error={"code": "ROGUE_PROVIDER_TRAP", "message": "Invocation intercepted by unverified rogue node"}
        )
