# Verify the device that signs an observation

Audience: operators who provision a contact observer and buyers who verify its receipts.

The ESP32 signs `state.observe` receipts with a device-generated P-256 key.
The buyer uses a pinned public key. The command HMAC cannot create an accepted device receipt.
This change supersedes the HMAC-only observation descriptions in earlier setup and status documents.
The simulated contact and legacy LED retain their public demo HMAC.

## What the signature establishes

A valid signature binds the challenge, location, sensor, result, samples, and timestamps to the pinned signing key.
It does not establish correct installation, independent time, honest firmware, independent sensing, site permission, or future gate state.

The private key persists in ordinary non-volatile storage (NVS).
The PSA Crypto API permits signing and public-key export. Its key policy does not permit private-key export.
NVS encryption and secure boot are disabled. Physical flash access can disclose or replace the stored key.
Do not call this hardware attestation or tamper-resistant identity.
[Espressif describes the NVS physical-access limits](https://docs.espressif.com/projects/esp-idf/en/latest/esp32c6/api-reference/storage/nvs_flash.html#security-tampering-and-robustness).

## Provision a new board

Prerequisites: ESP-IDF 6.1, the matching toolchain, USB access, and a trusted physical connection to the intended board.
Keep BOOT released during flashing and reset.

1. Activate your ESP-IDF 6.1 environment.
2. Run `idf.py build` from `firmware/esp32`.
3. Run `idf.py -p /dev/ttyACM0 app-flash`.
4. Open `idf.py -p /dev/ttyACM0 monitor`.
5. With BOOT released, press Reset.
6. Read the `P256_PUBLIC_KEY=` line.
7. Exit the monitor with **Ctrl+]**.
8. Replace the intended provider's public pin in `host/capmesh/protocol/receipt_keys.json`.
9. Run `uv sync --project host` from the repository root.
10. Run `uv run --project host capmesh observe-demo --ledger :memory:`.
11. Check `receipt_identity` equals `pinned-device-p256` and `attacks_passed` equals `true`.
12. Reset the board with BOOT released.
13. Check the USB public key matches the pin.
14. Repeat the observation command.

The attached demonstration uses provider ID `esp32-c6-96a2`.
Another board requires an explicit provider-ID update in the bridge, paid buyer, and demo configuration.
An ID derived from the MAC address does not establish identity by itself.

The pin contains a 65-byte uncompressed SEC1 point as 130 lowercase hex characters, starting with `04`.
The checked-in pin belongs to the attached demonstration board. It is public material.
Python package data includes this file. The JavaScript buyer reads the same source file.
Restart the JavaScript buyer after a pin change.

Do not learn a replacement pin from a receipt or provider manifest.
Use the trusted USB connection and verify the operator's intended device assignment.
A replaced or erased board requires a deliberate pin change.

## Signature wire format

The observation canonical message stays unchanged. See the [protocol](PROTOCOL.md#measurement-and-receipt).
The device signs its UTF-8 bytes with ECDSA P-256 and SHA-256.
`receipt_signature` contains `v3:` followed by padded, standard base64.
The decoded signature contains exactly 64 bytes: 32-byte big-endian `r`, then 32-byte big-endian `s`.
Verifiers reject malformed or noncanonical encoding and signatures from another key.
They reject `v2:` when buyer configuration pins a P-256 identity.
[PSA specifies the ECDSA signature encoding](https://arm-software.github.io/psa-api/crypto/1.2/api/ops/sign.html#c.PSA_ALG_ECDSA).

The signing key uses persistent PSA key ID `0x4650` in the SDK's default NVS backend.
Initialization enables the ADC entropy source before radio startup, then disables it before BLE and Wi-Fi initialization.
Radio operation supplies entropy during signing.
[Espressif defines these entropy conditions](https://docs.espressif.com/projects/esp-idf/en/latest/esp32c6/api-reference/system/random.html).

## Separate command and receipt authority

Requests retain the public demonstration HMAC. It is not deployed access control.
Public verification material grants no command authority and no permission to read a real facility's operational state.
`ObservationMarket` accepts separate `command_secrets`. Receipt pins cannot become request secrets.
The paid buyer checks the pin before it creates a purchase or signs a payment.

## Storage failures and recovery

A storage error stops provider startup. Firmware never erases NVS to recover automatically.
A key lookup creates a key only when the SDK reports a missing persistent handle.
Other storage errors and unexpected key attributes stop startup without a panic memory dump.
The first hardware attempt exposed this API distinction: a missing key returns `PSA_ERROR_INVALID_HANDLE`.
The SDK maps its internal `PSA_ERROR_DOES_NOT_EXIST` to that public result.
[PSA documents key-management errors](https://arm-software.github.io/psa-api/crypto/1.2/api/keys/management.html#c.psa_get_key_attributes).

Inspect the storage error before recovery. Preserve the existing NVS partition.
Application flashing preserves the NVS partition. Full flash erasure destroys the identity.
After intentional replacement, repeat trusted provisioning and update the buyer pin.
Existing buyers fail verification until their pins change. There is no automatic key rotation.

## Check the change

```sh
uv run --project host pytest -q
uv run --project host pytest -q --hardware
cd gateway
npm test
```

The focused identity tests reproduce the public-HMAC forgery and reject it with a pinned device key.
They check altered fields, another key, malformed signatures, replay, and expired evidence.
The [device-signed paid purchase](evidence/device-signed-purchase.json) includes a successful public-facilitator transaction and exact RPC token changes.
The independent buyer accepted the fresh GPIO9 receipt at seven seconds of age.
The [persistence and attack record](evidence/receipt-identity-checks.json) confirms the same key after reset and a fresh observation after reset.
It records rejection of a forged public HMAC, altered state, another challenge, and repeated requests and responses.
On October 1, 2026, the hardware-enabled Python suite passed all 57 tests in 122.90 seconds.
The gateway suite passed all 22 tests with no failures or skips.
Browser checks verified the original signature, expiry, altered state, another challenge, another key, and mobile width.
Screenshots were inspected at 1280 and 390 pixels of width.
Earlier committed Devnet and human-contact evidence retains its original `v2:` signatures as historical evidence.

Run the receipt inspector without hardware:

```sh
cd gateway
npm run demo
```

Open `http://127.0.0.1:4022/proof`. The browser verifies the committed hardware receipt through Web Crypto.
The original signature remains valid. Its recorded timestamp is expired, so the current decision is WAIT.
The experiment buttons never charge funds or invoke hardware.
The browser trusts the installed repository's pin and page code. It does not authenticate an arbitrary remote site's configuration.

For the read-only browser regression check, provide an installed Playwright module:

```sh
node scripts/check_receipt_ui.cjs /path/to/playwright http://127.0.0.1:4022
```

Static assets use exact relative paths under the configured repository root.
The hidden-checkout regression verifies public receipt access and rejects private file paths.
