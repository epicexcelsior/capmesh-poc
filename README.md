# FieldProof

**Fresh physical evidence before an autonomous agent acts.**

FieldProof asks whether a demo gate is open, buys a contact observation, checks its challenge and freshness, and returns `DISPATCH` or `WAIT`.
The attached ESP32-C6 samples GPIO9. Its BOOT button represents the gate contact. This is a real input measurement with a labeled physical stand-in.
The product pivots from the original CapMesh LED marketplace. The `capmesh` Python package and BLE UUIDs remain compatible.

Watch the [2:30 signed-receipt walkthrough](docs/assets/fieldproof-signed-receipt.webm). It inspects a recorded public Devnet purchase and executes browser receipt checks. It has captions and no audio. Start with the [condensed decision and next actions](docs/FOCUS.md). The [bounty execution plan](docs/BOUNTY_PLAN.md) owns deadlines and acceptance gates.
For a plain-language explanation, start with [Understand the product](docs/HOW_IT_WORKS.html#understand).
For technical detail, use the [overview](docs/OVERVIEW.md), [setup guide](docs/HOW_IT_WORKS.html#run), and [interactive dispatch desk](docs/overview.html).

## Run without hardware

Prerequisites: Python 3.10+, `uv`, and Node.js 22.13+ with `node:sqlite`.

```bash
uv sync --project host
uv run --project host capmesh observe-demo --simulated
uv run --project host capmesh observe-demo --simulated --closed
cd gateway
npm ci
npm run demo
```

Open `http://127.0.0.1:4022`. Select **Get payment quote**, then **Run simulation**.
The simulator uses the real x402 resource-server SDK with a fake facilitator. It moves no funds.
Run `npm run demo -- --closed` to rehearse the closed-contact decision.

The CLI adversarial loop rejects a cheaper stale provider, a replayed answer, a changed answer, and a replayed device request.
It records served and unmet demand in a local SQLite ledger.

## Inspect the recorded physical purchase

With a local gateway running, open `http://127.0.0.1:4022/proof`.
The browser verifies the actual device signature and rejects a changed state, another challenge, and another key.
Select **Verify recorded payment** for an independent, read-only Solana Devnet transaction query.
The chain check verifies the mint, payer, merchant, transfer instruction, and exact token balance changes.
No inspector button purchases evidence or invokes hardware. The authentic recorded receipt is expired and stays WAIT.

Export a standalone inspector for judge review:

```bash
python3 scripts/export_judge_demo.py .local/judge-demo
python3 -m http.server 8787 --bind 127.0.0.1 --directory .local/judge-demo
```

Open `http://127.0.0.1:8787`. The exporter also creates `.local/judge-demo.zip` and a SHA256 manifest.
It copies only public evidence, browser code, the public verification pin, and the current technical video.
It refuses to overwrite an existing directory or archive. Select a new output name for another export.
This package inspects recorded evidence. Use the simulator commands above to exercise a complete purchase without funding.
Publication remains an owner action. Serve the exported directory on HTTPS for browser cryptography outside localhost.

## Run with the ESP32

Build and flash with ESP-IDF 6.1. The current board uses `/dev/ttyACM0`.
Set `IDF_PATH` to your installed ESP-IDF directory before these commands.

```bash
source "$IDF_PATH/export.sh"
cd firmware/esp32
idf.py build
idf.py -p /dev/ttyACM0 flash
cd ../..
uv run --project host capmesh observe-demo
```

Keep other BLE scans closed. Live mode fails when the board is unavailable. It never substitutes simulated hardware.
For HTTP, connect to the board's `CAPMESH_96A2` access point and use `capmesh observe-demo --http-url http://192.168.4.1`.
On Linux with overlapping VPN routes, add `--http-interface wlp2s0` and use your Wi-Fi interface name.
The new observation path and replay rejection are verified over physical Wi-Fi.

For the browser with real hardware and simulated payment:

```bash
cd gateway
npm run demo -- --physical
```

Hold BOOT while the observation runs to represent a closed contact. Release BOOT to represent an open contact.
Do not hold BOOT during reset or flashing. GPIO9 is a boot strap.
Human press/release verification passed: held BOOT produced CLOSED/WAIT, and released BOOT produced OPEN/DISPATCH. Both states returned five matching samples.

## Run the Devnet payment gateway

```bash
cd gateway
npm start
```

The gateway binds to `127.0.0.1:4021`. It offers x402 V2 `exact` payment for 1,000 base units of Devnet USDC.
An unpaid request returns `402` and `PAYMENT-REQUIRED`. Verification and successful settlement precede measurement.
A public-facilitator purchase completed on October 1, 2026. Independent Devnet RPC checks confirmed the exact USDC transfer before the physical measurement.
See the [paid device-signed receipt](docs/evidence/device-signed-purchase.json) and [device-signed physical state checks](docs/evidence/device-signed-contact-states.json).

Create a purchase with `POST /requests` and a positive 32-bit `nonce`.
Request its `observe_url` with a compatible x402 client.
The included client requires a disposable Solana CLI keypair with Devnet USDC:

```bash
node buyer.js /path/to/disposable.keypair.json
```

The client rejects other networks, assets, recipients, and amounts above 0.001 USDC.
It checks the device receipt independently and derives its decision from the contact state.
It never prints key material. Do not use a funded mainnet keypair.

Retries return the original evidence without a second settlement or measurement.
The browser stops dispatch after its freshness window. A cached receipt does not become fresh on retry.
Unknown settlement and paid delivery failure require manual review. See the [demo and recovery runbook](docs/DEMO.md).

## Verify

```bash
uv run --project host pytest -q
uv run --project host pytest -q --hardware
cd gateway
npm test
```

The default Python run skips hardware tests explicitly. `--hardware` requires the board and fails if it is unavailable.
There is no declared Python formatter or type checker in the original repository.
The [verification record](docs/VERIFICATION.md) lists executed checks and remaining gaps.

## Architecture and limits

- [Protocol](docs/PROTOCOL.md): authenticated requests, observation receipts, freshness, and replay limits.
- [Architecture](docs/ARCHITECTURE.md): device, buyer, gateway, ledgers, and payment boundaries.
- [Overview](docs/OVERVIEW.md): pivot, verified results, strategy, and unfinished acceptance gates.
- [peaq integration](docs/PEAQ_INTEGRATION.md): read-only Agung registry readiness, proposed observer identity, and activation gates.

Command authorization uses a public demo HMAC key. Physical observation receipts use a persistent P-256 key pinned by the buyer. Unencrypted flash storage does not protect that key against physical access.
Discovery cannot certify its own provider. Buyer configuration pins demo identities.
Five matching samples do not establish calibrated confidence or independent corroboration.
The board retains up to 64 unexpired request nonces. It refuses new requests when that table is full.
A reboot clears replay state and the clock anchor. The first authenticated request supplies the prototype time anchor.

No production device provisioning, external gate sensor, peaq transaction, multi-observer aggregation, customer pilot, or public deployment exists yet.
The local product and reports stay in this repository. No repository rename, publication, or submission occurs automatically.
