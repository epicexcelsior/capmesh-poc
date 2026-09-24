# CapMesh Feasibility, Holes, and Hackathon Notes

**Date:** 2026-09-24  
**Primary target:** TUM Blockchain & AI Hackathon, Munich, Oct 30–31 2026 (theme: Agentic Payments)  
**Secondary:** future Colosseum/Solana hackathons (startup track — lower priority)  
**Sources:** Colosseum Copilot (projects, archives), web research, `ORIGINAL_PLAN.md`, repo docs  
**Skill:** colosseum-copilot v1.2.1

---

## 1. Verdict

| Dimension | Rating | Note |
|---|---|---|
| Protocol architecture (transport-independent capabilities) | Sound | Correctly separates BLE from capability logic; keep this invariant. |
| Timing | Strong | Agentic payments + Solana Payment Channels + TUM theme align. |
| Demo fit (30h build) | Good if scoped tight | LED is fine for v1; pair with a non-toy capability and real settlement story. |
| Startup readiness | Early | Cold-start, custody, liability, and standards competition unresolved. |
| Biggest unsolved risk | Physical delivery proof | Receipts only prove the device *claims* execution. |

**One-line pitch for TUM:**  
*A transport-independent capability protocol where an ESP32 is the first provider, a laptop agent the first buyer; BLE the first transport; settlement via Solana Payment Channels / x402-shaped authorizations; optional Arcium for private policy.*

---

## 2. What the plan gets right (do not reverse)

- Capability layer before payment (`ORIGINAL_PLAN.md` §1, §5).
- No RPC on the MCU; host-mediated settlement (Phase 5).
- HMAC first, Ed25519 later (ADR 004) — right for ESP32-C6.
- Replay, nonce, expiry, invalid-sig tests as definition of done.
- Explicit non-goals: no custom program, no ZK, no LLM inside the security boundary.
- Refusal to relabel HTTP x402 as a BLE protocol.

---

## 3. Holes poked → potential fixes

### H1. Physical delivery is an oracle problem

| | |
|---|---|
| **Hole** | Signed receipt = device self-report. Buyer cannot prove lock opened, motor ran, charger delivered energy. |
| **Evidence** | CSIRO oracle pattern; BIS oracle problem report; zk-IoT (Cypherpunk Sep 2025); DECISIONS.md Q2. |
| **Hackathon impact** | Judges will ask "how do I know the LED actually blinked?" |
| **Fix (demo)** | Sensor echo: actuator GPIO + independent readback in the receipt. Human confirmation for LED (already in plan §11). |
| **Fix (protocol)** | Receipt fields: `expected_state`, `observed_state`, `observer_id`. Dual-control for valuable actuators (actuator + separate sensor). |
| **Fix (stretch)** | zk-IoT-style proof of firmware execution; PUF-bound device identity. Defer past TUM. |
| **Open question** | What is the minimum attestation that makes a receipt *disputeable*? |

### H2. Keys on ESP32 are a liability

| | |
|---|---|
| **Hole** | Long-lived Solana or capability keys on a $4 board. |
| **Evidence** | CVE-2019-17391 (eFuse glitch readout), CVE-2019-15894 (secure-boot bypass); ESP-IDF flash encryption does not stop all physical attacks. Crowded prior art: `solana-esp32-x402`, Solduino (on-device Ed25519 + x402). |
| **Fix** | **Never put custody keys on-device.** Device holds only a host-issued session/HMAC key; verifies short-lived capability authorizations. Settlement keys stay in host wallet / Seeker / MWA. |
| **Rule** | If a demo wants "wallet on ESP32," reject it — you inherit hardware-wallet requirements without the protections. |
| **Open question** | How is the session key provisioned and rotated without a trusted display? |

### H3. Settlement economics break at $0.001

