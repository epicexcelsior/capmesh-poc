# FieldProof verification record

Date: October 1, 2026, Europe/Berlin.
This record describes the current continuation's executed checks. It does not claim production security or standards compliance.

## Automated checks

| Command | Observed result |
|---|---|
| `uv run --project host pytest -q --hardware` | 40 passed in 114.19 seconds |
| `uv run --project host pytest -q tests/test_http_interface.py tests/test_network_http.py` | 8 passed after the interface correction |
| `uv run --project host pytest -q --hardware tests/hardware_replay_capacity.py` | 1 passed in 48.03 seconds |
| `npm test` in `gateway` | 14 passed, 0 failed, 0 skipped |
| `npm ci` in `gateway` | Clean final-lockfile installation passed. Audit reported 0 vulnerabilities. |
| `npm ls @solana/kit @x402/fetch` | Compatible dependency tree after pinning Solana Kit 5.5.1 |
| `git diff --check` | Passed before final commits |
| `idf.py build` with ESP-IDF 6.1 | Built the new contact capability and serialized dispatcher |
| `idf.py -p /dev/ttyACM0 flash` | Flash completed. esptool verified the written hash. |

The default Python run passed 29 tests with 10 explicit hardware skips before the new interface test was added.
The final full run includes that interface test and all hardware cases.
The capacity test runs separately because it fills the replay table. The board was reset after that check.

Python tests cover source authentication, result tampering, challenge binding, stale/future/unstable evidence,
provider selection, budgets, demand persistence, HTTP behavior, and live BLE authorization and observation.
Node tests cover request pricing, invalid payment, settlement ordering, reused proofs, concurrent retries,
expired cached evidence, failed/unknown settlement, failed delivery, persistent purchase state, buyer policy, and signing compatibility.

The node payment tests use the real x402 resource-server SDK with a simulated facilitator.
The signing test creates an actual Ed25519 buyer signature and verifies it cryptographically against a local RPC fixture.
It does not confirm a chain transaction or token balance.

## Runtime and visual checks

| Check | Observed result |
|---|---|
| Public gateway `POST /requests`, then unpaid `GET observe_url` | HTTP 402 with the configured Devnet USDC requirement |
| Public offer | Network `solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1`, mint `4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU`, amount `1000`, configured merchant |
| Browser, simulated payment and contact | Fresh OPEN evidence produced DISPATCH |
| Browser evidence expiry | Evidence older than ten seconds produced WAIT |
| Browser, simulated payment and real BLE contact | DISPATCH with `physical-contact-demo` |
| Recorded video through the local gateway | HTTP 206, WebM content type, correct byte range |
| Browser at 390 × 844 | No horizontal overflow. Controls and evidence remained visible. |
| Real Wi-Fi observation | DISPATCH, five matching samples, and `REPLAY_DETECTED` on resend |
| Wi-Fi recovery | Original connection restored. Temporary test profiles removed. |
| CLI closed-contact rehearsal | WAIT, stale provider rejected, all four attack checks rejected |
| Legacy feedback checker | BLE discovery and unpaid x402 challenge passed. Wi-Fi was unavailable during that particular unbound probe. |

The first unbound Wi-Fi check failed. `ip route get` selected the VPN tunnel.
A direct Wi-Fi-bound request returned the manifest. The new interface regression test failed before implementation and passed after it.
An intermediate HTTP change raised exceptions for valid protocol error receipts. Existing HTTP tests detected it, and the correction restored the receipt contract.

No new formatter or static type checker was introduced. The original repository declares neither for these sources.

## Artifact verification

The screen recording shows actual browser interactions and executed CLI output. It has no audio.
`ffprobe` reports 69.760 seconds and 4,395,318 bytes.
Frames from the fresh evidence and attack-result scenes were extracted and visually inspected.
The duplicate raw recording was removed after its hash matched the delivered file.

- Video: `docs/assets/fieldproof-demo.webm`
- Video SHA256: `185cfda71111873ff5051603e1f8ecf72c6ab918882e76c2ebc186e519a889ba`
- Flashed application SHA256: `c56ca246115d4cab742916bfff09aa90afa0bfbbcebe7570fe7359ff06e4211a`

The firmware binary is a local build artifact. It stays excluded from Git.
The recording uses simulated settlement and simulated contact. Its title and evidence mode identify both.

## Versions and sources

- ESP-IDF 6.1.0 and esptool 5.4.0.
- ESP32-C6FH4, revision v0.2, 4 MB embedded flash, USB Serial/JTAG.
- Node.js 24.10.0. Built-in SQLite emits an experimental-feature warning.
- x402 core, fetch, and SVM packages: 2.27.0.
- Solana Kit: 5.5.1.
- Python host environment: CPython 3.13.13. Project minimum: Python 3.10.

The first Solana Kit 6.10.0 installation conflicted with the SVM package's token-program peers.
The installed SVM package accepts Kit 5.1.0 or later, and its program dependencies require Kit 5.x.
Pinning 5.5.1 removed the peer mismatch. A signing test verifies this stack's actual behavior.
The official [Solana x402 guide](https://solana.com/docs/payments/agentic-payments/x402) defines the V2 headers and Devnet identifiers.

## Unfinished gates

- Successful public-facilitator settlement with a funded disposable Devnet USDC buyer.
- Human press/release verification of both GPIO9 contact states on this exact board.
- Full hackathon technical submission requirements and useful peaq-native integration.
- Production identity, protected keys, independently trusted time, calibrated confidence, and independent observers.
- Customer pilot and actual recurring demand.
- Public deployment, repository publication, and submission.

The last five production and business items are roadmap work. The first three remain current submission gates.
The goal remains active because the completion audit does not prove every requested gate.
