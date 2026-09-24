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

- [ ] **Phase 1: BLE Transport & Basic Capability Invocation**
  - [ ] Configure ESP-IDF NimBLE peripheral service with Custom Service UUID.
  - [ ] Expose Manifest characteristic (Read / Notify).
  - [ ] Expose Request/Invocation characteristic (Write with response).
  - [ ] Expose Receipt/Response characteristic (Read / Notify).
  - [ ] Implement host Python CLI (`capmesh scan`, `capmesh manifest`, `capmesh invoke`).
  - [ ] Connect host BLE Central to ESP32 Peripheral, request manifest, send invoke for `led.blink`, verify physical LED blink.

- [ ] **Phase 2: Protocol Layer Separation**
  - [ ] Decouple capability dispatcher from BLE stack in C firmware.
  - [ ] Keep shared JSON protocol definitions in `protocol/`.
  - [ ] Ensure `led.blink` actuator knows nothing about BLE packets.

- [ ] **Phase 3: Authorization, Trust & Replay Protection**
  - [ ] Add `request_id`, `device_id`, `nonce`, `expiration` to invocations.
  - [ ] Implement cryptographic authorization verification (HMAC-SHA256 / Ed25519) on ESP32.
  - [ ] Implement replay prevention table (tracking seen nonces within validity window).
  - [ ] Generate signed receipt upon completion.
  - [ ] Unit & automated integration tests for:
    - [ ] Valid authorization -> executes
    - [ ] Invalid signature -> rejected
    - [ ] Expired request -> rejected
    - [ ] Replayed nonce -> rejected

- [ ] **Phase 4: Wi-Fi Transport**
  - [ ] Start embedded HTTP server on ESP32 (`esp_http_server`).
  - [ ] Expose `GET /manifest`, `POST /invoke`, `GET /receipt/<id>`.
  - [ ] Connect host agent via HTTP to demonstrate identical capability invocation over Wi-Fi.

- [ ] **Phase 5: Payment Adapter & Multi-Device Demo**
  - [ ] Create `PaymentVerifier` interface (`MockPaymentVerifier`, `SolanaDevnetVerifier`).
  - [ ] Host-mediated payment authorization on Solana Devnet.
  - [ ] Add second capability provider on laptop (`compute.sha256`, `storage.echo`).
  - [ ] Host agent policy routing: query multiple providers, select cheapest, invoke.

- [ ] **Phase 6: Verification & Final Report**
  - [ ] Run full automated test suite.
  - [ ] Request physical user verification of the LED.
  - [ ] Commit all milestones and push to GitHub.
