# Verify two contact observers

**The software requires both configured observers before DISPATCH. An unpaid concurrent BLE runner is ready. Two-board physical verification remains open.**
Audience: the founder who explains the extension and the developer who connects two receipt sources.
This document owns the pair policy. [Contact setup](CONTACT_SETUP.md) owns device configuration and trusted public pins.

## Understand the rule

Each observer answers the same contact question at `demo-gate` under its own original buyer challenge.
The buyer selects two distinct provider IDs, two distinct P-256 public pins, and each observer's exact physical sensor descriptor.
The verifier checks both receipts at one evaluation time. It requires five matching samples from each input.
The default limits are ten seconds of evidence age and two seconds between signed completion times.

| Observer A | Observer B | Pair decision |
|---|---|---|
| Fresh, stable OPEN | Fresh, stable OPEN | DISPATCH |
| Fresh, stable CLOSED | Fresh, stable CLOSED | WAIT: contact closed |
| Fresh, stable OPEN | Fresh, stable CLOSED | WAIT: observer disagreement |
| Any state | Missing, stale, unstable, invalid, or replayed receipt | WAIT: unmet evidence requirement |
| Both otherwise acceptable | Completion times differ by more than two seconds | WAIT: observation skew |

The rule requires both observers. It never selects the cheaper or more convenient answer after disagreement.
The output keeps `confidence: null`. Distinct keys do not establish independent sensing, correct installation, or calibrated confidence.
Two sensors on the same broken circuit can agree on an incorrect OPEN state.
DISPATCH remains a demo recommendation. The controller retains access permission and motion-safety checks.

```mermaid
flowchart LR
    A[Original challenge A + pinned receipt A] --> V[Verify both at one time]
    B[Original challenge B + pinned receipt B] --> V
    V --> C{"Both fresh, stable OPEN<br/>within completion limit?"}
    C -->|Yes| D[Demo DISPATCH]
    C -->|No| W[WAIT with rejection reason]
```

## Rehearse without hardware or funds

