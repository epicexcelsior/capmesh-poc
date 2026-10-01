"""The pivot's judging loop: physical question, provider selection, evidence, decision."""

from dataclasses import replace
import json

from ..market import DemandLedger, ObservationMarket
from ..observations import EvidenceError, ObservationContract, ObservationVerifier
from ..protocol.auth import DEFAULT_SECRET, compute_hmac_sha256, receipt_message
from ..protocol.identity import provisioned_observation_keys
from ..protocol.models import InvocationReceipt, InvocationRequest
from ..provider.observation_provider import SimulatedContactProvider
from ..transport.ble import BLETransportAdapter
from ..transport.http import HTTPTransportAdapter


async def run_observation_demo(*, simulated=False, closed=False, http_url=None, http_interface=None, ledger_path=".local/demand.sqlite"):
    stale = SimulatedContactProvider("stale-contact", stale_seconds=60, price="0.0001")
    physical = (SimulatedContactProvider(closed=closed) if simulated else
                HTTPTransportAdapter(http_url, interface=http_interface) if http_url else BLETransportAdapter())
    provider = "sim-contact-01" if simulated else "esp32-c6-96a2"
    receipt_keys = {provider: DEFAULT_SECRET} if simulated else provisioned_observation_keys()
    ledger = DemandLedger(ledger_path)
    try:
        contract = ObservationContract()
        market = ObservationMarket([stale, physical], {"stale-contact": DEFAULT_SECRET, **receipt_keys}, ledger)
        result = await market.observe(contract)
        result["mode"] = "SIMULATED" if simulated else "LIVE CONTACT DEMO"
        if result["status"] == "success":
            receipt = InvocationReceipt.from_dict(result["receipt"])
            request = InvocationRequest(**result["request"])
            attacks = {}
            cases = [
                ("replayed_response", receipt, request),
                ("different_challenge", receipt, replace(request, nonce=request.nonce + 1)),
                ("tampered_state", replace(receipt, result={**receipt.result, "closed": not receipt.result["closed"]}), request),
            ]
            if not simulated:
                forged = replace(receipt, result={**receipt.result, "closed": not receipt.result["closed"]})
                forged.receipt_signature = "v2:" + compute_hmac_sha256(DEFAULT_SECRET, receipt_message(forged))
                cases.append(("forged_public_hmac", forged, request))
            for label, candidate, challenge in cases:
                verifier = market.verifier if label == "replayed_response" else ObservationVerifier(receipt_keys)
                try:
                    verifier.verify(candidate, challenge, contract)
                    attacks[label] = "FAILED: accepted"
                except EvidenceError as exc:
                    attacks[label] = str(exc)
            replay = await physical.invoke(provider, request)
            attacks["replayed_request"] = (replay.error or {}).get("code", "FAILED: accepted")
            result["attacks"] = attacks
            result["attacks_passed"] = (attacks["replayed_request"] == "REPLAY_DETECTED" and
                                       all(not v.startswith("FAILED") for v in attacks.values()))
        result["demand"] = ledger.summary()
        # Do not include a reusable authorization token in the displayed artifact.
        result.pop("request", None)
        return result
    finally:
        ledger.close()
