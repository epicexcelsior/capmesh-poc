# FieldProof acceptance status

Canonical current state: [overview](docs/OVERVIEW.md) and [verification](docs/VERIFICATION.md).
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
- [ ] Verify a successful public-facilitator payment and transaction with a disposable Devnet USDC buyer.
- [ ] Physically hold/release BOOT and verify both live decisions.
- [x] Verify the new observation capability over the board's Wi-Fi HTTP transport.
- [x] Record a 60–90 second demo artifact.
- [ ] Verify full submission requirements and implement a useful peaq-native integration if required.
- [ ] Prepare submission materials against verified track requirements.

Production provisioning, calibrated confidence, independent observers, and customer pilots remain later milestones.
Publication, repository rename, and submission require explicit authorization.
