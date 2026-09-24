# CapMesh Learning Guide

This document explains key concepts for engineers learning this architecture.

## 1. BLE Central and Peripheral

- **Peripheral**: The device that advertises its presence and hosts data. In this prototype, the ESP32 acts as the Peripheral.
- **Central**: The device that scans for advertisements, initiates connections, and reads or writes data. The laptop acts as the Central.

## 2. GATT Services and Characteristics

GATT means Generic Attribute Profile. It organizes data in a hierarchy:

- **Service**: A logical collection of characteristics identified by a 128-bit or 16-bit UUID. CapMesh defines service UUID `0000cb00-0000-1000-8000-00805f9b34fb`.
- **Characteristic**: A specific data endpoint inside a service.
  - **Manifest Characteristic (`cb01`)**: Read-only (or notify). Central reads this endpoint to discover capabilities and pricing.
  - **Invoke Characteristic (`cb02`)**: Write. Central writes the invocation JSON payload here.
  - **Receipt Characteristic (`cb03`)**: Read / Notify. Central reads the execution result and cryptographic receipt here.

## 3. Where Discovery Happens

Discovery happens at the radio layer during BLE advertising.
The ESP32 broadcasts advertising packets containing its device name and the CapMesh Service UUID.
The laptop Central listens for these packets without an active connection.
Once found, the laptop connects and reads the Manifest characteristic to know what capabilities exist.

## 4. Where Authorization Happens

Authorization verification happens inside the provider firmware before execution.
The client signs the invocation parameters, nonce, and expiration.
The ESP32 inspects the signature:
1. If the expiration timestamp is past, the device rejects the request.
2. If the nonce is already in the replay table, the device rejects the request.
3. If the cryptographic signature does not match, the device rejects the request.
Only valid requests reach the actuator.

## 5. Why the Transport is Separated

Business logic must not couple to physical radio details.
The LED actuator code accepts structured parameters (`duration_ms`, `blink_count`) and returns a result struct.
It does not know if the request arrived via BLE packets, HTTP over Wi-Fi, or a UNIX domain socket.
This design allows adding new transports without modifying hardware control logic.

## 6. Where Solana Enters

Solana enters at the economic layer between the buyer agent and a settlement verifier.
Resource-constrained microcontrollers do not run full blockchain RPC clients.
Instead:
1. The host agent pays or escrows funds on Solana Devnet.
2. The settlement verifier confirms the transaction and issues an authorization token.
3. The host transmits the authorization token to the ESP32 over BLE.
4. The ESP32 validates the token locally in microseconds without internet access.

## 7. Current Security Guarantees vs Mocks

| Security Property | Phase 0-2 (Initial) | Phase 3 (Auth Milestone) | Phase 5 (Solana Adapter) |
|---|---|---|---|
| Replay Protection | None (Mock) | Nonce + Timestamp Window | Nonce + Timestamp Window |
| Tamper Resistance | None (Plain JSON) | HMAC-SHA256 Signature | Ed25519 / Bounded Token |
| Payment Settlement | Free / Mock USDC | Free / Mock USDC | Solana Devnet Signature |
| Hardware Identity | Static Device Name | Shared Secret / Device Key | Public Key Authority |
