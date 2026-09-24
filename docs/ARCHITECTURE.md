# CapMesh Architecture

CapMesh separates business capabilities from physical transports and economic settlement adapters.

## Layer Model

```text
┌──────────────────────────────────────────┐
│ Agent / Application Layer                │
│ Policy, discovery, provider selection    │
├──────────────────────────────────────────┤
│ Capability Protocol Layer                │
│ Manifest, Quote, Invoke, Receipt (JSON)  │
├──────────────────────────────────────────┤
│ Trust & Payment Adapter                  │
│ MockAuth -> BoundedAuth -> Solana Devnet │
├──────────────────────────────────────────┤
│ Transport Layer                          │
│ BLE GATT / Wi-Fi HTTP / Local IPC        │
├──────────────────────────────────────────┤
│ Device Adapter Layer                     │
│ ESP32-C6 / Linux Laptop / Android Seeker │
├──────────────────────────────────────────┤
│ Capability / Actuator Layer              │
│ LED, relay, compute, sensor, camera      │
└──────────────────────────────────────────┘
```

## Layer Responsibilities

1. **Agent / Application Layer**: Formulates goals (e.g. "blink a light under 0.01 USD"). Discovers providers across available transports, evaluates manifests, picks candidates based on policy.
2. **Capability Protocol Layer**: Defines standard data schemas and semantics. Formats requests, manifests, receipts, and error structures. Does not depend on the physical network.
3. **Trust & Payment Adapter Layer**: Manages cryptographic proof of payment or authorized execution tokens. Verifies that the client has the right to invoke the capability.
4. **Transport Layer**: Carries raw bytes between machines. Transports include Bluetooth Low Energy (GATT characteristics), Wi-Fi (HTTP REST endpoints), or local UNIX sockets.
5. **Device Adapter Layer**: Bridges platform-specific APIs (ESP-IDF FreeRTOS tasks, Linux async loops) to the capability dispatcher.
6. **Capability Layer**: Executes physical or computational actions (GPIO toggling, SHA-256 calculation, sensor reading). Contains zero transport or networking code.

## Protocol Sequence

The following diagram illustrates the lifecycle of a single capability invocation:

```mermaid
sequenceDiagram
    participant A as Laptop Agent
    participant T as BLE Transport
    participant E as ESP32
    participant C as LED Capability

    A->>E: Discover
    E-->>A: Manifest
    A->>E: Invoke + Authorization
    E->>E: Verify authorization
    E->>C: Execute
    C-->>E: Result
    E-->>A: Receipt
```

## Transport Independence

The logical flow does not change when the transport changes:

```mermaid
flowchart TD
    Client[Client / Agent] -->|BLE GATT Characteristic| ESP_BLE[ESP32 BLE Transport]
    Client -->|HTTP POST /invoke| ESP_HTTP[ESP32 HTTP Transport]
    ESP_BLE --> Dispatcher[CapMesh Dispatcher]
    ESP_HTTP --> Dispatcher
    Dispatcher --> Auth[Auth & Replay Verifier]
    Auth -->|Authorized| Actuator[LED Actuator GPIO 8]
```
