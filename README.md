# FieldProof

**Fresh physical evidence before an autonomous agent acts.**

FieldProof asks whether a demo gate is open, buys a contact observation, checks its challenge and freshness, and returns `DISPATCH` or `WAIT`.
The attached ESP32-C6 samples GPIO9. Its BOOT button represents the gate contact. This is a real input measurement with a labeled physical stand-in.
The product pivots from the original CapMesh LED marketplace. The `capmesh` Python package and BLE UUIDs remain compatible.

Watch the [2:30 live walkthrough](docs/assets/fieldproof-submission.webm). It includes a real BLE observation with simulated payment. Start with the [overview](docs/OVERVIEW.md), the [complete how-it-works and setup guide](docs/HOW_IT_WORKS.html), the [interactive dispatch desk](docs/overview.html), and the [MVP plan](docs/MVP_PLAN.md).
The [submission draft](docs/SUBMISSION.md) records actual track deadlines and remaining required fields.

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
See the [transaction and receipt](docs/evidence/devnet-purchase.json) and [physical state checks](docs/evidence/contact-states.json).

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

The host and firmware use a public demo HMAC key. It does not establish identity against a hostile operator.
Discovery cannot certify its own provider. Buyer configuration pins demo identities.
Five matching samples do not establish calibrated confidence or independent corroboration.
The board retains up to 64 unexpired request nonces. It refuses new requests when that table is full.
A reboot clears replay state and the clock anchor. The first authenticated request supplies the prototype time anchor.

No production device provisioning, external gate sensor, peaq transaction, multi-observer aggregation, customer pilot, or public deployment exists yet.
The local product and reports stay in this repository. No repository rename, publication, or submission occurs automatically.
