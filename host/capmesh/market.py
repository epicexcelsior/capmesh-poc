"""Local demand ledger and deterministic evidence routing for the MVP."""

from dataclasses import asdict
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sqlite3
import time
import uuid

from .observations import EvidenceError, ObservationContract, ObservationVerifier, observation_request
from .protocol.auth import DEFAULT_SECRET
from .protocol.identity import ReceiptPublicKey


class DemandLedger:
    def __init__(self, path=".local/demand.sqlite"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=5)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS demand (
            id TEXT PRIMARY KEY, created_at INTEGER NOT NULL, location TEXT NOT NULL,
            metric TEXT NOT NULL, max_age INTEGER NOT NULL, budget TEXT NOT NULL,
            status TEXT NOT NULL, provider TEXT, reason TEXT NOT NULL)""")
        self.db.commit()

    def record(self, contract, status, *, provider=None, reason=""):
        demand_id = uuid.uuid4().hex
        with self.db:
            self.db.execute("INSERT INTO demand VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (demand_id, int(time.time()), contract.location, contract.metric,
                             contract.max_age_seconds, contract.max_price_usdc, status, provider, reason))
        return demand_id

    def summary(self):
        rows = self.db.execute("""SELECT location, metric, status, COUNT(*) FROM demand
                                  GROUP BY location, metric, status ORDER BY location, status""").fetchall()
        return [{"location": r[0], "metric": r[1], "status": r[2], "requests": r[3]} for r in rows]

    def close(self):
        self.db.close()


class ObservationMarket:
    """Mock-priced rehearsal buyer. Real payments go through the x402 gateway."""

    def __init__(self, transports, provider_keys, ledger, *, command_secrets=None):
        self.transports = transports
        self.verifier = ObservationVerifier(provider_keys)
        self.ledger = ledger
        # Command authorization and receipt verification have different authorities.
        self.command_secrets = {provider: DEFAULT_SECRET if isinstance(key, ReceiptPublicKey) else key
                                for provider, key in provider_keys.items()}
        self.command_secrets.update(command_secrets or {})

    async def observe(self, contract: ObservationContract):
        if contract.location != "demo-gate":
            demand_id = self.ledger.record(contract, "unmet", reason="LOCATION_NOT_PROVISIONED")
            return {"status": "unmet", "decision": {"decision": "WAIT", "reason": "No observer at this location"},
                    "rejected_providers": [], "mock_spent": "0", "payment_mode": "mock; no funds moved", "demand_id": demand_id}
        candidates, rejected = [], []
        for transport in self.transports:
            try:
                manifests = await transport.discover(timeout=4)
            except Exception as exc:
                rejected.append({"provider": transport.transport_name, "reason": f"DISCOVERY_FAILED: {type(exc).__name__}"})
                continue
            for manifest in manifests:
                for capability in manifest.capabilities:
                    if capability.id != "state.observe":
                        continue
                    if manifest.device_id not in self.verifier.provider_keys:
                        rejected.append({"provider": manifest.device_id, "reason": "UNKNOWN_PROVIDER: no buyer-provisioned key"})
                        continue
                    try:
                        price = Decimal(capability.pricing.amount)
                        if not price.is_finite() or price < 0:
                            raise ValueError("Invalid price")
                    except (InvalidOperation, ValueError):
                        rejected.append({"provider": manifest.device_id, "reason": "INVALID_PRICE"})
                        continue
                    if capability.pricing.currency != "mock-usdc":
                        rejected.append({"provider": manifest.device_id, "reason": "USE_X402_GATEWAY: this buyer supports mock pricing"})
                        continue
                    candidates.append((price, manifest.device_id, transport))
        candidates.sort(key=lambda c: (c[0], c[1], c[2].transport_name))
        spent = Decimal("0")
        for price, provider, transport in candidates:
            if spent + price > Decimal(contract.max_price_usdc):
                rejected.append({"provider": provider, "reason": "BUDGET_EXCEEDED"})
                continue
            request = observation_request(provider, contract, secret=self.command_secrets[provider])
            # Count even unsuccessful observations against the mock budget. Do not imply refunds.
            spent += price
            try:
                receipt = await transport.invoke(provider, request)
                if receipt.status != "success":
                    raise EvidenceError(f"PROVIDER_REJECTED: {(receipt.error or {}).get('code', 'UNKNOWN_ERROR')}")
                decision = self.verifier.verify(receipt, request, contract)
            except Exception as exc:
                rejected.append({"provider": provider, "reason": f"{type(exc).__name__}: {exc}"})
                continue
            demand_id = self.ledger.record(contract, "served", provider=provider, reason=decision["decision"])
            return {"status": "success", "provider": provider, "transport": transport.transport_name,
                    "decision": decision, "receipt": asdict(receipt), "request": request.to_dict(),
                    "rejected_providers": rejected, "mock_spent": str(spent),
                    "payment_mode": "mock; no funds moved", "demand_id": demand_id}
        demand_id = self.ledger.record(contract, "unmet", reason=json.dumps(rejected))
        return {"status": "unmet", "decision": {"decision": "WAIT", "reason": "No fresh verified evidence"},
                "rejected_providers": rejected, "mock_spent": str(spent),
                "payment_mode": "mock; no funds moved", "demand_id": demand_id}
