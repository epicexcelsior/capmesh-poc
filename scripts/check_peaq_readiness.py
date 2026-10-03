"""Read the Agung deployment and compute an observer ID. No wallet or chain writes.

Run in an isolated environment with peaq-os-sdk==0.10.0.
The SDK supplies the published deployment snapshot and contract ABIs.
"""

from dataclasses import asdict, dataclass
import argparse
from importlib.metadata import version
import json
from pathlib import Path
import sys
import re
from cryptography.hazmat.primitives.asymmetric import ec

ROOT = Path(__file__).resolve().parents[1]
RPC_URL = "https://peaq-agung.api.onfinality.io/public"
DEPLOYMENT_ID = "agung-2026-08-28"
SDK_VERSION = "0.10.0"
READ_METHODS = frozenset({"eth_chainId", "eth_getBlockByNumber", "eth_getCode", "eth_call"})


def guarded_request(send, method, params, *, read_block=None):
    if method not in READ_METHODS:
        raise PermissionError(f"This diagnostic refuses the RPC method {method}.")
    if read_block is not None:
        if type(read_block) is not int or read_block < 0:
            raise ValueError("Use an explicit nonnegative finalized block number.")
        if method in {"eth_call", "eth_getCode"}:
            if not isinstance(params, (list, tuple)) or len(params) != 2:
                raise ValueError("Pinned contract reads require exactly two RPC parameters.")
            pinned = hex(read_block)
            if params[1] not in {"latest", "finalized", pinned}:
                raise ValueError("This diagnostic refuses a different contract-read block.")
            # SDK owner reads use latest by default. Keep them in the same finalized snapshot as readiness.
            params = [params[0], pinned]
    return send(method, params)


@dataclass(frozen=True)
class RegistryReadContext:
    """Implement the published SDK's two-property TokenomicsReadContext without a signing account."""
    w3: object
    tokenomics20: object


def registration_state(read_owner, machine_id, sdk_error_type):
    """Distinguish a decoded nonexistent token from RPC failure or foreign home state."""
    try:
        owner = read_owner(machine_id)
    except sdk_error_type as error:
        if error.code == "MACHINE_NOT_FOUND" and error.solidity_error == "ERC721NonexistentToken":
            return {"status": "not_found_at_block", "owner": None, "code": error.code,
                    "solidity_error": error.solidity_error}
        if error.code == "MACHINE_HOMED_ELSEWHERE":
            return {"status": "homed_elsewhere", "owner": None, "code": error.code}
        raise
    if not isinstance(owner, str) or not re.fullmatch(r"0x[0-9a-fA-F]{40}", owner) or int(owner[2:], 16) == 0:
        raise ValueError("The machine registry returned an invalid owner address.")
    return {"status": "registered", "owner": owner, "code": None}


def observer_subject(pins, provider="esp32-c6-96a2"):
    if not isinstance(provider, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,31}", provider):
        raise ValueError("Select a valid observer provider ID.")
    if not isinstance(pins, dict) or not isinstance(pins.get("providers"), dict):
        raise ValueError("The public pin file must contain an object with a providers object.")
    key = pins.get("providers", {}).get(provider, "")
    if (pins.get("algorithm") != "ecdsa-p256-sha256" or not isinstance(key, str)
            or len(key) != 130 or not key.startswith("04")):
        raise ValueError("The observer has no provisioned P-256 public key.")
    ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), bytes.fromhex(key))
    # These proposed identity bytes are explicit. They do not certify a location or operator permission.
    return json.dumps({"schema": "fieldproof-observer-v1", "provider": provider,
                       "public_key_sec1_hex": key.lower()}, sort_keys=True, separators=(",", ":")).encode()


