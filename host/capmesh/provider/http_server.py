import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from .local_provider import LaptopProvider
from ..protocol.models import InvocationRequest

class CapMeshHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler implementing CapMesh REST endpoints."""

    provider: LaptopProvider = LaptopProvider()
    last_receipt: Optional[dict] = None

    def log_message(self, format, *args):
        # Silence default stderr logging during tests
        pass

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/manifest":
            manifest = self.provider.get_manifest()
            data = json.loads(manifest.to_json())
            data["transport"] = "http"
            data["address"] = f"http://{self.server.server_address[0]}:{self.server.server_address[1]}"
            self._send_json(data)
        elif self.path.startswith("/receipt"):
            last_rcpt = getattr(self.server, "last_receipt", None)
            if last_rcpt:
                self._send_json(last_rcpt)
            else:
                self._send_json({"protocol": "capmesh/0.1", "status": "idle"})
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == "/invoke":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self.send_error(400, "Empty payload")
                return

            body = self.rfile.read(content_length).decode("utf-8")
            try:
                req_dict = json.loads(body)
                req = InvocationRequest(
                    request_id=req_dict.get("request_id", ""),
                    device_id=req_dict.get("device_id", self.provider.device_id),
                    capability=req_dict.get("capability", ""),
                    parameters=req_dict.get("parameters", {}),
                    nonce=int(req_dict.get("nonce", 0)),
                    timestamp=int(req_dict.get("timestamp", 0)),
                    expiration=int(req_dict.get("expiration", 0)),
                    authorization=req_dict.get("authorization", {})
                )
            except Exception as e:
                self._send_json({"protocol": "capmesh/0.1", "status": "error", "error": {"code": "BAD_JSON", "message": str(e)}}, status=400)
                return

            # Execute via provider async method synchronously
            import asyncio
            receipt = asyncio.run(self.provider.invoke(self.provider.device_id, req))
            receipt_dict = {
                "protocol": receipt.protocol,
                "request_id": receipt.request_id,
                "status": receipt.status,
                "provider": receipt.provider,
                "capability": receipt.capability,
                "parameters": receipt.parameters,
                "result": receipt.result,
                "started_at": receipt.started_at,
                "completed_at": receipt.completed_at,
                "authorization_ref": receipt.authorization_ref,
                "receipt_signature": receipt.receipt_signature,
                "error": receipt.error
            }
            if receipt.delivery_proof:
                receipt_dict["delivery_proof"] = {
                    "observer_id": receipt.delivery_proof.observer_id,
                    "expected_state": receipt.delivery_proof.expected_state,
                    "observed_state": receipt.delivery_proof.observed_state,
                    "verified_samples": receipt.delivery_proof.verified_samples,
                    "total_samples": receipt.delivery_proof.total_samples,
                    "readback_verified": receipt.delivery_proof.readback_verified
                }

            self.server.last_receipt = receipt_dict
            self._send_json(receipt_dict, status=200 if receipt.status == "success" else 400)
        else:
            self.send_error(404, "Not Found")

class CapMeshHTTPServer:
    """Threaded CapMesh HTTP server for automated network testing and standalone execution."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8088):
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        self.server = HTTPServer((self.host, self.port), CapMeshHTTPHandler)
        self.port = self.server.server_port  # Updates if port 0 was passed
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"
