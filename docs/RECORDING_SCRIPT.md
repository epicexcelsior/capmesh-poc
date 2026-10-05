# Record one clear FieldProof video

Record your voice and screen. Use a phone camera for your hand on BOOT during the same take.
Aim for 2:30. Your explanation and the live interaction carry the video.

**One story:** A robot needs a current answer from another operator's gate. Payment stays confirmed after that answer expires.

**Hardware prerequisite:** The attached board still runs the GPIO20 experiment. BOOT cannot control that input.
Unplug USB, remove both added leads, and reconnect the bare board. Confirm the board is clear before firmware restoration.
Use the live BOOT scene only after restoration and an actual held/released check.
The foil fixture is unreliable. Keep the verified gate-contact story.

## 1. Explain the problem / 0:00–0:20

**Show:** Your face or the problem frame. Keep the robot and gate visible.

**Say:**

> A delivery robot arrives at another company's warehouse. It can pay, but payment doesn't tell it whether the gate is open now. FieldProof lets the buyer verify a fresh physical answer before its next decision.

## 2. Show the physical input / 0:20–1:15

**Show:** The focused physical page at `http://127.0.0.1:4023/?present=1`.
Film your hand and board with the phone at the same time.

1. Hold BOOT.
2. Select **Get payment quote**.
3. Select **Request observation**.
4. Keep BOOT held until the page shows CLOSED and WAIT.
5. Release BOOT.
6. Select **Get payment quote** again.
7. Select **Request observation** again.
8. Point to OPEN and DISPATCH.
9. Wait for the evidence age to exceed ten seconds.
10. Point to WAIT.

**Say:**

> This ESP32 is the observer. BOOT stands in for a gate contact. This live hardware rehearsal uses simulated payment. Holding it gives CLOSED, so the buyer waits. I release it and request a new observation. OPEN gives DISPATCH. Now I leave that answer alone. After ten seconds, it expires. The buyer waits again.

**Keep clear:** Pressing BOOT alone does not update the page. Each state needs a new request.
DISPATCH is a prototype recommendation. This demo controls no gate and moves no robot.
If a request fails, stop the take. Preserve the error and diagnose it before another request.

## 3. Show the real Solana proof / 1:15–2:05

**Show:** Play the short October 5 paid excerpt from the local start page.
Then open `http://127.0.0.1:4021/proof?live=1&present=1`.
Verify the displayed transfer result before you describe it.
Select **Flip contact state**. Point to REJECTED and WAIT.

**Say:**

> Here is the actual payment run from today. The buyer sends 0.001 test USDC on Solana Devnet. After settlement, the laptop requests the ESP32 answer over Bluetooth. The device signs that answer. Here, the browser independently verifies the receipt and the transfer. The payment remains confirmed and the signature remains valid, but the answer expires. If I change the signed state, verification rejects it.

**Keep clear:** Label the excerpt **Recorded actual Devnet purchase · October 5**.
It preserves the original clock and continuous fresh-to-expired transition.
The excerpt omits the initial waiting period. Keep the full capture as supporting evidence.
The saved inspector never pays or measures hardware. The saved answer is expired now.
If the current chain query fails, state the failure. Use the recorded result and Explorer link as historical evidence.

## 4. Explain the next useful test / 2:05–2:30

**Show:** The pilot frame or your face. Keep the ending personal.

**Say:**

> The next test is one fleet and one authorized facility, then a second facility using the same integration. I want to test paid integration and support first. Customer demand is unvalidated. The goal is one interface for machines to transact with infrastructure they don't own.

The four sections are rehearsal targets. Speak naturally and measure the take.
Pause while results load. Trim setup pauses, but keep the physical action and resulting answer together.

## Record screen and hardware together

Use OBS for the screen and voice. Use the Seeker's ordinary camera for the hand and board.
The phone acts as a camera in this take. Its separate verifier role remains optional.

1. Open OBS. Run **Tools → Auto-Configuration Wizard** for recording.
2. Add a screen or window capture source for the FieldProof browser.
3. On Wayland, use the PipeWire capture source and select the browser or display.
4. Select your microphone in **Settings → Audio**.
5. Speak and verify movement in the microphone meter.
6. Mute desktop audio to avoid notification sounds.
7. Set the recording path in **Settings → Output**.
8. Select MKV as the recording format.
9. Use 1920 × 1080 at 30 fps if the five-second test plays smoothly.
10. Keep the native screen resolution if 1080p makes text small or adds scaling blur.

OBS documents source setup, audio meters, and a test recording in its [quick-start guide](https://obsproject.com/kb/quick-start-guide).
OBS recommends MKV for interrupted-recording recovery. Use **File → Remux Recordings** to export MP4 without re-encoding.
See the [official output guide](https://obsproject.com/kb/standard-recording-output-guide).

1. Prop the phone horizontally. Frame BOOT, your hand, and part of the laptop screen.
2. Keep power cables secure. Use a lamp beside the board.
3. Make a five-second test with screen capture, voice, and the phone camera.
4. Play both recordings. Verify readable text, clear speech, focus, and the visible button.
5. Start both recordings for the main take.
6. Clap once where the phone sees your hands.
7. Say “FieldProof, take one,” then start the opening.
8. Keep both recordings running through the BOOT scene.
9. Stop both recordings after the closing sentence.

The clap aligns the two recordings. Use OBS audio as the final voice track.
Overlay the phone view during BOOT without covering the state, age, or decision.
Keep the action and result synchronized. Keep a short wide shot as evidence of the live setup.

Do not build another slide deck. Use the problem and pilot frames briefly.
Keep the product on screen for most of the video. Skip music and decorative transitions.
Keep private wallets, terminals, notifications, and unrelated tabs outside both recordings.

## Finish one take

1. Watch the complete video with sound.
2. Verify the live scene says simulated payment.
3. Verify the paid scene says recorded actual Devnet purchase.
4. Verify the button, state, age, and decision remain readable.
5. Export the final MP4.
6. Open the public video link while signed out before submission.

Use the [video cover and project graphic](SUBMISSION.md#ready-to-use-visual-materials).
The [rehearsal](REHEARSAL.md#record-one-150-second-walkthrough) owns setup and recovery.
The [demo runbook](DEMO.md) owns gateway and actual-payment commands.

## Explain the technicals in plain words

- **Solana:** records the test-USDC transfer from buyer to merchant.
- **x402:** returns machine-readable payment terms before delivery.
- **Bluetooth:** carries the question and answer between the laptop and ESP32. USB supplies power.
- **Device signature:** authenticates the answer against the buyer's trusted device key.
- **Challenge:** binds the answer to this particular question.
- **Freshness:** compares the signed observation time with the buyer's ten-second limit.
- **WAIT:** the available evidence does not permit the prototype dispatch recommendation.

The device signs its observation, not a Solana transaction. The gateway ledger associates the question with the purchase.
A signature authenticates a device's claim. It does not prove truthful sensing, safe movement, or permission to enter.
Payment and delivery are separate. Automatic refunds do not exist in this prototype.
peaq identity activation remains incomplete. Keep it outside this MVP video.
