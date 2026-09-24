# CapMesh MVP — Project Progress & Task Tracker

## Target Milestones

- [x] **Phase 0: Establish Hardware Truth**
  - [x] Identify exact board and chip (ESP32-C6FH4 v0.2, 4MB Flash).
  - [x] Confirm serial port access (`/dev/ttyACM0`, dialout group ok).
  - [x] Identify ESP-IDF toolchain (`v6.1.0` in `/home/epic/.espressif/v6.1/esp-idf`).
  - [x] Verify host Bluetooth controller (`hci0`, Central & Peripheral supported).
  - [x] Locate onboard LED pin (GPIO 8).
  - [x] Build and flash minimal blink firmware to confirm physical LED works locally.
  - [x] Verified serial boot logs and 5-cycle blink sequence.

- [x] **Phase 1: BLE Transport & Basic Capability Invocation**
  - [x] Configure ESP-IDF NimBLE peripheral service with Custom Service UUID `0xCB00`.
  - [x] Expose Manifest characteristic (`0xCB01`, Read / Notify).
  - [x] Expose Request/Invocation characteristic (`0xCB02`, Write with response).
  - [x] Expose Receipt/Response characteristic (`0xCB03`, Read / Notify).
  - [x] Implement host Python CLI (`capmesh scan`, `capmesh manifest`, `capmesh invoke`).
  - [x] Connect host BLE Central to ESP32 Peripheral, request manifest, send invoke for `led.blink`, verify physical LED blink.

- [x] **Phase 2: Protocol Layer Separation**
  - [x] Decouple capability dispatcher from BLE stack in C firmware (`protocol/capmesh_dispatcher.c`).
  - [x] Keep shared JSON protocol definitions in `protocol/` and `host/capmesh/protocol/`.
  - [x] Ensure `led.blink` actuator knows nothing about BLE packets (`capabilities/led_capability.c`).

- [x] **Phase 3: Authorization, Trust & Replay Protection**
  - [x] Add `request_id`, `device_id`, `nonce`, `expiration` to invocations.
  - [x] Implement cryptographic authorization verification (RFC 2104 HMAC-SHA256) on ESP32.
  - [x] Implement replay prevention table (tracking seen nonces within validity window).
  - [x] Generate signed receipt upon completion with HMAC authenticator.
  - [x] Automated integration tests passing:
    - [x] Valid authorization -> executes (`test_02_valid_invocation`)
    - [x] Invalid signature -> rejected (`test_04_invalid_signature_rejected`)
    - [x] Expired request -> rejected (`test_05_expired_request_rejected`)
    - [x] Replayed nonce -> rejected (`test_03_replay_attack_rejected`)
    - [x] Unknown capability -> rejected (`test_06_unknown_capability_rejected`)

- [x] **Phase 4: Wi-Fi Transport**
  - [x] Start Wi-Fi SoftAP on ESP32 (`CAPMESH_96A2`, channel 6, 192.168.4.1).
  - [x] Start embedded HTTP server on ESP32 (`esp_http_server`).
  - [x] Expose `GET /manifest`, `POST /invoke`, `GET /receipt`.
  - [x] Dual-transport operation verified: BLE + Wi-Fi HTTP coexisting simultaneously without logic duplication.

- [x] **Phase 5: Payment Adapter & Multi-Device Demo**
  - [x] Create `PaymentVerifier` interface (`MockPaymentVerifier`, `SolanaDevnetVerifier`).
  - [x] Verified against real confirmed transaction on Solana Devnet (`48FSxG35...`).
  - [x] Add second capability provider on laptop (`laptop-agent-01`: `compute.sha256`, `storage.echo`).
  - [x] Multi-device discovery in `capmesh scan` (ESP32-C6 + Laptop).
  - [x] Host agent autonomous policy routing (`capmesh policy-run`): query multiple providers, select cheapest, invoke, verify receipt.

- [x] **Phase 6: Verification & Complete Test Suite**
  - [x] Full automated test suite passes (9/9 tests passed in `tests/test_protocol.py`).
  - [x] All code committed and pushed to private GitHub repository (`epicexcelsior/capmesh-poc`).
