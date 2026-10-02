# FieldProof verification record

Current continuation: October 2, 2026, Europe/Berlin. Public paid evidence dates to October 1.
The local MVP completes a public Devnet purchase, a real ESP32 observation, and both human-controlled contact states.
This record does not claim production security, safety certification, or standards compliance.

## October 2 input-pair inspector and founder rehearsal

Starting source: `6b9d284`, pushed and confirmed against the remote branch.
The inspector now verifies both recorded physical input states with the same provisioned P-256 key.
It displays neither state unless the complete pair passes. Both expired observations remain WAIT.
The [rehearsal guide](REHEARSAL.md) separates simulation, actual test payment, unpaid input checks, and peaq readiness.

| Check | Observed result |
|---|---|
| `uv run --project host pytest -q` | 54 passed, 10 hardware tests skipped in 1.19 seconds |
| `npm --prefix gateway test` | 26 passed, 0 failed in 648.11 milliseconds |
| Browser regression against gateway and final static export | Original receipt, attacks, both input states, three damaged input archives, payment fixtures, 429 recovery, and phone width passed |
| Complete browser simulation | Quote, simulated purchase, DISPATCH, then expired WAIT passed. No funds or hardware. |
| Current browser public Devnet query | Exact recorded transfer verified. The expired receipt remained WAIT. No funds moved. |
| Both simulated CLI contact states, in-memory ledger | OPEN/DISPATCH and CLOSED/WAIT passed. Stale provider rejected. All reported attacks passed. |
| Export manifest and ZIP | Eight public asset hashes and all nine ZIP members matched. Archive integrity passed. |

The final export has 7,911,926 bytes and SHA256 `180106a7b8e2f35c7ec078222f03b00145ac8f9cf951a0bff5187d22ce3f2d47`.
The paid-result video remains unchanged. It does not contain the new input-pair scene.
The RPC fixtures test browser recovery. The separate current chain query establishes the live read result.
The first simulation harness used a nonexistent selector. The corrected harness used the actual `observe` control and passed.
No new payment, physical measurement, peaq write, deployment, registration, or submission occurred in this change.

## October 2 review before push

Review scope: all five unpublished commits from `origin/main` at `fa9eecf` through `4b0e02e`, plus the fixes below.
Independent passes covered identity/security, tests, API/demo contracts, and adversarial failure paths.
A separate read-only CLI review found no concrete new P1/P2 defect in its scope.
The review found and corrected these defects:

- The peaq diagnostic accepted an off-curve P-256 point. A new regression failed before curve validation and passed afterward.
- Setup commands changed directories before later commands assumed the repository root. Commands now preserve the starting directory.
- Live setup omitted trusted pin provisioning for another board. The guide now states that prerequisite explicitly.
- The guide labeled an older firmware hash as current and duplicated stale test counts. It now links the canonical results.

| Check | Observed result |
|---|---|
| `uv run --project host pytest -q`, after fixes | 54 passed, 10 hardware tests skipped in 1.17 seconds |
| `npm --prefix gateway test` | 26 passed, 0 failed in 646.49 milliseconds |
| Full `--hardware` suite, before three new software-only pin rejection cases | 61 passed in 126.04 seconds |
| Focused legacy policy hardware test | Passed in 34.03 seconds after the first full run missed the board |
| ESP-IDF dependency check and firmware build | Requirements satisfied. Build completed. No flash occurred. |
| Revised peaq diagnostic, isolated SDK 0.10.0 | Public Agung reads completed after public-point validation. No writes occurred. |
| Browser inspector regression | Original, attacks, expiry, payment fixtures, 429 recovery, and phone width passed |
| Revised setup guide | Relative links, HTML/Markdown anchors, desktop/mobile layout, and zero page errors passed |

The first full hardware run had 60 passes and one legacy policy discovery failure.
The focused rerun and next full run passed. The intermittent discovery miss remains a rehearsal reliability limit.
No blind retry or simulated substitution entered the physical path.

The standard ESP-IDF activation failed because this machine uses Espressif Installation Manager's tool layout.
The installer's generated activation script selected its tool, constraint, and Python paths.
The explicit dependency check and subsequent build passed. No dependency check was disabled.
The rebuilt binary was not flashed. The device firmware evidence below still identifies the earlier flashed artifact.
No new payment, peaq activation, deployment, registration, or submission occurred during this review.

