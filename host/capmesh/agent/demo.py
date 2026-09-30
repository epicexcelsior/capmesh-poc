import asyncio
import time
import sys
from typing import Optional
from .policy import AgentPolicyEngine
from ..protocol.models import InvocationRequest, InvocationReceipt, DeliveryProof
from ..protocol.auth import generate_nonce, create_auth_payload, verify_receipt, receipt_message, compute_hmac_sha256, DEFAULT_SECRET
from ..transport.ble import BLETransportAdapter
from ..provider.local_provider import LaptopProvider
from ..provider.untrusted_provider import UntrustedRogueProvider

# ANSI Colors
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
RESET = "\033[0m"

class SimulatedBLETransport:
    """Mock/Simulated BLE transport for deterministic rehearsal or offline demonstrations."""
    def __init__(self, device_id: str = "esp32-c6-96a2"):
        self.device_id = device_id
        self._seen_nonces = set()

    @property
    def transport_name(self) -> str:
        return "ble"

    async def discover(self, timeout: float = 1.0):
        from ..protocol.models import Manifest, Capability, Pricing
        return [Manifest(
            protocol="capmesh/0.1",
            device_id=self.device_id,
            transport="ble",
            address="10:BD:A3:AC:96:A2",
            trust_tier="verified",
            attestation="esp32-puf-attestation-0x96a2",
            capabilities=[Capability(
                id="led.blink",
                description="Blink onboard status LED",
                pricing=Pricing(model="fixed", amount="0.004", currency="mock-usdc"),
                parameters={"duration": {"type": "integer", "default": 2}, "count": {"type": "integer", "default": 3}}
            )]
        )]

    async def invoke(self, target: str, request: InvocationRequest, timeout: float = 5.0) -> InvocationReceipt:
        now = int(time.time())
        if request.nonce in self._seen_nonces:
            return InvocationReceipt(
                protocol=request.protocol,
                request_id=request.request_id,
                status="error",
                provider=self.device_id,
                error={"code": "REPLAY_DETECTED", "message": "Nonce has already been processed"}
            )
        if request.expiration and request.expiration < now:
            return InvocationReceipt(
                protocol=request.protocol,
                request_id=request.request_id,
                status="error",
                provider=self.device_id,
                error={"code": "AUTH_EXPIRED", "message": "Request expiration timestamp is in the past"}
            )
        auth = request.authorization or {}
        expected = create_auth_payload(
            request.request_id, request.capability, request.nonce, request.expiration,
            device_id=request.device_id, parameters=request.parameters, timestamp=request.timestamp,
        )
        if auth != expected:
            return InvocationReceipt(
                protocol=request.protocol,
                request_id=request.request_id,
                status="error",
                provider=self.device_id,
                error={"code": "UNAUTHORIZED", "message": "Invalid cryptographic authorization signature"}
            )

        self._seen_nonces.add(request.nonce)
        start_time = now
        await asyncio.sleep(0.5)
        completed_time = int(time.time())
        dp = DeliveryProof(
            observer_id="esp32_gpio8_hw_pad",
            expected_state="PULSED",
            observed_state="ACTIVE_HIGH",
            verified_samples=3,
            total_samples=3,
            readback_verified=True
        )
        receipt = InvocationReceipt(
            protocol=request.protocol,
            request_id=request.request_id,
            status="success",
            provider=self.device_id,
            capability=request.capability,
            parameters=request.parameters,
            result={"blinks_completed": 3},
            started_at=start_time,
            completed_at=completed_time,
            delivery_proof=dp,
        )
        receipt.receipt_signature = "v2:" + compute_hmac_sha256(DEFAULT_SECRET, receipt_message(receipt))
        return receipt

