# Architecture Decisions & Research Record

## Architectural Decisions

### ADR 001: JSON Encoding for Protocol Phase 1-5
- **Status**: Accepted
- **Context**: Embedded protocol prototypes often face debugging friction if binary serialization (Protobuf, CBOR, FlatBuffers) is introduced too early.
- **Decision**: Use standard UTF-8 JSON payloads across BLE and HTTP. ESP-IDF provides `cJSON` natively in its standard library.
- **Consequences**: Easy inspection via serial monitor, CLI, and Wireshark. Payload sizes remain well within BLE MTU (using standard BLE MTU exchange or chunking if necessary).

### ADR 002: Espressif NimBLE Stack over Bluedroid
- **Status**: Accepted
- **Context**: Bluedroid has a large RAM footprint on ESP32 chips. Apache NimBLE is officially supported, lighter, and optimized for BLE-only applications on ESP32-C6.
- **Decision**: Use Apache NimBLE via `nimble_port` in ESP-IDF v6.1.
- **Consequences**: Significantly faster boot, lower RAM consumption, and reliable GATT server integration.

### ADR 003: Strict Decoupling of Capabilities from Transport
- **Status**: Accepted
- **Context**: CapMesh must support BLE, Wi-Fi HTTP, and future transports without rewriting actuator logic.
- **Decision**: Capabilities register with a central `capmesh_dispatcher`. Transports only decode inbound bytes into a request struct, pass it to the dispatcher, and transmit the receipt back.

### ADR 004: Two-Tier Authorization Strategy
- **Status**: Accepted
- **Context**: Solana uses Ed25519 signatures. However, verifying asymmetric signatures on resource-constrained microcontrollers can add setup overhead.
- **Decision**: Support symmetric HMAC-SHA256 authorization as the primary built-in verification on the ESP32 (using ESP32 hardware SHA engine or mbedtls), while keeping the authorization interface modular so Ed25519 / Solana devnet verifiers can be plugged in on host and device.

### ADR 005: Hardware Pad Readback for Physical Delivery Proof
- **Status**: Accepted
- **Context**: A software-only receipt signed by the provider proves only that the firmware claimed actuation, leaving the physical actuator oracle problem unsolved.
- **Decision**: Configure the actuator GPIO in `GPIO_MODE_INPUT_OUTPUT` mode. On every actuation cycle, synchronous electrical pad voltage levels are sampled via the hardware input buffer. The receipt schema includes structured `delivery_proof` containing `observer_id`, `expected_state`, `observed_state`, `verified_samples`, and `readback_verified`.
- **Consequences**: Provides verifiable electrical evidence of actuation distinct from software assertions. Extensible to external sensors (photodiodes, limit switches, current sensors).

### ADR 006: Settlement Neutrality and Payment Channels
- **Status**: Accepted
- **Context**: Hackathon prize tracks vary (TUM includes Cardano, BSV, and prospective sponsor tracks), and $0.001 micropayments cannot afford per-invocation L1 blockchain gas fees.
- **Decision**: Abstract payments behind a `PaymentVerifier` interface. Implement `SolanaPaymentChannelVerifier` (escrow ceiling with off-chain signed sequence vouchers) and `MultiChainPaymentVerifier` supporting dynamic chain routing.
- **Consequences**: Enables sub-cent micropayments, zero firmware dependencies on blockchain SDKs, and fast adaptation to judging track requirements.

---

## Future Research Questions

1. **Device Identity**: Should device identity use persistent cryptographic keypairs, hardware PUFs, or rotating privacy-preserving ephemeral identities?
2. **Physical Capability Verification**: How can a buyer verify that a physical capability (e.g. LED blink, motor movement, sensor reading) was actually delivered without trusted third-party oracles?
3. **Prepaid / Channel Balances**: Can one prepaid balance or payment-channel escrow authorize payments to previously unknown or intermittent providers?
4. **Offline Double-Spend Risk**: How should offline double-spend risk be bounded when machines interact in isolated mesh networks without internet connectivity?
5. **Reputation without Tracking**: How do devices establish reputation across interactions without creating globally trackable identifiers that compromise privacy?
6. **Capability Token Types**: When should capability tokens use wallet signatures, delegated session keys, verifiable credentials, or hardware-backed attestations?
7. **Metered Services**: How should metered services (such as continuous charging or bandwidth streaming) continuously authorize additional consumption with minimal latency?
8. **Multi-Hop Discovery**: How should discovery scale smoothly from BLE proximity to local area networks (mDNS/SSDP) to wide-area DHTs or internet brokers?
9. **Atomic Capability Composition**: How can multiple capabilities across different machines be composed conditionally or atomically (e.g. reserve lock, then pay, then unlock)?
10. **Agent Spending Policy**: What does a safe spending policy look like for an autonomous agent to prevent runaway loops or malicious drain?
11. **On-Chain vs Off-Chain Data**: What specific evidence belongs on-chain (commitments, dispute hashes, receipts) versus strictly peer-to-peer between buyer and provider?
12. **Receipts as Proofs**: Can receipts become verifiable credentials for machine accounting, tax reporting, or dispute resolution?