## October 2 device, inspector, and peaq continuation

Starting source: `844fdc6`. No firmware or payment-path behavior changed in this continuation.

| Check | Observed result |
|---|---|
| `uv run --project host pytest -q --hardware` | 57 passed in 116.87 seconds before the four new packaging/readiness cases |
| `uv run --project host pytest -q`, expanded final software suite | 51 passed, 10 hardware tests skipped in 1.19 seconds |
| `npm test` in `gateway`, expanded final suite | 26 passed, 0 failed in 941.99 milliseconds |
| Held BOOT, `scripts/check_device_latency.py` | Real BLE input. P-256 signature verified. CLOSED, WAIT, 5/5 agreement, five-second evidence age. |
| Released BOOT, separate diagnostic | Real BLE input. P-256 signature verified. OPEN, DISPATCH, 5/5 agreement, four-second evidence age. |
| Recorded inspector, actual public Devnet RPC | VERIFIED TRANSFER. Slot 506374923, successful execution, expected mint, payer −1000 and merchant +1000 base units. |
| Final `querySettlement` module, live Devnet RPC | The actual transaction passed the final strict response and transfer checks. No funds moved. |
| `scripts/check_receipt_ui.cjs`, gateway | Original, expiry, altered state, another challenge, another key, restored original, and phone width passed. No page errors. |
| Same browser check, exported `/judge-demo-v2/index.html` under a URL prefix | All receipt, RPC fixture, retry, and phone-width checks passed. |
| Browser payment-check fixtures | Exact transfer passed. HTTP 429 produced NOT VERIFIED. Manual retry passed. Receipt remained expired WAIT throughout. |
| `tests/test_judge_export.py` | Public whitelist and URL paths passed. Existing directory and archive refusal passed. No private fixture entered the ZIP. |
| `tests/test_peaq_readiness.py` | RPC write/signing refusal and identity-input binding passed. No SDK dependency entered the MVP environment. |
| `scripts/check_peaq_readiness.py`, isolated SDK 0.10.0 | Agung chain 9990, finalized block 10996074, seven contracts contain code, six peer addresses match, economic authority true, both pause flags false. |
| Documented `uv run --no-project --with peaq-os-sdk==0.10.0` command | Installed the isolated SDK and completed the public read-only diagnostic successfully. |
| Committed contact-state re-verification | Both original signatures, challenges, historical decisions, and ten-second expiry passed. |
| How-it-works browser review | All 16 relative document links and section anchors passed. Desktop and 390 × 844 views were visually inspected. |
| Export manifest and ZIP | All seven asset hashes and every ZIP member match the exported files. No private state appears in the whitelist. |
| Final export video in Chromium | Metadata loaded: 149.76 seconds, 1280 × 900. |
| JavaScript syntax, Python compilation, staged diff and secret-pattern review | All passed. No formatter or static type checker is declared. |

The [device-signed contact evidence](evidence/device-signed-contact-states.json) preserves both current human-controlled readings.
These direct measurements moved no funds and issued no GPIO output operation.
The historical October 1 contact-state file retains its HMAC signatures.
The October 2 checks used the existing P-256 identity. They did not reprovision, flash, reset, or burn device security settings.
No GPIO20 output operation occurred. The unverified bare LED is not evidence of a controlled optical result.

The first hardware-suite attempt failed ten hardware cases because Bluetooth was soft-blocked and powered off.
Unblocking and powering the adapter restored access. The next full hardware run passed all 57 collected cases.
This recovery corrects local adapter state. It does not establish that Bluetooth cannot become blocked again.

The latency diagnostic measured 14.31 seconds for discovery plus the held reading, and 13.24 seconds for the released reading.
Evidence ages were five and four seconds at acceptance. These are different measurements from total operation duration.
SDK implicit scans accounted for only part of that duration. No transport optimization or independent time guarantee is claimed.

The exporter initially created a directory before it discovered an existing ZIP conflict.
A focused regression reproduced the failure. The exporter now checks both target paths before copying assets.
The package contains recorded evidence only. The full simulator separately exercises a complete purchase without funding.
The final reviewed ZIP has 7,909,635 bytes and SHA256 `cd56f54b379c82ac61f186931558a9633e03660f2c6b19eba60c6c925f055b73`.
Its video retains the current walkthrough hash listed below.