| | |
|---|---|
| **Hole** | Per-blink SPL transfer: ~$0.0007 base fee + priority + possible ~$0.40 ATA rent ≫ or ≈ payment. |
| **Fix** | **Solana Payment Channels** (mainnet program `CHNLxYvVA28MJP9PrFuDXccuoGXAx7jBacfLEkahyGsX`): escrow ceiling → off-chain Ed25519 vouchers → single settle. Bench Sep 2026: 1M payments/s, 100k channels. |
| **Fix (TUM)** | One channel open per session; many BLE invokes metered off-chain; settle once. Map to x402 `upto` / MPP `session` semantics. |
| **Fix (interface)** | Add `PaymentChannelVerifier` next to `Mock` / `SolanaDevnet`. |
| **Open question** | How does a channel voucher attach to a BLE invoke when the device has no RPC? (Host signs voucher; device trusts host-issued bounded auth.) |

### H4. x402 / HTTP owns the agent-payment standard; BLE is not a payment rail

| | |
|---|---|
| **Hole** | Inventing a third payment envelope. |
| **Evidence** | x402 ~200M tx / ~$50B vol (Aug 2026); competitors: Stripe MPP, Google AP2, Visa TAP. Academic attacks: arXiv *Five Attacks on x402*, *Free-Riding the Agentic Web* — auth, binding, replay, cache issues. |
| **Fix** | CapMesh = capability + transport protocol that **carries** payment-requirement / authorization / receipt objects compatible with x402 V2 shape. Over HTTP: speak real x402. Over BLE: same logical objects, different framing. |
| **Reuse** | Your nonce/expiry/replay tests already address the same class of flaws x402 is criticized for — document that mapping for judges. |
| **Open question** | Canonical JSON schema shared between BLE GATT frames and HTTP body? |

### H5. Standards competition: WoT and Matter already do discovery + invoke

| | |
|---|---|
| **Hole** | Looks like reinventing Web of Things / Matter. |
| **Evidence** | W3C WoT Thing Descriptions + discovery; Matter uses BLE for commissioning, DNS-SD for operational discovery (Apple/Google/Amazon). |
| **Fix (positioning)** | "WoT/Matter for strangers who need one paid interaction — no home ecosystem, no commissioning ceremony." Payment + trust for *ad-hoc* encounters is the delta. |
| **Open question** | Can a CapMesh manifest embed or export a WoT Thing Description for interop? |

### H6. Apple/Google stablecoin story is hiring, not product

| | |
|---|---|
| **Hole** | Over-indexing on "Apple/Google stablecoin connections" as if live. |
| **Evidence (as of 2026-09)** | Apple financial-product strategy hire; Google Cloud Web3 roles; Samsung Wallet stablecoin plans (CoinDesk 2026-09-21). **No confirmed Apple/Google stablecoin product.** Live adjacent: Google Cloud + Solana **Pay.sh** (May 2026); Coinbase Apple Pay USDC onramp (Aug 2026); Stripe Link opened to agents; Visa USDC settlement on Solana. |
| **Implication** | Distribution will default to OS wallets. Do not build a consumer wallet. Be the protocol those wallets use to pay devices. |
| **Open question** | What does CapMesh look like if Phantom/Apple Wallet is the payer UI? |

### H7. Arcium: host-side privacy, not MCU privacy

| | |
|---|---|
| **Hole** | Assuming Arcium runs on or near the ESP32. |
| **Evidence** | Arcium = MPC network on Solana (mainnet alpha; 1M+ computations Jun 2026; cSPL; ZINC). SDK is TS/Rust host-side. |
| **Privacy hole in CapMesh** | Persistent device_id + payment graph ⇒ trackable presence (where you were, what you unlocked, when). DECISIONS.md Q1/Q5. |
| **Fix** | Arcium for: confidential spending policy, private reputation, sealed quotes, batch settlement privacy. Device uses rotating ephemeral IDs for discovery; stable ID only in settlement layer if needed. |
| **TUM fit** | TUM sponsors **both Solana and Arcium** — "confidential agent payments for physical capabilities" is a differentiated demo vs plain x402. |
| **Open question** | Does Arcium latency fit a 30h build, or is it a slide + one circuit? |

### H8. Other chains — relevance map

