"""The pivot's judging loop: physical question, provider selection, evidence, decision."""

from dataclasses import replace
import json
import re

from ..market import DemandLedger, ObservationMarket
from ..observations import CONTACT_SENSORS, EvidenceError, ObservationContract, ObservationVerifier
from ..protocol.auth import DEFAULT_SECRET, compute_hmac_sha256, receipt_message
from ..protocol.identity import provisioned_observation_keys
from ..protocol.models import InvocationReceipt, InvocationRequest
from ..provider.observation_provider import SimulatedContactProvider
from ..transport.ble import BLETransportAdapter
from ..transport.http import HTTPTransportAdapter


async def run_observation_demo(*, simulated=False, closed=False, http_url=None, http_interface=None,
                               ledger_path=".local/demand.sqlite", provider=None, sensor="gpio9-contact", pins_path=None):
    if provider is None:
        provider = "sim-contact-01" if simulated else "esp32-c6-96a2"
    if not isinstance(provider, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,31}", provider):
        raise ValueError("Select a provider ID with 1–31 letters, digits, hyphens, or underscores")
    if not simulated and (not isinstance(sensor, str) or sensor not in CONTACT_SENSORS):
        raise ValueError("Physical mode requires a configured GPIO contact sensor")
    if simulated and (not isinstance(sensor, str) or sensor not in {"gpio9-contact", "simulated-contact"}):
        raise ValueError("Simulation reports simulated-contact and cannot select a physical GPIO")
    contract = ObservationContract(sensor="simulated-contact" if simulated else sensor)
    if simulated:
        receipt_keys = {provider: DEFAULT_SECRET}
    else:
        pins = provisioned_observation_keys(pins_path)
        if provider not in pins:
            raise ValueError("The selected provider has no buyer-provisioned public key")
        receipt_keys = {provider: pins[provider]}
    stale = SimulatedContactProvider("stale-contact", stale_seconds=60, price="0.0001")
    physical = (SimulatedContactProvider(provider, closed=closed) if simulated else
                HTTPTransportAdapter(http_url, interface=http_interface) if http_url else BLETransportAdapter())
    ledger = DemandLedger(ledger_path)
    try:
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
