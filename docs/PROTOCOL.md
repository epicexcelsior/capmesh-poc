# CapMesh Protocol Specification (Version 0.1)

CapMesh defines a minimal, human-readable, JSON-based message format for machine capability exchange.

## 1. Protocol Manifest

A provider advertises its identity and capabilities via a manifest.

### Schema

```json
{
  "protocol": "capmesh/0.1",
  "device_id": "esp32-c6-96a2",
  "transport": "ble",
  "trust_tier": "verified",
  "attestation": "esp32-puf-attestation-0x96a2",
  "capabilities": [
    {
      "id": "led.blink",
      "description": "Blink onboard status LED",
      "parameters": {
        "duration": {
          "type": "integer",
          "default": 3,
          "min": 1,
          "max": 10,
          "unit": "seconds"
        },
        "count": {
          "type": "integer",
          "default": 5,
          "min": 1,
          "max": 50
        }
      },
      "pricing": {
        "model": "fixed",
        "amount": "0.001",
        "currency": "mock-usdc"
      }
    }
  ]
}
```

## 2. Capability Invocation Request

A client invokes a capability by sending an invocation payload.

### Schema

```json
{
  "protocol": "capmesh/0.1",
  "request_id": "req-98f2b1d0",
  "device_id": "esp32-c6-96a0",
  "capability": "led.blink",
  "parameters": {
    "duration": 5,
    "count": 5
  },
  "nonce": 104857,
  "timestamp": 1727185000,
  "expiration": 1727185300,
  "authorization": {
    "type": "hmac-sha256",
    "token": "4a7f01c8..."
  }
}
```

### Fields

- `protocol`: Protocol version string (`"capmesh/0.1"`).
- `request_id`: Client-generated unique identifier for tracking.
- `device_id`: Target device identifier.
- `capability`: Capability identifier matching the manifest.
- `parameters`: Key-value map of arguments.
- `nonce`: Monotonically increasing or random integer for replay protection.
- `timestamp`: Unix epoch seconds at creation.
- `expiration`: Unix epoch seconds after which the request is invalid.
- `authorization`: Authorization token or signature.

## 3. Invocation Receipt / Response

When execution finishes (or fails), the provider returns a receipt with physical delivery proof:

### Schema

```json
{
  "protocol": "capmesh/0.1",
  "request_id": "req-98f2b1d0",
  "status": "success",
  "provider": "esp32-c6-96a0",
  "capability": "led.blink",
  "parameters": {
    "duration": 5,
    "count": 5
  },
  "result": {
    "blinks_completed": 5
  },
  "delivery_proof": {
    "observer_id": "esp32_gpio8_hw_pad",
    "expected_state": "PULSED",
    "observed_state": "ACTIVE_HIGH",
    "verified_samples": 5,
    "total_samples": 5,
    "readback_verified": true
  },
  "started_at": 1727185002,
  "completed_at": 1727185007,
  "authorization_ref": "hmac-sha256:4a7f01c8...",
  "receipt_signature": "e89b21f..."
}
```


### Error Schema

If authorization fails or parameters are invalid, the provider returns an error receipt:

```json
{
  "protocol": "capmesh/0.1",
  "request_id": "req-98f2b1d0",
  "status": "error",
  "error": {
    "code": "AUTH_EXPIRED",
    "message": "Request expiration timestamp 1727185000 is in the past"
  }
}
```

## 4. Transport Mappings

### BLE Transport

- **Service UUID**: `0000cb00-0000-1000-8000-00805f9b34fb` (CapMesh Service)
- **Manifest Characteristic**: `0000cb01-0000-1000-8000-00805f9b34fb` (Read, Notify)
- **Invoke Characteristic**: `0000cb02-0000-1000-8000-00805f9b34fb` (Write with Response / Write without Response)
- **Receipt Characteristic**: `0000cb03-0000-1000-8000-00805f9b34fb` (Read, Notify)

### HTTP Transport

- `GET /manifest`: Returns Manifest JSON.
- `POST /invoke`: Accepts Invocation Request JSON; returns Receipt JSON.
- `GET /receipt/:request_id`: Returns Receipt JSON for a previous invocation.
