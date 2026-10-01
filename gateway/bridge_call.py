"""Measure after gateway settlement. Input is one JSON object on stdin."""
import asyncio
from dataclasses import asdict
import json
import sys
from capmesh.observations import ObservationContract, ObservationVerifier, observation_request
from capmesh.protocol.auth import DEFAULT_SECRET
from capmesh.protocol.identity import provisioned_observation_keys
from capmesh.provider.observation_provider import SimulatedContactProvider
from capmesh.transport.ble import BLETransportAdapter

async def run(purchase):
    simulated = purchase.get('simulated') is True
    provider = 'sim-contact-01' if simulated else 'esp32-c6-96a2'
    contract = ObservationContract(location=purchase['location'], max_age_seconds=purchase['max_age_seconds'])
    transport = SimulatedContactProvider(closed=purchase.get('closed') is True) if simulated else BLETransportAdapter()
    manifests = await transport.discover(timeout=4)
    if not any(m.device_id == provider and any(c.id == 'state.observe' for c in m.capabilities) for m in manifests):
        raise RuntimeError('The provisioned contact provider is unavailable')
    request = observation_request(provider, contract, request_id=purchase['id'], nonce=purchase['nonce'])
    receipt = await transport.invoke(provider, request)
    keys = {provider: DEFAULT_SECRET} if simulated else provisioned_observation_keys()
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
