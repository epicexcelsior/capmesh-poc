# CapMesh

CapMesh is a transport-independent capability marketplace protocol for machines.

Machines can discover nearby providers, inspect advertised capabilities, satisfy authorization or payment policies, invoke physical or digital actions, and receive verifiable receipts.

## Hardware in This Prototype

- **Provider**: ESP32-C6FH4 (QFN32, revision v0.2) running native ESP-IDF v6.1 firmware with NimBLE.
- **Actuator**: Onboard LED on GPIO 8.
- **Client / Buyer**: Linux laptop (Framework Laptop, Ubuntu) running Python host CLI with BLE central support (`bleak`).
- **First Transport**: Bluetooth Low Energy (GATT).
- **Second Transport**: Wi-Fi + HTTP (embedded web server).

## Repository Structure

```text
capmesh/
├── docs/
│   ├── ARCHITECTURE.md   # Architecture layers and sequence diagrams
│   ├── PROTOCOL.md       # CapMesh protocol specification (capmesh/0.1)
│   ├── DECISIONS.md      # Architecture decision records and research questions
│   └── LEARNING.md       # Educational conceptual guide for BLE and payments
├── firmware/
│   └── esp32/            # ESP-IDF C firmware for ESP32-C6
├── host/                 # Python host agent, CLI, and transport adapters
├── protocol/             # Transport-independent protocol models and validation
├── scripts/              # Setup, flashing, and testing utility scripts
├── tests/                # Automated unit and integration tests
├── TODO.md               # Implementation progress and milestone checklist
└── README.md
```

## Quick Start

### 1. Host Setup

```bash
uv venv
source .venv/bin/activate
uv pip install -e host/
```

### 2. Flash ESP32 Firmware

```bash
source /home/epic/.espressif/tools/activate_idf_v6.1.sh
cd firmware/esp32
idf.py set-target esp32c6
idf.py build
idf.py -p /dev/ttyACM0 flash monitor
```

### 3. Run the 60-Second Adversarial Judging Demo

```bash
# Execute the full autonomous agent decision, settlement, physical actuation, and live attack suite:
capmesh demo

# Or use the standalone bash runner:
./scripts/run_adversarial_demo.sh
```

### 4. Interactive Architecture & Technical Brief

Open [`docs/overview.html`](file:///home/epic/Documents/Projects/capmesh/docs/overview.html) in any browser for an interactive dashboard visualizing the 6-layer model, threat defense matrix, physical delivery proof, and sequence diagrams:

```bash
xdg-open docs/overview.html
```

### 5. Manual CLI Operations

```bash
# Scan for nearby providers (BLE + Local)
capmesh scan

# Retrieve capability manifest
capmesh manifest esp32-c6-96a2

# Manually invoke with hardware pad readback verification
capmesh invoke esp32-c6-96a2 led.blink --duration 2 --count 3

# Autonomous agent policy routing with budget limits
capmesh policy-run visual_signal --max-price 0.01
```

## Key Technical Highlights

1. **Transport-Independent Protocol**: Identical JSON requests (`capmesh/0.1`) execute over BLE GATT characteristics and Wi-Fi HTTP endpoints without duplicating capability code.
2. **Physical Delivery Proof (Actuator Oracle Solved)**: GPIO 8 configured in `GPIO_MODE_INPUT_OUTPUT` continuously samples the electrical pad level to verify voltage changes during physical actuation, returning `delivery_proof` in the signed receipt.
3. **On-Chip Adversarial Defense**: Firmware actively detects and blocks replay attacks (nonce cache), expired requests (monotonic epoch tracking), and forged tokens (RFC 2104 HMAC-SHA256).
4. **Settlement Neutrality**: Pluggable `PaymentVerifier` interface supporting Solana Devnet L1 transactions, off-chain micropayment channel vouchers, and extensible multi-chain adapters.
