from abc import ABC, abstractmethod
from typing import List
from ..protocol.models import Manifest, InvocationRequest, InvocationReceipt

class TransportAdapter(ABC):
    """Abstract capability transport adapter."""

    @property
    @abstractmethod
    def transport_name(self) -> str:
        """Name of the transport (e.g. 'ble', 'http')."""
        pass

    @abstractmethod
    async def discover(self, timeout: float = 4.0) -> List[Manifest]:
        """Discover nearby providers and retrieve their manifests."""
        pass

    @abstractmethod
    async def invoke(self, target: str, request: InvocationRequest, timeout: float = 10.0) -> InvocationReceipt:
        """Send invocation request to target device and receive receipt."""
        pass
