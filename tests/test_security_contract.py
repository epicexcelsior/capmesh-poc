from capmesh.protocol.auth import compute_hmac_sha256, receipt_message, verify_receipt
from capmesh.protocol.models import DeliveryProof, InvocationReceipt


def test_receipt_rejects_changed_result_and_proof():
    receipt = InvocationReceipt(
        protocol="capmesh/0.1",
        request_id="req-1",
        status="success",
        provider="esp32-c6-96a2",
        capability="led.blink",
        parameters={"duration": 1, "count": 2},
        result={"blinks_completed": 2},
        started_at=100,
        completed_at=101,
        delivery_proof=DeliveryProof("esp32_gpio8_hw_pad", "PULSED", "ACTIVE_HIGH", 2, 2, True),
    )
    receipt.receipt_signature = "v2:" + compute_hmac_sha256("capmesh-secret-key-2026", receipt_message(receipt))
    assert verify_receipt(receipt, require_delivery_proof=True)
    receipt.result["blinks_completed"] = 9
    assert not verify_receipt(receipt, require_delivery_proof=True)
    receipt.result["blinks_completed"] = 2
    receipt.delivery_proof.verified_samples = 9
    assert not verify_receipt(receipt, require_delivery_proof=True)
