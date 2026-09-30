import requests
import logging
import re
import socket
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection
from typing import List, Optional
from .base import TransportAdapter
from ..protocol.models import Manifest, InvocationRequest, InvocationReceipt

logger = logging.getLogger(__name__)


class InterfaceHTTPAdapter(HTTPAdapter):
    def __init__(self, interface):
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,15}", interface):
            raise ValueError("Invalid network interface name")
        if not hasattr(socket, "SO_BINDTODEVICE"):
            raise ValueError("Explicit HTTP interface selection requires Linux")
        self.interface = interface
        super().__init__()

    def init_poolmanager(self, *args, **kwargs):
        kwargs["socket_options"] = list(HTTPConnection.default_socket_options) + [
            (socket.SOL_SOCKET, socket.SO_BINDTODEVICE, self.interface.encode("ascii") + b"\0")
        ]
        return super().init_poolmanager(*args, **kwargs)

class HTTPTransportAdapter(TransportAdapter):
    """HTTP / Wi-Fi transport adapter."""

    def __init__(self, default_base_url: str = "http://192.168.4.1", interface: Optional[str] = None):
        self.default_base_url = default_base_url
        self.session = requests.Session()
        if interface:
            # Local device traffic must follow the selected interface, including when a VPN overlaps its subnet.
            self.session.trust_env = False
            adapter = InterfaceHTTPAdapter(interface)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

    @property
    def transport_name(self) -> str:
        return "http"

    async def discover(self, timeout: float = 2.0) -> List[Manifest]:
        """Query standard local embedded endpoints for CapMesh manifest."""
        manifests = []
        try:
            url = f"{self.default_base_url}/manifest"
            resp = self.session.get(url, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                manifest = Manifest.from_dict(data, address=self.default_base_url, transport="http")
                manifests.append(manifest)
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning("HTTP provider discovery failed: %s", type(exc).__name__)
        return manifests

    async def invoke(self, target: str, request: InvocationRequest, timeout: float = 10.0) -> InvocationReceipt:
        """Send invocation request over HTTP POST /invoke."""
        base_url = target if target.startswith("http") else self.default_base_url
        url = f"{base_url.rstrip('/')}/invoke"
        payload = request.to_dict()

        resp = self.session.post(url, json=payload, timeout=timeout)
        data = resp.json()
        return InvocationReceipt.from_dict(data)

    async def get_receipt(self, target: str, request_id: Optional[str] = None, timeout: float = 5.0) -> InvocationReceipt:
        """Fetch receipt from HTTP GET /receipt."""
        base_url = target if target.startswith("http") else self.default_base_url
        url = f"{base_url.rstrip('/')}/receipt"
        resp = self.session.get(url, timeout=timeout)
        data = resp.json()
        return InvocationReceipt.from_dict(data)
