"""Pair decisions depend on both configured keys, original challenges, and one evaluation time."""

import base64
from copy import deepcopy
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from click.testing import CliRunner

from capmesh.agent.corroboration_demo import SCENARIOS, run_corroboration_demo
from capmesh.cli import main
from capmesh.corroboration import ContactObserver, ContactPairVerifier, ObserverEvidence
from capmesh.observations import ObservationContract, ObservationVerifier, observation_request
from capmesh.protocol.auth import receipt_message
from capmesh.protocol.identity import ReceiptPublicKey
from capmesh.protocol.models import InvocationReceipt


@pytest.fixture
def pair_data():
    keys = [ec.generate_private_key(ec.SECP256R1()) for _ in range(2)]
    observers = [ContactObserver(f"observer-{i}", f"gpio{18 + i}-contact", ReceiptPublicKey(
        key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint).hex()))
        for i, key in enumerate(keys)]

    def evidence(*, closed=(False, False), completed=(100, 100), challenge_time=100, nonce_offset=0, samples=(5, 5)):
        results = {}
        for i, observer in enumerate(observers):
            request = observation_request(observer.provider, ObservationContract(sensor=observer.sensor),
                nonce=1000 + i + nonce_offset, request_id=f"pair-{i}-{nonce_offset}", now=challenge_time)
            receipt = InvocationReceipt(protocol=request.protocol, request_id=request.request_id, status="success",
                provider=request.device_id, capability=request.capability, nonce=request.nonce, parameters=request.parameters,
                result={"metric": "gate.closed", "sensor": observer.sensor, "closed": closed[i],
                        "stable_samples": samples[i], "total_samples": 5},
                started_at=completed[i], completed_at=completed[i])
            r, s = utils.decode_dss_signature(keys[i].sign(receipt_message(receipt).encode(), ec.ECDSA(hashes.SHA256())))
            receipt.receipt_signature = "v3:" + base64.b64encode(r.to_bytes(32, "big") + s.to_bytes(32, "big")).decode()
            results[observer.provider] = ObserverEvidence(request, receipt)
        return results

    return observers, evidence


@pytest.mark.parametrize("closed,decision,reason", [
    ((False, False), "DISPATCH", "CONTACT_OPEN"), ((True, True), "WAIT", "CONTACT_CLOSED"),
    ((False, True), "WAIT", "OBSERVER_DISAGREEMENT"), ((True, False), "WAIT", "OBSERVER_DISAGREEMENT")])
def test_two_configured_fresh_states_control_one_decision(pair_data, closed, decision, reason):
    observers, evidence = pair_data
    result = ContactPairVerifier(observers).verify(evidence(closed=closed), now=100)
    assert result["decision"] == decision
    assert result["status"] == "verified-pair"
    assert result["reason"].startswith(reason)
    assert len(result["verified_observations"]) == 2
    assert result["confidence"] is None
    assert result["valid_until_epoch_seconds"] == 110
    assert all("decision" not in report and "evidence_mode" not in report for report in result["verified_observations"].values())


def test_missing_or_invalid_pair_does_not_consume_a_recoverable_valid_member(pair_data):
    observers, make = pair_data
    evidence = make()
    verifier = ContactPairVerifier(observers)
    assert verifier.verify({"observer-0": evidence["observer-0"]}, now=100)["reason"].startswith("MISSING_OBSERVER")
    broken = {**evidence, "observer-1": replace(evidence["observer-1"],
        receipt=replace(evidence["observer-1"].receipt, receipt_signature="v3:AAAA"))}
    assert verifier.verify(broken, now=100)["decision"] == "WAIT"
    assert verifier.verify(evidence, now=100)["decision"] == "DISPATCH"
    assert verifier.verify(evidence, now=100)["decision"] == "WAIT"
    assert verifier.verify(make(nonce_offset=10), now=100)["decision"] == "DISPATCH"


def test_complete_conflict_consumes_both_receipts_and_prevents_open_member_reuse(pair_data):
    observers, make = pair_data
    verifier = ContactPairVerifier(observers)
    conflict = make(closed=(False, True))
    assert verifier.verify(conflict, now=100)["reason"].startswith("OBSERVER_DISAGREEMENT")
    fresh = make(nonce_offset=10)
    mixed = {**fresh, "observer-0": conflict["observer-0"]}
    result = verifier.verify(mixed, now=100)
    assert result["decision"] == "WAIT"
    assert result["rejections"][0]["reason"] == "REPLAY_DETECTED"
    assert verifier.verify(fresh, now=100)["decision"] == "DISPATCH"


