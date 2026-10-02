"""Measure one real BLE observation. No payments or GPIO output operations."""

import asyncio
from dataclasses import asdict
import json
import time

from bleak import BleakScanner
from capmesh.observations import ObservationContract, ObservationVerifier, observation_request
from capmesh.protocol.identity import provisioned_observation_keys
from capmesh.transport.ble import BLETransportAdapter


async def run():
    # Instrument the SDK's implicit scans in this process only.
    descriptor = BleakScanner.__dict__["find_device_by_address"]
    original = BleakScanner.find_device_by_address
    implicit_scans = []

    async def measured_find(*args, **kwargs):
        started = time.monotonic()
        try:
            return await original(*args, **kwargs)
        finally:
            implicit_scans.append(round(time.monotonic() - started, 3))

    BleakScanner.find_device_by_address = staticmethod(measured_find)
    try:
        transport = BLETransportAdapter()
        started = time.monotonic()
        manifests = await transport.discover(timeout=4)
        discovered = time.monotonic()
        provider = "esp32-c6-96a2"
        if not any(m.device_id == provider for m in manifests):
            raise RuntimeError("The provisioned ESP32 is unavailable")
        contract = ObservationContract()
        request = observation_request(provider, contract)
        receipt = await transport.invoke(provider, request)
        received = time.monotonic()
        decision = ObservationVerifier(provisioned_observation_keys()).verify(receipt, request, contract)
        return {
            "payment_mode": "No payment. One real BLE input measurement.",
            "timing_seconds": {
                "discovery_and_manifest": round(discovered - started, 3),
                "invocation_and_delivery": round(received - discovered, 3),
                "total": round(received - started, 3),
            },
            "sdk_implicit_scan_seconds": implicit_scans,
            "challenge": {"request_id": request.request_id, "nonce": request.nonce,
                          "timestamp": request.timestamp, "expiration": request.expiration},
            "decision": decision,
            "receipt": asdict(receipt),
        }
    finally:
        BleakScanner.find_device_by_address = descriptor


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run()), indent=2))
