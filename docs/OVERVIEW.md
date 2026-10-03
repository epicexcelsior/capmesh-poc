# FieldProof — MVP overview

**The local decision loop works with a real Devnet payment and real ESP32 input.**
FieldProof purchases a fresh contact observation, checks its challenge and age, and returns DISPATCH or WAIT.
The ESP32-C6 BOOT button represents a gate contact. The product does not control a vehicle.

Current verified evidence:

- A public x402 facilitator settled 0.001 Devnet USDC before the real BLE observation.
- Independent RPC checks confirmed the exact mint, merchant, amount, and successful transaction.
- October 2 human-held BOOT produced signed CLOSED/WAIT. Released BOOT produced signed OPEN/DISPATCH. Both returned five matching samples.
- The hardware suite, expanded software suites, browser inspector, and static export passed. Exact results live in [verification](VERIFICATION.md).
- The current 2:30 walkthrough inspects recorded public payment and device evidence and executes browser attack checks.
- A read-only peaq Agung check verified registry peers, activation flags, the proposed observer ID, and the full tier-0 bond.

The repository is public at `https://github.com/epicexcelsior/capmesh-poc`. Registration, public video links, founder presentation, and submission remain owner tasks. Follow the [bounty execution plan](BOUNTY_PLAN.md).

## Open the result

- [Interactive dispatch desk](overview.html).
- [Complete how-it-works and setup guide](HOW_IT_WORKS.html). Protocol, payment states, failure paths, test suites, and every run command.
- [2:30 signed-receipt walkthrough](assets/fieldproof-signed-receipt.webm). Recorded public payment evidence and interactive receipt attacks. Captioned, no audio.
- [Paid device-signed receipt](evidence/device-signed-purchase.json).
- [Device-signed physical contact states](evidence/device-signed-contact-states.json).
- [peaq readiness and integration decision](PEAQ_INTEGRATION.md).
- [Quick start](../README.md) and [demo runbook](DEMO.md).
- [Verification record](VERIFICATION.md), [product review](STRATEGY.md#product-risks-and-decisions), and [submission draft](SUBMISSION.md).

Run `npm run demo` in `gateway`, then open `http://127.0.0.1:4022`.
Use `npm run demo -- --physical` for real BLE contact with simulated payment.
Use `npm start` for the public Devnet facilitator on port 4021.
All servers bind to loopback. A public hosted service and phone-wallet flow do not exist.

## What changed

| Area | Current implementation |
|---|---|
| Physical question | `gate.closed` at `demo-gate` replaces the LED marketplace narrative |
| Device | Authorized `state.observe` samples GPIO9 five times without driving the boot strap |
| Evidence | Authenticator binds device, location, sensor, result, nonce, samples, and timestamps |
| Buyer | Pins identity, location, price, and ten-second freshness. Rejects altered or expired evidence. |
| Provider rehearsal | Rejects a cheaper stale provider and selects fresh evidence within a cumulative mock budget |
| Demand | Local SQLite records served and unmet queries. Gateway demand counts purchase states. |
| Payment | Real x402 V2 SDK verifies and settles before BLE measurement |
| Purchase identity | SQLite reserves the signed transaction message once, including across signature variants and concurrent writers |
| Recovery | Original receipts and failed/unknown outcomes remain reviewable. The buyer preserves purchase IDs. |
| Product view | Shows quote, contact, recommendation, age, agreement, receipt, payment mode, and local demand |

The `capmesh` Python package and BLE UUIDs remain compatible.
Legacy transaction-reference and unsigned payment-channel adapters reject payment claims.
Confirmation alone does not establish a transaction's recipient, mint, amount, or purchase binding.

## Trust and operational limits

Command authorization uses a public demo HMAC key. Physical receipts use a persistent buyer-pinned P-256 key. Unencrypted flash storage remains vulnerable to physical key extraction.
The location is a provisioned label. No location attestation or independent observer exists.
Five matching samples establish sample agreement, not calibrated confidence.
Time derives from an authenticated host request. Reboot clears the time anchor and replay table.
The device retains 64 unexpired nonce entries and refuses new requests when full.

DISPATCH is a demo recommendation over one contact. It does not establish clearance, permission, or safe vehicle motion.
No external contact installation, protected device key, vehicle control integration, or customer pilot exists.
A successful payment followed by delivery failure requires refund review. Automatic refunds do not exist.
Cached evidence retains its original time and becomes WAIT after expiry.

## Product direction

The company hypothesis is autonomous machines buying and verifying physical services from infrastructure another operator owns.
The current prototype purchases one fresh contact observation. It grants no access, reserves no service, and controls no robot.
The first buyer hypothesis is a fleet software operator with repeated interactions at independent facilities.
Start with one buyer and one authorized operator. A second facility tests whether the buyer can reuse its integration.
A ten-second contact observation cannot predict advance availability.
This is a buyer hypothesis. No recurring demand, avoided-cost result, sustainable price, or provider income is established.
The [product review](STRATEGY.md#product-risks-and-decisions) examines access rights, truth, remote delivery, economics, and demand quality.
Earn one recurring buyer-provider workflow before building an open sensor marketplace.

The project follows Carlo's Germany MVP and peaq machine-economy direction.
The [submission draft](SUBMISSION.md) records verified deadlines and required fields.
No peaq transaction exists. Native activation is not an explicit mandatory listing requirement.
Official documentation reports paused Solana onboarding and a mainnet-only activation flow.
Native Agung registry readiness is a separate verified read-only path. Activation remains pending.

## Owner and later tasks

1. Record the founder presentation and provide public viewing links for both presentation and current technical walkthrough.
2. Provide the presentation, test access, Colosseum project, and contact in the submission form.
3. Validate one recurring buyer decision and the site's permission to sell its operational state.

The repository is public at `https://github.com/epicexcelsior/capmesh-poc`.
Upload, registration, and submission did not occur here.
Build outputs, local databases, private keys, node modules, and environment files remain excluded from Git.
Git, networking, USB, and BLE access are restored. No further access is needed for the completed local checks.