| Chain / stack | Relevance to CapMesh | Action |
|---|---|---|
| **Solana** | Payment Channels, x402-on-Solana, Arcium, Seeker, Colosseum | **Primary settlement** for TUM. |
| **Base** | x402 home; Coinbase agentic wallets (TEE); 119M+ x402 tx (Mar 2026) | Keep `PaymentVerifier` chain-agnostic; optional second adapter. |
| **Stripe Tempo / MPP** | Enterprise agent checkout (Deel, Ramp) | Competes for wallet UX, not BLE actuators. Watch only. |
| **IOTA Rebased** (May 2025) | Move+EVM, IoT branding, 50k TPS | Weak agent-payments distribution. Ignore for TUM. |
| **Ethereum L1** | Stablecoin depth, slow/expensive | Not for micropayments. |

**Rule:** never hard-code a chain into transport or capability layers.

### H9. Cold-start / adoption

| | |
|---|---|
| **Hole** | Nobody installs CapMesh firmware without an SDK story. |
| **Fix (bootstrap)** | You are both sides: ESP32 provider + laptop buyer; then laptop as second provider (plan §5). |
| **Fix (adoption hook)** | "Expose any HTTP API or GPIO as a paid capability in <10 lines." For TUM: HTTP/x402 first (internet devices), BLE second (proximity). |
| **Open question** | What is the MCP-equivalent distribution hook for physical devices? |

### H10. Liability and regulation (startup track)

| | |
|---|---|
| **Hole** | Agent-paid physical actuation with no liability model. |
| **Evidence** | GENIUS Act + EU AI Act (mid-2026) do not cover autonomous M2M liability (Keyrock May 2026). |
| **Fix** | Not a hackathon blocker. Record in DECISIONS.md: who is liable when an agent opens the wrong door; money-transmission adjacency for stablecoin facilitation. |

---

## 4. Competitive / prior-art map (Copilot)

| Project | Hackathon | Signal | Lesson for CapMesh |
|---|---|---|---|
| **SolBeacon** (`solbeacon`) | Breakout Apr 2025 | ESP32+BLE+iBeacon+MPC payments; no prize | Closest stack; lacks capability manifest layer. Differentiate on protocol, not "BLE payment." |
| **PlaiPin** (`plaipin`) | Cypherpunk Sep 2025, 3rd $15k | Wearable agent proximity tx + edge | Physical agent encounter is fundable. |
| **DeCharge** (`decharge`) | Renaissance Mar 2024, 2nd $20k, **accelerator C1** | EV charging DePIN | Vertical: paid physical actuator already won once. |
| **MCPay** (`mcpay`) | Cypherpunk Sep 2025, 1st Stablecoins $25k, **C4** | x402 for MCP tools | Same thesis, digital-only. Study their pricing/manifest UX. |
| **XAAM** (`xaam`) | Breakout Apr 2025 | Agent capability marketplace (MCP) | Capability discovery language exists; steal vocabulary. |
| **zk-IoT** (`zk-iot-1`) | Cypherpunk Sep 2025 | ZK sensor → conditional payout | Answers H1 if you ever leave demo land. |
| **ChipCasher** (`chipcasher`) | Radar Sep 2024 | Crypto vending | Retail actuator + payment. |
| **BlockMesh** (`blockmesh-network`) | Renaissance, 1st DePIN $30k, **C1** | Bandwidth marketplace | Verification-at-scale is the DePIN bottleneck. |
| **Unruggable** (`unruggable-2`) | Breakout, 3rd $15k, **C4** | Solana hardware wallet | Why not to put keys on cheap hardware casually. |
| **SOLYD** (`solyd`) | Breakout, HM DePIN | Seeker hardware rewards | Seeker as buyer/provider is live territory. |
| **Autonomous Vehicle Micropayments** | Cypherpunk Sep 2025 | Escrow M2M for vehicles | Escrow pattern for physical delivery. |
| **Corbits** (`corbits.dev`) | Cypherpunk, 2nd Infra $20k | x402 API dashboard | Merchant-side tooling matters for adoption. |

