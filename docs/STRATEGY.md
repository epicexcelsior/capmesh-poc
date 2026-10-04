# FieldProof product strategy

**Company hypothesis: machines buy and verify physical services from infrastructure another operator owns.**
The implemented first step buys a fresh contact observation. The next commercial test connects one buyer to one authorized provider.
The [starting page](FOCUS.md) condenses the current decision. The [bounty plan](BOUNTY_PLAN.md) owns execution priorities.
The [dated research](research/2026-10-02-fieldproof.md) owns sources, precedents, economics, and unresolved commercial claims.
The [October 4 source check](research/2026-10-04-physical-services.md) evaluates the physical-service framing and existing infrastructure solutions.

## The story to explain

**Company target: one integration for machines to transact with another operator's physical infrastructure.**

A fleet operates a robot. Another company operates the facility the robot needs to use.
Their software needs agreed service terms, permission, payment, and evidence before it can rely on the interaction.
FieldProof tests a common transaction layer across that operator boundary.

The first buyer hypothesis is a fleet software operator that needs repeated interactions at independent facilities.
The buyer benefit to test is reusable service integration across those facilities.
The provider benefit to test is controlled access to its existing services and accountable delivery to approved buyers.
No customer confirms either benefit yet.

The demonstration answers one small question in that larger workflow: what does the gate-contact observer report now?
It purchases that answer on Solana Devnet, authenticates the pinned device receipt, and checks its freshness.
It grants no access, opens no gate, reserves no dock, and moves no robot.

| Responsibility | Implemented today | Next integration |
|---|---|---|
| Payment | Solana Devnet test USDC through x402 | Commercial terms and a recovery policy with a pilot operator |
| Evidence | Pinned device signature, original challenge, stable samples, and freshness | Evidence for a permitted service precondition or result |
| Operator and service identity | Trusted USB public pin. peaq Agung registry reads only. | Activated peaq operator/key/service claims, compared with the buyer's trusted pin |
| Permission and control | Outside the MVP | Facility authorization and the robot controller's own safety checks |

The receipt signs an observation challenge. The gateway ledger associates that challenge with the purchase.
Payment and measurement remain separate side effects. A paid observation does not establish completed access or service delivery.
The current buyer pays for the observation before measurement.
A future access-service purchase needs separate terms for readiness, reservation, use, completion, and recovery.
A readiness answer cannot reserve a resource or prevent its state from changing before use.
The operator must define any commitment window. The controller must check the conditions that govern actual use.

## Why this boundary is worth testing

