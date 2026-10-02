"""An explicit two-observer contact rule. Distinct keys do not establish physical independence."""

from copy import deepcopy
from dataclasses import dataclass
import re
from threading import Lock
import time

from .observations import CONTACT_SENSORS, EvidenceError, ObservationContract, ObservationVerifier
from .protocol.identity import ReceiptPublicKey
from .protocol.models import InvocationReceipt, InvocationRequest


@dataclass(frozen=True)
class ContactObserver:
    provider: str
    sensor: str
    public_key: ReceiptPublicKey

    def __post_init__(self):
        if not isinstance(self.provider, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,31}", self.provider):
            raise ValueError("Select an explicit contact provider ID")
        if not isinstance(self.sensor, str) or self.sensor not in CONTACT_SENSORS:
            raise ValueError("Select an explicit supported physical contact sensor")
        if not isinstance(self.public_key, ReceiptPublicKey):
            raise ValueError("Each contact observer requires a trusted P-256 public pin")


@dataclass(frozen=True)
class ObserverEvidence:
    request: InvocationRequest
    receipt: InvocationReceipt


class ContactPairVerifier:
    """Verify exactly two configured observers and consume only a complete, timely pair.

    The caller supplies its original challenges. It must never infer them from receipts.
    Replay state lasts for this instance. No payment or hardware collection occurs here.
    """

    def __init__(self, observers, *, max_age_seconds=10, max_completion_skew_seconds=2):
        if not isinstance(observers, (tuple, list)) or len(observers) != 2 or any(not isinstance(observer, ContactObserver) for observer in observers):
            raise ValueError("Configure exactly two contact observers")
        observers = tuple(observers)
        if len({observer.provider for observer in observers}) != 2:
            raise ValueError("The pair requires two distinct provider IDs")
        if len({observer.public_key.sec1_hex for observer in observers}) != 2:
            raise ValueError("The pair requires two distinct public signing keys")
        self._contracts = {observer.provider: ObservationContract(sensor=observer.sensor, max_age_seconds=max_age_seconds)
                           for observer in observers}
        if type(max_completion_skew_seconds) is not int or not 0 <= max_completion_skew_seconds <= max_age_seconds:
            raise ValueError("Completion skew must be an integer from zero through the freshness limit")
        self._observers = observers
        self._max_age_seconds = max_age_seconds
        self._max_skew_seconds = max_completion_skew_seconds
        self._consumed = set()
        self._lock = Lock()

    def verify(self, evidence: dict[str, ObserverEvidence], *, now=None):
        with self._lock:
            return self._verify(evidence, now=now)

    def _verify(self, evidence, *, now):
        now = int(time.time()) if now is None else now
        if type(now) is not int or now < 1:
            raise ValueError("Use a positive integer evaluation time")
        result = {"status": "unmet", "decision": "WAIT", "reason": "No complete verified contact pair",
                  "location": "demo-gate", "metric": "gate.closed", "confidence": None,
                  "identity_note": "Two signing keys do not establish independent sensing or calibrated confidence",
                  "max_age_seconds": self._max_age_seconds, "max_completion_skew_seconds": self._max_skew_seconds,
                  "verified_observations": {}, "rejections": [], "valid_until_epoch_seconds": None}
        if not isinstance(evidence, dict):
            result["reason"] = "INVALID_EVIDENCE: supply evidence indexed by the configured provider IDs"
            return result
        expected = set(self._contracts)
        if set(evidence) - expected:
            result["reason"] = "UNEXPECTED_OBSERVER: the evidence contains an unconfigured provider"
            return result
        if expected - set(evidence):
            result["reason"] = "MISSING_OBSERVER: both configured contact observers are required"
            result["rejections"] = [{"provider": provider, "reason": "MISSING_OBSERVER"}
                                    for provider in sorted(expected - set(evidence))]
            return result
        if any(not isinstance(value, ObserverEvidence) or not isinstance(value.request, InvocationRequest)
               or not isinstance(value.receipt, InvocationReceipt) for value in evidence.values()):
            result["reason"] = "INVALID_EVIDENCE: retain the original request and its receipt for each observer"
            return result
        # Authenticate and decide from one captured snapshot, even if the caller later changes its models.
        evidence = deepcopy(evidence)
        tokens = set()
        for observer in self._observers:
            item = evidence[observer.provider]
            request, receipt = item.request, item.receipt
            if (request.device_id != observer.provider or request.protocol != "capmesh/0.1"
                or request.capability != "state.observe" or request.parameters != {"location": "demo-gate"}
                or not isinstance(request.request_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,16}", request.request_id)
                or type(request.nonce) is not int or not 1 <= request.nonce <= 0x7fffffff
                or type(request.timestamp) is not int or type(request.expiration) is not int
                or not 1 <= request.timestamp < request.expiration <= 0xffffffff
                or request.timestamp > now + 2 or request.expiration - request.timestamp > 300):
                result["rejections"].append({"provider": observer.provider, "reason": "INVALID_CHALLENGE"})
                continue
            token = (observer.provider, request.nonce)
            if token in self._consumed:
                result["rejections"].append({"provider": observer.provider, "reason": "REPLAY_DETECTED"})
                continue
            try:
                # Temporary verification cannot consume part of a failed pair.
                decision = ObservationVerifier({observer.provider: observer.public_key}).verify(
                    receipt, request, self._contracts[observer.provider], now=now)
            except EvidenceError as error:
                result["rejections"].append({"provider": observer.provider, "reason": str(error)})
                continue
            result["verified_observations"][observer.provider] = {
                "closed": decision["closed"], "age_seconds": decision["age_seconds"], "sensor": observer.sensor,
                "sample_agreement": decision["sample_agreement"], "receipt_identity": decision["receipt_identity"]}
            tokens.add(token)
        if result["rejections"]:
            result["reason"] = "UNVERIFIED_PAIR: at least one observer failed its challenge, signature, stability, freshness, or replay check"
            return result
        completed = [item.receipt.completed_at for item in evidence.values()]
        skew = max(completed) - min(completed)
        result["completion_skew_seconds"] = skew
        if skew > self._max_skew_seconds:
            result["reason"] = "OBSERVATION_SKEW: completion times exceed the configured limit"
            return result
        result["status"] = "verified-pair"
        result["valid_until_epoch_seconds"] = min(
            min(item.receipt.completed_at + self._max_age_seconds, item.request.expiration)
            for item in evidence.values())
        states = {observation["closed"] for observation in result["verified_observations"].values()}
        # CLOSED and conflicting complete pairs also consume both receipts. A caller cannot cherry-pick their OPEN member later.
        self._consumed.update(tokens)
        if len(states) != 1:
            result["reason"] = "OBSERVER_DISAGREEMENT: the two contact states conflict"
        elif True in states:
            result["reason"] = "CONTACT_CLOSED: both configured contacts report CLOSED"
        else:
            result["decision"] = "DISPATCH"
            result["reason"] = "CONTACT_OPEN: both configured contacts report fresh, stable OPEN"
        return result
