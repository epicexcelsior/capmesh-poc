"""Explicitly simulated signed evidence for rehearsing the two-observer rule."""

import base64
from dataclasses import replace
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

from ..corroboration import ContactObserver, ContactPairVerifier, ObserverEvidence
from ..observations import ObservationContract, observation_request
from ..protocol.auth import receipt_message
from ..protocol.identity import ReceiptPublicKey
from ..protocol.models import InvocationReceipt

SCENARIOS = ("open", "closed", "conflict", "missing", "stale", "skew", "invalid", "replay")


def run_corroboration_demo(scenario="open", *, now=None):
    if scenario not in SCENARIOS:
        raise ValueError("Select a supported pair-verification scenario")
    now = int(time.time()) if now is None else now
    observers, evidence = [], {}
    for index in range(2):
        # Fixture keys exist only for this process. They are never exported or installed as device pins.
        key = ec.generate_private_key(ec.SECP256R1())
        pin = ReceiptPublicKey(key.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint).hex())
        observer = ContactObserver(f"fixture-observer-{index + 1}", f"gpio{18 + index}-contact", pin)
        observers.append(observer)
        request = observation_request(observer.provider, ObservationContract(sensor=observer.sensor), now=now - 12)
        measured = now - (11 if scenario == "stale" and index == 1 else
                          3 if scenario == "skew" and index == 1 else 0)
        closed = scenario == "closed" or scenario == "conflict" and index == 1
        receipt = InvocationReceipt(protocol=request.protocol, request_id=request.request_id, status="success",
            provider=request.device_id, capability=request.capability, nonce=request.nonce, parameters=request.parameters,
            result={"metric": "gate.closed", "sensor": observer.sensor, "closed": closed,
                    "stable_samples": 5, "total_samples": 5}, started_at=measured, completed_at=measured)
        r, s = utils.decode_dss_signature(key.sign(receipt_message(receipt).encode(), ec.ECDSA(hashes.SHA256())))
        receipt.receipt_signature = "v3:" + base64.b64encode(r.to_bytes(32, "big") + s.to_bytes(32, "big")).decode()
        if scenario == "invalid" and index == 1:
            receipt = replace(receipt, result={**receipt.result, "closed": not closed})
        if scenario != "missing" or index != 1:
            evidence[observer.provider] = ObserverEvidence(request, receipt)
    verifier = ContactPairVerifier(observers)
    first = verifier.verify(evidence, now=now)
    result = verifier.verify(evidence, now=now) if scenario == "replay" else first
    return {"mode": "SIMULATED SIGNED FIXTURES", "payment_mode": "none; no funds moved",
            "hardware_used": False, "scenario": scenario, **({"first_decision": first["decision"]} if scenario == "replay" else {}),
            "pair": result}
