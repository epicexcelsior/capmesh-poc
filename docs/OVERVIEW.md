# FieldProof — overnight MVP overview

FieldProof now buys a fresh contact observation and uses it to decide whether an autonomous vehicle can dispatch.
The ESP32-C6 samples a real GPIO input. Its BOOT button represents the gate contact.
The product replaces the old LED marketplace narrative while preserving the original transport and package interfaces.

**Current result:** a working observation product, real BLE and Wi-Fi evidence, tested x402 ordering, a local dispatch desk, and a recorded demonstration.
**Unfinished:** a successful public-facilitator payment, human verification of both physical contact states, and verified peaq-track requirements and integration.
The active build goal remains open.

## Open the result

- [Interactive dispatch desk](overview.html): local product UI and overview.
- [69-second recorded simulation](assets/fieldproof-demo.webm): quote, fresh evidence, expiry, closed state, and executed attack checks.
- [Quick start](../README.md): simulator, real hardware, payment gateway, and test commands.
- [Demo and recovery runbook](DEMO.md): reproduce the judging loop and review failed purchases.
- [Verification record](VERIFICATION.md): exact checks, results, versions, and evidence gaps.

The simulator runs at `http://127.0.0.1:4022` after `npm run demo` in `gateway`.
The real-contact simulator uses `npm run demo -- --physical`.
The public Devnet gateway uses `npm start` and binds to port 4021.
All servers bind to loopback. No public deployment or phone-wallet path exists.

## What changed

| Area | Implemented behavior |
|---|---|
| Physical question | `gate.closed` at `demo-gate` replaces generic LED actuation as the product narrative |
| Device capability | `state.observe` samples GPIO9 five times after authorization |
| Evidence | Authenticator binds device, location, metric, sensor, nonce, result, samples, and timestamps |
| Buyer policy | Reject unknown identities, changed challenges, bad signatures, unstable samples, stale results, and replayed responses |
| Provider competition | Try a cheaper stale fixture, reject it, and select fresh evidence within a cumulative mock budget |
| Demand | SQLite records served and unmet queries, including missing-location demand |
| Payment | Real x402 V2 server SDK verifies and settles before the BLE bridge receives authorization |
| Retries | SQLite reserves each transaction proof once and preserves the original receipt |
| Recovery | Unknown settlement and failed delivery preserve review states and block automatic repetition |
| Product UI | Quote, observation, DISPATCH/WAIT, sample agreement, freshness expiry, and demand summary |
| Buyer client | Constrained Solana Kit signer, Devnet USDC policy, and independent receipt checks |
| Documentation | New plan, protocol, architecture, strategy, runbook, Markdown overview, and HTML overview |

The legacy transaction-signature and unsigned payment-channel adapters fail closed.
A transaction's confirmation alone does not prove its recipient, mint, amount, or purchase binding.
Historical documents carry a notice that their earlier trust and payment claims are superseded.

## Verification

The final full Python run passes 40 tests with the ESP32 attached.
The gateway passes 14 Node tests. One separate hardware capacity test also passes.
These are 55 executed passing tests across the three runs.
The default Python run intentionally excludes hardware tests. See the exact commands in the verification record.

Live evidence includes:

- BLE discovery, authenticated input samples, and rejected request replay.
- Wi-Fi HTTP input samples and rejected replay through the board's access point.
- Browser purchase with simulated settlement and real BLE contact evidence.
- Public-facilitator 402 quote for 1,000 base units of Devnet USDC.
- A cryptographically verified buyer transaction signature against a local RPC fixture.
- A full replay table that refuses new requests and retains existing nonces.
- Browser rendering at desktop and 390-pixel phone widths, with no horizontal overflow.
- DISPATCH while evidence is fresh and WAIT after expiry.

The recorded video contains simulated contact and payment, labeled on screen. It does not show an on-chain payment.
The real input's released state is verified. No unattended action physically pressed the BOOT button.

## Trust limits

The host and firmware share a public demo HMAC key. It demonstrates field binding, not identity against a hostile repository reader.
The clock anchors from an authenticated host request. Reboot resets this anchor and the replay table.
The device keeps 64 unexpired nonce entries and refuses new requests when full.
The buyer pins device identity in its own configuration. Discovery does not certify providers.

Sample agreement is not calibrated confidence. One device cannot corroborate itself independently.
No external gate contact, loading-bay occupancy sensor, secure element, location attestation, or production provisioning exists.
A signed GPIO observation does not establish external physical truth.

## Payment limits

The gateway pins Solana Devnet, Devnet USDC, the merchant, and an exact amount of 1,000 base units.
The provided payment client has no configured funded wallet. A complete public-facilitator paid request remains unverified.
A fake facilitator proves the gateway's ordering and recovery logic without moving funds.
The separate physical mode proves that this gateway can deliver a real contact observation after simulated settlement.

A payment can settle before hardware delivery fails. The preserved settlement supports manual refund review.
Automatic refunds do not exist. Unknown settlement requires review before anyone retries a payment.
Cached evidence retains its original timestamp. The gateway and browser return WAIT after its freshness window expires.

## Wi-Fi integration lesson

The laptop's VPN advertised `192.168.4.1` through its tunnel. Joining the board's access point did not override that route.
A request explicitly bound to Wi-Fi retrieved the correct manifest and authenticated observation.
The HTTP adapter now exposes `--http-interface` on Linux. It does not change global VPN routes.
The temporary test connection was removed, and the original Wi-Fi connection was restored.

## Track direction and next work

The [strategy](STRATEGY.md) follows Carlo's Germany and peaq machine-economy direction.
The retrieved listings identify the region and winner announcement dates. They do not expose complete technical submission requirements.
No peaq transaction or machine identity registration exists yet.

Next work follows the remaining gates in [TODO](../TODO.md):

1. Verify the complete listing requirements and choose a useful peaq-native machine operation.
2. Exercise the paid client with disposable Devnet USDC and preserve the transaction and receipt.
3. Physically hold and release BOOT to verify both live decisions.
4. Prepare submission materials that distinguish measured evidence, simulations, and future plans.

The longer roadmap targets independent evidence, provider-quality history, buyer pilots, and demand-directed deployment.
No customer demand, calibrated confidence, durable business moat, or prize outcome is established by this prototype.

## Repository and artifacts

The implementation stays in the existing repository. The user-facing name is FieldProof.
The Python package stays `capmesh` to preserve existing commands.
Build outputs, local databases, node modules, environment files, and keypair files stay excluded from Git.
The demonstration video and its recording script belong to the repository.
No repository rename, push, deployment, external message, or hackathon submission occurred in this continuation.