VDA 5050 focuses on robot-to-fleet-control communication and excludes infrastructure and external IT interfaces.
This identifies a boundary, not a vacant market. [VDA 5050, section 2](https://www.vda.de/dam/jcr%3A09f03b91-13e2-4db3-bf30-4f221710071b/VDA5050-V3.0.0-2025-03.pdf).
Open-RMF already integrates fleets, doors, elevators, and building systems. [Open-RMF](https://www.open-rmf.org/).

Use existing adapters where their semantics fit.
Test whether independent operators still need common commercial terms, evidence checks, and recovery around those adapters.
An existing API, camera, integrator, or Open-RMF deployment remains a valid alternative.
If it solves the buyer's problem adequately, record that result before adding another layer.

## Start with a service relationship

### The wedge to test first

A visiting delivery robot reaches another operator's loading gate and needs a current contact answer for its next decision.
The candidate product is a buyer contract for that answer: selected device, independent key, exact question, spending limit, and useful-time limit.
The implemented purchase supplies this contact evidence. It does not supply access rights or prove that a route is clear.

Start at the moment of arrival. Advance availability, dock reservations, and charging sessions need different commitments and service contracts.
The first pilot must expose a repeated failure that the facility's existing API or integration does not already resolve.
Compare useful evidence, integration effort, failure recovery, and total costs before claiming an advantage.

Open-RMF already supplies infrastructure interoperability. robotic.sh already presents a machine-service market.
Machine commerce alone is not a novelty claim. [Open-RMF](https://www.open-rmf.org/), [robotic.sh](https://www.robotic.sh/).
The differentiated hypothesis is independent buyer acceptance of transaction-associated physical evidence across operators.
The receipt signs the challenge. The ledger supplies the purchase association. Neither proves physical truth or atomic service delivery.
No source check establishes an uncrowded market. A real buyer workflow must establish the wedge.

### Validate one relationship

1. Find one fleet decision that depends on infrastructure another operator controls.
2. Establish the operator's permission and the buyer's right to use the service.
3. Connect an existing API or checked contact to the same observation contract.
4. Measure repeated use, end-to-end delay, failures, recovery cost, and willingness to pay.
5. Connect a second independent facility and measure how much integration work the buyer reuses.

The second facility tests the central hypothesis. More sensors at one site do not establish cross-operator value.
The first commercial product can charge for integration and service operation.
A transaction fee becomes meaningful only when real service value and recurring paid use exist.
Enterprise fees, transaction fees, and service-level commitments remain pricing options to test.
The 0.001 test-USDC observation price sets no commercial service price.

## Earn revenue before network scale

The early business hypothesis is paid enterprise integration and support for one fleet-provider relationship.
It does not require an open marketplace or substantial transaction volume to test.
The buyer must confirm a budget and renewal value before this becomes a business model.

| Stage | Revenue hypothesis | Evidence required before expansion |
|---|---|---|
| First relationship | Integration, deployment, and support fees | An authorized buyer funds a pilot. Total delivery and support costs remain viable. |
| Repeat deployments | Recurring software fees per fleet, facility, or endpoint | Buyers renew. The second facility reuses substantial integration work. |
| Paid service volume | A fee on machine-service transactions | Real service spend exists. Failed delivery and dispute costs remain controlled. |
| Useful network | Discovery, trust history, and demand routing | Independent providers and buyers repeatedly use shared interfaces and history. |

A proposed low-four-figure monthly fee remains an untested pricing hypothesis.
Quoted service prices, provider income, and revenue projections require actual buyer evidence.
Do not turn unsupported requests into a claim that a monthly revenue opportunity exists.

Buyer interviews start alongside the MVP, rather than after several more endpoint builds.
The founder owns outreach and customer commitments. The existing application and robot safety controls remain outside this prototype.

## Expand after the first workflow works

[View the commercial-path graphic](assets/fieldproof-service-expansion.svg). Every expansion and revenue stage remains a hypothesis.

Access readiness is the first candidate. Dock use, charging, elevators, handoffs, and equipment use are later candidates.
Each needs its own permission, controller adapter, evidence contract, failure policy, and economics.
An OPEN contact cannot establish dock clearance, charger availability, reservation, or successful handoff.

Potential network effects require measured reuse: more authorized endpoints make the existing buyer integration useful in more places.
Service history must separate observed latency, failed delivery, disputes, and independently established outcomes.
A signed answer or successful test transfer alone cannot create a reliability score.
Unsupported requests can guide interviews. Committed demand and actual delivery economics must precede new hardware investment.

## Evidence required for a pilot

The fleet operator must identify an actual incident, its existing alternative, and the cost of missing the required fact.
The facility operator must approve the service, eligible buyers, installation, and data exposure.
Measure useful-time limits, purchase-to-decision delay, installation, support, delivery failures, and recovery costs.
Test repeated use and renewal. Compliments and demo transactions do not establish demand.

The six-month validation target is one fleet using the same integration at two independent facilities with repeated paid service use.
This is an acceptance target, not a forecast or customer commitment.
If integration remains bespoke at every site, test an enterprise adapter product before investing in a network.

## Durable advantage to test

The potential assets are installed buyer workflows, permissioned supplier relationships, and measured delivery and recovery quality.
A request format, signature, payment rail, or local demand counter remains easy to reproduce.
Calibrated sensing, protected device identity, and independent corroboration require separate pilot evidence.

## Product risks and decisions

These conclusions follow from the current implementation. They are hypotheses for a pilot, not validated market facts.

| Risk | Current evidence | Decision or validation |
|---|---|---|
| Open contact does not establish safe passage | The device samples one GPIO. It checks no clearance, permission, vehicle condition, or later gate movement. | Keep DISPATCH as a demo recommendation. A vehicle controller retains its own motion checks. |
| The buyer and seller remain unproven | No customer pilot, recurring paid demand, or avoided-cost measurement exists. | Test one immediate logistics or robotics decision with a buyer and an authorized site operator. |
| Local sensing does not establish a remote marketplace | The gateway binds to loopback and reaches one nearby BLE device. No remote provider registry or buyer integration exists. | Earn one cross-site buyer workflow before building open provider discovery. |
| Provenance does not establish truth or location | Device receipts now use a USB-provisioned P-256 identity. Physical flash access can extract the key. The location remains a provisioned label. | Protect storage and firmware integrity before production. Begin with a known site operator and checked installation. |
| Payment does not authorize access to operational data | The gateway sells the same observation to any compatible payer. It has no site-specific buyer permissions. | Establish site-owner consent and buyer access rules before exposing real facility state. |
| Delivery can fail after payment | The Bluetooth-off rehearsal retained a delivery failure. The latest device-signed paid receipt was seven seconds old within a ten-second contract. | Measure payment, measurement, and transport latency. Define credits or refund review before promising a commercial service. |
| Per-query payment does not establish sustainable economics | The 0.001 USDC price is a demonstration value. Hardware, installation, support, failure, and refund costs remain unmeasured. | Compare repeated-query purchases with a subscription or prepaid budget in one pilot. Record total service costs. |
| Ledger counts do not establish investment demand | Rehearsal queries and unpaid quotes can increase counts without demonstrating willingness to pay. | Separate test traffic, requests, delivered paid purchases, and committed demand before using counts to fund installations. |

The strongest next validation is one recurring decision outside the buyer's own facility.
Measure the cost of missing that fact, the required freshness, and the operator's permission to sell it.
Use existing operational data when it answers the question. Add a sensor when it supplies otherwise unavailable evidence.
Keep Solana as the demonstrated payment rail. Add peaq when identity or activity history serves that buyer-provider relationship.

## Evidence discipline

A ten-second contact observation cannot predict availability at arrival after a long trip.
Advance dispatch requires an operator-backed availability commitment for a stated future interval.
Do not describe the current measurement as that commitment.

Keep test traffic, requests, delivered paid purchases, and committed demand separate.
Do not fund installations from raw query counts.
Freeze the existing contact MVP through the Germany submission. Reopen scope only under the [research stop rule](FOCUS.md#do-next).
