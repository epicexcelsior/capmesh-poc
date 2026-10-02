import asyncio
import json
import logging
from typing import List, Optional, Dict
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice
from .base import TransportAdapter
from ..protocol.models import Manifest, InvocationRequest, InvocationReceipt

logger = logging.getLogger(__name__)

SERVICE_UUID   = "0000cb00-0000-1000-8000-00805f9b34fb"
MANIFEST_UUID  = "0000cb01-0000-1000-8000-00805f9b34fb"
INVOKE_UUID    = "0000cb02-0000-1000-8000-00805f9b34fb"
RECEIPT_UUID   = "0000cb03-0000-1000-8000-00805f9b34fb"

class BLETransportAdapter(TransportAdapter):
    """Bluetooth Low Energy transport adapter."""

    def __init__(self):
        self._address_cache: Dict[str, str] = {}
        self._device_cache: Dict[str, tuple[asyncio.AbstractEventLoop, BLEDevice]] = {}

    @property
    def transport_name(self) -> str:
        return "ble"

    async def discover(self, timeout: float = 4.0) -> List[Manifest]:
        """Scan for CapMesh BLE peripherals and retrieve manifests."""
        discovered: List[Manifest] = []
        scanner_results = await BleakScanner.discover(timeout=timeout, return_adv=True)

        for device, adv in scanner_results.values():
            name = device.name or adv.local_name or ""
            uuids = [u.lower() for u in adv.service_uuids]

            # Check for CapMesh service or naming convention
            is_capmesh = (
                any("cb00" in u for u in uuids) or
                name.startswith("capmesh") or
                name.startswith("esp32-c6")
            )
            if not is_capmesh:
                continue

            try:
                # Read manifest from peripheral
                async with BleakClient(device, timeout=6.0) as client:
                    raw_data = await client.read_gatt_char(MANIFEST_UUID)
                    manifest_json = json.loads(raw_data.decode("utf-8"))
                    manifest = Manifest.from_dict(
                        manifest_json,
                        address=device.address,
                        transport="ble"
                    )
                    self._address_cache[manifest.device_id] = device.address
                    self._address_cache[device.address.upper()] = device.address
                    self._device_cache[device.address.upper()] = (asyncio.get_running_loop(), device)
                    discovered.append(manifest)
            except Exception as e:
                logger.warning(f"Failed to read manifest from {device.address} ({name}): {e}")

        return discovered

    async def resolve_address(self, target: str) -> str:
        """Resolve device_id or address to BLE MAC address."""
        if target in self._address_cache:
            return self._address_cache[target]
        
        # Check if target is already a MAC address
        if target.count(":") == 5:
            return target
        
        # Quick scan to resolve
        manifests = await self.discover(timeout=3.0)
        for m in manifests:
            if m.device_id == target or m.address == target:
                return m.address
            
        raise ValueError(f"Could not resolve BLE target '{target}'. Run 'capmesh scan' first.")

    async def invoke(self, target: str, request: InvocationRequest, timeout: float = 12.0) -> InvocationReceipt:
        """Invoke a capability over BLE and wait for receipt."""
        address = await self.resolve_address(target)

        # CoreBluetooth handles belong to discovery's event loop. Other loops use
        # the address fallback, while the same loop avoids Bleak's implicit scan.
        cached = self._device_cache.get(address.upper())
        device = cached[1] if cached and cached[0] is asyncio.get_running_loop() else address
        async with BleakClient(device, timeout=8.0) as client:
            receipt_received = asyncio.Event()
            receipt_raw_bytes = bytearray()

            def on_receipt_notify(sender, data: bytearray):
                nonlocal receipt_raw_bytes
                receipt_raw_bytes = data
                receipt_received.set()

            try:
                await client.start_notify(RECEIPT_UUID, on_receipt_notify)
            except Exception:
                pass  # Fall back to polling read if notify setup fails

            # Send invocation JSON
            payload = request.to_json().encode("utf-8")
            await client.write_gatt_char(INVOKE_UUID, payload, response=True)

            # Wait for completion notification or fallback to reading receipt char
            try:
                await asyncio.wait_for(receipt_received.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                pass

            # Always perform a full read of RECEIPT_UUID to guarantee complete blob
            final_receipt_bytes = await client.read_gatt_char(RECEIPT_UUID)
            receipt_str = final_receipt_bytes.decode("utf-8")
            receipt_dict = json.loads(receipt_str)
            return InvocationReceipt.from_dict(receipt_dict)