@pytest.mark.parametrize("change,reason", [
    ({"completed": (100, 89), "challenge_time": 88}, "STALE_EVIDENCE"),
    ({"completed": (100, 97), "challenge_time": 97}, "OBSERVATION_SKEW"),
    ({"samples": (5, 4)}, "UNSTABLE_MEASUREMENT")])
def test_stale_skewed_or_unstable_pair_never_dispatches(pair_data, change, reason):
    observers, make = pair_data
    result = ContactPairVerifier(observers).verify(make(**change), now=100)
    assert result["decision"] == "WAIT"
    assert reason in result["reason"] or any(reason in item["reason"] for item in result["rejections"])
    assert result["valid_until_epoch_seconds"] is None


def test_pair_expires_when_its_oldest_member_or_request_expires(pair_data):
    observers, make = pair_data
    evidence = make(completed=(100, 99), challenge_time=99)
    assert ContactPairVerifier(observers).verify(evidence, now=109)["decision"] == "DISPATCH"
    assert ContactPairVerifier(observers).verify(evidence, now=109)["valid_until_epoch_seconds"] == 109
    assert ContactPairVerifier(observers).verify(evidence, now=110)["decision"] == "WAIT"
    near_expiration = make(completed=(100, 100), challenge_time=73)
    assert ContactPairVerifier(observers).verify(near_expiration, now=100)["valid_until_epoch_seconds"] == 103
    assert ContactPairVerifier(observers).verify(near_expiration, now=104)["decision"] == "WAIT"


@pytest.mark.parametrize("field,value", [("provider", "other"), ("nonce", 123), ("request_id", "other"),
    ("parameters", {"location": "elsewhere"}), ("receipt_signature", "v3:AAAA")])
def test_changed_receipt_cannot_join_a_valid_pair(pair_data, field, value):
    observers, make = pair_data
    evidence = make()
    item = evidence["observer-1"]
    evidence["observer-1"] = replace(item, receipt=replace(item.receipt, **{field: value}))
    result = ContactPairVerifier(observers).verify(evidence, now=100)
    assert result["decision"] == "WAIT"
    assert result["status"] == "unmet"


@pytest.mark.parametrize("closed", [float("inf"), float("-inf"), float("nan"), 0, 1, "false", None])
def test_malformed_contact_returns_wait_and_preserves_valid_pair(pair_data, closed):
    observers, make = pair_data
    original = make()
    malformed = deepcopy(original)
    # Untrusted JSON numbers can parse as infinity. No valid signature is required to trigger canonicalization.
    malformed["observer-1"].receipt.result["closed"] = closed
    malformed["observer-1"].receipt.receipt_signature = "v3:" + base64.b64encode(bytes(64)).decode()
    verifier = ContactPairVerifier(observers)
    result = verifier.verify(malformed, now=100)
    assert result["decision"] == "WAIT"
    assert result["status"] == "unmet"
    assert result["rejections"] == [{"provider": "observer-1", "reason": "INVALID_SIGNATURE: observation fields failed authentication"}]
    assert verifier.verify(original, now=100)["decision"] == "DISPATCH"


def test_swapped_receipts_repeated_provider_and_extra_evidence_fail_closed(pair_data):
    observers, make = pair_data
    evidence = make()
    verifier = ContactPairVerifier(observers)
    for wrong in [{"observer-0": evidence["observer-1"], "observer-1": evidence["observer-0"]},
                  {"observer-0": evidence["observer-1"], "observer-1": evidence["observer-1"]},
                  {**evidence, "unconfigured": evidence["observer-0"]}]:
        assert verifier.verify(wrong, now=100)["decision"] == "WAIT"
    assert verifier.verify(evidence, now=100)["decision"] == "DISPATCH"


def test_concurrent_consumers_cannot_dispatch_the_same_pair_twice(pair_data):
    observers, make = pair_data
    verifier = ContactPairVerifier(observers)
    evidence = make()
    barrier = Barrier(2)

    def evaluate():
        barrier.wait(timeout=5)
        return verifier.verify(evidence, now=100)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(lambda _: evaluate(), range(2)))
    assert sorted([first["decision"], second["decision"]]) == ["DISPATCH", "WAIT"]
    assert any(item["reason"] == "REPLAY_DETECTED" for result in (first, second) for item in result["rejections"])


