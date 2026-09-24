import pytest
import asyncio
import time
from capmesh.transport.ble import BLETransportAdapter
from capmesh.protocol.models import InvocationRequest
from capmesh.protocol.auth import generate_nonce, create_auth_payload, verify_receipt
from capmesh.provider.local_provider import LaptopProvider
from capmesh.agent.policy import AgentPolicyEngine
from capmesh.payment.verifier import MockPaymentVerifier, SolanaDevnetVerifier

DEVICE_ID = "esp32-c6-96a2"

@pytest.fixture(scope="module")
def ble_adapter():
    return BLETransportAdapter()

@pytest.fixture(scope="module")
def laptop_provider():
    return LaptopProvider()

@pytest.mark.asyncio
async def test_01_discovery_and_manifest(ble_adapter):
    manifests = await ble_adapter.discover(timeout=4.0)
    assert len(manifests) > 0, "No CapMesh providers found"
    
    target = next((m for m in manifests if m.device_id == DEVICE_ID), None)
    assert target is not None, f"Device {DEVICE_ID} not found in scan"
    assert target.protocol == "capmesh/0.1"
    
    cap_ids = [c.id for c in target.capabilities]
    assert "led.blink" in cap_ids
    print(f"\n[PASS] Discovered {target.device_id} with capabilities: {cap_ids}")

@pytest.mark.asyncio
async def test_02_valid_invocation(ble_adapter):
    nonce = generate_nonce()
    now = int(time.time())
    expiration = now + 300
    req_id = f"test-valid-{nonce & 0xffff}"

    auth_payload = create_auth_payload(
        request_id=req_id,
        capability="led.blink",
        nonce=nonce,
        expiration=expiration,
        auth_type="hmac-sha256"
    )

    req = InvocationRequest(
        request_id=req_id,
        device_id=DEVICE_ID,
        capability="led.blink",
        parameters={"duration": 1, "count": 2},
        nonce=nonce,
        timestamp=now,
        expiration=expiration,
        authorization=auth_payload
    )

    receipt = await ble_adapter.invoke(DEVICE_ID, req)
    assert receipt.status == "success", f"Expected success, got {receipt}"
    assert receipt.request_id == req_id
    assert receipt.provider == DEVICE_ID
    assert receipt.result.get("blinks_completed") == 2
    assert verify_receipt(receipt) is True, "Receipt HMAC signature was invalid"
    print(f"\n[PASS] Valid invocation succeeded, receipt signature verified: {receipt.receipt_signature}")

@pytest.mark.asyncio
async def test_03_replay_attack_rejected(ble_adapter):
    nonce = generate_nonce()
    now = int(time.time())
    expiration = now + 300
    req_id = f"test-replay-{nonce & 0xffff}"

    auth_payload = create_auth_payload(
        request_id=req_id,
        capability="led.blink",
        nonce=nonce,
        expiration=expiration,
        auth_type="hmac-sha256"
    )

    req = InvocationRequest(
        request_id=req_id,
        device_id=DEVICE_ID,
        capability="led.blink",
        parameters={"duration": 1, "count": 1},
        nonce=nonce,
        timestamp=now,
        expiration=expiration,
        authorization=auth_payload
    )

    # First attempt: succeeds
    r1 = await ble_adapter.invoke(DEVICE_ID, req)
    assert r1.status == "success"

    # Second attempt: exact same nonce and request -> MUST be rejected as replay
    r2 = await ble_adapter.invoke(DEVICE_ID, req)
    assert r2.status == "error", f"Expected replay rejection, got: {r2}"
    assert r2.error.get("code") == "REPLAY_DETECTED"
    print(f"\n[PASS] Replay attack correctly rejected with code: {r2.error.get('code')}")

@pytest.mark.asyncio
async def test_04_invalid_signature_rejected(ble_adapter):
    nonce = generate_nonce()
    now = int(time.time())
    expiration = now + 300
    req_id = f"test-tampered-{nonce & 0xffff}"

    auth_payload = {
        "type": "hmac-sha256",
        "token": "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"
    }

    req = InvocationRequest(
        request_id=req_id,
        device_id=DEVICE_ID,
        capability="led.blink",
        parameters={"duration": 1, "count": 1},
        nonce=nonce,
        timestamp=now,
        expiration=expiration,
        authorization=auth_payload
    )

    receipt = await ble_adapter.invoke(DEVICE_ID, req)
    assert receipt.status == "error"
    assert receipt.error.get("code") == "UNAUTHORIZED"
    print(f"\n[PASS] Tampered signature correctly rejected with code: {receipt.error.get('code')}")

