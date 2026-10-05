# Record one clear FieldProof video

Record a 2:30 screen walkthrough with your voice. Change these suggested words to sound like you.
The opening must explain the buyer's problem before it names the technology.
Use the verified gate-contact demo below. The foil package sensor remains unverified.

## Prepare only these three things

1. Open the three recording frames from the local start page.
2. Open the actual 32.8-second October 5 paid capture from that page.
3. Open the saved paid inspector at `http://127.0.0.1:4021/proof?live=1&present=1`.

Before recording, check VALID, VERIFIED TRANSFER, EXPIRED, and WAIT in the saved inspector.
Make a five-second microphone test. Play it back with sound.
Keep private wallets, terminals, notifications, and unrelated tabs outside the capture.
The [rehearsal](REHEARSAL.md#record-one-150-second-walkthrough) owns setup and recovery. The [demo runbook](DEMO.md) owns live commands.

## 1. The problem / 0:00–0:20

**Show:** The problem frame. A face-camera introduction is optional.

**Say:**

> A delivery robot arrives at a warehouse owned by another company. It can pay for an observation, but payment doesn't tell it whether the gate is open now. FieldProof checks whether a signed physical answer is still useful.

**Point:** The robot and the gate belong to different operators. The question is about now.

## 2. The product / 0:20–0:40

**Show:** The purchase frame: Pay → Measure → Verify.

**Say:**

> The buyer asks one question, chooses a device, and sets a ten-second limit. It pays 0.001 test USDC on Solana Devnet. After settlement, the ESP32 reads its contact input and signs the answer.

**Point:** Payment comes before the measurement. The device signs the observation, not the payment.

## 3. The actual purchase / 0:40–1:13

**Show:** Play the continuous October 5 paid capture. Speak over its silent footage.

**Say:**

> This is a recording of our actual purchase today. The laptop sends the payment and talks to the ESP32 over Bluetooth. The buyer checks the device key, the question, and the observation's age. Fresh OPEN evidence produces DISPATCH. Eleven seconds later, the same answer expires and the buyer changes to WAIT.

**Point:** This footage records actual Devnet settlement and a real ESP32 input. It uses the original clock.
If playback takes longer, pause your narration. Never edit the receipt times to make the saved answer fresh.

## 4. Why the buyer waits / 1:13–1:45

**Show:** The current saved inspector. Point to payment, signature, age, and WAIT.
Select **Flip contact state**. Wait for REJECTED. Select **Verify original** to restore it.

**Say:**

> Here is that saved answer now. Solana still verifies the payment. The device signature is still valid. But the observation is too old. Now I change its contact state. The signature check rejects it, and the buyer keeps WAIT. Paying for an answer does not make every answer acceptable.

**Point:** One attack is enough. Keep the pointer still while you explain each result.
If the current chain query fails, state that failure. Do not read the successful-query line above.
Use the recorded purchase and its Explorer link as historical evidence instead.

## 5. What the hardware does / 1:45–2:05

**Show:** A short shot of the ESP32. The Seeker shot is optional.

**Say:**

> This board is the physical observer. For this prototype, its BOOT button stands in for a gate contact. The Seeker independently verifies the same receipt. It does not supply a second measurement or send the payment.

**Point:** The board is real. The gate and robot are illustrations. DISPATCH is a demo recommendation.
If you omit the phone, omit the last two spoken sentences.

## 6. The next useful test / 2:05–2:30

**Show:** The pilot frame. Return to face camera for the last sentence if convenient.

**Say:**

> The next test is one fleet working with one authorized facility, then a second facility using the same integration. I want to test paid integration and support first. Customer demand is still unvalidated. The goal is one interface for machines to transact with infrastructure they do not own.

**Point:** This is the next business test, not an existing customer or network claim.

## Record these extra shots only if convenient

| Shot | Length | What to show |
|---|---|---|
| Board close-up | 8 seconds | USB-powered board. Point to BOOT. Show one press and release. |
| Laptop and board | 5 seconds | Both devices in one frame. Keep private screens outside the shot. |
| Seeker verifier | 5 seconds | FieldProof's receipt page with payment, signature, expired age, and WAIT. |

These are supporting shots. A board press alone does not prove a new request or payment.
For a new physical request, show the action and result in one continuous shot. Label simulated settlement explicitly.
The existing actual paid capture supplies the complete transaction evidence.
Skip extra shots if they delay the main recording. Screen capture with your voice is sufficient for this route.

## Keep the first take simple

Record the screen and voice together. You do not need music, transitions, or a new slide deck.
If you stumble, pause and repeat the sentence. Trim the pause afterward.
Capture at 1280 × 900 or larger. Keep the browser zoom at 100 percent.
Keep the final video within two to three minutes. Verify sound and public playback before submission.
Use the [video cover and project graphic](SUBMISSION.md#ready-to-use-visual-materials).

## Explain these terms if someone asks

- **Solana:** records the test-USDC payment from buyer to merchant.
- **x402:** gives the buyer payment terms through an HTTP response.
- **Bluetooth:** carries the question and device answer between the laptop and ESP32.
- **Device signature:** lets the buyer verify the answer against its trusted device key.
- **Challenge:** identifies this particular question. Another question cannot reuse this answer.
- **Freshness:** compares the observation's signed time with the buyer's age limit.
- **WAIT:** the available evidence does not permit the demo recommendation to dispatch.
- **peaq:** machine identity is the planned next integration. Registry reads work. Activation remains incomplete.

The signature verifies a device's claim. It does not prove truthful sensing, safe movement, or permission to enter.
Payment and delivery are separate. Automatic refunds do not exist in this prototype.
