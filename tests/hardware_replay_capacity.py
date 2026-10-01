"""Opt-in destructive-to-session check. Run last, then reset the ESP32."""

import json
import time

import pytest
from bleak import BleakClient

from capmesh.observations import ObservationContract, observation_request
from capmesh.protocol.auth import create_auth_payload, verify_receipt
from capmesh.protocol.identity import provisioned_observation_keys
from capmesh.protocol.models import InvocationReceipt
from capmesh.transport.ble import BLETransportAdapter, INVOKE_UUID, RECEIPT_UUID


@pytest.mark.asyncio
@pytest.mark.hardware
async def test_replay_cache_never_evicts_unexpired_authorization():
    ble = BLETransportAdapter()
    manifests = await ble.discover(timeout=4)
    device = next(m for m in manifests if m.device_id == "esp32-c6-96a2")
    first_request = None
    full = False
    async with BleakClient(device.address, timeout=8) as client:
        async def invoke(request):
            await client.write_gatt_char(INVOKE_UUID, request.to_json().encode(), response=True)
            return InvocationReceipt.from_dict(json.loads((await client.read_gatt_char(RECEIPT_UUID)).decode()))

        for _ in range(65):
            request = observation_request(device.device_id, ObservationContract())
            request.expiration = request.timestamp + 300
            request.authorization = create_auth_payload(
                request.request_id, request.capability, request.nonce, request.expiration,
                device_id=request.device_id, parameters=request.parameters, timestamp=request.timestamp,
            )
            receipt = await invoke(request)
            if receipt.status == "error":
                assert receipt.error["code"] == "NONCE_CACHE_FULL"
                full = True
                break
            assert verify_receipt(receipt, public_key=provisioned_observation_keys()[device.device_id])
            first_request = first_request or request
        assert full, "The replay table evicted unexpired entries instead of refusing new requests"
        assert first_request is not None, "Reset the board before this capacity check"
        replay = await invoke(first_request)
        assert replay.error["code"] == "REPLAY_DETECTED"
