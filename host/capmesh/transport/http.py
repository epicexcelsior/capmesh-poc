import requests
from typing import List, Optional
from .base import TransportAdapter
from ..protocol.models import Manifest, InvocationRequest, InvocationReceipt

class HTTPTransportAdapter(TransportAdapter):
    """HTTP / Wi-Fi transport adapter."""

    def __init__(self, default_base_url: str = "http://192.168.4.1"):
        self.default_base_url = default_base_url

    @property
    def transport_name(self) -> str:
        return "http"

    async def discover(self, timeout: float = 2.0) -> List[Manifest]:
        """Query standard local embedded endpoints for CapMesh manifest."""
        manifests = []
        try:
            url = f"{self.default_base_url}/manifest"
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                manifest = Manifest.from_dict(data, address=self.default_base_url, transport="http")
                manifests.append(manifest)
        except Exception:
            pass
        return manifests

    async def invoke(self, target: str, request: InvocationRequest, timeout: float = 10.0) -> InvocationReceipt:
        """Send invocation request over HTTP POST /invoke."""
        base_url = target if target.startswith("http") else self.default_base_url
        url = f"{base_url.rstrip('/')}/invoke"
        payload = request.to_dict()

        resp = requests.post(url, json=payload, timeout=timeout)
        data = resp.json()
        return InvocationReceipt.from_dict(data)

    async def get_receipt(self, target: str, request_id: Optional[str] = None, timeout: float = 5.0) -> InvocationReceipt:
        """Fetch receipt from HTTP GET /receipt."""
        base_url = target if target.startswith("http") else self.default_base_url
        url = f"{base_url.rstrip('/')}/receipt"
        resp = requests.get(url, timeout=timeout)
        data = resp.json()
        return InvocationReceipt.from_dict(data)
