> Historical CapMesh material. It is not the current implementation contract.
> Read [the current overview](OVERVIEW.md), [architecture](ARCHITECTURE.md), and [verification](VERIFICATION.md).
> Earlier payment-channel, provider-trust, and physical-truth claims are superseded.

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

| Security Property | Phase 0-2 (Initial) | Phase 3 (Auth Milestone) | Phase 5-7 (Production / Demo) |
|---|---|---|---|
| Replay Protection | None (Mock) | Nonce + Timestamp Window | Nonce Cache + Monotonic Epoch Window |
| Tamper Resistance | None (Plain JSON) | HMAC-SHA256 Signature | RFC 2104 HMAC-SHA256 Canonical Token |
| Physical Delivery Proof | Software assertion | Software assertion | Hardware Input Buffer Pad Readback |
| Payment Settlement | Free / Mock USDC | Free / Mock USDC | Solana Devnet L1 + Micropayment Channels |
| Provider Trust | Assumed Trust | Assumed Trust | Cryptographic Trust Tiers & Attestations |
| Hardware Identity | Static Device Name | Shared Secret / Device Key | Public Key Authority |

## 8. The Physical Actuator Oracle Problem & Hardware Readback

A software-signed receipt stating "the LED blinked" or "the lock opened" only proves the software claims it executed.
To solve this oracle vulnerability:
1. The microcontroller configures the actuator pin in `GPIO_MODE_INPUT_OUTPUT`.
2. While driving output signals, the hardware input buffer samples the physical voltage level on the electrical pad.
3. If an electrical short, disconnection, or hardware stall occurs, readback fails.
4. The signed receipt embeds structured delivery proof (`expected_state`, `observed_state`, `verified_samples`, `readback_verified`).

## 9. Off-Chain Micropayment Channels vs L1 Transactions

Paying $0.001 per invocation cannot sustain on-chain L1 gas fees (~$0.0007 + priority fees) or wait for block confirmation times:
1. The agent escrows a budget ceiling (e.g. €0.10) in an on-chain channel once.
2. The agent issues incrementing, signed sequence vouchers (e.g. €0.004) directly to the provider over BLE.
3. The provider verifies vouchers locally in sub-milliseconds without touching internet or RPC.
4. When the session terminates, the final voucher is redeemed on-chain in a single batch settlement.

## 10. Adversarial Demonstrations for Hackathons

Judges are inundated with happy-path demos. CapMesh stands out by demonstrating real-time defense against adversarial attacks:
1. **Replay Attack**: Capturing and resending an authorization token fails immediately with `REPLAY_DETECTED`.
2. **Expired Authorization**: Submitting an authorization with a past timestamp fails with `AUTH_EXPIRED`.
3. **Parameter Tampering**: Altering execution parameters without a valid private key fails with `UNAUTHORIZED`.
4. **Rogue Node**: An untrusted provider offering lower prices is rejected by the agent's trust policy before any money is spent.