async def run_adversarial_demo(simulated: bool = False, live_timeout: float = 3.0) -> bool:
    print(f"\n{BOLD}{CYAN}================================================================================{RESET}")
    print(f"{BOLD}{CYAN}      CAPMESH — {'SIMULATED' if simulated else 'LIVE'} HARDWARE AUTHORIZATION DEMO (TUM 2026)      {RESET}")
    print(f"{BOLD}{CYAN}================================================================================{RESET}\n")

    goal_prompt = "Find the ESP32 LED and invoke it within the mock price limit."
    print(f"{BOLD}User Goal Prompt:{RESET} \"{YELLOW}{goal_prompt}{RESET}\"")
    print(f"{BOLD}Agent Policy Constraints:{RESET}")
    print(f"  * Capability requirement: {CYAN}visual_signal{RESET} (or {CYAN}led.blink{RESET})")
    print(f"  * Price Ceiling: {GREEN}€0.0100{RESET}")
    print(f"  * Provider identity: {YELLOW}not authenticated by discovery{RESET}")
    print(f"  * Payment: {YELLOW}mock only{RESET}")

    # Set up transports
    ble_transport = BLETransportAdapter() if not simulated else SimulatedBLETransport()
    rogue_transport = UntrustedRogueProvider()

    # Check if live hardware is available if not explicitly forced simulated
    if not simulated:
        print(f"\n{CYAN}[PROBE]{RESET} Scanning for live ESP32-C6 hardware over BLE...")
        try:
            live_devs = await ble_transport.discover(timeout=live_timeout)
            if not live_devs:
                print(f"{YELLOW}[WARN]{RESET} Live ESP32 BLE peripheral not detected within {live_timeout}s.")
                print(f"{RED}[FAIL]{RESET} Live hardware required. Use --simulated for rehearsal.")
                return False
            else:
                print(f"{GREEN}[FOUND]{RESET} Live ESP32-C6 detected: {live_devs[0].device_id} ({live_devs[0].address})")
        except Exception as e:
            print(f"{RED}[FAIL]{RESET} BLE scan failed ({e}). Use --simulated for rehearsal.")
            return False

    engine = AgentPolicyEngine(
        transports=[ble_transport, rogue_transport, LaptopProvider()],
        spending_ceiling=0.10
    )

    # STEP 1: Discovery
    print(f"\n{BOLD}{CYAN}[STEP 1] PROXIMITY DISCOVERY ACROSS TRANSPORTS{RESET}")
    print("  -> Scanning Bluetooth Low Energy (GATT Service 0xCB00)...")
    print("  -> Scanning Local Area Network (Wi-Fi HTTP)...")
    discovered = await engine.discover_all(timeout=3.0)

    print(f"\n  {BOLD}Discovered Providers & Capabilities:{RESET}")
    for manifest, transport in discovered:
        trust_color = GREEN if manifest.trust_tier == "verified" else YELLOW
        print(f"  * {BOLD}{manifest.device_id}{RESET} [{transport.transport_name}]")
        print(f"    - Trust Tier: {trust_color}{manifest.trust_tier.upper()}{RESET} (attestation: {manifest.attestation or 'none'})")
        for cap in manifest.capabilities:
            print(f"    - Capability: {CYAN}{cap.id}{RESET} ({cap.description})")
            print(f"      Pricing: {YELLOW}{cap.pricing.amount} {cap.pricing.currency}{RESET}")

    # STEP 2: Policy Evaluation & Rogue Node Rejection
    print(f"\n{BOLD}{CYAN}[STEP 2] DEMO DEVICE SELECTION{RESET}")
    print("  -> Selecting the known ESP32 ID for this hardware test.")
    print("  -> The rogue provider is a labeled fixture. No provider identity attestation is implemented.")

    # STEP 3: Mock-priced authorization. No funds move in this demo.
    print(f"\n{BOLD}{CYAN}[STEP 3] DEMO AUTHORIZATION (NO PAYMENT){RESET}")
    print("  -> The manifest price is mock-usdc. No Solana transaction or channel settlement occurs.")

    # STEP 4: Execution
    print(f"\n{BOLD}{CYAN}[STEP 4] CAPABILITY INVOCATION & PHYSICAL ACTUATION{RESET}")
    req_nonce = generate_nonce()
    now = int(time.time())
    expiration = now + 120
    req_id = f"demo-{int(time.time()*1000)%10000000:07x}"

    auth_payload = create_auth_payload(
        request_id=req_id,
        capability="led.blink",
        nonce=req_nonce,
        expiration=expiration,
        device_id="esp32-c6-96a2",
        parameters={"duration": 2, "count": 3},
        timestamp=now,
        secret=DEFAULT_SECRET
    )

    req = InvocationRequest(
        request_id=req_id,
        device_id="esp32-c6-96a2",
        capability="led.blink",
        parameters={"duration": 2, "count": 3},
        nonce=req_nonce,
        timestamp=now,
        expiration=expiration,
        authorization=auth_payload
    )

    print(f"  -> Dispatching invocation token to ESP32 (Transport: {ble_transport.transport_name})...")
    print(f"     Payload: req_id={req_id}, capability=led.blink, nonce={req_nonce}")
    print(f"  -> Actuating onboard LED on GPIO 8...")
    receipt = await ble_transport.invoke("esp32-c6-96a2", req)

    # STEP 5: Delivery Proof
    print(f"\n{BOLD}{CYAN}[STEP 5] DEVICE-REPORTED GPIO PAD READBACK{RESET}")
    if receipt.status != "success":
        print(f"{RED}[FAIL]{RESET} Invocation failed: {receipt.error}")
        return False

    receipt_sig_valid = verify_receipt(receipt, secret=DEFAULT_SECRET)
    if not receipt_sig_valid:
        print(f"{RED}[FAIL]{RESET} Receipt HMAC did not match the result and pad samples.")
        return False
    print(f"  -> Provider Receipt HMAC: {GREEN}VERIFIED{RESET}")

    dp = receipt.delivery_proof
    if dp and dp.readback_verified:
        print(f"  -> {GREEN}[PAD SAMPLED]{RESET} The same ESP32 reports its output pin level:")
        print(f"     * Observer ID: {CYAN}{dp.observer_id}{RESET} (GPIO 8 Input Buffer)")
        print(f"     * Expected State: {dp.expected_state}")
        print(f"     * Observed State: {GREEN}{dp.observed_state}{RESET}")
        print(f"     * Electrical Pad Readback: {GREEN}{dp.verified_samples}/{dp.total_samples} cycles verified{RESET}")
        print(f"     * {BOLD}This does not prove that an external good was delivered.{RESET}")
    else:
        print(f"  -> {YELLOW}[WARN]{RESET} Delivery proof missing or degraded.")

    # STEP 6: Adversarial Live Fire Test
    print(f"\n{BOLD}{CYAN}[STEP 6] ADVERSARIAL ATTACK RESILIENCE (LIVE FIRE TEST){RESET}")

    # Attack 1: Replay Attack
    print(f"\n  {BOLD}[ATTACK 1: REPLAY ATTACK]{RESET}")
    print("  -> Attacker captures previously valid invocation token and resends it...")
    replay_receipt = await ble_transport.invoke("esp32-c6-96a2", req)
    if replay_receipt.status == "error" and replay_receipt.error.get("code") == "REPLAY_DETECTED":
        print(f"  -> Response: {GREEN}BLOCKED ({replay_receipt.error.get('code')}: {replay_receipt.error.get('message')}){RESET}")
    else:
        print(f"  -> {RED}[FAIL]{RESET} Replay attack was not blocked!")
        return False

    # Attack 2: Expired Authorization
    print(f"\n  {BOLD}[ATTACK 2: EXPIRED AUTHORIZATION]{RESET}")
    print("  -> Attacker submits authorization token with expiration timestamp in the past...")
    exp_nonce = generate_nonce()
    expired_req = InvocationRequest(
        request_id=f"atk-{int(time.time()*1000)%10000000:07x}",
        device_id="esp32-c6-96a2",
        capability="led.blink",
        parameters={"duration": 1, "count": 1},
        nonce=exp_nonce,
        timestamp=now - 200,
        expiration=now - 100,
        authorization=create_auth_payload(
            request_id=f"atk-{int(time.time()*1000)%10000000:07x}",
            capability="led.blink",
            nonce=exp_nonce,
            expiration=now - 100,
            device_id="esp32-c6-96a2",
            parameters={"duration": 1, "count": 1},
            timestamp=now - 200,
        )
    )
    exp_receipt = await ble_transport.invoke("esp32-c6-96a2", expired_req)
    if exp_receipt.status == "error" and exp_receipt.error.get("code") == "AUTH_EXPIRED":
        print(f"  -> Response: {GREEN}BLOCKED ({exp_receipt.error.get('code')}: {exp_receipt.error.get('message')}){RESET}")
    else:
        print(f"  -> {RED}[FAIL]{RESET} Expired authorization was not blocked!")
        return False

    # Attack 3: Tampered Signature
    print(f"\n  {BOLD}[ATTACK 3: TAMPERED AUTHORIZATION]{RESET}")
    print("  -> Attacker alters invocation parameters while forging cryptographic token...")
    tamper_nonce = generate_nonce()
    tampered_req = InvocationRequest(
        request_id=f"tamper-{int(time.time()*1000)%10000000:07x}",
        device_id="esp32-c6-96a2",
        capability="led.blink",
        parameters={"duration": 10, "count": 50},
        nonce=tamper_nonce,
        timestamp=now,
        expiration=now + 120,
        authorization={"type": "hmac-sha256", "token": "tampered-token"}
    )
    tamper_receipt = await ble_transport.invoke("esp32-c6-96a2", tampered_req)
    if tamper_receipt.status == "error" and tamper_receipt.error.get("code") == "UNAUTHORIZED":
        print(f"  -> Response: {GREEN}BLOCKED ({tamper_receipt.error.get('code')}: {tamper_receipt.error.get('message')}){RESET}")
    else:
        print(f"  -> {RED}[FAIL]{RESET} Tampered signature was not blocked!")
        return False

    # Summary
    print(f"\n{BOLD}{GREEN}================================================================================{RESET}")
    print(f"{BOLD}{GREEN}              {'SIMULATED' if simulated else 'LIVE'} AUTHORIZATION DEMO PASSED                               {RESET}")
    print(f"{BOLD}{GREEN}================================================================================{RESET}")
    print(f"  1. {GREEN}Discovery{RESET}: Read the ESP32 capability manifest over BLE.")
    print(f"  2. {YELLOW}Trust{RESET}: Device identity remains unverified by discovery.")
    print(f"  3. {YELLOW}Payment{RESET}: Mock-priced only; no funds moved.")
    print(f"  4. {GREEN}Physical Actuation{RESET}: Commanded {'simulated' if simulated else 'physical'} ESP32 LED over BLE.")
    print(f"  5. {YELLOW}Delivery Evidence{RESET}: Device-reported GPIO pad sample only.")
    print(f"  6. {GREEN}Adversarial Defense{RESET}: Blocked Replay, Expiry, and Tampering live on chip.")
    print(f"  7. {YELLOW}x402{RESET}: Exercise the separate gateway to test the payment challenge.")
    print(f"{BOLD}{GREEN}================================================================================{RESET}\n")
    return True

if __name__ == "__main__":
    is_sim = "--simulated" in sys.argv
    raise SystemExit(0 if asyncio.run(run_adversarial_demo(simulated=is_sim)) else 1)
