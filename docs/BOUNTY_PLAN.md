# FieldProof bounty execution plan

**Decision date: October 2, 2026.** Complete the Germany MVP package first.
The [adversarial research](research/2026-10-02-fieldproof.md) supports this bounded build and records commercial uncertainty.

## Fixed scope

One observation: `gate.closed` at `demo-gate`. One supplier: the existing ESP32-C6 contact demonstration.
One demonstrated payment rail: Solana Devnet USDC through x402 V2.
One buyer recommendation: DISPATCH or WAIT after independent receipt checks.
Keep the simulator for reviewers without hardware. Label it clearly.

No training-data pivot, new token, multi-chain settlement, custom Solana program, open marketplace, or new hardware fleet before October 5.
Build only to remove a failed acceptance gate or serve an identified buyer workflow.

## Finish the package

| Order | Deliverable | Acceptance criterion | Current state |
|---|---|---|---|
| 1 | Human eligibility and registration | Germany selected, World's Fair joined, FieldProof project page available | Blocking. Copilot still reports unregistered. |
| 2 | Judge test path | A fresh checkout runs both CLI contact states and browser simulation without hardware or wallet funding | Fresh checkout passed CLI states, browser simulation, expiry, receipt attacks, and video access. |
| 3 | Current technical walkthrough | 2–3 minutes, playable, states what is recorded and what is simulated | Signed-receipt video is 149.76 seconds and decodes. Captioned, no audio. |
| 4 | Review links | Judges can open test instructions, repository, presentation, and technical evidence without private credentials | Local artifacts ready. Public links require publication. |
| 5 | Human MVP submission | Every required field is complete and receipt retained before October 5, 23:59:59 CEST | Not submitted. |
| 6 | Buyer test | One real decision, current alternative, useful-time window, operator permission, and price/budget evidence | Not completed. Run in parallel with packaging, not as a reason to delay MVP. |
| 7 | Final hackathon presentation | Founder explains buyer, alternatives, evidence, hypothesis, and next test in 2–3 minutes | Prepare after the MVP package. It does not block using the technical walkthrough for Germany MVP. |
| 8 | peaq integration decision | One useful adapter flow or an explicit activation limitation | After MVP package. Mainnet activation and spending require a separate decision. |
| 9 | Human final submissions | peaq and Colosseum submissions complete before October 13, 08:59 CEST | Not submitted. |

Aim to finish the MVP package by October 4 at 18:00 CEST.
Use October 5 for link checks and submission recovery. This is an internal buffer, not an organizer deadline.
Aim to finish final Colosseum and peaq materials by October 11 at 18:00 CEST.

## Judge rehearsal

From a fresh checkout, follow the README prerequisites and commands.

1. Run `uv sync --project host`.
2. Run `uv run --project host capmesh observe-demo --simulated`.
3. Check DISPATCH, stale-provider rejection, and `attacks_passed: true`.
4. Run `uv run --project host capmesh observe-demo --simulated --closed`.
5. Check WAIT and `attacks_passed: true`.
6. In `gateway`, run `npm ci`.
7. Run `npm run demo`.
8. Open `http://127.0.0.1:4022`.
9. Select **Get payment quote**, then **Run simulation**.
10. Check the simulation label and DISPATCH.
11. Wait eleven seconds and check WAIT.
12. Open `/proof` and test the changed state, changed challenge, and wrong key.
13. Check that the authentic recorded receipt remains expired.
14. Open the signed-receipt walkthrough and the public evidence files.

This path moves no funds and invokes no physical device.
A recorded public Devnet transfer establishes the real integration separately.
A deployed simulator must not expose the physical gateway, private keys, device authorization, or private ledgers.
Publication requires a concrete review and owner authorization.

## Founder presentation outline

Use your own words. These are topics, not submission-field text.

- 0:00–0:20: one immediate buyer decision and the fact missing from its current workflow.
- 0:20–1:10: quote, payment evidence, measured contact, and independently checked receipt.
- 1:10–1:40: expiry and attacks. Explain why authentic evidence can still be unusable.
- 1:40–2:10: existing alternatives and the specific cross-organization workflow hypothesis.
- 2:10–2:40: what works, what remains unvalidated, and the next buyer test.

State that BOOT represents a contact. Show actual device footage if available.
Do not imply live payment during a recorded-evidence scene.
Do not describe the demo price as revenue, a signature as physical truth, or DISPATCH as permission to move.

## Evidence and disclosure

Use the [signed receipt](evidence/device-signed-purchase.json), [identity checks](evidence/receipt-identity-checks.json), and [physical contact states](evidence/contact-states.json).
The older contact-state evidence uses the historical HMAC format. Do not relabel it as P-256 evidence.

Inspect Git history before completing the prior-development field.
The initial checked repository commit dates to September 24, inside the September 14 event window.
The original concept and other relevant work can predate that commit. A commit date alone cannot establish when all development began.
The founder must disclose earlier concept/code history accurately and distinguish it from work inside the event window.

Registration, acceptance of contest terms, public uploads, external outreach, spending, pushing, and final submission remain separate owner actions.
Local research, documentation, verification, and commits are authorized in this task.