def run(provider_id="esp32-c6-96a2", pins_path=None):
    pins = json.loads((ROOT / (pins_path or "host/capmesh/protocol/receipt_keys.json")).read_text())
    subject = observer_subject(pins, provider_id)
    if version("peaq-os-sdk") != SDK_VERSION:
        raise ValueError(f"Use peaq-os-sdk=={SDK_VERSION} for the recorded deployment snapshot.")
    from web3 import Web3, HTTPProvider
    from peaq_os_sdk.tokenomics.deployments import resolve_tokenomics20_deployment
    from peaq_os_sdk.tokenomics.get_machine_owner import get_machine_owner
    from peaq_os_sdk.tokenomics.errors import TokenomicsActivationError
    from peaq_os_sdk.tokenomics.abis import (INFO_DESK_ABI, MACHINE_REGISTRY_ABI,
                                           MACHINE_STATE_AND_SYNC_ABI, MACHINE_SUBSCRIPTION_ABI)

    class ReadOnlyHTTPProvider(HTTPProvider):
        read_block = None

        def make_request(self, method, params):
            return guarded_request(super().make_request, method, params, read_block=self.read_block)

    provider = ReadOnlyHTTPProvider(RPC_URL, request_kwargs={"timeout": 15}, exception_retry_configuration=None)
    w3 = Web3(provider)
    deployment = resolve_tokenomics20_deployment(DEPLOYMENT_ID)
    chain_id = w3.eth.chain_id
    if chain_id != 9990 or deployment.chain_id != chain_id:
        raise ValueError("The connected RPC does not match the published Agung deployment.")
    block = w3.eth.get_block("finalized")
    block_number = block["number"]
    provider.read_block = block_number
    contracts = asdict(deployment.contracts)
    bytecode_lengths = {}
    for role, address in contracts.items():
        size = len(w3.eth.get_code(Web3.to_checksum_address(address), block_identifier=block_number))
        if size == 0:
            raise ValueError(f"No deployed contract exists for {role} at the recorded address.")
        bytecode_lengths[role] = size

    def contract(role, abi):
        return w3.eth.contract(address=Web3.to_checksum_address(contracts[role]), abi=abi)

    def read(function):
        return function.call(block_identifier=block_number)

    info = contract("info_desk", INFO_DESK_ABI)
    for role, expected in contracts.items():
        if role == "info_desk":
            continue
        actual = read(info.functions.peer(Web3.keccak(text=role.upper())))
        if actual.lower() != expected.lower():
            raise ValueError(f"InfoDesk does not confirm the published {role} address.")

    machine_type = "FieldProofContactObserverV1"
    registry = contract("machine_registry", MACHINE_REGISTRY_ABI)
    machine_id = read(registry.functions.computeTokenId(machine_type, subject))
    read_context = RegistryReadContext(w3=w3, tokenomics20=deployment)
    registration = registration_state(lambda identifier: get_machine_owner(read_context, identifier),
                                      machine_id, TokenomicsActivationError)
    state = contract("machine_state_and_sync", MACHINE_STATE_AND_SYNC_ABI)
    subscription = contract("machine_subscription", MACHINE_SUBSCRIPTION_ABI)
    paused_global = read(state.functions.isTechnicalPausedGlobal())
    paused_machine = read(state.functions.isTechnicalPaused(machine_id))
    authority = read(subscription.functions.isEconomicAuthority())
    if any(type(flag) is not bool for flag in (paused_global, paused_machine, authority)):
        raise ValueError("The deployment returned an invalid activation flag.")
    if paused_global or paused_machine or not authority:
        raise ValueError("The deployment currently blocks this activation path.")
    bond = read(subscription.functions.requiredPeaqAmount(0))
    if type(bond) is not int or bond < 0:
        raise ValueError("The deployment returned an invalid bond amount.")
    return {"method": "Public Agung contract reads at one finalized block. No wallet, signature, approval, or transaction.",
            "sdk": {"package": "peaq-os-sdk", "version": SDK_VERSION, "deployment_id": DEPLOYMENT_ID},
            "rpc": RPC_URL, "chain_id": chain_id, "finalized_block": block_number,
            "block_hash": block["hash"].to_0x_hex(), "block_timestamp": block["timestamp"],
            "contracts": contracts, "contract_bytecode_lengths": bytecode_lengths, "peers_match": True,
            "identity_proposal": {"machine_type": machine_type, "credential_subject_utf8": subject.decode(),
                                  "computed_machine_id": str(machine_id), "activated": False},
            "registry_state": registration,
            "activation_checks": {"economic_authority": authority, "paused_global": paused_global,
                                  "paused_machine": paused_machine, "tier": 0,
                                  "bond_base_units": str(bond), "payment_token": read(info.functions.peaqToken())},
            "limits": "This snapshot excludes operator funding, allowance, gas, manufacturer, DID methods, and service endpoints. A not-found ID is not reserved and can change after this block. This diagnostic does not authorize activation or establish sensor truth."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default="esp32-c6-96a2", help="Operator-selected provider ID")
    parser.add_argument("--pins", help="Trusted public pin file, relative to the repository root or absolute")
    arguments = parser.parse_args()
    try:
        print(json.dumps(run(arguments.provider, arguments.pins), indent=2))
    except Exception as error:
        print(f"Agung readiness check failed: {error}", file=sys.stderr)
        sys.exit(1)