The guide initially overflowed a 390-pixel phone viewport to 741 pixels.
Wide tables and unbroken identifiers caused the overflow. Table scroll containers and identifier wrapping restored the 390-pixel page width.
The review retained visible content and table columns.

The peaq diagnostic reads public contract state and computes a proposed ID from the device public pin.
It does not query ownership, activate a machine, sign, approve a bond, submit an event, or use mainnet funds.
The [peaq readiness evidence](evidence/peaq-agung-readiness.json) and [integration decision](PEAQ_INTEGRATION.md) record exact values and remaining gates.
The SDK remains isolated from the firmware, host, and gateway dependency sets.

No new paid transfer, public deployment, external judge session, registration, or submission occurred in this continuation.

## October 2 research continuation and judge rehearsal

Current source before documentation changes: `1ef57de`.

| Check | Observed result |
|---|---|
| `uv run --project host pytest -q` | 47 passed, 10 hardware tests skipped |
| `npm test` in `gateway` | 22 passed, 0 failed |
| Fresh checkout: `uv sync --project host` | Installed successfully without local device state |
| Fresh checkout: `npm ci` in `gateway` | Installed successfully. Audit reported zero vulnerabilities at this check. |
| Fresh checkout: both simulated CLI observation commands | OPEN/DISPATCH and CLOSED/WAIT, stale-provider rejection, all reported attacks passed |
| Fresh-checkout browser simulation | Quote, simulated purchase, DISPATCH, expired WAIT, and video HTTP 206 byte range passed. No page errors. |
| `node scripts/check_receipt_ui.cjs <installed-playwright> <local-origin>` | Original signature, expiry, altered state, another challenge, wrong key, restored receipt, and phone width passed |
| `ffmpeg -v error -i docs/assets/fieldproof-signed-receipt.webm -f null -` | Full decode passed |
| `ffprobe` on current signed-receipt video | 149.76 seconds |

The current video SHA256 is `616055dba5d09aac805bd114f79d5808918975f9031a8ad990b0b31ec85da6e3`.
A paid-result video frame and current browser screenshots were visually inspected.
The rehearsal uses simulated payment and simulated hardware. It moves no funds.
That earlier rehearsal used no hardware, mainnet, new public payment, deployment, or external judge session.
The later physical and public read-only checks appear above.
The fresh checkout came from the committed source, not private local configuration.
Browser tooling uses an existing Playwright installation. It is not an MVP runtime dependency.

The [research decision](research/2026-10-02-fieldproof.md) supersedes the inherited novelty and winner-causality claims.
The [bounty execution plan](BOUNTY_PLAN.md) records owner actions and the research stop rule.

## Historical October 1 automated checks

| Command | Observed result |
|---|---|
| `uv run --project host pytest -q --hardware` after access returned | 40 passed in 116.52 seconds |
| `npm test` in `gateway`, final source | 20 passed, 0 failed, 0 skipped in 617.81 milliseconds |
| `uv run --project host pytest -q --hardware tests/hardware_replay_capacity.py`, earlier firmware check | 1 passed in 48.03 seconds. The board was reset afterward. |
| `uv run --project host pytest -q tests/test_http_interface.py tests/test_network_http.py`, earlier transport correction | 8 passed |
| `npm ci` in `gateway`, final lockfile | Installation passed. Audit reported 0 vulnerabilities at that check. |
| `idf.py build` with ESP-IDF 6.1 | Built the contact capability and serialized dispatcher |
| `idf.py -p /dev/ttyACM0 flash` | Flash completed. esptool verified the written hash. |
| `git diff --check` | Passed |
| `node --check scripts/record_demo.cjs` | Passed |
| `python3 -m py_compile scripts/build_walkthrough.py` | Passed |

No firmware or Python behavior changed after the restored-access full hardware run.
The repository declares no formatter or static type checker for these sources.
The default Python command explicitly skips hardware cases. `--hardware` requires an available board.

