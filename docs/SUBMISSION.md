# FieldProof submission preparation

Status: public repository, draft submission. The project is not ready to submit.
Public paid settlement and both human-controlled contact states pass. The repository is public. Presentation, Colosseum, and contact details remain incomplete.
The current [2:30 signed-receipt walkthrough](assets/fieldproof-signed-receipt.webm) includes recorded verified payment evidence and browser attacks.
It has captions and no audio. The founder presentation and public viewing links remain incomplete.
Follow the [bounty execution plan](BOUNTY_PLAN.md) and [research decision](research/2026-10-02-fieldproof.md).

## Verified requirements and deadlines

Requirements and deadlines were checked again from both complete public `__NEXT_DATA__` listing payloads on October 4, 2026.
Both listings specify Germany regional eligibility and `agentAccess: HUMAN_ONLY`. The founder must complete human submission.
The earlier text-only retrieval omitted these details. This record supersedes that gap.

| Track | Deadline in UTC | Deadline in Europe/Berlin |
|---|---|---|
| Germany MVP | October 5, 2026, 21:59:59 | October 5, 2026, 23:59:59 CEST |
| peaq Germany | October 13, 2026, 06:59:00 | October 13, 2026, 08:59:00 CEST |

The Germany MVP track requires a working Solana integration on Devnet or Mainnet.
An existing SDK or protocol qualifies. A custom Solana program is optional.
The form requires product details, a test link, a public GitHub repository, deployment evidence, and a 2–3 minute video.
It also requires a Colosseum project and a team contact. Register under Germany. [Germany MVP listing](https://superteam.fun/earn/listing/road-to-colosseum-hackathon-build-your-mvp)

The peaq track accepts a working demo or a promising prototype in English.
The form requires a description, GitHub link, presentation link, and a truthful answer about Colosseum submission.
Website and social links are optional.
Judges assess the machine-economy mechanism, implementation, usefulness, originality, and explanation.
Native peaq activation is not an explicit mandatory requirement.
The listing warns against superficial peaq additions and fragmented features. [peaq Germany listing](https://superteam.fun/earn/listing/build-solutions-advancing-the-machine-economy-with-peaq)

Winner announcements are separate: October 12 for the MVP track and October 27 for peaq.
Verify both deadlines again before submission. Eligibility and acceptance remain organizer decisions.

## Project name and tagline

**FieldProof — Fresh device evidence for physical services machines rely on.**

## One-line description

The prototype buys a fresh contact observation on Solana Devnet and independently checks the device's signed answer before DISPATCH or WAIT.
The [company hypothesis](STRATEGY.md#the-story-to-explain) is machines buying and verifying physical services from infrastructure another operator owns.

## Problem and buyer

The first buyer hypothesis is a fleet software operator that needs repeated interactions with independent facilities.
It needs permitted service terms, payment, and useful evidence before it relies on the interaction.
The implemented first step purchases a current contact observation with an explicit age limit and budget.
Access rights, actuation, reservations, and completed-service verification remain future work.
Existing facility APIs and Open-RMF integrations remain alternatives. Customer demand and avoided costs remain unvalidated.

## Working product

The MVP asks one question at `demo-gate`: is the contact closed?
A flashed ESP32-C6 samples its GPIO9 input five times after authorization.
Its BOOT button represents a gate contact.
The buyer checks device identity, location, nonce, result authentication, sample agreement, and freshness.
Fresh open evidence produces `DISPATCH`. Closed or expired evidence produces `WAIT`.

The CLI rejects a cheaper stale provider before selecting fresh evidence.
It records served and unmet demand.
Executed attack checks reject repeated requests, repeated responses, changed challenges, and changed results.
BLE and Wi-Fi measurements passed on the attached board.
Human press/release verification passed: held BOOT produced CLOSED/WAIT, and released BOOT produced OPEN/DISPATCH.
[Device-signed physical state evidence](evidence/device-signed-contact-states.json) preserves both October 2 P-256 receipts.
The older HMAC state checks remain historical evidence.

## Solana integration

FieldProof uses the x402 V2 SDK and Solana Kit to purchase one observation with Devnet USDC.
The gateway pins the network, mint, recipient, and a price of 1,000 base units, equivalent to 0.001 USDC.
The real resource-server SDK verifies payment and settles it before authorizing measurement.
SQLite reserves each transaction proof once and preserves its purchase state and original receipt.

A public-facilitator purchase settled 0.001 Devnet USDC and then returned a real authenticated GPIO9 observation.
Independent RPC checks confirmed the successful transaction, configured mint, buyer debit, and merchant credit.
[Paid P-256 evidence](evidence/device-signed-purchase.json) records the current transaction and receipt. The public gateway also returns the expected 402 offer.
Tests execute verification, settlement, retries, and failures through the real SDK with a simulated facilitator.
The signing test creates and cryptographically verifies an Ed25519 buyer signature against a local RPC fixture.
The live purchase establishes the chain integration separately from these unit tests.

Solana supplies the payment rail for small autonomous purchases.
The physical observation and buyer policy supply the decision value.
There is no custom on-chain program in this MVP.

## Machine-economy contribution

The observer offers a priced observation. The buyer controls spending and evidence age before it derives a demo recommendation.
The longer-term hypothesis connects approved buyers to physical services from separate operators.
Start with paid enterprise integration and support. Test recurring software fees before relying on machine-service transaction volume.
A second independent facility tests integration reuse. Pricing, income, demand, and network effects remain unvalidated.
The local demand ledger includes test requests. It establishes no monthly revenue opportunity or case for new hardware investment.

No peaq identity or revenue event is activated.
The current [Solana onboarding guide](https://docs.peaq.xyz/peaqos/guides/onboard-on-solana) reports paused onboarding and a mainnet-only flow.
The read-only Agung registry check now verifies deployment peers and activation flags and derives a proposed observer ID from the public key.
No machine activation or activity event exists. The [peaq integration decision](PEAQ_INTEGRATION.md) records the bounded native testnet path and remaining inputs.
The next useful peaq step is an activated observer identity and honest activity history after an explicit operator and funding decision.
The public command HMAC key does not provide private authorization. Physical receipts use buyer-pinned P-256 identity with unencrypted device storage.
Simulated payments and Devnet tokens do not establish real revenue.

## Judging walkthrough

Open [the illustrated founder guide](HOW_IT_WORKS.html) to learn and rehearse one transaction.
The exported package includes this guide beside the actual recorded-receipt verifier. The guide's interactive examples are teaching models.
Run `python3 scripts/demo.py check`, then follow its simulation, real-board, and recorded-payment stages.
Those launcher stages move no funds. They do not activate peaq or deploy a public product.

Use the [current signed-receipt walkthrough](assets/fieldproof-signed-receipt.webm) for technical review.
Its recorded paid scene does not execute another payment. Its browser scenes verify the real receipt and reject attacks.
The October 4 version is 149.88 seconds, 1280 × 900, and passed full decoding and visual inspection.
It labels the simulated unpaid quote separately from the recorded real Devnet purchase. It has captions and no audio.
A separate founder presentation remains incomplete.
The October 5 local kit adds a 75.64-second visual proof companion with an actual read-only Devnet query.
It shows the payment, robot-and-gate illustration, receipt attacks, and recorded BOOT states. It includes captions and no audio.
Use it as a short explanation or additional demo. It does not replace a required 2–3 minute presentation.
The local review kit also contains a 159.88-second visual version: a ten-second flow picture followed by the unchanged technical walkthrough.
It remains local and includes no audio. Its full decode, browser playback, opening picture, transition, and closing frame passed.
The Germany MVP requires a walkthrough. The current technical video can serve that purpose once its public link works.
The final Colosseum presentation requires the buyer and business explanation alongside the technical demonstration.
Prepare that presentation after the MVP package.
Use the [rehearsal](REHEARSAL.md) for technical explanation and the [strategy](STRATEGY.md) for the company hypothesis.
Write final application answers and record the founder presentation in your own words.

The [older live walkthrough](assets/fieldproof-submission.webm), [composed presentation](assets/fieldproof-walkthrough.webm), and [69-second simulation](assets/fieldproof-demo.webm) remain historical artifacts.
Their earlier pending-payment captions do not describe the current integration.
Do not use them as current status evidence or relabel simulated scenes as real settlement.

## Required fields that remain incomplete

| Field | Current state | Required next action |
|---|---|---|
| Public repository | Public at `https://github.com/epicexcelsior/capmesh-poc` | Paste the link into the submission form |
| Test access | Public repository with full setup instructions in `README.md` | Confirm the judge can follow the no-hardware path, or provide a reachable demo |
| Presentation link | Current captioned technical walkthrough ready locally. Founder presentation incomplete. | Record the founder presentation and provide public viewing links |
| Payment evidence | Verified Devnet transaction and real GPIO9 receipt | Link the committed evidence and include it in the final walkthrough |
| Colosseum project | No verified project page | Register under Germany and provide the project link |
| Team contact | No submission contact selected | Supply the contact directly in the submission form |
| peaq submission answer | No submission occurred | Answer accurately at submission time |

These links and details are intentionally absent. No placeholder is a valid submission value.
Video upload, account registration, and submission require explicit authorization.

## Owner publication steps

The origin is `https://github.com/epicexcelsior/capmesh-poc.git`. `main` is pushed and the repository visibility is Public. Keep every later change pushed before submission.

1. Check that `origin` still points to the repository judges will review.
2. Run `git push -u origin main` after every accepted change.
3. Confirm the repository visibility stays Public.
4. Check the public README, simulator setup, verification record, and `docs/evidence/` files.
5. Review the current signed-receipt walkthrough and record the founder presentation.
6. Upload both videos and check their public viewing links.
7. Paste the presentation, test-access, Colosseum project, and contact values into the submission form.

Keep `.local/`, keypair files, databases, environment files, and build outputs excluded.
The existing recording script requires an installed Playwright package and Chromium. See the [demo runbook](DEMO.md).
Video upload, registration, and submission remain owner tasks. A hosted public gateway requires separate access controls and deployment work.

## Source reproduction

Open each listing in a browser. Read its details section.
Read `JSON.parse(document.querySelector('#__NEXT_DATA__').textContent).props.pageProps.listing` in the browser console.
Inspect only `deadline`, `region`, `description`, and `eligibility` for this requirements check.
The deadline fields were `2026-10-05T21:59:59.000Z` and `2026-10-13T06:59:00.000Z`.
Convert those UTC values with the `Europe/Berlin` time zone.

The [verification record](VERIFICATION.md) identifies tested behavior and remaining gaps.
