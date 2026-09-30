"""Labeled fixtures for rehearsals and adversarial provider selection."""

import time

from ..observations import ObservationContract, observation_request
from ..protocol.auth import DEFAULT_SECRET, compute_hmac_sha256, receipt_message
from ..protocol.models import Capability, InvocationReceipt, Manifest, Pricing
from ..transport.base import TransportAdapter


class SimulatedContactProvider(TransportAdapter):
    def __init__(self, device_id="sim-contact-01", *, closed=False, stale_seconds=0, price="0.002"):
        self.device_id = device_id
        self.closed = closed
        self.stale_seconds = stale_seconds
        self.price = price
        self._seen = set()

    @property
    def transport_name(self):
        return "simulated"

    async def discover(self, timeout=1):
        return [Manifest(protocol="capmesh/0.1", device_id=self.device_id, transport=self.transport_name,
                         capabilities=[Capability("state.observe", "Simulated contact at demo-gate",
                                                  Pricing(amount=self.price))])]

    async def invoke(self, target, request, timeout=5):
        now = int(time.time())
        error = None
        if request.device_id != self.device_id or target != self.device_id:
            error = "INVALID_REQUEST"
        elif request.nonce in self._seen:
            error = "REPLAY_DETECTED"
        elif request.expiration <= now or request.timestamp > now + 2:
            error = "AUTH_EXPIRED"
        elif request.capability != "state.observe":
            error = "UNKNOWN_CAPABILITY"
        else:
            expected = observation_request(self.device_id, ObservationContract(location=request.parameters.get("location", "")),
                                           nonce=request.nonce, request_id=request.request_id, now=request.timestamp)
            if request.authorization != expected.authorization:
                error = "UNAUTHORIZED"
        if error:
            return InvocationReceipt(protocol=request.protocol, request_id=request.request_id, status="error",
                                     error={"code": error, "message": "Simulated provider rejected the request"})
        self._seen.add(request.nonce)
        measured = now - self.stale_seconds
        receipt = InvocationReceipt(
            protocol=request.protocol, request_id=request.request_id, status="success", provider=self.device_id,
            capability="state.observe", parameters=request.parameters, nonce=request.nonce,
            result={"metric": "gate.closed", "sensor": "simulated-contact", "closed": self.closed,
                    "stable_samples": 5, "total_samples": 5}, started_at=measured, completed_at=measured,
        )
        receipt.receipt_signature = "v2:" + compute_hmac_sha256(DEFAULT_SECRET, receipt_message(receipt))
        return receipt
