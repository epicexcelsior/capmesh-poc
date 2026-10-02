# Prepare the next physical demonstration

**Decision: borrow a contact sensor first. Keep the existing signed-contact demonstration as the fallback.**
As of October 2, 2026. This plan uses the founder's reported Munich MakerSpace access.
Parts availability, reservations, and local prices remain unverified. This document authorizes no purchase.

The next result must show a physical fixture that changes the measured state.
A second board then tests distinct device identities. A phone tests reviewer access and an optional wallet workflow.
These upgrades do not establish customer demand or safe robot motion.

## Borrow these parts within three days

| Priority | Part | Quantity | Purpose and selection rule |
|---|---|---|---|
| 1 | Enclosed magnetic reed contact and matching magnet | 1 set | A two-wire, unpowered contact. Avoid a powered alarm module with an unknown output voltage. |
| 1 | Solderless breadboard and jumper wires | 1 board, 10 wires | Use connectors that fit the actual board headers and sensor leads. |
| 1 | Multimeter | 1 | Check continuity, resistor values, and the sensor's open/closed behavior before connection. |
| 1 | Hinged cardboard or scrap-wood gate, tape, and mounting material | 1 fixture | Mount the contact and magnet so closing the fixture closes the circuit. |
| 1 | 1 kΩ resistors, ¼ W | 2 | Add series current limiting before any bare-LED output test. |
| 1 | 10 kΩ resistors, ¼ W | 2 | Available for a defined external pull-up if the selected circuit requires it. |
| 2 | ESP32-C6 development board with populated headers | 1 extra | Prefer the same documented board model. Another ESP32 family requires a separate firmware compatibility check. |
| 2 | USB data cable and stable USB power | 1 extra each | Give the second board its own connection and provisioned signing key. |
| 2 | Mechanical limit switch with COM and NO contacts | 1 | Optional second sensing method. Check its circuit with the multimeter. |
| 3 | Android phone with Chrome | 1 | Test the mobile inspector. A wallet workflow requires separate software integration and test-only funds. |