**Accelerator overlap:** none direct for "physical capability protocol." Adjacent: MCPay/Frames C4, DeCharge C1, BlockMesh C1, Unruggable C4.

**Open-source prior art outside Copilot:**
- `PlaiPin/solana-esp32-x402` — production-flavored x402 on ESP32-S3 (on-device keys; see H2).
- `torrey-xyz/sol` / Solduino — Solana lib for Arduino/ESP32.
- `solana-foundation/payment-channels` — settlement primitive to build on.
- Solana docs: agentic payments, x402 V2, payment channels.

---

## 5. Ecosystem facts that change outcomes

| Fact | Date | Why it matters |
|---|---|---|
| Solana Payment Channels mainnet + 1M pay/s bench | Sep 2026 | Solves H3; central to TUM demo. |
| x402 ~200M tx, ~$50B volume | Aug 2026 | Standard is real; align or die. |
| Pay.sh (Google Cloud × Solana) | May 2026 | Agent API payments are production-shaped. |
| Solana Subscriptions & Allowances mainnet | Jun 2026 | On-chain spending caps for agents — use for agent budgets, not per-blink. |
| Arcium 1M+ computations; ZINC top-3 Solana revenue | Jun 2026 | Privacy narrative is hot; TUM sponsors Arcium. |
| Stripe Link → agents; Gemini × Stripe agentic commerce | Apr 2026 | Big-tech agent checkout is moving; stay protocol-layer. |
| Apple/Google stablecoin **hiring** only (no product) | Sep 2026 | Do not bet the roadmap on OS wallets yet. |
| Keyrock: agent vol $73M / 176M tx (May 25–Apr 26) | May 2026 | Market real but tiny vs Visa $14.5T — early. |
| GENIUS / EU AI Act ignore M2M liability | 2026 | H10 open. |
| x402 security papers (5 attacks; free-riding) | 2026 | Spec your auth tests against these invariants. |
| TUM theme = Agentic Payments; Solana + Arcium sponsors | Oct 2026 | Direct fit; prize pool still forming (BSV €4k live). |
| Colosseum Agent Hackathon (agents built products) | Feb 2026 | Precedent for agentic framing; separate from TUM. |
| Frontier Hackathon Colosseum | Apr–May 2026 | Startup path if you continue past TUM. |

---

## 6. TUM 30-hour build brief

### Scope (cut ruthlessly)

```text
Must ship
  ESP32-C6 NimBLE GATT: manifest + invoke + receipt
  Host CLI: scan → manifest → authorize → invoke → receipt
  Nonce / expiry / replay tests green
  One non-LED capability OR solid LED story with sensor echo
  Host-side Solana devnet: Payment Channel or signed bounded auth
  Demo script + mermaid sequence diagram

Nice if time
  Same capability over Wi-Fi HTTP (x402-shaped headers)
  Second provider (laptop compute.sha256)
  Arcium: one confidential policy circuit OR clear architecture slide
  Seeker as payer (MWA) — only if hardware present

Do not start
  Custom on-chain program
  On-device wallet keys
  LLM planner
  Android app
  Production identity / full DID
```

### Story for judges (2 minutes)

1. Machines meet strangers; need: what can you do, price, trust, authorize, invoke, proof.  
2. Demo: discover → manifest → authorize → actuate → receipt → replay rejected.  
3. Payment: host opens channel / verifies auth; device never touches RPC or custody keys.  
4. Why Solana: Payment Channels + x402 + (optional) Arcium private policy.  
5. Why not just x402: x402 is HTTP; physical/proximity devices need a capability layer that *carries* the same payment objects over BLE.

### Risks during the event

| Risk | Mitigation |
|---|---|
| BLE flakiness on venue Wi-Fi/BT | BLE does not need venue Wi-Fi; bring USB serial fallback; test hotel night before. |
| Payment Channel integration too deep | Ship `Mock` + host-signed Ed25519 bounded auth; show channel diagram as Phase 5. |
| Judges: "why blockchain?" | Micropayment + multi-device trust without bilateral accounts; cite x402 volume + channels. |
| Judges: "Matter/WoT already exists" | Answer H5 positioning in first slide. |
| Scope creep to EV charging | Plan already bans optimizing for EV; one actuator class only. |

