# peaq integration decision

**October 2, 2026: Agung identity readiness passed. No machine activation or peaq transaction occurred.**
Keep the Solana contact MVP frozen through the October 5 Germany submission.
The next peaq flow connects the observer's identity to its public signing key and permitted observation service.
This document owns peaq interfaces, readiness, and activation gates.

## What the diagnostic establishes

[`check_peaq_readiness.py`](../scripts/check_peaq_readiness.py) reads the Agung testnet through the published RPC.
It uses the deployment snapshot and contract interfaces from `peaq-os-sdk==0.10.0`.
It requires no private key, account, platform API key, or physical board.
Its RPC transport permits only chain ID, block, bytecode, and contract reads. It refuses signing and transaction methods.

The [recorded readiness result](evidence/peaq-agung-readiness.json) reports:

| Read at finalized block 10,996,074 | Result |
|---|---|
| Connected chain | Agung, chain ID 9990 |
| Published deployment | `agung-2026-08-28` |
| Seven contract addresses | All contain bytecode |
| Six InfoDesk peer entries | All match the published snapshot |
| Subscription economic authority | `true` |
| Global and proposed-machine technical pause | Both `false` |
| Tier-0 full bond | `400000000000000000` base units |
| Payment token | Native-balance precompile `0x0000000000000000000000000000000000000809` |

The SDK identifies this precompile as the native balance used for the bond and gas.
The recorded bond equals 0.4 native test tokens at 18 decimals. Gas requires additional balance.
This is a full bond read, not an operator-specific quote. Voucher credit, allowance, gas, and operator funding remain unchecked.
These values can change before activation. The script reads every value again when it runs.
[Network configuration](https://docs.peaq.xyz/peaqchain/build/getting-started/connecting-to-peaq), [published Python SDK](https://pypi.org/project/peaq-os-sdk/0.10.0/).

Bytecode presence and peer agreement do not audit implementation code or establish the safety of contract upgrades.
This readiness result does not replace the SDK's full activation preflight.

## How the identity proposal connects to FieldProof

The proposed machine type is `FieldProofContactObserverV1`.
The credential subject contains a versioned schema, the ESP32 provider ID, and the existing public P-256 pin.
The diagnostic accepts an operator-selected provider and trusted public pin file for another observer.
Changing either value changes the proposed identity bytes. Missing or invalid pins fail before RPC access.
The script sends these exact public bytes to `MachineRegistry.computeTokenId` at the recorded block.
It preserves the resulting 256-bit identifier as a decimal string. JavaScript numbers cannot preserve every identifier of this size.

The proposed ID is:

```text
2044618828586167349407969644236800133676464971368659651643404080491769435145
```

The result means that the registry can derive an identity from these proposed bytes.
It does not mean that FieldProof owns an activated identity.
The diagnostic's `activated: false` states that it performs no activation. It does not query ownership or prove ID availability.

Before activation, define the operator, controller, manufacturer field, verification method, and service endpoint.
Use the approved SDK activation flow with explicit spending bounds and receipt reconciliation.
The current full client also requires legacy contract constructor arguments. Do not fill them with invented addresses to make initialization pass.

The intended completed flow is:

1. Activate an observer identity with an explicit operator and public verification method.
2. Read its owner, controller, verification method, and observation endpoint back from peaq.
3. Compare the registered key with the independently provisioned buyer pin.
4. Complete a Solana Devnet observation purchase through the existing gateway.
5. Verify the delivered device receipt independently.
6. Record a permitted activity event with the observation evidence hash.

Steps 1–6 remain integration work. The existing Solana purchase already works independently.
Do not represent a test-token payment as revenue in a machine history.
Do not publish private location or customer data as event metadata.

Registry registration records an operator claim. It does not establish device key possession, installation, physical truth, or site permission.
The public identity inputs also require an ownership and reservation review before activation. An identifier alone is not an authorization mechanism.

## Why Solana onboarding does not remove this gate

The official Solana onboarding guide reports paused onboarding and a mainnet-only flow.
It also identifies a contract migration. Treat copied reservation instructions as stale until the supported deployment is verified.
Native Agung readiness is a separate path. It does not prove that Solana onboarding works.
[Solana onboarding guide](https://docs.peaq.xyz/peaqos/guides/onboard-on-solana).

The inspected Python release supports selected Tokenomics identity and event surfaces.
It also rejects unsupported identity-dependent Machine Markets operations before network work.
No public generic registration endpoint for a FieldProof provider was established through the inspected robotic.sh service example.
Do not claim that catalog access activates a FieldProof observer.
[Python SDK interface status](https://pypi.org/project/peaq-os-sdk/0.10.0/), [robotic.sh service example](https://www.robotic.sh/services/acurast).

## Reproduce the read-only result

Run from the repository root. This command uses an isolated SDK environment and leaves MVP dependencies unchanged.
The explicit environment values disable SDK telemetry.

```bash
DO_NOT_TRACK=1 PEAQOS_TELEMETRY=0 uv run --no-project --with peaq-os-sdk==0.10.0 python scripts/check_peaq_readiness.py
```

Expect `chain_id: 9990`, `peers_match: true`, both pause flags `false`, and a proposed machine ID.
Add `--provider` and `--pins` after the script path to select a provisioned second observer.
Pin-file paths resolve from the repository root. No second physical observer or activated identity is claimed.
An unavailable RPC, changed peer, missing contract, wrong chain, or active pause produces a visible error and exits unsuccessfully.
The script does not silently switch endpoints or deployments.

The inspected wheel SHA256 is `508808bb565ec3bf088759e047cba12e70678aa3f9d0ef335c88c34ab90e0e3e`.
The readiness run used that wheel in an isolated environment. The command above resolves the same version through PyPI.

## Decision required before a write

After the MVP package, authorize one permanent Agung test identity and select its operator wallet.
Review exact public identity inputs and the current bounded bond and gas cost first.
Activation creates permanent public state. The SDK describes no deactivation or bond refund.
No mainnet funds or activation belong in the October 5 critical path.
[SDK activation and integration limits](https://pypi.org/project/peaq-os-sdk/0.10.0/).
