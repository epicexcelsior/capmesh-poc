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
| 1 | Human eligibility and registration | Germany selected, World's Fair joined, FieldProof project page available | Owner will handle it. Completion and project URL are not yet verified. |
| 2 | Judge test path | A fresh checkout runs both CLI contact states and browser simulation without hardware or wallet funding | Fresh checkout passed CLI states, browser simulation, expiry, receipt attacks, and video access. |
| 3 | Current technical walkthrough | 2–3 minutes, playable, states what is recorded and what is simulated | Signed-receipt video is 149.76 seconds and decodes. Captioned, no audio. |
| 4 | Review links | Judges can open test instructions, repository, presentation, and technical evidence without private credentials | Whitelisted inspector ZIP, public-key verification, live chain query, and video pass locally. Public links require owner publication. |
| 5 | Human MVP submission | Every required field is complete and receipt retained before October 5, 23:59:59 CEST | Not submitted. |
| 6 | Buyer test | One real decision, current alternative, useful-time window, operator permission, and price/budget evidence | Not completed. Run in parallel with packaging, not as a reason to delay MVP. |
| 7 | Final hackathon presentation | Founder explains buyer, alternatives, evidence, hypothesis, and next test in 2–3 minutes | Prepare after the MVP package. It does not block using the technical walkthrough for Germany MVP. |
| 8 | peaq integration decision | One useful adapter flow or an explicit activation limitation | Read-only Agung registry readiness passed. Observer ID and bond are recorded. Activation, service binding, and activity events remain unimplemented. |
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
15. Select **Verify recorded payment** on `/proof`.
16. Check the exact transfer result and the unchanged expired WAIT decision.

This path moves no funds and invokes no physical device.
A recorded public Devnet transfer establishes the real integration separately.
A deployed simulator must not expose the physical gateway, private keys, device authorization, or private ledgers.
Publication requires a concrete review and owner authorization.

The [README export instructions](../README.md#inspect-the-recorded-physical-purchase) create a separate static inspector ZIP.
It includes no wallet, backend, private key, device authorization, or local ledger.
Use the complete simulator rehearsal to demonstrate a purchase. Use the inspector to examine recorded physical and chain evidence.

For the founder explanation, read [Understand the product](HOW_IT_WORKS.html#understand).
For the peaq path, read the [integration decision](PEAQ_INTEGRATION.md).

## Publish the test package: owner steps

The exported inspector is ready for owner review. These steps are instructions, not a record of publication.

1. Open the local exported `index.html` through the README's localhost server.
2. Verify the original receipt, three attacks, and recorded payment query.
3. Open the current captioned walkthrough.
4. Extract the exported ZIP into an empty folder.
5. Create a separate public GitHub repository for the static demo.
6. Upload the extracted contents with `index.html` at the repository root.
7. Preserve the `assets` and `evidence` directories during upload.
8. In GitHub Settings, open Pages.
9. Select deployment from the uploaded branch and its root directory.
10. Select **Save**.
11. Open the resulting HTTPS URL after GitHub finishes deployment.
12. Repeat the receipt, attack, payment-query, and video checks at that public URL.
13. Use that verified URL as recorded-evidence test access.

Do not upload the ZIP as the website itself. GitHub Pages needs its extracted files.
The inspector contains recorded evidence. Include the repository README link for the full simulated purchase rehearsal.
The local source commits also need an owner-controlled push before reviewers can inspect the latest source.
Registration and contest terms remain human actions. Do not mark them complete from a technical rehearsal.
The upload and Pages settings match [GitHub's upload instructions](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository) and [publishing-source guide](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

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

Use the [signed receipt](evidence/device-signed-purchase.json), [identity checks](evidence/receipt-identity-checks.json), and [device-signed contact states](evidence/device-signed-contact-states.json).
The October 2 state checks verify both BOOT states with the same provisioned P-256 pin.
The older contact-state evidence uses the historical HMAC format. Do not relabel it as P-256 evidence.

Inspect Git history before completing the prior-development field.
The initial checked repository commit dates to September 24, inside the September 14 event window.
The original concept and other relevant work can predate that commit. A commit date alone cannot establish when all development began.
The founder must disclose earlier concept/code history accurately and distinguish it from work inside the event window.

Registration, acceptance of contest terms, public uploads, external outreach, spending, pushing, and final submission remain separate owner actions.
Local research, documentation, verification, and commits are authorized in this task.
