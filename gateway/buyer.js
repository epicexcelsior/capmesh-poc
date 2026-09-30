import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHmac, randomInt, timingSafeEqual } from 'node:crypto';
import { createKeyPairSignerFromBytes } from '@solana/kit';
import { x402Client, wrapFetchWithPayment } from '@x402/fetch';
import { ExactSvmScheme } from '@x402/svm/exact/client';
import { decodePaymentResponseHeader } from '@x402/core/http';
import { NETWORK, USDC, PAY_TO } from './server.js';

export function allowedOffers(offers, payTo = PAY_TO) {
  return offers.filter(offer => offer.scheme === 'exact' && offer.network === NETWORK && offer.asset === USDC &&
    offer.payTo === payTo && /^\d+$/.test(offer.amount) && BigInt(offer.amount) > 0n && BigInt(offer.amount) <= 1000n);
}

export function checkEvidence(body, purchase, now = Math.floor(Date.now() / 1000)) {
  const r = body.receipt, s = r?.result;
  if (!r || r.protocol !== 'capmesh/0.1' || r.status !== 'success' || r.provider !== 'esp32-c6-96a2' ||
      r.capability !== 'state.observe' || r.request_id !== purchase.id || r.nonce !== purchase.nonce ||
      r.parameters?.location !== 'demo-gate' || s?.metric !== 'gate.closed' || s.sensor !== 'gpio9-contact' ||
      typeof s.closed !== 'boolean' || s.total_samples !== 5 || s.stable_samples !== 5 ||
      !Number.isInteger(r.started_at) || !Number.isInteger(r.completed_at) || r.started_at > r.completed_at ||
      r.started_at < purchase.created_at - 2 || r.completed_at > now + 2 || now - r.completed_at > purchase.max_age_seconds) {
    throw new Error('Evidence does not satisfy the buyer challenge, contact contract, or freshness limit');
  }
  const message = ['fieldproof-observation-v1', r.protocol, r.request_id, r.provider, r.capability,
    r.parameters.location, r.nonce, s.metric, s.sensor, Number(s.closed), s.stable_samples, s.total_samples,
    r.started_at, r.completed_at].join('|');
  const expected = createHmac('sha256', 'capmesh-secret-key-2026').update(message).digest();
  if (!/^v2:[0-9a-f]{64}$/.test(r.receipt_signature || '') ||
      !timingSafeEqual(expected, Buffer.from(r.receipt_signature.slice(3), 'hex'))) throw new Error('Receipt authentication failed');
  return { decision: s.closed ? 'WAIT' : 'DISPATCH', evidence_age_seconds: Math.max(0, now - r.completed_at) };
}

export async function buyObservation(signer, origin = 'http://127.0.0.1:4021') {
  const url = new URL(origin);
  if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1') throw new Error('The prototype buyer accepts only a loopback gateway');
  const nonce = randomInt(1, 0x7fffffff);
  const createdAt = Math.floor(Date.now() / 1000);
  const created = await fetch(new URL('/requests', url), { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nonce }), signal: AbortSignal.timeout(10000) });
  if (created.status !== 201) throw new Error(`Request creation failed: HTTP ${created.status}`);
  const purchase = { ...await created.json(), created_at: createdAt };
  const expectedUrl = new URL(`/observe/${purchase.id}`, url).href;
  if (purchase.nonce !== nonce || purchase.observe_url !== expectedUrl) throw new Error('Gateway changed the buyer challenge or endpoint');
  const client = new x402Client();
  client.registerPolicy((_version, offers) => allowedOffers(offers));
  client.register(NETWORK, new ExactSvmScheme(signer));
  const paidFetch = wrapFetchWithPayment(fetch, client);
  const response = await paidFetch(expectedUrl, { signal: AbortSignal.timeout(45000) });
  if (!response.ok) throw new Error(`Purchase failed: HTTP ${response.status}. Keep purchase ID ${purchase.id} for review.`);
  const settlement = decodePaymentResponseHeader(response.headers.get('PAYMENT-RESPONSE') || '');
  if (settlement.success !== true || settlement.network !== NETWORK || !settlement.transaction) throw new Error('No successful Devnet settlement response');
  const body = await response.json();
  return { purchase_id: purchase.id, settlement, ...checkEvidence(body, purchase), receipt: body.receipt };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const path = process.argv[2];
  if (!path) throw new Error('Usage: node buyer.js /path/to/disposable.keypair.json [http://127.0.0.1:4021]');
  const bytes = JSON.parse(await readFile(path, 'utf8'));
  if (!Array.isArray(bytes) || bytes.length !== 64 || !bytes.every(v => Number.isInteger(v) && v >= 0 && v <= 255)) throw new Error('Use a 64-byte Solana CLI keypair file');
  const signer = await createKeyPairSignerFromBytes(Uint8Array.from(bytes));
  console.log(JSON.stringify(await buyObservation(signer, process.argv[3]), null, 2));
}
