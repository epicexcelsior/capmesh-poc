# Product and hackathon strategy

FieldProof sells fresh evidence for a costly physical decision. The first buyer hypothesis is mobile logistics and robotics.
The gate contact makes the decision visible: dispatch through an open gate, or wait for new evidence.
A generic environmental reading does not communicate that decision value as directly.

## Demonstration priorities

1. Show the real physical measurement and its declared limits.
2. Show challenge-bound authenticity and freshness.
3. Reject old or altered evidence deliberately.
4. Compare the cheaper stale provider with the fresh provider.
5. Separate payment verification, settlement, and delivery failure.
6. Show demand as a future deployment signal.

The current MVP preserves this narrative with a button/contact stand-in.
The next hardware upgrade is an external contact, distance, or occupancy sensor with independently checked wiring and behavior.
The current demonstration does not establish loading-bay occupancy or independently observed gate motion.

## Submission path

The project targets the Germany MVP and peaq machine-economy tracks referenced by Carlo.
The [submission draft](SUBMISSION.md) records the verified requirements, deadlines, required fields, and local presentation copy.
The MVP deadline is October 5, 2026, at 23:59:59 CEST. The peaq deadline is October 13 at 08:59 CEST.
Winner announcement dates are separate. Verify the listings again before submission.

The peaq listing accepts prototypes and assesses the underlying machine-economy mechanism.
Native peaq activation is not an explicit mandatory requirement. Keep the paid observation and decision loop as the core demonstration.
The current [peaq Solana onboarding guide](https://docs.peaq.xyz/peaqos/guides/onboard-on-solana) reports paused onboarding and a mainnet-only flow.
No peaq transaction exists. No prize, eligibility outcome, or acceptance is guaranteed.

After a supported onboarding path exists, a useful integration gives the observer an identity and reports honest observation activity.
The current [event guide](https://docs.peaq.xyz/peaqos/guides/submit-events) distinguishes self-reported activity from protected hardware signatures and verifiable revenue.
A public HMAC demo key does not qualify as protected hardware. Simulated payments and Devnet tokens do not establish real revenue.

## Roadmap after the MVP

| Horizon | Evidence to earn | Product change |
|---|---|---|
| First submission | Paid observation, real input change, rejected replay, recorded demo | Complete and document the one-observer decision loop |
| First month | A buyer repeatedly needs one specific physical fact | Run one logistics or robotics pilot and collect unmet demand |
| Months 2–3 | Independent observers improve a useful decision | Choose one vertical and add corroboration and provider history |
| Months 4–6 | Recurring demand and sustainable provider earnings | Use committed demand to guide installations |
| Later | Dense coverage, quality history, buyer integrations | Develop the trust and routing network |

Source identity and signatures establish provenance. They do not establish truth.
Confidence requires sensor error models, calibration, independence, and evidence from repeated outcomes.
Raw vote counts cannot defeat fake or correlated observers.

## Customer test

Find one buyer with a recurring, fresh, location-specific fact that costs more to operate directly than to purchase.
Temporary demand, mobile requesters, and infrastructure owned by another party are useful starting conditions.
Record what decision the observation changes, the alternative cost, the freshness requirement, and the budget.
If buyers prefer owning sensors and dynamic discovery adds no value, revise the product hypothesis.

## Compounding assets

The potential assets are the demand graph, provider-quality history, independent coverage, and buyer workflow integration.
Solana, x402, peaq, BLE, and ESP32 are replaceable implementation choices.
The MVP aims to prove evidence that changes a decision. It does not yet prove market demand or a durable business.

## Product risks and decisions

These conclusions follow from the current implementation. They are hypotheses for a pilot, not validated market facts.

| Risk | Current evidence | Decision or validation |
|---|---|---|
| Open contact does not establish safe passage | The device samples one GPIO. It checks no clearance, permission, vehicle condition, or later gate movement. | Keep DISPATCH as a demo recommendation. A vehicle controller retains its own motion checks. |
| The buyer and seller remain unproven | No customer pilot, recurring paid demand, or avoided-cost measurement exists. | Test a fleet dispatcher that needs advance loading-dock availability and a site operator that can supply it. |
| Local sensing does not establish a remote marketplace | The gateway binds to loopback and reaches one nearby BLE device. No remote provider registry or buyer integration exists. | Earn one cross-site buyer workflow before building open provider discovery. |
| Provenance does not establish truth or location | The public demo key is forgeable. The location is a provisioned label. One observer supplies all five samples. | Use protected asymmetric receipt signing with public verification keys. Keep command authorization separate. Begin with a known site operator and checked installation. |
| Payment does not authorize access to operational data | The gateway sells the same observation to any compatible payer. It has no site-specific buyer permissions. | Establish site-owner consent and buyer access rules before exposing real facility state. |
| Delivery can fail after payment | The Bluetooth-off rehearsal retained a delivery failure. The successful paid receipt was six seconds old within a ten-second contract. | Measure payment, measurement, and transport latency. Define credits or refund review before promising a commercial service. |
| Per-query payment does not establish sustainable economics | The 0.001 USDC price is a demonstration value. Hardware, installation, support, failure, and refund costs remain unmeasured. | Compare repeated-query purchases with a subscription or prepaid budget in one pilot. Record total service costs. |
| Ledger counts do not establish investment demand | Rehearsal queries and unpaid quotes can increase counts without demonstrating willingness to pay. | Separate test traffic, requests, delivered paid purchases, and committed demand before using counts to fund installations. |

The strongest next validation is one recurring decision outside the buyer's own facility.
Measure the cost of missing that fact, the required freshness, and the operator's permission to sell it.
Use existing operational data when it answers the question. Add a sensor when it supplies otherwise unavailable evidence.
Keep Solana as the demonstrated payment rail. Add peaq when identity or activity history serves that buyer-provider relationship.

## Deferred execution tasks

The owner handles GitHub visibility, pushing, video upload, Colosseum registration, and submission contact.
A later smaller task can refresh the video's pre-payment captions and add the verified payment and human state-change evidence.
The [submission draft](SUBMISSION.md) contains publication steps. The [acceptance tracker](../TODO.md) separates these tasks from completed integration.
