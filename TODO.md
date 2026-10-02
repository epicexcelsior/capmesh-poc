# FieldProof acceptance status

Start with [the condensed decision](docs/FOCUS.md). Use [verification](docs/VERIFICATION.md) for observed results.
The previous phase tracker overstated payment, provider trust, and physical truth. Current evidence replaces those claims.

- [x] Document the physical-evidence pivot and implementation plan.
- [x] Implement a challenge-bound contact observation and buyer freshness policy.
- [x] Reject a cheaper stale provider and record served/unmet demand.
- [x] Implement GPIO9 input sampling on the attached ESP32-C6.
- [x] Build, flash, and verify a live authenticated observation over BLE.
- [x] Reject request replay, response replay, changed challenge, and changed state.
- [x] Enforce settlement before measurement with the real x402 resource-server SDK.
- [x] Test concurrent retries, reused proofs, settlement failure, and delivery failure.
- [x] Persist purchase states and prevent duplicate payment or measurement.
- [x] Add an explicitly simulated payment/hardware browser flow.
- [x] Add a constrained Devnet payment client with independent receipt checks.
- [x] Verify the public facilitator's unpaid Devnet USDC quote.
- [x] Check the dispatch desk at desktop and phone widths.
- [x] Verify simulated payment with real BLE evidence through the complete browser flow.
- [x] Verify a successful public-facilitator payment and transaction with a disposable Devnet USDC buyer.
- [x] Physically hold/release BOOT and verify both live decisions.
- [x] Verify the new observation capability over the board's Wi-Fi HTTP transport.
- [x] Record a 60–90 second demo artifact.
- [x] Verify full submission requirements and the native peaq integration requirement.
- [x] Produce and inspect a 2:30 presentation from the verified simulator recording and explanatory title cards.
- [x] Promote the newer signed-receipt walkthrough with recorded verified payment and browser attacks. Preserve older recordings as history.
- [x] Prepare local submission text against verified track requirements.
- [x] Push the repository and make it public: https://github.com/epicexcelsior/capmesh-poc
- [ ] Provide test access, presentation link, Colosseum project details, and submission contact.
- [x] Preserve the buyer purchase ID after a lost payment connection or truncated delivery.
- [x] Run the gateway suite: 22 tests passed on October 2. See the verification record.
- [x] Preserve purchase identity, buyer policy, metadata, recovery, recordings, evidence, and current documentation in local commits.

Production provisioning, calibrated confidence, independent observers, and customer pilots remain later milestones.
Publication, repository rename, and submission require explicit authorization.

## Product decisions that require stronger evidence

- [ ] Validate one recurring cross-site buyer decision and its avoided cost.
- [ ] Establish the site operator's permission to sell the observation and the buyer's right to access it.
- [ ] Measure installation, delivery, support, and failure costs before treating the demo price as sustainable.
- [ ] Separate test requests, paid delivery, and committed demand before funding sensor deployments.
- [ ] Choose protected asymmetric receipt signing and separate command authorization for a real pilot.

The [product review](docs/STRATEGY.md#product-risks-and-decisions) explains these priorities.

## October 2 bounty priority

Follow [the execution plan](docs/BOUNTY_PLAN.md). Broad research stops at [the current decision](docs/research/2026-10-02-fieldproof.md).
The signed-receipt technical video is ready locally. Registration, founder presentation, public links, buyer validation, and human submissions remain open.
