# Demonstrate fresh physical evidence

Use the local simulator for reviewers without hardware. Use BLE when the ESP32 is attached.
Run commands from the repository root unless a step changes directories.

## Recorded demonstration

Use the [2:30 signed-receipt walkthrough](assets/fieldproof-signed-receipt.webm) for the current technical demonstration.
It inspects a recorded public Devnet purchase and executes browser verification and attacks. It has captions and no audio.
The older recordings below preserve historical simulator and HMAC demonstrations.

[Watch the 69-second screen recording](assets/fieldproof-demo.webm). It shows simulated payment and simulated contact evidence.
The final scene includes results from the executed CLI adversarial loop. The recording has no audio.

To reproduce it, start open and closed simulators on ports 4022 and 4024.
Run `node scripts/record_demo.cjs /path/to/installed/playwright` from the repository root.
Playwright requires its installed Chromium browser.

The MVP track requires a 2–3 minute video. The [2:30 presentation](assets/fieldproof-walkthrough.webm) meets that length.
It combines unchanged simulator footage with explanatory title cards. It has no audio.
Run `python3 scripts/build_walkthrough.py` to reproduce it with ffmpeg, ffprobe, and the system Lato fonts.
The build checks the source hash and duration. It replaces the local artifact only after those checks pass.
The [submission draft](SUBMISSION.md) contains its scene sequence and the unresolved submission fields.

The extended recorder expects gateways on ports 4021, 4022, 4023, and 4024.
Port 4023 uses real BLE contact with simulated settlement. Port 4024 simulates a closed contact.
Run `node scripts/record_demo.cjs /path/to/installed/playwright docs/assets --submission`.
The recorder preserves the final artifact only after every scene passes. The [2:30 live walkthrough](assets/fieldproof-submission.webm) passed all scenes.
It includes a real BLE observation with simulated payment. It predates the verified public payment and human state-change checks.
The current script uses an updated quote caption. Add the newer evidence before uploading a final submission video.

## Short rehearsal script

1. Open the dispatch desk at `http://127.0.0.1:4022` after `npm run demo` in `gateway`.
2. Explain the question: an autonomous vehicle needs fresh gate state before it moves.
3. Select **Get payment quote**. Show 0.001 Devnet USDC and the 402 response.
4. Select **Run simulation**. Show the labeled payment mode, receipt, and DISPATCH decision.
5. Wait eleven seconds. Show WAIT after evidence expires.
6. Run `uv run --project host capmesh observe-demo --simulated` in another terminal.
7. Show the cheaper stale provider's rejection and the fresh provider's selection.
8. Show the rejected response replay, changed challenge, changed state, and request replay.
9. Explain the demand ledger and the path toward independent observers.

No funds move in this script. Do not describe fake facilitator settlement as an on-chain payment.
For closed-contact rehearsal, restart the simulator with `npm run demo -- --closed`.

## Inspect the recorded signed purchase

1. Open `/proof` on the running local gateway.
2. Check VALID signature, MATCHES challenge, 5/5 AGREE, and expired WAIT.
3. Select **Flip contact state** and check REJECTED signature.
4. Select **Change challenge** and check REJECTED binding.
5. Select **Use another key** and check REJECTED signature.
6. Select **Verify original** and check VALID with expired WAIT.
7. Select **Verify recorded payment**.
8. Check the confirmed slot, expected mint, payer −1000, and merchant +1000 base units.
9. Check that the evidence remains expired WAIT.

The signature tests run locally in Web Crypto. The payment check needs internet access to the public Devnet RPC.
An unavailable or rate-limited RPC produces NOT VERIFIED. The button permits a manual retry and leaves receipt verification intact.
The inspector never sends funds or measures hardware.
The [README export steps](../README.md#inspect-the-recorded-physical-purchase) create a static package for judge review.
The [founder explanation](HOW_IT_WORKS.html#understand) connects the demonstration to the buyer workflow and its limits.

## Real hardware

1. Stop other BLE scans.
2. Run `uv run --project host capmesh observe-demo`.
3. Check `evidence_mode: physical-contact-demo` and `sample_agreement: 5/5`.
4. Run `npm run demo -- --physical` in `gateway` for a browser purchase with real evidence.
5. Hold BOOT while you select **Run simulation**.
6. Check CLOSED and WAIT.
7. Release BOOT, create another quote, and run another observation.
8. Check OPEN and DISPATCH.

Do not press Reset while you hold BOOT. This combination can enter the ROM download mode.
The P-256 human press/release sequence passed on October 2, 2026. [Both device-signed receipts](evidence/device-signed-contact-states.json) record it.
The older [October 1 checks](evidence/contact-states.json) retain historical HMAC receipts.

## Public-facilitator payment

1. Run `npm start` in `gateway`.
2. Fund a disposable buyer with Devnet USDC.
3. Run `node buyer.js /path/to/disposable.keypair.json` from `gateway`.
4. Preserve the purchase ID, settlement transaction, authenticated receipt, and buyer decision.
5. Check the transaction on Devnet before you claim an on-chain integration result.

If the connection or evidence delivery fails, keep the purchase ID from the buyer error. Review it before another payment.
The keypair stays outside the repository. The client accepts only loopback endpoints and 0.001 USDC on the configured Devnet mint.
This successful payment gate passed on October 1, 2026. The user funded the disposable buyer through the supported faucet interface.
Independent Devnet RPC checks confirmed the exact mint, recipient, and 1,000-unit transfer. [Paid P-256 evidence](evidence/device-signed-purchase.json) records the current signed purchase.

## Failure review

- `settling` after a crash: check the facilitator or chain before you repeat any payment.
- `settlement_unknown`: preserve the purchase ID and review the chain outcome.
- `measuring` after a crash: preserve settlement and inspect device logs. Do not settle again.
- `delivery_failed`: use the preserved settlement for refund review. Automatic refunds do not exist.
- `NONCE_CACHE_FULL`: wait for outstanding authorizations to expire. Do not evict replay protection.
- `AUTH_EXPIRED`: create a new challenge. A reboot also resets the prototype time anchor and replay table.

Back up `.local/purchases.sqlite` before a manual repair. Keep its WAL files with the database during an active process.
Never edit a purchase record to make an unresolved settlement appear successful.

## Wi-Fi route conflict

A VPN can advertise the same subnet as the ESP32 access point.
On this machine, Tailscale selected its tunnel for `192.168.4.1` even after Wi-Fi joined the board.
Use `--http-interface YOUR_WIFI_INTERFACE` to bind device HTTP to Wi-Fi on Linux.
The option does not change VPN routes or global proxy configuration.

```bash
uv run --project host capmesh observe-demo --http-url http://192.168.4.1 --http-interface wlp2s0
uv run --project host python scripts/check_wifi_observation.py --interface wlp2s0
```

Replace `wlp2s0` with your Wi-Fi interface name. Connect to the board access point first.
