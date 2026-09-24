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

- [x] **Phase 7: Adversarial Defense & Physical Delivery Proof (TUM Hackathon Readiness)**
  - [x] Physical Delivery Proof: configured GPIO 8 in `GPIO_MODE_INPUT_OUTPUT`, synchronous pad readback samples voltage transition on every pulse cycle.
  - [x] Delivery proof schema added to receipt JSON (`observer_id`, `expected_state`, `observed_state`, `verified_samples`, `readback_verified`).
  - [x] Solved physical actuator oracle problem (verifiable electrical pad evidence distinct from software assertion).
  - [x] Settlement Neutrality: implemented `SolanaPaymentChannelVerifier` (off-chain micropayment vouchers) and `MultiChainPaymentVerifier` (Solana, Cardano, BSV).
  - [x] Adversarial Provider: created `UntrustedRogueProvider` under-cutting price (0.002 vs 0.004) with forged attestation.
  - [x] Agent Policy Engine: verified autonomous rejection of untrusted rogue provider and enforcement of €0.1000 spending ceiling.
  - [x] 60-Second Adversarial Demo: implemented `capmesh demo` and `scripts/run_adversarial_demo.sh` testing live replay, expired auth, and tampered signature defenses.
  - [x] Interactive Overview Dashboard: built standalone `docs/overview.html` with layer diagrams, threat matrix, delivery proof breakdown, beginner primer ("Explain Like I'm 5"), and curated further reading deep dives.
  - [x] Full multi-transport automated test suite passing (19/19 tests): 12 live hardware BLE integration tests in `tests/test_protocol.py` and 7 live socket HTTP tests in `tests/test_network_http.py`.
  - [x] Live physical adversarial execution verified: `scripts/run_adversarial_demo.sh` executed on-device with 100% PASS verdict.

---

## What Cannot Be Done Yet (Hardware & External Prerequisites)

The following items are architected and ready, but intentionally deferred because they require external hardware or live event infrastructure:

1. **Secondary Physical Sensors & High-Power Actuators (Servo / Solenoid Lock / Light Sensor)**:
   - *Current State*: Fully solved on-chip using GPIO 8 electrical pad loopback sampling (`GPIO_MODE_INPUT_OUTPUT`).
   - *Next Step*: Attach a €5 physical servo or photodiode sensor once external hardware is acquired before Munich.
2. **Solana Seeker / Android Mobile Wallet Adapter (MWA)**:
   - *Current State*: Linux laptop acts as the economic buyer and Bluetooth Central (`bleak`).
   - *Next Step*: Build Android React Native / Kotlin client when physical Seeker hardware is available.
3. **Arcium Private Policy Circuit Deployment**:
   - *Current State*: Architectural extension point defined in `docs/FEASIBILITY_AND_HOLES.md`; policy engine runs locally on host.
   - *Next Step*: Deploy confidential multi-party computation circuit once TUM official sponsor tracks and developer SDKs are published.
4. **Final Hackathon Track Settlement Selection**:
   - *Current State*: Pluggable `PaymentVerifier` interface implements Solana Devnet L1, Solana Payment Channels, and Multi-chain routing (Cardano, BSV).
   - *Next Step*: Bind the winning chain adapter once TUM publishes final prize track details.

