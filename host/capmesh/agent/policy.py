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
    """Autonomous agent capability discovery, trust verification, and deterministic policy execution."""

    def __init__(
        self,
        transports: Optional[List[TransportAdapter]] = None,
        payment_verifier: Optional[PaymentVerifier] = None,
        spending_ceiling: float = 0.10
    ):
        self.transports = transports or [BLETransportAdapter(), LaptopProvider()]
        self.payment_verifier = payment_verifier or MockPaymentVerifier()
        self.spending_ceiling = spending_ceiling
        self.total_spent = 0.0

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
        solana_tx_sig: Optional[str] = None,
        require_verified_trust: bool = True,
        require_delivery_proof: bool = True
    ) -> Dict[str, Any]:
        """
        Find providers offering capability_or_tag with price <= max_price.
        Enforces trust policy, rejects untrusted providers, selects cheapest verified candidate,
        enforces spending ceiling, settles payment, executes capability, and verifies delivery proof.
        """
        discovered = await self.discover_all()
        candidates = []
        rejected = []

        allowed_caps = TAG_MAPPINGS.get(capability_or_tag, [capability_or_tag])

        for manifest, transport in discovered:
            for cap in manifest.capabilities:
                if cap.id in allowed_caps:
                    price = float(cap.pricing.amount)
                    
                    # 1. Trust Policy Filter
                    if require_verified_trust and manifest.trust_tier != "verified":
                        rejected.append({
                            "provider": manifest.device_id,
                            "capability": cap.id,
                            "price": price,
                            "reason": f"Trust policy violation: provider trust tier is '{manifest.trust_tier}' (required: 'verified')"
                        })
                        continue

                    # 2. Price Budget Filter
                    if price > max_price:
                        rejected.append({
                            "provider": manifest.device_id,
                            "capability": cap.id,
                            "price": price,
                            "reason": f"Budget exceeded: {price} > max allowable {max_price}"
                        })
                        continue

                    candidates.append({
                        "manifest": manifest,
                        "capability": cap,
                        "price": price,
                        "transport": transport
                    })

        if not candidates:
            return {
                "status": "error",
                "message": f"No eligible providers found for '{capability_or_tag}'",
                "rejected_providers": rejected
            }

        # Deterministic policy: sort by price ascending (cheapest verified first)
        candidates.sort(key=lambda c: c["price"])
        chosen = candidates[0]
        manifest: Manifest = chosen["manifest"]
        cap: Capability = chosen["capability"]
        transport: TransportAdapter = chosen["transport"]

        if cap.pricing.currency != "mock-usdc":
            return {"status": "error", "message": "Paid capabilities require the x402 gateway"}

        # 3. Agent Spending Ceiling Check
        if (self.total_spent + chosen["price"]) > self.spending_ceiling:
            return {
                "status": "error",
                "message": f"Agent spending ceiling exceeded: {self.total_spent + chosen['price']:.4f} > limit {self.spending_ceiling:.4f}",
                "rejected_providers": rejected
            }

        # Legacy transaction references are never sufficient authorization.
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
            device_id=manifest.device_id,
            parameters=parameters or {"duration": 2, "count": 3},
            timestamp=now,
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
        receipt_verified = verify_receipt(receipt, require_delivery_proof=require_delivery_proof)
        if receipt.status == "success" and receipt_verified:
            self.total_spent += chosen["price"]

        return {
            "status": receipt.status,
            "chosen_provider": manifest.device_id,
            "transport": transport.transport_name,
            "capability": cap.id,
            "price": chosen["price"],
            "currency": cap.pricing.currency,
            "payment_mode": "mock; no funds moved",
            "receipt": receipt,
            "receipt_verified": receipt_verified,
            "delivery_proof": receipt.delivery_proof,
            "rejected_providers": rejected
        }
