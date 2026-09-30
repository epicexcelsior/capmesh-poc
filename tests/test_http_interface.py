import sys

import pytest

from capmesh.protocol.models import InvocationRequest
from capmesh.provider.http_server import CapMeshHTTPServer
from capmesh.transport.http import HTTPTransportAdapter


@pytest.mark.asyncio
@pytest.mark.skipif(sys.platform != "linux", reason="SO_BINDTODEVICE is Linux-specific")
async def test_explicit_interface_carries_manifest_and_invocation():
    server = CapMeshHTTPServer(host="127.0.0.1", port=0)
    server.start()
    try:
        transport = HTTPTransportAdapter(f"http://127.0.0.1:{server.server.server_port}", interface="lo")
        manifests = await transport.discover()
        assert len(manifests) == 1
        request = InvocationRequest(request_id="bound", device_id=manifests[0].device_id, capability="storage.echo",
                                    parameters={"payload": "bound-to-interface"}, nonce=123, timestamp=0,
                                    expiration=0, authorization={"type": "mock"})
        receipt = await transport.invoke(manifests[0].device_id, request)
        assert receipt.result["echo"] == "bound-to-interface"
    finally:
        server.stop()
