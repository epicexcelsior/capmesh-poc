import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from ..protocol.models import Manifest, Capability, InvocationRequest, InvocationReceipt
from ..protocol.auth import generate_nonce, create_auth_payload, verify_receipt
from ..transport.ble import BLETransportAdapter
from ..transport.base import TransportAdapter
from ..provider.local_provider import LaptopProvider
from ..payment.verifier import PaymentVerifier, MockPaymentVerifier, SolanaDevnetVerifier

TAG_MAPPINGS = {
    "visual_signal": ["led.blink", "display.show", "light.toggle"],
    "led": ["led.blink"],
    "compute": ["compute.sha256"],
    "storage": ["storage.echo"]
}

class AgentPolicyEngine:
    """Autonomous agent capability discovery and deterministic policy execution."""

    def __init__(self, transports: Optional[List[TransportAdapter]] = None, payment_verifier: Optional[PaymentVerifier] = None):
        self.transports = transports or [BLETransportAdapter(), LaptopProvider()]
        self.payment_verifier = payment_verifier or MockPaymentVerifier()

    async def discover_all(self, timeout: float = 4.0) -> List[Tuple[Manifest, TransportAdapter]]:
        """Discover across all configured transports."""
        all_manifests = []
        for t in self.transports:
            try:
                manifests = await t.discover(timeout=timeout)
                for m in manifests:
                    all_manifests.append((m, t))
            except Exception:
                pass
        return all_manifests

    async def select_and_invoke(
        self,
        capability_or_tag: str,
        max_price: float = 0.05,
        parameters: Optional[Dict[str, Any]] = None,
        auth_type: str = "hmac-sha256",
        solana_tx_sig: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find providers offering capability_or_tag with price <= max_price.
        Select cheapest, verify payment policy, invoke, and verify receipt.
        """
        discovered = await self.discover_all()
        candidates = []

        allowed_caps = TAG_MAPPINGS.get(capability_or_tag, [capability_or_tag])

        for manifest, transport in discovered:
            for cap in manifest.capabilities:
                if cap.id in allowed_caps:
                    price = float(cap.pricing.amount)
                    if price <= max_price:
                        candidates.append({
                            "manifest": manifest,
                            "capability": cap,
                            "price": price,
                            "transport": transport
                        })

        if not candidates:
            return {
                "status": "error",
                "message": f"No providers found offering '{capability_or_tag}' for <= {max_price} USD"
            }

        # Deterministic policy: sort by price ascending (cheapest first)
        candidates.sort(key=lambda c: c["price"])
        chosen = candidates[0]
        manifest: Manifest = chosen["manifest"]
        cap: Capability = chosen["capability"]
        transport: TransportAdapter = chosen["transport"]

        # Payment verification check if Solana devnet signature provided
        if solana_tx_sig:
            is_paid = self.payment_verifier.verify_payment(solana_tx_sig, chosen["price"], manifest.device_id)
            if not is_paid:
                return {
                    "status": "error",
                    "message": f"Solana payment verification failed for tx {solana_tx_sig}"
                }

        # Issue capability authorization
        req_nonce = generate_nonce()
        now = int(time.time())
        expiration = now + 300
        req_id = f"policy-{int(time.time() * 1000) % 10000000:07x}"

        auth_payload = create_auth_payload(
            request_id=req_id,
            capability=cap.id,
            nonce=req_nonce,
            expiration=expiration,
            auth_type=auth_type
        )

        req = InvocationRequest(
            request_id=req_id,
            device_id=manifest.device_id,
            capability=cap.id,
            parameters=parameters or {"duration": 2, "count": 3},
            nonce=req_nonce,
            timestamp=now,
            expiration=expiration,
            authorization=auth_payload
        )

        receipt = await transport.invoke(manifest.device_id, req)
        receipt_verified = verify_receipt(receipt)

        return {
            "status": receipt.status,
            "chosen_provider": manifest.device_id,
            "transport": transport.transport_name,
            "capability": cap.id,
            "price": chosen["price"],
            "currency": cap.pricing.currency,
            "receipt": receipt,
            "receipt_verified": receipt_verified
        }
