# FieldProof observation protocol

The MVP uses the existing `capmesh/0.1` JSON envelope. `state.observe` is the new capability.
The provisioned metric is `gate.closed`, and the provisioned location is `demo-gate`.
The sensor is GPIO9 in input mode. The onboard BOOT button represents a contact in this demo.

## Request

```json
{
  "protocol": "capmesh/0.1",
  "request_id": "obs-00000001",
  "device_id": "esp32-c6-96a2",
  "capability": "state.observe",
  "parameters": {"location": "demo-gate"},
  "nonce": 1,
  "timestamp": 1790807040,
  "expiration": 1790807070,
  "authorization": {"type": "hmac-sha256-v2", "token": "64-lowercase-hex-characters"}
}
```

Request IDs contain 1–16 ASCII letters, digits, hyphens, or underscores.
Nonces are integers from 1 to 2,147,483,647. Fractional JSON numbers fail validation.
The expiration follows the timestamp by at most 300 seconds.
The timestamp must fit the device's unsigned 32-bit epoch representation, with room for the validity window.
Only the single provisioned location parameter is accepted.

The host and firmware authenticate this exact UTF-8 message with HMAC-SHA256:

```text
fieldproof-auth-v1|request_id|device_id|state.observe|location|nonce|timestamp|expiration
```

Replace each field name with its value. Use decimal integers with no padding.
The result is a lowercase hex digest. The public demo key is shared through the host and firmware configuration.
It is disposable demonstration material, not a credential for a deployed service.

## Measurement and receipt

After authorization, the device reads five contact samples at approximately 10-millisecond intervals.
`closed=true` means GPIO9 reads low. `stable_samples` counts samples that match the first sample.
The buyer requires five matching samples. It returns WAIT for unstable evidence.

The response includes the challenge nonce, requested location, metric, sensor, state, sample counts, and epoch timestamps.
The authenticator covers this exact message:

```text
fieldproof-observation-v1|protocol|request_id|provider|capability|location|nonce|metric|sensor|closed|stable_samples|total_samples|started_at|completed_at
```

Encode `closed` as `0` or `1`. Prefix the lowercase digest with `v2:` in `receipt_signature`.
The receipt fits a 512-byte BLE characteristic. JSON field order does not affect the canonical message.
Simulated receipts use `simulated-contact` as the sensor. They are visibly labeled by the buyer.

## Buyer verification

The buyer checks these conditions before it dispatches:

1. The provider key exists in buyer configuration.
2. The protocol, request ID, provider, capability, nonce, and location match the challenge.
3. The receipt authenticator matches the observation fields.
4. The sensor and metric match the contact contract.
5. All five samples agree, and the state is a JSON boolean.
6. The measurement starts after the challenge, with at most two seconds of clock tolerance.
7. The completion timestamp follows the start and is not more than two seconds in the future.
8. The evidence age fits the contract and the request has not expired.
9. The verifier has not consumed this provider/nonce pair already.

Fresh open evidence produces DISPATCH. Closed, missing, stale, or invalid evidence produces WAIT.
Confidence stays `null`. Sample agreement does not imply calibrated confidence.
The in-process buyer replay set lasts for one verifier instance. Gateway purchase state persists in SQLite.

## Device replay and concurrency

BLE and HTTP share one dispatcher mutex and one replay table.
The device keeps 64 nonce/expiration pairs. It never evicts an unexpired authorization to admit another request.
A full table returns `NONCE_CACHE_FULL`. Concurrent dispatch returns `BUSY`.
Reboot clears the table and time anchor. The device has no independently trusted clock.
The first authenticated request anchors epoch time to monotonic uptime.

## Payment interface

- `POST /requests`: create an immutable challenge and purchase ID.
- `GET /observe/:id`: return a 402 quote, or verify and settle a matching x402 V2 payment.
- `GET /manifest`: describe the single contact observation.
- `GET /demand`: summarize local purchase states.
- `GET /health`: identify the configured payment and evidence mode.
- `POST /simulate/:id`: simulated server only. Exercise the same purchase handler with fake settlement.

The gateway pins Devnet, the USDC mint, merchant, exact scheme, and 1,000 base units.
It matches the payment resource to the stored purchase and checks the complete advertised requirements.
It hashes the decoded signed transaction message for a unique proof reservation before settlement.
The facilitator can replace its signature without changing that message. Signature variants cannot authorize another purchase.
Changing a resource wrapper cannot authorize another purchase with the same transaction message.
Solana transaction signatures do not independently sign HTTP resource metadata. Purchase binding is enforced by this gateway ledger.

SQLite stores the unique purchase nonce, unique proof hash, settlement result, receipt, and review state.
A retry returns the original receipt. It does not refresh its timestamp.
States are `quoted`, `settling`, `payment_failed`, `settlement_unknown`, `measuring`, `delivered`, and `delivery_failed`.
A crash during settlement or measurement leaves a reviewable state. No automatic retry repeats those effects.
The paid buyer requests `demo-gate` with a ten-second freshness limit. It rejects a changed contract before payment.
Connection and delivery failures retain the purchase ID in the buyer error for review.

## Existing LED compatibility

`led.blink` remains available for regression checks. Its request and receipt use the existing LED-specific v2 canonical messages.
GPIO8 readback reports the output pad. It does not prove light emission or independent delivery.
Legacy transaction-reference and unsigned payment-channel adapters reject payment claims.
They do not participate in the observation payment path.