def test_pair_uses_the_authenticated_snapshot_after_caller_mutation(pair_data, monkeypatch):
    observers, make = pair_data
    original = make()
    verify = ObservationVerifier.verify

    def mutate_after_authentication(self, receipt, request, contract, *, now):
        result = verify(self, receipt, request, contract, now=now)
        original["observer-0"].receipt.result["closed"] = True
        original["observer-0"].request.expiration = 1
        return result

    monkeypatch.setattr(ObservationVerifier, "verify", mutate_after_authentication)
    result = ContactPairVerifier(observers).verify(original, now=100)
    assert result["decision"] == "DISPATCH"
    assert result["verified_observations"]["observer-0"]["closed"] is False
    assert result["valid_until_epoch_seconds"] == 110


def test_pair_configuration_requires_distinct_ids_and_p256_keys(pair_data):
    observers, _ = pair_data
    for invalid in [None, [], [observers[0]], [*observers, observers[0]], [observers[0], observers[0]],
                    [observers[0], replace(observers[1], public_key=observers[0].public_key)]]:
        with pytest.raises(ValueError):
            ContactPairVerifier(invalid)
    for values in [("observer", "simulated-contact", observers[0].public_key),
                   ("observer", "gpio12-contact", observers[0].public_key),
                   ("invalid/id", "gpio18-contact", observers[0].public_key),
                   ("observer", "gpio18-contact", "public-demo-hmac")]:
        with pytest.raises(ValueError):
            ContactObserver(*values)
    for skew in [True, -1, 11, 1.5]:
        with pytest.raises(ValueError):
            ContactPairVerifier(observers, max_completion_skew_seconds=skew)


@pytest.mark.parametrize("field,value", [("timestamp", True), ("timestamp", 104), ("nonce", True),
    ("request_id", "invalid/id"), ("capability", "led.blink"), ("protocol", "other/0.1"), ("expiration", 99)])
def test_invalid_original_challenge_fails_without_consumption(pair_data, field, value):
    observers, make = pair_data
    evidence = make()
    item = evidence["observer-1"]
    evidence["observer-1"] = replace(item, request=replace(item.request, **{field: value}))
    result = ContactPairVerifier(observers).verify(evidence, now=100)
    assert result["decision"] == "WAIT"
    assert result["rejections"] == [{"provider": "observer-1", "reason": "INVALID_CHALLENGE"}]


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_signed_fixture_rehearsal_never_claims_hardware_or_payment(scenario):
    result = run_corroboration_demo(scenario, now=1790860000)
    assert result["mode"] == "SIMULATED SIGNED FIXTURES"
    assert result["hardware_used"] is False
    assert result["payment_mode"] == "none; no funds moved"
    assert result["pair"]["decision"] == ("DISPATCH" if scenario == "open" else "WAIT")
    assert result["pair"]["confidence"] is None
    expected_reason = {"open": "CONTACT_OPEN", "closed": "CONTACT_CLOSED", "conflict": "OBSERVER_DISAGREEMENT",
        "missing": "MISSING_OBSERVER", "stale": "STALE_EVIDENCE", "skew": "OBSERVATION_SKEW",
        "invalid": "INVALID_SIGNATURE", "replay": "REPLAY_DETECTED"}[scenario]
    assert expected_reason in result["pair"]["reason"] or any(
        expected_reason in rejection["reason"] for rejection in result["pair"]["rejections"])
    if scenario == "replay":
        assert result["first_decision"] == "DISPATCH"


def test_cli_rehearses_all_eight_labeled_scenarios():
    result = CliRunner().invoke(main, ["corroborate-demo", "--scenario", "all"])
    assert result.exit_code == 0, result.output
    scenarios = json.loads(result.output)
    assert [scenario["scenario"] for scenario in scenarios] == list(SCENARIOS)
    assert all(scenario["mode"] == "SIMULATED SIGNED FIXTURES" and scenario["hardware_used"] is False
               for scenario in scenarios)
    assert [scenario["pair"]["decision"] for scenario in scenarios] == ["DISPATCH", *["WAIT"] * 7]
