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
            if status.get("err") is not None:
                return False

            confirmation = status.get("confirmationStatus")
            return confirmation in ("confirmed", "finalized")
        except Exception as e:
            logger.error(f"Solana devnet verification failed for {payment_ref}: {e}")
            return False

class SolanaPaymentChannelVerifier(PaymentVerifier):
    """
    Verifies off-chain micropayment channel vouchers.
    Escrows a maximum ceiling on-chain and validates cumulative sequence vouchers
    for sub-cent capability invocations without per-action L1 transaction fees.
    """

    def __init__(self, escrow_channel_id: str = "escrow-chan-01", max_ceiling: float = 1.0):
        self.escrow_channel_id = escrow_channel_id
        self.max_ceiling = max_ceiling
        self._current_spent = 0.0
        self._last_seq = 0

    def verify_payment(self, payment_ref: str, expected_amount: float, recipient: str) -> bool:
        """
        payment_ref format: "channel:<channel_id>:<seq>:<voucher_amount>"
        """
        if not payment_ref.startswith("channel:"):
            return False

        parts = payment_ref.split(":")
        if len(parts) < 4:
            return False

        _, chan_id, seq_str, amount_str = parts[:4]
        try:
            seq = int(seq_str)
            amount = float(amount_str)
        except ValueError:
            return False

        if seq <= self._last_seq:
            logger.warning(f"Payment channel replay: seq {seq} <= last {self._last_seq}")
            return False

        if amount < expected_amount or (self._current_spent + amount) > self.max_ceiling:
            logger.warning(f"Payment channel balance exceeded: spending {amount} exceeds ceiling {self.max_ceiling}")
            return False

        self._last_seq = seq
        self._current_spent += amount
        return True

class MultiChainPaymentVerifier(PaymentVerifier):
    """
    Multi-chain aggregator supporting pluggable settlement backends.
    Allows dynamic selection between Solana, Payment Channels, Cardano, BSV, and Mock.
    """

    def __init__(self):
        self.solana = SolanaDevnetVerifier()
        self.channel = SolanaPaymentChannelVerifier()
        self.mock = MockPaymentVerifier()

    def verify_payment(self, payment_ref: str, expected_amount: float, recipient: str) -> bool:
        if not payment_ref:
            return False

        if payment_ref.startswith("channel:"):
            return self.channel.verify_payment(payment_ref, expected_amount, recipient)
        elif payment_ref.startswith("mock:"):
            return self.mock.verify_payment(payment_ref, expected_amount, recipient)
        elif payment_ref.startswith("cardano:") or payment_ref.startswith("bsv:"):
            # Pluggable track adapter stub for TUM sponsors
            return True
        else:
            # Default to Solana Devnet signature verification
            return self.solana.verify_payment(payment_ref, expected_amount, recipient)
