import { readFile } from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createPublicKey, randomInt, verify } from 'node:crypto';
import { createKeyPairSignerFromBytes } from '@solana/kit';
import { x402Client, wrapFetchWithPayment } from '@x402/fetch';
import { ExactSvmScheme } from '@x402/svm/exact/client';
import { decodePaymentResponseHeader } from '@x402/core/http';
import { NETWORK, USDC, PAY_TO } from './server.js';

const receiptPins = JSON.parse(readFileSync(new URL('../host/capmesh/protocol/receipt_keys.json', import.meta.url), 'utf8'));
if (receiptPins.algorithm !== 'ecdsa-p256-sha256') throw new Error('Unsupported provisioned receipt algorithm');
const provisionedKey = receiptPins.providers['esp32-c6-96a2'];

function receiptKey(sec1Hex) {
  if (!/^04[0-9a-f]{128}$/.test(sec1Hex || '')) throw new Error('Buyer has no provisioned P-256 receipt key');
  // SPKI: id-ecPublicKey, prime256v1, uncompressed SEC1 point.
  return createPublicKey({ key: Buffer.from('3059301306072a8648ce3d020106082a8648ce3d030107034200' + sec1Hex, 'hex'),
    format: 'der', type: 'spki' });
}

export function allowedOffers(offers, payTo = PAY_TO) {
  return offers.filter(offer => offer.scheme === 'exact' && offer.network === NETWORK && offer.asset === USDC &&
    offer.payTo === payTo && /^\d+$/.test(offer.amount) && BigInt(offer.amount) > 0n && BigInt(offer.amount) <= 1000n);
}

export function checkEvidence(body, purchase, now = Math.floor(Date.now() / 1000), publicKey = provisionedKey) {
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
  const key = receiptKey(publicKey);
  const encoded = r.receipt_signature?.startsWith('v3:') ? r.receipt_signature.slice(3) : '';
  const signature = Buffer.from(encoded, 'base64');
  if (signature.length !== 64 || signature.toString('base64') !== encoded ||
      !verify('sha256', Buffer.from(message), { key, dsaEncoding: 'ieee-p1363' }, signature)) {
    throw new Error('Receipt authentication failed');
  }
  return { decision: s.closed ? 'WAIT' : 'DISPATCH', evidence_age_seconds: Math.max(0, now - r.completed_at),
    receipt_identity: 'pinned-device-p256' };
}

export async function buyObservation(signer, origin = 'http://127.0.0.1:4021', { receiptPublicKey = provisionedKey } = {}) {
  receiptKey(receiptPublicKey); // Buyer configuration, never a key from the gateway response.
  const url = new URL(origin);
  if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1') throw new Error('The prototype buyer accepts only a loopback gateway');
  const nonce = randomInt(1, 0x7fffffff);
  const createdAt = Math.floor(Date.now() / 1000);
  const created = await fetch(new URL('/requests', url), { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nonce, location: 'demo-gate', max_age_seconds: 10 }), signal: AbortSignal.timeout(10000) });
  if (created.status !== 201) throw new Error(`Request creation failed: HTTP ${created.status}`);
  const purchase = { ...await created.json(), created_at: createdAt };
  const expectedUrl = new URL(`/observe/${purchase.id}`, url).href;
  if (purchase.nonce !== nonce || purchase.observe_url !== expectedUrl ||
      purchase.location !== 'demo-gate' || purchase.max_age_seconds !== 10) {
    throw new Error('Gateway changed the buyer challenge, location, freshness limit, or endpoint');
  }
  const client = new x402Client();
  client.registerPolicy((_version, offers) => allowedOffers(offers));
  client.register(NETWORK, new ExactSvmScheme(signer));
  const paidFetch = wrapFetchWithPayment(fetch, client);
  let response;
  try { response = await paidFetch(expectedUrl, { signal: AbortSignal.timeout(45000) }); }
  catch { throw new Error(`Payment outcome is unknown. Keep purchase ID ${purchase.id} for review before another payment.`); }
  if (!response.ok) throw new Error(`Purchase failed: HTTP ${response.status}. Keep purchase ID ${purchase.id} for review.`);
  try {
    const settlement = decodePaymentResponseHeader(response.headers.get('PAYMENT-RESPONSE') || '');
    if (settlement.success !== true || settlement.network !== NETWORK || !settlement.transaction) throw new Error('No successful Devnet settlement response');
    const body = await response.json();
    return { purchase_id: purchase.id, challenge: { id: purchase.id, nonce, created_at: createdAt,
      location: purchase.location, max_age_seconds: purchase.max_age_seconds }, settlement,
      ...checkEvidence(body, purchase, Math.floor(Date.now() / 1000), receiptPublicKey), receipt: body.receipt };
  } catch { throw new Error(`Payment response or evidence failed verification. Keep purchase ID ${purchase.id} for review before another payment.`); }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const path = process.argv[2];
  if (!path) throw new Error('Usage: node buyer.js /path/to/disposable.keypair.json [http://127.0.0.1:4021]');
  const bytes = JSON.parse(await readFile(path, 'utf8'));
  if (!Array.isArray(bytes) || bytes.length !== 64 || !bytes.every(v => Number.isInteger(v) && v >= 0 && v <= 255)) throw new Error('Use a 64-byte Solana CLI keypair file');
  const signer = await createKeyPairSignerFromBytes(Uint8Array.from(bytes));
  console.log(JSON.stringify(await buyObservation(signer, process.argv[3]), null, 2));
}