An example magnetic contact closes near its matching magnet. It needs no powered sensing module.
Treat the exact switching distance as a property of the borrowed part. [Adafruit contact description](https://www.adafruit.com/product/375)

MakerSpace lists Munich workshop facilities. This does not establish component stock or permission to borrow these parts.
Use your existing access to check the electronics area and material rules. [MakerSpace](https://www.maker-space.de/)

## Resolve the board before wiring

The current chip is ESP32-C6FH4. The exact development-board model and header layout remain unknown.
Chip GPIO numbers and physical header positions are different labels.

1. Disconnect the bare LED until its series resistor and wiring are identified.
2. Photograph both board faces and all visible model and pin labels.
3. Photograph the sensor and its model or terminal labels.
4. Match the board to its manufacturer's schematic.
5. With USB disconnected, check the sensor circuit with the multimeter.

The current firmware reads GPIO9 through BOOT. GPIO9 also controls boot mode.
An external switch that holds it low during reset can prevent normal application boot.
Do not use GPIO9 as the permanent fixture input. [Espressif boot troubleshooting](https://docs.espressif.com/projects/esp-idf/en/stable/esp32c6/get-started/flashing-troubleshooting.html)

GPIO18 is a candidate input only after the actual board schematic confirms its availability.
Keep the native USB pins, flash connections, and boot-strapping pins out of the external-contact selection.
ESP32-C6FH4 does not expose every numbered chip GPIO. [Espressif GPIO restrictions](https://docs.espressif.com/projects/esp-idf/en/stable/esp32c6/api-reference/peripherals/gpio.html)

## Understand the contact circuit

Planned circuit, not the current wiring:

```text
3.3 V
  |
  +-- 10 kΩ pull-up -- selected INPUT GPIO -- dry contact -- GND
```

The pull-up sets an open circuit to HIGH. A closed dry contact connects the input to GND and reads LOW.
The firmware reports LOW as `closed: true`.
Place the magnet so a closed fixture produces that state. Verify both fixture positions before assigning the gate meaning.

The board must configure the selected pin as an input. The contact supplies no external voltage.
Never connect a powered 5 V sensor output directly to this input.
Do not change the wire while USB power remains connected.
The exact pull-up choice and GPIO assignment require the board and part checks above.

**Failure limit:** a broken wire can look like an open gate in this simple circuit.
Five matching readings cannot distinguish that fault from a real open state.
Use the fixture as a demonstration. A deployed installation needs a defined fault-detection design and physical reference.

## Acceptance gates for each upgrade

| Upgrade | Required observed result | Claim to avoid |
|---|---|---|
| External contact | Fixture closed/open yields two new signed readings. The buyer verifies the configured sensor, key, challenge, and age. | BOOT evidence proves the new installation |
| Second device | Distinct provider IDs and keys verify separately. Swapped keys, provider IDs, and challenges fail. | Two boards automatically establish independent truth |
| Corroboration | Contradictory or stale observations produce WAIT under an explicit buyer rule. | Two observers remove correlated faults or measure confidence |
| Phone | Chrome displays controls, evidence, failures, and the same decision correctly. | Mobile layout proves wallet payment integration |
| Wallet | An explicitly approved test payment settles once. Its independently verified receipt remains subject to freshness. | A wallet button alone proves machine autonomy |

Two boards on one switch share its wiring and physical faults.
Two separately installed sensors still require checked placement, permissions, and a failure model.
Never turn sample agreement or observer count into a calibrated probability.

## Use the next three days

### Day 1: protect the working entry

- Complete the human registration and project-page tasks in [the bounty plan](BOUNTY_PLAN.md).
- Rehearse the existing purchase, expiry, and receipt attacks with [the short guide](REHEARSAL.md).
- Borrow priority-one parts. Preserve the working board until the new circuit and software pass their gates.
- Record one actual buyer incident and its existing alternative. Leave missing commercial facts unknown.

### Day 2: add physical evidence

- Assemble the hinged fixture with the disconnected sensor.
- Resolve the board pin and record its circuit before firmware changes.
- Test open, closed, an unstable transition, disconnect, and stale evidence.
- Use the original recorded inspector if the new fixture misses its acceptance gates.

### Day 3: submit the verified result

- Record the technical demonstration with exact simulation and test-payment labels.
- Record the founder presentation in your own words.
- Check the judge link on another browser or phone.
- Complete the human MVP submission before October 5 at 23:59:59 CEST.
- Keep the second board and native peaq integration for the next checkpoint if they threaten that deadline.

## Give the phone a specific job

The first phone test requires no wallet. Use it to inspect the judge package and explain a rejected receipt.
The phone cannot reach the laptop's `127.0.0.1` address. Public HTTPS hosting requires a separate publishing step.
The current gateway binds to loopback. Do not expose its physical or simulated payment endpoints for this test.

A later Android wallet workflow can use Mobile Wallet Adapter with a wallet on the same device.
Current official guidance supports Android Chrome and lists compatible wallets. It excludes iOS browser support.
This adapter is not implemented in FieldProof. [Solana Mobile web integration](https://docs.solanamobile.com/get-started/web/apps)

## Test the need before adding another sensor type

The strongest next product evidence is an actual decision that an existing camera, operator API, or direct integration fails to support.
Hardware demonstrates execution. It does not establish the need for a marketplace or per-query payment.

Record these facts from one buyer and one infrastructure operator:

1. Describe the last incident and its measurable consequence.
2. Name the missing fact and the exact decision it changes.
3. Describe the current workaround, access rights, and cost.
4. Measure the useful lifetime from receipt to actual use.
5. Identify who permits the observation and its sale.
6. Record the buyer's actual budget and expected frequency.

If the buyer already receives the fact reliably, record that result and revise the workflow.
Do not cite test purchases or local request counts as demand.
The [research decision](research/2026-10-02-fieldproof.md) owns precedents, alternatives, and the commercial hypothesis.

Copilot's new authentication preflight returned HTTP 403 on October 2.
Fresh authenticated research did not run. Restore that access before the next Copilot-specific query.
The existing research record remains available. This parts plan uses the official sources linked above.
