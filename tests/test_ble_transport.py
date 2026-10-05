"""Discovered BLE devices must not trigger another implicit address scan."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from bleak.backends.device import BLEDevice

import capmesh.transport.ble as ble
from capmesh.observations import ObservationContract, observation_request


@pytest.fixture
def radio(monkeypatch):
    device = BLEDevice("AA:BB:CC:DD:EE:FF", "esp32-c6-fixture", {})
    connections, scans, writes = [], [], []

    async def discover(**kwargs):
        scans.append(kwargs)
        device.details["discovery_loop"] = asyncio.get_running_loop()
        return {device.address: (device, SimpleNamespace(local_name=device.name, service_uuids=[ble.SERVICE_UUID]))}

    async def find_device_by_address(address, **kwargs):
        scans.append({"address": address, **kwargs})
        device.details["discovery_loop"] = asyncio.get_running_loop()
        return device

    class Client:
        def __init__(self, target, **kwargs):
            connections.append(target)
            self.target = target
            self.notify = None
            self.request = None

        async def __aenter__(self):
            if isinstance(self.target, BLEDevice) and self.target.details["discovery_loop"] is not asyncio.get_running_loop():
                raise RuntimeError("The discovered BLE handle belongs to another event loop")
            return self

        async def __aexit__(self, *args):
            pass

        async def start_notify(self, characteristic, callback):
            self.notify = callback

        async def write_gatt_char(self, characteristic, payload, *, response):
            assert characteristic == ble.INVOKE_UUID and response is True
            self.request = json.loads(payload)
            writes.append(self.request)
            self.notify(None, bytearray(b"ready"))

        async def read_gatt_char(self, characteristic):
            if characteristic == ble.MANIFEST_UUID:
                return json.dumps({"protocol": "capmesh/0.1", "device_id": "device-fixture",
                                   "capabilities": [{"id": "state.observe"}]}).encode()
            assert characteristic == ble.RECEIPT_UUID
            return json.dumps({"protocol": "capmesh/0.1", "request_id": self.request["request_id"],
                               "status": "success", "provider": "device-fixture"}).encode()

    monkeypatch.setattr(ble.BleakScanner, "discover", discover)
    monkeypatch.setattr(ble.BleakScanner, "find_device_by_address", find_device_by_address)
    monkeypatch.setattr(ble, "BleakClient", Client)
    return device, connections, scans, writes


@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["device-fixture", "aa:bb:cc:dd:ee:ff"])
async def test_discovered_device_serves_manifest_and_invocation_without_address_rescan(radio, target):
    device, connections, scans, writes = radio
    adapter = ble.BLETransportAdapter()
    manifests = await adapter.discover()
    assert manifests[0].address == device.address
    assert manifests[0].trust_tier == "unknown"
    request = observation_request("device-fixture", ObservationContract(), nonce=123, now=1790860000)
    receipt = await adapter.invoke(target, request)
    assert receipt.request_id == request.request_id
    assert writes == [request.to_dict()]
    assert len(scans) == 1
    # Passing a string here makes real Bleak connect perform an implicit scan.
    assert connections == [device, device]


@pytest.mark.asyncio
async def test_direct_address_remains_supported_without_prior_discovery(radio):
    _, connections, scans, _ = radio
    request = observation_request("device-fixture", ObservationContract(), nonce=123, now=1790860000)
    receipt = await ble.BLETransportAdapter().invoke("AA:BB:CC:DD:EE:FF", request)
    assert receipt.request_id == request.request_id
    assert connections == ["AA:BB:CC:DD:EE:FF"]
    assert scans == []


def test_separate_cli_event_loops_use_address_fallback(radio):
    device, connections, scans, _ = radio
    adapter = ble.BLETransportAdapter()
    asyncio.run(adapter.discover())
    request = observation_request("device-fixture", ObservationContract(), nonce=123, now=1790860000)
    receipt = asyncio.run(adapter.invoke("device-fixture", request))
    assert receipt.request_id == request.request_id
    assert connections == [device, device.address]
    assert len(scans) == 1


@pytest.mark.asyncio
async def test_configured_address_uses_one_connection_and_creates_challenge_after_connection(radio):
    device, connections, scans, writes = radio
    def build_request():
        assert connections == [device]
        return observation_request("device-fixture", ObservationContract(), request_id="0123456789abcdef", nonce=123)
    request, receipt = await ble.BLETransportAdapter().invoke_at_address(device.address, "device-fixture", build_request)
    assert request.request_id == receipt.request_id == "0123456789abcdef"
    assert request.nonce == 123
    assert connections == [device]
    assert scans == [{"address": device.address, "timeout": 4.0}]
    assert writes == [request.to_dict()]


@pytest.mark.asyncio
async def test_configured_address_rejects_another_provider_or_capability_before_write(radio):
    device, _, _, writes = radio
    build = lambda: observation_request("device-fixture", ObservationContract(), nonce=123)
    adapter = ble.BLETransportAdapter()
    with pytest.raises(ValueError, match="another provider"):
        await adapter.invoke_at_address(device.address, "another-provider", build)
    def wrong_capability():
        request = build()
        request.capability = "led.blink"
        return request
    with pytest.raises(ValueError, match="selected capability"):
        await adapter.invoke_at_address(device.address, "device-fixture", wrong_capability)
    assert writes == []


@pytest.mark.asyncio
async def test_configured_address_never_falls_back_to_another_board(radio, monkeypatch):
    _, connections, scans, writes = radio
    adapter = ble.BLETransportAdapter()
    with pytest.raises(ValueError, match="MAC address"):
        await adapter.invoke_at_address("not-a-mac", "device-fixture", lambda: None)
    assert scans == []
    async def missing(*args, **kwargs):
        return None
    monkeypatch.setattr(ble.BleakScanner, "find_device_by_address", missing)
    with pytest.raises(RuntimeError, match="unavailable"):
        await adapter.invoke_at_address("AA:BB:CC:DD:EE:FF", "device-fixture", lambda: None)
    assert connections == writes == []
