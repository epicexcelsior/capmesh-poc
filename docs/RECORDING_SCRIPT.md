# Record FieldProof in four short clips

Use your own words. Record the opening and ending on camera.
Record the two demonstrations separately. Add your explanation as voiceover if that feels easier.
Aim for 2–3 minutes after editing. A slide deck is optional.

**One point:** A confirmed payment and a valid signature do not make an old physical reading current.

Use parcel pickup as a possible application. The working hardware uses BOOT as a test input.
It does not detect a parcel. The unreliable foil contact stays out of this take.

## 1. Opening / about 25 seconds

**Record:** Your face. Save this as `01-opening.mp4`.

**Say:**

> I built FieldProof for a simple problem: payment can stay confirmed while a physical reading goes out of date. Think of a robot checking whether a parcel is ready for pickup. It needs a current answer before it acts.

## 2. Hardware / about 60 seconds

**Record:** The screen at `http://127.0.0.1:4026/proof?present=1`.
Save this as `02-hardware-screen.mkv`.
If you use the phone, film your hand and board at the same time. Save that as `02-hardware-phone.mp4`.
Clap once to align these two recordings.

1. Hold BOOT.
2. Select **Pay 0.001 Devnet USDC and read** once.
3. Keep BOOT held until CLOSED, VALID, and VERIFIED TRANSFER appear.
4. Release BOOT.
5. Select **Pay 0.001 Devnet USDC and read** again.
6. Point to OPEN, FRESH, and DISPATCH.
7. Leave the answer alone until its age exceeds ten seconds.
8. Point to EXPIRED and WAIT.

**Say:**

> For this prototype, I use the ESP32 button as a test input. Each click pays 0.001 test USDC on Solana, then the device signs a reading. I hold it: CLOSED. I release it and buy another reading: OPEN. Now I wait. After ten seconds, the reading expires. The payment and signature remain valid, but the decision returns to WAIT.

Keep this hardware clip continuous from the button action through the result.
You can record the spoken explanation afterward.
Pressing the button alone does not update the page. Each state needs a new request.
DISPATCH is the demo's decision label. No machine moves.
If a request fails, preserve the error. Stop the take and diagnose the failure.
Each paid request takes several seconds. Keep the board action and its result in the same continuous recording.
Practice first at `http://127.0.0.1:4023/?present=1`. That page uses simulated payment and separate quote/request buttons.
The paid server must run before the actual take. See [its one-click setup](DEMO.md#pay-and-read-with-one-click).

## 3. Actual payment / about 45 seconds

**Record:** Keep the same paid screen open after the reading expires.
Save this as `03-payment-screen.mkv`.

1. Wait for **VERIFIED TRANSFER** and **VALID**.
2. Point to EXPIRED and WAIT.
3. Open **Inspect the Devnet transaction** if you want to show Explorer.
4. Return to the inspector.
5. Select **Flip contact state**.
6. Point to REJECTED and WAIT.

**Say:**

> Here is the Solana transaction for that reading. The laptop's test wallet signs the payment. The ESP32 signs its answer separately. The browser verifies both. If I change the answer, the signature check fails. Payment does not make a changed or expired answer usable.

Explorer and the tamper controls send no payment and request no measurement.
If the paid flow fails, use `http://127.0.0.1:4021/proof?live=1&present=1` for the saved actual purchase.
Label that fallback as recorded evidence. It creates no new payment or reading.
If the chain query fails, state the failure. Use Explorer and the recorded result as historical evidence.
The existing October 5 paid excerpt is optional supporting footage. Label it as recorded footage.
Its original visuals remain unchanged. Do not imply that an old capture uses the new screen design.

## 4. Ending / about 25 seconds

**Record:** Your face. Save this as `04-ending.mp4`.

**Say:**

> Next, I want to test a real pickup sensor with one operator, then repeat it at a second site. The question is whether this saves a buyer another custom integration. I still need to validate that with customers.

Edit these paragraphs before recording. Keep sentences that sound like you.
Record two takes of the opening and ending. Choose the clearer take.
Leave two quiet seconds before and after each clip for editing.

## Record screen and hardware together

Use OBS for the screen and voice. Use the Seeker's ordinary camera for the hand and board.
The phone acts as a camera in this take. Its separate verifier role remains optional.

1. Open OBS. Use the existing screen and microphone sources if they work.
2. Add a screen or window capture source for the FieldProof browser.
3. On Wayland, use the PipeWire capture source and select the browser or display.
4. Enable Preview. Use **Transform → Fit to Screen** on the selected capture source.
5. Select your microphone in **Settings → Audio**.
6. Speak and verify movement in the microphone meter.
7. Mute desktop audio to avoid notification sounds.
8. Set the recording path in **Settings → Output**.
9. Select MKV as the recording format.
10. Use 1920 × 1080 at 30 fps if the five-second test plays smoothly.
11. Keep the native screen resolution if 1080p makes text small or adds scaling blur.

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

Use your face for the opening and ending. A slide deck is optional.
Keep the product on screen for most of the video. Skip music and decorative transitions.
Keep private wallets, terminals, notifications, and unrelated tabs outside both recordings.

## Finish one take

1. Watch the complete video with sound.
2. Verify the paid scene shows the actual transfer and current signed reading.
3. If you use practice or recorded fallback footage, label that footage accurately.
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
