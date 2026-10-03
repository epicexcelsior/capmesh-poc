"""Collect one unpaid contact pair through a single BLE adapter and event loop."""

import asyncio
from copy import deepcopy
from dataclasses import asdict
import json
import time

from .corroboration import ContactPairVerifier, ObserverEvidence
from .observations import ObservationContract, observation_request
from .protocol.models import InvocationReceipt
from .transport.ble import BLETransportAdapter


def _redact_command_tokens(value, tokens):
    if isinstance(value, str):
        for token in tokens:
            value = value.replace(token, "[REDACTED_COMMAND_TOKEN]")
        return value
    if isinstance(value, dict):
        return {_redact_command_tokens(key, tokens): _redact_command_tokens(item, tokens) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_command_tokens(item, tokens) for item in value]
    return value


async def collect_contact_pair(observers, *, transport=None):
    """Discover first, invoke both concurrently, then verify at one final time.

    The repository diagnostic supplies a bounded process around this operation.
    This coroutine alone does not guarantee that a stuck BLE disconnect finishes.
    """
    verifier = ContactPairVerifier(observers)
    observers = tuple(observers)
    transport = BLETransportAdapter() if transport is None else transport
    if not isinstance(transport, BLETransportAdapter):
        raise ValueError("Pair collection requires one BLE transport adapter")
    started = time.monotonic()
    result = {"payment_mode": "none; no funds moved", "received_receipts": {}, "redacted_receipts": [], "challenges": {},
              "collection": {"transport": "ble", "invocations_started": 0, "errors": [], "timing_seconds": {}}}
    collection = result["collection"]
    try:
        manifests = await transport.discover(timeout=4)
    except Exception as error:
        collection["errors"].append({"reason": f"DISCOVERY_FAILED: {type(error).__name__}"})
        result["pair"] = verifier.verify({})
        return result
    discovered = time.monotonic()
    collection["timing_seconds"]["discovery_and_manifests"] = round(discovered - started, 3)
    for observer in observers:
        matches = [manifest for manifest in manifests if manifest.device_id == observer.provider]
        if len(matches) != 1:
            collection["errors"].append({"provider": observer.provider,
                "reason": "MISSING_PROVIDER" if not matches else "AMBIGUOUS_PROVIDER"})
        elif not any(capability.id == "state.observe" for capability in matches[0].capabilities):
            collection["errors"].append({"provider": observer.provider, "reason": "CAPABILITY_UNAVAILABLE"})
    if collection["errors"]:
        result["pair"] = verifier.verify({})
        return result

    # Discovery can be slow. Start the useful-time windows only after both selected providers are available.
    challenge_time = int(time.time())
    requests = {observer.provider: observation_request(observer.provider,
        ObservationContract(sensor=observer.sensor), now=challenge_time) for observer in observers}
    for provider, request in requests.items():
        challenge = request.to_dict()
        challenge.pop("authorization")
        result["challenges"][provider] = challenge

    async def invoke(observer):
        request = requests[observer.provider]
        collection["invocations_started"] += 1
        try:
            # An adapter cannot rewrite the buyer's original challenge through a mutable request object.
            receipt = await transport.invoke(observer.provider, deepcopy(request), timeout=12)
            if not isinstance(receipt, InvocationReceipt):
                return observer.provider, None, "INVALID_RESPONSE: receipt envelope required"
            snapshot = deepcopy(receipt)
            try:
                json.dumps(asdict(snapshot), allow_nan=False)
            except (TypeError, ValueError):
                return observer.provider, None, "INVALID_RESPONSE: finite JSON receipt required"
            return observer.provider, ObserverEvidence(request, snapshot), None
        except Exception as error:
            # Exception messages can contain authorization payloads. Retain only the selected provider and error type.
            return observer.provider, None, f"INVOKE_FAILED: {type(error).__name__}"

    responses = await asyncio.gather(*(invoke(observer) for observer in observers))
    received = time.monotonic()
    evidence = {}
    tokens = tuple(request.authorization["token"] for request in requests.values())
    for provider, item, error in responses:
        if error:
            collection["errors"].append({"provider": provider, "reason": error})
        else:
            evidence[provider] = item
            original = asdict(item.receipt)
            public = _redact_command_tokens(original, tokens)
            if public != original:
                result["redacted_receipts"].append(provider)
            result["received_receipts"][provider] = public
    result["pair"] = verifier.verify(evidence)
    collection["timing_seconds"].update(invocation_and_delivery=round(received - discovered, 3),
                                        total=round(received - started, 3))
    return result
