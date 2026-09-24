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

### 3. Scan and Invoke via BLE

```bash
capmesh scan
capmesh invoke <device-id> led.blink --duration 5
```
