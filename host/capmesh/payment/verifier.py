from abc import ABC, abstractmethod
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
    """Legacy adapter disabled: confirmation alone is not proof of payment."""

    def __init__(self, rpc_url: str = "https://api.devnet.solana.com"):
        self.rpc_url = rpc_url

    def verify_payment(self, payment_ref: str, expected_amount: float, recipient: str) -> bool:
        logger.warning("A transaction signature alone cannot prove recipient, asset, amount, or purchase binding; use the x402 gateway")
        return False

class SolanaPaymentChannelVerifier(PaymentVerifier):
    """Legacy placeholder disabled until escrow and signatures are implemented."""

    def __init__(self, escrow_channel_id: str = "escrow-chan-01", max_ceiling: float = 1.0):
        self.escrow_channel_id = escrow_channel_id
        self.max_ceiling = max_ceiling
        self._current_spent = 0.0
        self._last_seq = 0

    def verify_payment(self, payment_ref: str, expected_amount: float, recipient: str) -> bool:
        logger.warning("Unsigned channel strings do not prove payment; use the x402 gateway")
        return False

class MultiChainPaymentVerifier(PaymentVerifier):
    """
    Compatibility router. Only the explicit mock path can return true.
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
            return False
        else:
            # Default to Solana Devnet signature verification
            return self.solana.verify_payment(payment_ref, expected_amount, recipient)
