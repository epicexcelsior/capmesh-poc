from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import requests
import logging

logger = logging.getLogger(__name__)

class PaymentVerifier(ABC):
    """Abstract payment verifier interface."""

    @abstractmethod
    def verify_payment(self, payment_ref: str, expected_amount: float, recipient: str) -> bool:
        """Verify that payment has been settled."""
        pass

class MockPaymentVerifier(PaymentVerifier):
    """Mock payment verifier for development and tests."""

    def verify_payment(self, payment_ref: str, expected_amount: float, recipient: str) -> bool:
        # Accepts any non-empty mock payment reference
        return bool(payment_ref and len(payment_ref) > 0)

class SolanaDevnetVerifier(PaymentVerifier):
    """Verifies real transactions on Solana Devnet via JSON-RPC."""

    def __init__(self, rpc_url: str = "https://api.devnet.solana.com"):
        self.rpc_url = rpc_url

    def verify_payment(self, payment_ref: str, expected_amount: float, recipient: str) -> bool:
        """
        Verify transaction signature on Solana Devnet.
        payment_ref: Solana transaction signature (base58 string)
        """
        if not payment_ref or len(payment_ref) < 32:
            return False

        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignatureStatuses",
                "params": [[payment_ref], {"searchTransactionHistory": True}]
            }
            resp = requests.post(self.rpc_url, json=payload, timeout=8.0)
            if resp.status_code != 200:
                return False

            result = resp.json().get("result", {})
            statuses = result.get("value", [])
            if not statuses or statuses[0] is None:
                return False

            status = statuses[0]
            # Transaction must have no error and confirmation level finalized/confirmed
            if status.get("err") is not None:
                return False

            confirmation = status.get("confirmationStatus")
            return confirmation in ("confirmed", "finalized")
        except Exception as e:
            logger.error(f"Solana devnet verification failed for {payment_ref}: {e}")
            return False
