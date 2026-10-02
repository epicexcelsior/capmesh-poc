"""Read the Agung deployment and compute an observer ID. No wallet or chain writes.

Run in an isolated environment with peaq-os-sdk==0.10.0.
The SDK supplies the published deployment snapshot and contract ABIs.
"""

from dataclasses import asdict
from importlib.metadata import version
import json
from pathlib import Path
import sys
from cryptography.hazmat.primitives.asymmetric import ec

ROOT = Path(__file__).resolve().parents[1]
RPC_URL = "https://peaq-agung.api.onfinality.io/public"
DEPLOYMENT_ID = "agung-2026-08-28"
SDK_VERSION = "0.10.0"
READ_METHODS = frozenset({"eth_chainId", "eth_getBlockByNumber", "eth_getCode", "eth_call"})


def guarded_request(send, method, params):
    if method not in READ_METHODS:
        raise PermissionError(f"This diagnostic refuses the RPC method {method}.")
    return send(method, params)


def observer_subject(pins):
    key = pins.get("providers", {}).get("esp32-c6-96a2", "")
    if (pins.get("algorithm") != "ecdsa-p256-sha256" or not isinstance(key, str)
            or len(key) != 130 or not key.startswith("04")):
        raise ValueError("The observer has no provisioned P-256 public key.")
    ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), bytes.fromhex(key))
    # These proposed identity bytes are explicit. They do not certify a location or operator permission.
    return json.dumps({"schema": "fieldproof-observer-v1", "provider": "esp32-c6-96a2",
                       "public_key_sec1_hex": key.lower()}, sort_keys=True, separators=(",", ":")).encode()


def run():
    if version("peaq-os-sdk") != SDK_VERSION:
        raise ValueError(f"Use peaq-os-sdk=={SDK_VERSION} for the recorded deployment snapshot.")
    from web3 import Web3, HTTPProvider
    from peaq_os_sdk.tokenomics.deployments import resolve_tokenomics20_deployment
    from peaq_os_sdk.tokenomics.abis import (INFO_DESK_ABI, MACHINE_REGISTRY_ABI,
                                           MACHINE_STATE_AND_SYNC_ABI, MACHINE_SUBSCRIPTION_ABI)

    class ReadOnlyHTTPProvider(HTTPProvider):
        def make_request(self, method, params):
            return guarded_request(super().make_request, method, params)

    provider = ReadOnlyHTTPProvider(RPC_URL, request_kwargs={"timeout": 15}, exception_retry_configuration=None)
    w3 = Web3(provider)
    deployment = resolve_tokenomics20_deployment(DEPLOYMENT_ID)
    chain_id = w3.eth.chain_id
    if chain_id != 9990 or deployment.chain_id != chain_id:
        raise ValueError("The connected RPC does not match the published Agung deployment.")
    block = w3.eth.get_block("finalized")
    block_number = block["number"]
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

    pins = json.loads((ROOT / "host/capmesh/protocol/receipt_keys.json").read_text())
    subject = observer_subject(pins)
    machine_type = "FieldProofContactObserverV1"
    registry = contract("machine_registry", MACHINE_REGISTRY_ABI)
    machine_id = read(registry.functions.computeTokenId(machine_type, subject))
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
            "activation_checks": {"economic_authority": authority, "paused_global": paused_global,
                                  "paused_machine": paused_machine, "tier": 0,
                                  "bond_base_units": str(bond), "payment_token": read(info.functions.peaqToken())},
            "limits": "This snapshot excludes operator funding, allowance, gas, manufacturer, DID methods, and service endpoints. It does not authorize activation or establish sensor truth."}


if __name__ == "__main__":
    try:
        print(json.dumps(run(), indent=2))
    except Exception as error:
        print(f"Agung readiness check failed: {error}", file=sys.stderr)
        sys.exit(1)