Python checks cover authentication, challenge binding, tampering, freshness, unstable measurements, budgets, demand, HTTP, and live BLE behavior.
Node checks cover payment policy, settlement ordering, concurrent retries, proof reuse, persistence, failure recovery, signing, and buyer freshness.
Payment unit tests use the real x402 resource-server SDK with a simulated facilitator.
A signing test cryptographically verifies a real Ed25519 buyer signature against a local RPC fixture.
The independent live purchase below establishes the chain integration separately.

## Public Devnet purchase

The user funded the disposable buyer through Circle's supported faucet interface.
Before purchase, Devnet RPC reported 20 USDC for the configured mint.
The constrained buyer then completed `node buyer.js ../.local/disposable-buyer.keypair.json` from `gateway`.
The private key remains ignored by Git. No mainnet funds were used.

- Purchase: `5776367cd42b408e`.
- Network: `solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1`.
- Transaction: `5T9cAims9tmCcgYV6KkuTedn9DhPjKmAVwENqoLjyA4GfboLfcwtTAu93Vk7kCNDyfR6QUVEpFq3XpdY7bDHoe8A`.
- Confirmed slot: `506294679`. Transaction error: `null`.
- Mint: `4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU`.
- Merchant: `CaQAKBcwf7G5vXeu2RNuNGJafnJ8724Uj4wv9ivfxfQA`.
- Buyer token balance change: `-1000` base units. Merchant token balance change: `+1000` base units.
- Amount: 0.001 Devnet USDC, with six decimals.
- Real receipt: `gpio9-contact`, OPEN, five matching samples, independently derived DISPATCH, evidence age six seconds at verification.

[Transaction and receipt evidence](evidence/devnet-purchase.json) contains the public test result and calculated balance changes.
Independent RPC `getTransaction` returned `transferChecked` with the same mint, amount, buyer, and merchant token account.
The chain block time was `1790862927`. The device reported measurement time `1790862937`.
Device time remains host-anchored. These timestamps are not independent physical-time attestation.