### Team positioning

- One person owns firmware (ESP-IDF NimBLE), one owns host/protocol + settlement, one owns demo/slides + Arcium optionality.  
- Bring: ESP32-C6, USB-C cable, laptop with IDF v6.1 preinstalled, devnet wallet, spare board.

---

## 7. Open questions (carry in DECISIONS.md)

1. Minimum receipt attestation for dispute (sensor echo vs dual sign vs PUF)?  
2. Session-key provisioning and rotation without a trusted display?  
3. Payment-channel voucher ↔ BLE invoke binding when device has no RPC?  
4. Shared JSON schema for BLE frames and HTTP/x402 bodies?  
5. Export path from CapMesh manifest ↔ W3C WoT Thing Description?  
6. Rotating discovery IDs vs stable settlement identity without global tracking?  
7. Offline / partitioned BLE mesh double-spend bounds (plan Q4)?  
8. Batch settle: N physical invocations → one channel settlement with per-invoke receipts?  
9. Agent spending policy: reuse Subscriptions & Allowances vs custom policy vs Arcium circuit?  
10. Liability model when agent-paid actuator causes harm (regulatory)?  
11. Adoption hook: what is "one-line integration" for a device vendor?  
12. If Apple/Google ship native stablecoin wallets, does CapMesh remain the device protocol or get absorbed?

---

## 8. Technologies that could change the conclusion

| Technology | Direction of change |
|---|---|
| Solana Payment Channels maturation | Makes per-use physical micropayments viable → strengthens CapMesh. |
| x402 batch / upto schemes + facilitators | Absorbs more of your payment layer → CapMesh must stay capability-only. |
| WoT 1.1 / Matter multi-admin | If they add paid interactions, positioning pressure → need payment delta proof. |
| Arcium cSPL + confidential compute cheap | Privacy differentiator for TUM and beyond. |
| Base agentic wallets + TEE | Settlement portability test for `PaymentVerifier`. |
| Apple/Google actual stablecoin product | Distribution shift; protocol must be wallet-agnostic. |
| zk light clients / zk-IoT proofs on MCU-class HW | Fixes H1 without trusted sensors — currently unrealistic for ESP32 demo. |
| ESP32-C6 / later secure elements, PSA certified parts | Softens H2 but does not eliminate custody design. |
| Stripe MPP / Visa TAP / Google AP2 winning standards | Pressure to map CapMesh auth to their intent objects too. |
| Failure of x402 (security papers → fragmentation) | Opportunity for a stricter capability+payment envelope — still do not invent crypto. |

---

## 9. Quick reference links

- Plan: `ORIGINAL_PLAN.md` · Architecture: `docs/ARCHITECTURE.md` · Decisions: `docs/DECISIONS.md` · Progress: `TODO.md`  
- Solana payment channels: https://github.com/solana-foundation/payment-channels  
- Solana agentic payments / x402: https://solana.com/docs/payments/agentic-payments  
- Payment Channels announce (2026-09): https://solana.com/news/payment-channels-1-million-payments-per-second  
- x402: https://www.x402.org/ · whitepaper + FAQ  
- x402 attacks: arXiv 2605.11781, arXiv 2605.30998  
- Arcium: https://www.arcium.com/build · docs.arcium.com  
- ESP-IDF security: flash encryption + secure boot guides (docs.espressif.com)  
- WoT Discovery: https://www.w3.org/TR/2020/WD-wot-discovery-20201124  
- TUM: https://hackathon.tum-blockchain.com/ · https://tum.devfolio.co/  
- Colosseum Copilot project samples: solbeacon, plaipin, decharge, mcpay, xaam, zk-iot-1 (colosseum.com/projects/explore/…)

---

## 10. Change log

| Date | Change |
|---|---|
| 2026-09-24 | Initial compilation from Copilot + web research; TUM-first framing. |