Prerequisites: [README Python setup](../README.md#run-without-hardware). Start at the repository root.

```bash
uv run --project host capmesh corroborate-demo --scenario all
```

Expect eight results and exit code zero. Only `open` returns DISPATCH.
`closed`, `conflict`, `missing`, `stale`, `skew`, `invalid`, and `replay` return WAIT with their specific reasons.
For the replay scene, `first_decision` records DISPATCH before the repeated pair returns WAIT.

Every result states `SIMULATED SIGNED FIXTURES`, `hardware_used: false`, and `none; no funds moved`.
The command generates temporary signing keys in memory. It exports no private key and accesses no radio, network, or wallet.
The fixture uses physical-style GPIO descriptors to exercise the exact contract. Those descriptors do not claim an actual sensor installation.

To isolate one scene, run:

```bash
uv run --project host capmesh corroborate-demo --scenario conflict
```

Use this scene after the main paid-receipt demonstration if time permits.
Say: two individually authentic answers can conflict, so the buyer waits.
The command demonstrates a tested decision policy. It does not demonstrate two physical boards or two paid deliveries.

## Collect two provisioned BLE contacts once

Prerequisites: two configured boards, independently provisioned public pins, checked wiring, and no other Bluetooth Low Energy (BLE) consumer.
Wait for the active overnight diagnostic to finish before using this runner.
Follow [contact setup](CONTACT_SETUP.md) for firmware, sensor selection, and USB provisioning.
The current first board still uses `gpio9-contact`. Replace `SECOND_USB_ID` with the second board's USB-verified provider ID.
Use its actual configured sensor instead of the example `gpio18-contact` when they differ.

Start at the repository root:

```bash
uv run --project host python -m scripts.check_contact_pair \
  --observer esp32-c6-96a2:gpio9-contact \
  --observer SECOND_USB_ID:gpio18-contact \
  --pins .local/contact-pins.json
```

The parent validates and snapshots both public pins before it starts a worker.
The worker uses one BLE scan, one adapter, and one event loop.
It requires one unambiguous manifest per selected provider and the `state.observe` capability before either invocation.
It creates both original challenges after discovery and invokes both providers concurrently through their cached BLE handles.
It verifies both responses at one final evaluation time. Collection never widens the existing freshness or completion limits.

The output states `LIVE BLE CONTACT DEMO` and `none; no funds moved`.
The mode names the selected transport. A failed discovery still produces this label with an unmet WAIT result.
`invocations_started` counts attempted adapter invocations. It does not certify request delivery.
`received_receipts` preserves returned finite JSON envelopes, including invalid signatures, for inspection.
`challenges` preserves the original buyer challenges without command authorization.
The collector redacts literal command tokens from receipt fields and keys before output.
`redacted_receipts` identifies changed envelopes. Verification uses the original captured receipts.
A redacted envelope is an inspection artifact, not a complete original receipt for independent verification.

| Exit code | Meaning |
|---|---|
| 0 | Both receipts passed the pair checks. OPEN/OPEN gives DISPATCH. CLOSED or disagreement still gives WAIT. |
| 1 | The pair remains unmet, or collection failed. Read `pair.rejections` and `collection.errors`. |
| 2 | Trusted configuration failed before worker or BLE access. |

The whole-worker deadline defaults to 45 seconds. `--timeout` accepts integer values from 1 through 60 seconds.
Cleanup allows two seconds after TERM and two seconds after KILL.
Caller cancellation waits for the same bounded cleanup operation, including repeated cancellation during the TERM grace period.
`worker_cleanup_confirmed: false` requires operator recovery before any other BLE observation.
Read the structured `worker_pid` in `collection.errors`. Inspect and stop that worker before continuing.
The runner performs no automatic retry, simulation fallback, payment, output GPIO operation, or clock override.
The underlying collection coroutine alone does not bound a stuck BLE disconnect. Use the parent runner for hardware diagnostics.
This runner supports BLE only. The existing HTTP adapter does not provide concurrent pair collection.

## Integrate original requests and receipts

`host/capmesh/corroboration.py` supplies three types:

| Type | Caller responsibility |
|---|---|
| `ContactObserver(provider, sensor, public_key)` | Supply the selected provider, supported physical sensor, and trusted `ReceiptPublicKey`. |
| `ObserverEvidence(request, receipt)` | Retain the buyer's original `InvocationRequest` and its returned `InvocationReceipt`. |
| `ContactPairVerifier(observers, max_age_seconds=10, max_completion_skew_seconds=2)` | Configure exactly two observers and retain this verifier instance across evaluations. |

Call `verifier.verify({provider_a: evidence_a, provider_b: evidence_b})` after collection.
The verifier samples the current time once. Explicit `now` exists for deterministic tests and recorded-history checks.
Never derive the original challenge from the receipt. Never install a key from the receipt or discovery result.
`provisioned_observation_keys(path)` loads the independently provisioned public pin file.

The verifier returns WAIT for missing, extra, malformed, or unacceptable evidence.
Invalid trusted configuration raises `ValueError` before evidence verification.
The result identifies verified observations and rejection reasons. It grants no individual DISPATCH while the pair remains unmet.

## Keep expiry and replay behavior explicit

The pair expires at the earliest member's completion time plus its freshness limit, or either original request's expiration.
`valid_until_epoch_seconds` records that bound. It does not refresh either observation.
At that final second, the time comparison still accepts the bound. At the next second, verification rejects expired evidence.
A controller must compare its current time with the bound again before use.

A missing, invalid, stale, or skewed pair consumes neither member.
The caller can recover a valid partial response by supplying its missing acceptable partner within both validity windows.
A complete, timely pair consumes both provider/nonce tokens, including CLOSED and disagreement results.
This prevents later reuse of a conflicting pair's OPEN member.

A lock makes verification and consumption atomic within one verifier instance.
A captured copy prevents caller mutation from changing the authenticated decision.
Replay state remains in memory. A process restart clears it.
No durable robot-action ledger, payment aggregation, or cross-process action guarantee exists.

## Pass the physical gates before extending the paid demo

The gateway and paid buyer still deliver and verify one provider per purchase.
The new diagnostic collects an unpaid BLE pair. It adds no second payment or paired purchase endpoint.
The [hardware acceptance plan](HARDWARE_NEXT.md#acceptance-gates-for-each-upgrade) owns the physical extension.

The current single-board BLE round trip takes about thirteen seconds in the running diagnostic.
Sequential collection can expire the first receipt before the second returns.
Do not widen the ten-second useful-time window merely to make the pair pass.
Measure the prepared concurrent runner, actual completion skew, and end-to-end age when a second board becomes available.
The two-second skew limit is a selected demo policy. Host-anchored timestamps do not prove independent clock accuracy.

The next physical result needs separately provisioned keys, checked sensor placement, OPEN/CLOSED readings, disagreement, missing input, stale input, and swapped-key rejection.
Keep the verified one-board entry and recorded inspector until the extension passes those gates.
The [verification record](VERIFICATION.md) owns executed results.
