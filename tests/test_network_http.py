import pytest
import time
from capmesh.provider.http_server import CapMeshHTTPServer
from capmesh.transport.http import HTTPTransportAdapter
from capmesh.protocol.models import InvocationRequest
from capmesh.protocol.auth import generate_nonce, create_auth_payload, verify_receipt
from capmesh.agent.policy import AgentPolicyEngine
from capmesh.payment.verifier import MockPaymentVerifier, SolanaPaymentChannelVerifier
from capmesh.provider.untrusted_provider import UntrustedRogueProvider

@pytest.fixture(scope="module")
def http_server():
    server = CapMeshHTTPServer(host="127.0.0.1", port=0)
    server.start()
    yield server
    server.stop()

@pytest.fixture(scope="module")
def http_adapter(http_server):
    return HTTPTransportAdapter(default_base_url=http_server.base_url)

@pytest.mark.asyncio
async def test_01_http_discovery_manifest(http_adapter, http_server):
    manifests = await http_adapter.discover(timeout=2.0)
    assert len(manifests) == 1, "Expected 1 manifest from HTTP provider"
    m = manifests[0]
    assert m.protocol == "capmesh/0.1"
    assert m.device_id == "laptop-agent-01"
    assert m.transport == "http"
    cap_ids = [c.id for c in m.capabilities]
    assert "compute.sha256" in cap_ids
    assert "storage.echo" in cap_ids
    print(f"\n[PASS] HTTP Network Manifest retrieved from {http_server.base_url}: {cap_ids}")

@pytest.mark.asyncio
async def test_02_http_valid_invocation(http_adapter):
    nonce = generate_nonce()
    now = int(time.time())
    expiration = now + 300
    req_id = f"http-test-{nonce & 0xffff}"

    auth_payload = create_auth_payload(
        request_id=req_id,
        capability="compute.sha256",
        nonce=nonce,
        expiration=expiration,
        auth_type="hmac-sha256"
    )

    req = InvocationRequest(
        request_id=req_id,
        device_id="laptop-agent-01",
        capability="compute.sha256",
        parameters={"data": "network-test-payload-123"},
        nonce=nonce,
        timestamp=now,
        expiration=expiration,
        authorization=auth_payload
    )

    receipt = await http_adapter.invoke("laptop-agent-01", req)
    assert receipt.status == "success", f"Expected success, got {receipt}"
    assert receipt.request_id == req_id
    assert receipt.provider == "laptop-agent-01"
    assert "hash" in receipt.result
    assert receipt.delivery_proof is not None
    assert receipt.delivery_proof.readback_verified is True
    assert verify_receipt(receipt, require_delivery_proof=True) is True
    print(f"\n[PASS] HTTP Invocation successful over TCP socket: hash={receipt.result['hash']}")

@pytest.mark.asyncio
async def test_03_http_receipt_polling(http_adapter):
    receipt = await http_adapter.get_receipt("laptop-agent-01")
    assert receipt.status == "success"
    assert receipt.provider == "laptop-agent-01"
    assert receipt.receipt_signature is not None
    print(f"\n[PASS] HTTP GET /receipt retrieved authentic prior receipt")

@pytest.mark.asyncio
async def test_04_http_replay_attack_rejected(http_adapter):
    nonce = generate_nonce()
    now = int(time.time())
    expiration = now + 300
    req_id = f"http-replay-{nonce & 0xffff}"

    req = InvocationRequest(
        request_id=req_id,
        device_id="laptop-agent-01",
        capability="storage.echo",
        parameters={"payload": "replay-test"},
        nonce=nonce,
        timestamp=now,
        expiration=expiration,
        authorization=create_auth_payload(req_id, "storage.echo", nonce, expiration)
    )

    # 1. First execution succeeds
    r1 = await http_adapter.invoke("laptop-agent-01", req)
    assert r1.status == "success"

    # 2. Replayed request with same nonce must be rejected
    r2 = await http_adapter.invoke("laptop-agent-01", req)
    assert r2.status == "error"
    assert r2.error.get("code") == "REPLAY_DETECTED"
    print(f"\n[PASS] HTTP Replay attack rejected: {r2.error.get('code')}")

@pytest.mark.asyncio
async def test_05_http_expired_request_rejected(http_adapter):
    nonce = generate_nonce()
    now = int(time.time())
    req_id = f"http-exp-{nonce & 0xffff}"

    req = InvocationRequest(
        request_id=req_id,
        device_id="laptop-agent-01",
        capability="storage.echo",
        parameters={"payload": "expired-test"},
        nonce=nonce,
        timestamp=now - 200,
        expiration=now - 100,  # Expired
        authorization=create_auth_payload(req_id, "storage.echo", nonce, now - 100)
    )

    r = await http_adapter.invoke("laptop-agent-01", req)
    assert r.status == "error"
    assert r.error.get("code") == "AUTH_EXPIRED"
    print(f"\n[PASS] HTTP Expired request rejected: {r.error.get('code')}")

@pytest.mark.asyncio
async def test_06_http_unknown_capability_rejected(http_adapter):
    nonce = generate_nonce()
    now = int(time.time())
    req_id = f"http-unk-{nonce & 0xffff}"

    req = InvocationRequest(
        request_id=req_id,
        device_id="laptop-agent-01",
        capability="quantum.teleport",
        parameters={},
        nonce=nonce,
        timestamp=now,
        expiration=now + 300,
        authorization=create_auth_payload(req_id, "quantum.teleport", nonce, now + 300)
    )

    r = await http_adapter.invoke("laptop-agent-01", req)
    assert r.status == "error"
    assert r.error.get("code") == "UNKNOWN_CAPABILITY"
    print(f"\n[PASS] HTTP Unknown capability rejected: {r.error.get('code')}")

@pytest.mark.asyncio
async def test_07_agent_policy_engine_over_network(http_adapter):
    rogue = UntrustedRogueProvider()
    channel_verifier = SolanaPaymentChannelVerifier(escrow_channel_id="net-chan-01", max_ceiling=0.05)

    engine = AgentPolicyEngine(
        transports=[http_adapter, rogue],
        payment_verifier=channel_verifier,
        spending_ceiling=0.10
    )

    # Agent goal: "compute"
    res = await engine.select_and_invoke(
        capability_or_tag="compute",
        max_price=0.01,
        parameters={"data": "agent-network-policy-goal"}
    )

    assert res["status"] == "success"
    assert res["chosen_provider"] == "laptop-agent-01"
    assert res["transport"] == "http"
    assert res["capability"] == "compute.sha256"
    assert res["receipt_verified"] is True
    assert res["delivery_proof"].readback_verified is True
    print(f"\n[PASS] Agent Policy Engine solved goal over HTTP network transport: {res['chosen_provider']} via {res['transport']}")
