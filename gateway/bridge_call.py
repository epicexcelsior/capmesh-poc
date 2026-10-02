"""Measure after gateway settlement. Input is one JSON object on stdin."""
import asyncio
from dataclasses import asdict
import json
import re
import sys
from capmesh.observations import ObservationContract, ObservationVerifier, observation_request
from capmesh.protocol.auth import DEFAULT_SECRET
from capmesh.protocol.identity import ReceiptPublicKey
from capmesh.provider.observation_provider import SimulatedContactProvider
from capmesh.transport.ble import BLETransportAdapter

async def run(purchase):
    simulated = purchase.get('simulated') is True
    contact = purchase['contact']
    provider = contact['provider']
    if not isinstance(provider, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,31}', provider):
        raise ValueError('Invalid contact provider')
    contract = ObservationContract(location=purchase['location'], max_age_seconds=purchase['max_age_seconds'], sensor=contact['sensor'])
    if simulated != (contract.sensor == 'simulated-contact'):
        raise ValueError('Contact contract must match physical or simulated observation mode')
    # The gateway snapshots this trusted public pin before quoting and stores it with the purchase.
    # A file change after settlement cannot replace the selected pin in this worker.
    keys = {provider: DEFAULT_SECRET if simulated else ReceiptPublicKey(purchase['receipt_public_key'])}
    transport = SimulatedContactProvider(provider, closed=purchase.get('closed') is True) if simulated else BLETransportAdapter()
    manifests = await transport.discover(timeout=4)
    if not any(m.device_id == provider and any(c.id == 'state.observe' for c in m.capabilities) for m in manifests):
        raise RuntimeError('The provisioned contact provider is unavailable')
    request = observation_request(provider, contract, request_id=purchase['id'], nonce=purchase['nonce'])
    receipt = await transport.invoke(provider, request)
    decision = ObservationVerifier(keys).verify(receipt, request, contract)
    return {'receipt': asdict(receipt), 'decision': decision,
            'challenge': {'request_id': request.request_id, 'nonce': request.nonce,
                          'timestamp': request.timestamp, 'expiration': request.expiration}}

if __name__ == '__main__':
    try:
        print(json.dumps(asyncio.run(run(json.load(sys.stdin)))))
    except Exception as exc:
        print(f'Observation failed: {type(exc).__name__}: {exc}', file=sys.stderr)
        raise SystemExit(1)
