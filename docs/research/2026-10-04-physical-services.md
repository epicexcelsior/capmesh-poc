# Physical services: story decision

Decision date: October 4, 2026, Europe/Berlin.
Question: does the physical-service thesis clarify the existing MVP and its next commercial test?
Audience: the founder who explains the project and selects the next build.
The [strategy](../STRATEGY.md) owns the current thesis. This note preserves the source check and reasoning.

## Decision

Use cross-operator physical services as the company hypothesis.
Keep the paid contact observation as the implemented first step.
Build one buyer-provider workflow before a marketplace or new sensor fleet.
The MVP purchases an observation. It grants no access, reservation, actuation, or service-completion guarantee.

The proposed framing connects the buyer, provider, payment, and evidence into one coherent direction.
Its economics, network effects, and adoption remain hypotheses.
The refined economic sequence is enterprise integration, recurring software fees, then fees on real service transactions.
This sequence tests profitability before network scale. No proposed monthly fee or physical-service price is validated.

## What the sources establish

VDA 5050 version 3.0.0 covers communication between mobile robots and fleet control.
Section 2 excludes peripheral equipment, infrastructure components, and external IT interfaces.
The PDF itself says March 2026, despite the URL filename containing `2025-03`.
This scope boundary is real. It does not establish commercial demand or an unsolved infrastructure market.
[VDA 5050, section 2, pages 6–7](https://www.vda.de/dam/jcr%3A09f03b91-13e2-4db3-bf30-4f221710071b/VDA5050-V3.0.0-2025-03.pdf).

Open-RMF explicitly supports multiple robot fleets and infrastructure, including doors, elevators, and building systems.
Its interface documentation includes door-state and door-command messages.
FieldProof cannot claim that robot-infrastructure interoperability itself lacks a solution.
[Open-RMF](https://www.open-rmf.org/), [official interface documentation](https://github.com/open-rmf/rmf_docs/blob/main/docs/source/interfacing/index.rst).

Hivemapper rewards coverage, freshness, and quality. Its documentation also describes customer-funded area bounties.
This provides an analogy for directing supply toward useful demand.
It does not validate FieldProof's economics, permission model, or network effects.
[Hivemapper reward factors](https://docs.hivemapper.com/honey-token/earning-honey/individual-reward-factors/).

## Inference to test

Existing infrastructure adapters can supply the physical connection.
FieldProof tests a commercial boundary above that connection: explicit terms, permitted buyers, payment, fresh evidence, and recovery across operators.
No fleet adapter, permissioned facility integration, or recurring customer exists today.
The first pilot must establish a problem that an existing API, camera, integrator, or Open-RMF deployment does not already solve adequately.

## Corrections to the proposed pitch

| Proposed claim | Accurate wording today |
|---|---|
| FieldProof proves a physical precondition | The buyer authenticates what the pinned device reports and checks its age. Installation and truth remain separate. |
| peaq proves machine identity | An activated registry entry can record operator and key claims. Current FieldProof peaq work is read-only. |
| Evidence binds to a transaction | The receipt signs the original observation challenge. The gateway ledger associates that challenge with the purchase. |
| One physical transaction completes atomically | Payment and measurement remain separate side effects. Failed delivery needs manual review. |
| Check readiness, then pay for access | The current purchase pays for the observation before measurement. Access needs a separate commitment and delivery contract. |
| A robot pays for access | The implemented buyer pays for one observation. Access permission and control remain outside the MVP. |
| Machines safely pay for and use services today | The prototype checks an observation purchase. Service access, actuation, authorization, and safety controls remain separate. |
| More endpoints create a network effect | Endpoint reuse across independent operators is a hypothesis. Test a second facility before claiming it. |

## Stop research and improve the entry

Keep one story, one observed purchase, and one failure demonstration.
Use the existing technical walkthrough and simulator as the stable review path.
Prepare peaq identity inputs in isolation. Permanent activation requires reviewed inputs, an operator wallet, and bounded spending authorization.
Stop peaq implementation at a documented blocker. Keep it outside the October 5 MVP critical path.
Collect one actual buyer incident, existing alternative, operator permission, useful-time window, and budget.
Start buyer validation alongside engineering. Do not wait until week three to test the main market assumption.
Do not invent market size, customer interest, revenue, savings, or service prices.
