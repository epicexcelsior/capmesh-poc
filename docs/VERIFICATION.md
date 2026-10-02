# FieldProof verification record

Date: October 1, 2026, Europe/Berlin.
The local MVP completes a public Devnet purchase, a real ESP32 observation, and both human-controlled contact states.
This record does not claim production security, safety certification, or standards compliance.

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
No hardware, mainnet, new public payment, deployment, or external judge session ran on October 2.
The fresh checkout came from the committed source, not private local configuration.
Browser tooling uses an existing Playwright installation. It is not an MVP runtime dependency.

The [research decision](research/2026-10-02-fieldproof.md) supersedes the inherited novelty and winner-causality claims.
The [bounty execution plan](BOUNTY_PLAN.md) records owner actions and the research stop rule.

## Automated checks

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

## Video artifacts

| Artifact | Content | Duration | Bytes | SHA256 |
|---|---|---|---|---|
| `assets/fieldproof-submission.webm` | Actual public quote, simulated purchase, real BLE contact, expiry, simulated closed state, executed CLI attacks | 149.880 s | 10,043,415 | `d5f9518aede3ae5cbe9949c7262d7e36fa44d794dad69e9569a00706a4388fb3` |
| `assets/fieldproof-walkthrough.webm` | Original simulator footage with explanatory cards | 150.000 s | 9,048,301 | `9e7353debf84bf18fed5c86c34acea0c56ac32c7cf796aaaab3165ffe962dfa3` |
| `assets/fieldproof-demo.webm` | Original simulator browser and CLI rehearsal | 69.760 s | 4,395,318 | `185cfda71111873ff5051603e1f8ecf72c6ab918882e76c2ebc186e519a889ba` |

All recordings contain no audio and remain local.
The extended recording completed every scene before saving. `ffmpeg -v error -i docs/assets/fieldproof-submission.webm -f null -` passed.
Public-quote and real-contact frames were extracted and visually inspected.
The composed presentation passed full decode and visual inspection. Its 1,744 source packets remain unchanged.

Both longer videos predate the successful public payment and human input checks.
Their pending-payment captions describe the earlier state. Refresh those captions and add the verified evidence before submission.
The recording script's new quote caption states that its scene executes no payment.

## Versions and limits

ESP-IDF 6.1.0, esptool 5.4.0, Node.js 24.10.0, CPython 3.13.13, Solana Kit 5.5.1, and x402 2.27.0.
The chip is ESP32-C6FH4 revision v0.2, with 4 MB embedded flash and USB Serial/JTAG.
Flashed application SHA256: `c56ca246115d4cab742916bfff09aa90afa0bfbbcebe7570fe7359ff06e4211a`.
Node's built-in SQLite emits an experimental-feature warning.

The public demo HMAC key, host-anchored time, reboot-cleared replay state, and single observer remain prototype limits.
No external gate sensor, protected identity, calibrated confidence, vehicle controller, customer pilot, peaq activation, or public deployment exists.
The [product review](STRATEGY.md#product-risks-and-decisions) identifies the decisions that require further evidence.

Git, sockets, USB, and BLE access are restored. No current access restriction blocks the completed local integration.
Local source and evidence checkpoint: `dd1ebdc`. Source and evidence were pushed and made public in `ed8d539`.
Video upload, account registration, contact selection, and submission remain owner tasks.