@pytest.mark.asyncio
async def test_05_expired_request_rejected(ble_adapter):
    nonce = generate_nonce()
    now = int(time.time())
    expiration = 10  # Expired timestamp (10 seconds after epoch)
    req_id = f"test-expired-{nonce & 0xffff}"

    auth_payload = create_auth_payload(
        request_id=req_id,
        capability="led.blink",
        nonce=nonce,
        expiration=expiration,
        auth_type="hmac-sha256"
    )

    req = InvocationRequest(
        request_id=req_id,
        device_id=DEVICE_ID,
        capability="led.blink",
        parameters={"duration": 1, "count": 1},
        nonce=nonce,
        timestamp=now,
        expiration=expiration,
        authorization=auth_payload
    )

    receipt = await ble_adapter.invoke(DEVICE_ID, req)
    assert receipt.status == "error"
    assert receipt.error.get("code") == "AUTH_EXPIRED"
    print(f"\n[PASS] Expired request correctly rejected with code: {receipt.error.get('code')}")

@pytest.mark.asyncio
async def test_06_unknown_capability_rejected(ble_adapter):
    nonce = generate_nonce()
    now = int(time.time())
    expiration = now + 300
    req_id = f"test-unknown-{nonce & 0xffff}"

    auth_payload = create_auth_payload(
        request_id=req_id,
        capability="laser.fire",
        nonce=nonce,
        expiration=expiration,
        auth_type="hmac-sha256"
    )

    req = InvocationRequest(
        request_id=req_id,
        device_id=DEVICE_ID,
        capability="laser.fire",
        parameters={},
        nonce=nonce,
        timestamp=now,
        expiration=expiration,
        authorization=auth_payload
    )

    receipt = await ble_adapter.invoke(DEVICE_ID, req)
    assert receipt.status == "error"
    assert receipt.error.get("code") == "UNKNOWN_CAPABILITY"
    print(f"\n[PASS] Unknown capability correctly rejected with code: {receipt.error.get('code')}")

@pytest.mark.asyncio
async def test_07_laptop_provider_capabilities(laptop_provider):
    manifest = laptop_provider.get_manifest()
    assert manifest.device_id == "laptop-agent-01"
    cap_ids = [c.id for c in manifest.capabilities]
    assert "compute.sha256" in cap_ids
    assert "storage.echo" in cap_ids

    # Invoke compute.sha256
    req = InvocationRequest(
        request_id="req-laptop-comp",
        device_id="laptop-agent-01",
        capability="compute.sha256",
        parameters={"data": "capmesh-test-payload"},
        nonce=99901,
        timestamp=int(time.time()),
        expiration=int(time.time()) + 300,
        authorization={"type": "mock", "token": "test"}
    )
    receipt = await laptop_provider.invoke("laptop-agent-01", req)
    assert receipt.status == "success"
    assert "hash" in receipt.result
    assert verify_receipt(receipt) is True
    print(f"\n[PASS] Laptop provider compute.sha256 executed and verified: {receipt.result['hash']}")

@pytest.mark.asyncio
async def test_08_agent_policy_engine_routing(ble_adapter, laptop_provider):
    engine = AgentPolicyEngine(transports=[ble_adapter, laptop_provider], payment_verifier=MockPaymentVerifier())
    
    # 1. Goal: visual_signal under $0.01 -> should route to ESP32-C6 (led.blink at 0.001)
    res_vis = await engine.select_and_invoke("visual_signal", max_price=0.01)
    assert res_vis["status"] == "success"
    assert res_vis["chosen_provider"] == DEVICE_ID
    assert res_vis["capability"] == "led.blink"
    assert res_vis["receipt_verified"] is True
    print(f"\n[PASS] Policy Engine routed 'visual_signal' to cheapest provider: {res_vis['chosen_provider']}")

    # 2. Goal: compute under $0.01 -> should route to laptop-agent-01 (compute.sha256 at 0.002)
    res_comp = await engine.select_and_invoke("compute", max_price=0.01, parameters={"data": "hello policy"})
    assert res_comp["status"] == "success"
    assert res_comp["chosen_provider"] == "laptop-agent-01"
    assert res_comp["capability"] == "compute.sha256"
    assert res_comp["receipt_verified"] is True
    print(f"\n[PASS] Policy Engine routed 'compute' to cheapest provider: {res_comp['chosen_provider']}")

def test_09_solana_devnet_verifier():
    verifier = SolanaDevnetVerifier()
    # Real confirmed transaction on Devnet
    tx_sig = "48FSxG35ME3RRfMRHgBUNp3HrbxeqwnSpXQUZuMfJQV72nZQcgYJF2ZMPcKVS8Z6Uy49qbssLLGWiq8Ao4kgaoZV"
    assert verifier.verify_payment(tx_sig, 0.0001, "CaQAKBcwf7G5vXeu2RNuNGJafnJ8724Uj4wv9ivfxfQA") is True
    # Fake / invalid transaction
    assert verifier.verify_payment("invalid-nonexistent-signature-1111111111111111", 0.0001, "dest") is False
    print("\n[PASS] SolanaDevnetVerifier verified authentic Devnet transaction and rejected invalid signature")
