"""Verify the new observation and replay contract on the real ESP32 HTTP server."""
import asyncio
import argparse
import json

from capmesh.observations import ObservationContract, ObservationVerifier, observation_request
from capmesh.protocol.auth import DEFAULT_SECRET
from capmesh.transport.http import HTTPTransportAdapter


async def run(interface=None):
    http = HTTPTransportAdapter(interface=interface)
    manifests = await http.discover(timeout=4)
    assert any(m.device_id == "esp32-c6-96a2" and any(c.id == "state.observe" for c in m.capabilities) for m in manifests)
    contract = ObservationContract()
    request = observation_request("esp32-c6-96a2", contract)
    receipt = await http.invoke(request.device_id, request)
    decision = ObservationVerifier({request.device_id: DEFAULT_SECRET}).verify(receipt, request, contract)
    replay = await http.invoke(request.device_id, request)
    assert replay.error["code"] == "REPLAY_DETECTED"
    print(json.dumps({"transport": "physical-wifi-http", "decision": decision, "replay": replay.error["code"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interface", help="Bind HTTP to this Linux Wi-Fi interface")
    asyncio.run(run(parser.parse_args().interface))
