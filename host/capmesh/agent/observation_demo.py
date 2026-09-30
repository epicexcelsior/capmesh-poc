"""The pivot's judging loop: physical question, provider selection, evidence, decision."""

from dataclasses import replace
import json

from ..market import DemandLedger, ObservationMarket
from ..observations import EvidenceError, ObservationContract, ObservationVerifier
from ..protocol.auth import DEFAULT_SECRET
from ..protocol.models import InvocationReceipt, InvocationRequest
from ..provider.observation_provider import SimulatedContactProvider
from ..transport.ble import BLETransportAdapter
from ..transport.http import HTTPTransportAdapter


async def run_observation_demo(*, simulated=False, closed=False, http_url=None, http_interface=None, ledger_path=".local/demand.sqlite"):
    stale = SimulatedContactProvider("stale-contact", stale_seconds=60, price="0.0001")
    physical = (SimulatedContactProvider(closed=closed) if simulated else
                HTTPTransportAdapter(http_url, interface=http_interface) if http_url else BLETransportAdapter())
    provider = "sim-contact-01" if simulated else "esp32-c6-96a2"
    ledger = DemandLedger(ledger_path)
    try:
        contract = ObservationContract()
        market = ObservationMarket([stale, physical], {"stale-contact": DEFAULT_SECRET, provider: DEFAULT_SECRET}, ledger)
        result = await market.observe(contract)
        result["mode"] = "SIMULATED" if simulated else "LIVE CONTACT DEMO"
        if result["status"] == "success":
            receipt = InvocationReceipt.from_dict(result["receipt"])
            request = InvocationRequest(**result["request"])
            attacks = {}
            for label, candidate, challenge in [
                ("replayed_response", receipt, request),
                ("different_challenge", receipt, replace(request, nonce=request.nonce + 1)),
                ("tampered_state", replace(receipt, result={**receipt.result, "closed": not receipt.result["closed"]}), request),
            ]:
                verifier = market.verifier if label == "replayed_response" else ObservationVerifier({provider: DEFAULT_SECRET})
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