Reproduce the chain lookup against `https://api.devnet.solana.com` with this JSON-RPC body:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "getTransaction",
  "params": [
    "5T9cAims9tmCcgYV6KkuTedn9DhPjKmAVwENqoLjyA4GfboLfcwtTAu93Vk7kCNDyfR6QUVEpFq3XpdY7bDHoe8A",
    {"encoding": "jsonParsed", "commitment": "confirmed", "maxSupportedTransactionVersion": 0}
  ]
}
```

For each matching token account, subtract its pre-transaction integer amount from its post-transaction integer amount.
Check the mint and owner. Check `meta.err` before interpreting the result as a successful transfer.

## Physical and runtime checks

| Check | Observed result |
|---|---|
| User held BOOT, direct authenticated BLE observation | CLOSED, WAIT, five matching samples |
| User released BOOT, separate authenticated BLE observation | OPEN, DISPATCH, five matching samples |
| Browser, simulated settlement and real contact | OPEN, DISPATCH, `physical-contact-demo` |
| Browser evidence expiry | WAIT after the ten-second freshness window |
| Browser, simulated closed contact | CLOSED, WAIT |
| Public gateway unpaid purchase | HTTP 402 with pinned Devnet USDC, merchant, and amount |
| All three video byte-range requests | HTTP 206, `video/webm`, correct byte ranges |
| Both evidence JSON routes | HTTP 200 with the expected public test results |
| Earlier browser at 390 × 844 | No horizontal overflow. Controls and evidence remained visible. |
| Earlier real Wi-Fi observation | DISPATCH, five matching samples, rejected request replay |

[Physical state evidence](evidence/contact-states.json) preserves both authenticated receipts and challenges.
The human checks used direct BLE observations and moved no funds.
No reset or GPIO output drive occurred during the input checks.

The first extended recording failed after Bluetooth became soft-blocked and powered off.
A direct bridge call identified `BleakBluetoothNotAvailableError`, rather than substituting simulated evidence.
Unblocking Bluetooth restored the adapter. A direct real observation and the next recording passed.
The failed purchase remains `delivery_failed` in its simulation ledger. No automatic retry overwrote it.

The earlier Wi-Fi failure came from an overlapping VPN route to `192.168.4.1`.
Explicit Linux interface binding restored the manifest and observation without changing global VPN routes.
The original Wi-Fi connection was restored and temporary profiles were removed.

## Reproduced defects and corrections

| Defect | Reproduction | Correction and evidence |
|---|---|---|
| Signature bytes changed payment identity | A valid buyer signature remained unchanged while the facilitator signature changed. A second local purchase incorrectly returned 200. | Hash the signed message. The regression now returns 409 for the second purchase and the original cached receipt for a retry. |
| Gateway extended buyer freshness | A gateway response supplied 3,600 seconds and the buyer entered payment. | Request and require ten seconds locally. The regression rejects the changed contract before another fetch. |
| Concurrent SQLite startup failed | A separate process opened a ledger under an exclusive lock and immediately failed with `database is locked`. | Set the busy timeout before WAL initialization. The regression waits for release and passes. |
| Buyer lost the purchase ID after a network failure | The focused test returned `Connection lost` without review context. | Connection loss and truncated delivery retain the purchase ID. Both regressions pass. |
| Physical sensor inherited the simulated-payment label | The physical simulator described its sensor as simulated. | Sensor metadata now remains separate from payment mode. The metadata regression passes. |

The signature-variant regression uses a simulated facilitator and a cryptographically valid buyer signature.
It does not claim an exploit against the public facilitator. Its own SDK also identifies settlements by transaction message.
The local ledger now enforces its own durable identity across facilitator-signature variants.
No completed real purchase existed before this identity correction. Existing tagged simulation proofs retain their original hashes.

## Historical video artifacts

| Artifact | Content | Duration | Bytes | SHA256 |
|---|---|---|---|---|
| `assets/fieldproof-submission.webm` | Actual public quote, simulated purchase, real BLE contact, expiry, simulated closed state, executed CLI attacks | 149.880 s | 10,043,415 | `d5f9518aede3ae5cbe9949c7262d7e36fa44d794dad69e9569a00706a4388fb3` |
| `assets/fieldproof-walkthrough.webm` | Original simulator footage with explanatory cards | 150.000 s | 9,048,301 | `9e7353debf84bf18fed5c86c34acea0c56ac32c7cf796aaaab3165ffe962dfa3` |
| `assets/fieldproof-demo.webm` | Original simulator browser and CLI rehearsal | 69.760 s | 4,395,318 | `185cfda71111873ff5051603e1f8ecf72c6ab918882e76c2ebc186e519a889ba` |

All recordings contain no audio and remain local.
The extended recording completed every scene before saving. `ffmpeg -v error -i docs/assets/fieldproof-submission.webm -f null -` passed.
Public-quote and real-contact frames were extracted and visually inspected.
The composed presentation passed full decode and visual inspection. Its 1,744 source packets remain unchanged.

Both older longer videos predate the successful public payment and human input checks.
Their pending-payment captions describe the earlier state. Use the current signed-receipt video from the October 2 record above.
The recording script's new quote caption states that its scene executes no payment.

## Versions and limits

ESP-IDF 6.1.0, esptool 5.4.0, Node.js 24.10.0, CPython 3.13.13, Solana Kit 5.5.1, and x402 2.27.0.
The chip is ESP32-C6FH4 revision v0.2, with 4 MB embedded flash and USB Serial/JTAG.
The earlier application SHA256 was `c56ca246115d4cab742916bfff09aa90afa0bfbbcebe7570fe7359ff06e4211a`.
The current signed-receipt firmware reports `8012b267e1c10878a46700989bf9a49a1a1c988bcc4ce1b7ec2808f1491423fb` in the [identity record](evidence/receipt-identity-checks.json).
Node's built-in SQLite emits an experimental-feature warning.

Historical receipts use the public demo HMAC key. Current physical receipts use the provisioned P-256 identity with unencrypted device storage.
Host-anchored time, reboot-cleared replay state, and the single observer remain prototype limits.
No external gate sensor, protected identity, calibrated confidence, vehicle controller, customer pilot, peaq activation, or public deployment exists.
The [product review](STRATEGY.md#product-risks-and-decisions) identifies the decisions that require further evidence.

Git, sockets, USB, and BLE access are restored. No current access restriction blocks the completed local integration.
Historical source and evidence checkpoint: `dd1ebdc`. That earlier source and evidence were pushed in `ed8d539`.
That historical continuation's changes remained local at the time of this record.
The October 2 review above records the later requested source push.
Video upload, account registration, contact selection, and submission remain owner tasks.
