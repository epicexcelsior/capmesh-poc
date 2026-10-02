import express from 'express';
import { spawn } from 'node:child_process';
import { randomUUID, createHash } from 'node:crypto';
import { isDeepStrictEqual } from 'node:util';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { HTTPFacilitatorClient, x402ResourceServer } from '@x402/core/server';
import { decodePaymentSignatureHeader, encodePaymentRequiredHeader, encodePaymentResponseHeader, encodePaymentSignatureHeader } from '@x402/core/http';
import { ExactSvmScheme } from '@x402/svm/exact/server';
import { getTransactionDecoder } from '@solana/kit';
import { PurchaseStore } from './store.js';

export const NETWORK = 'solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1';
export const USDC = '4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU';
export const PAY_TO = 'CaQAKBcwf7G5vXeu2RNuNGJafnJ8724Uj4wv9ivfxfQA';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

export async function createPaymentServer(facilitator) {
  const server = new x402ResourceServer(facilitator).register(NETWORK, new ExactSvmScheme());
  await server.initialize();
  if (!server.getSupportedKind(2, NETWORK, 'exact')) throw new Error('Facilitator must support x402 V2 exact on Solana Devnet');
  return server;
}
export function observeHardware(purchase) {
  return new Promise((resolvePromise, rejectPromise) => {
    const child = spawn('uv', ['run', '--project', 'host', 'python', 'gateway/bridge_call.py'], {
      cwd: root, stdio: ['pipe', 'pipe', 'pipe'],
    });
    let output = '';
    let error = '';
    const timer = setTimeout(() => child.kill('SIGKILL'), 30000);
    child.stdout.on('data', chunk => { output += chunk; if (output.length > 32768) child.kill('SIGKILL'); });
    child.stderr.on('data', chunk => { error = (error + chunk).slice(-4096); });
    child.on('error', err => { clearTimeout(timer); rejectPromise(err); });
    child.on('close', code => {
      clearTimeout(timer);
      if (code !== 0) return rejectPromise(new Error(error.trim() || 'Observation bridge failed'));
      try { resolvePromise(JSON.parse(output)); } catch (err) { rejectPromise(err); }
    });
    child.stdin.on('error', () => {}); // The close/error handlers report an early bridge exit.
    child.stdin.end(JSON.stringify(purchase));
  });
}
export async function createGateway({ paymentServer, store, observe = observeHardware,
    origin = 'http://127.0.0.1:4021', payTo = PAY_TO, simulated = false,
    sensor = simulated ? 'simulated-contact' : 'gpio9-contact', assetsRoot = root } = {}) {
  const requirements = await paymentServer.buildPaymentRequirements({
    scheme: 'exact', price: { asset: USDC, amount: '1000' }, network: NETWORK, payTo,
  });
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: '2kb' }));
  app.use((_req, res, next) => { res.set('Cache-Control', 'no-store'); next(); });
  // Check only these relative asset names for dotfiles, not the trusted checkout path.
  for (const [route, file] of Object.entries({
    '/': 'docs/overview.html', '/proof': 'docs/proof.html', '/proof.js': 'docs/proof.js',
    '/settlement.mjs': 'docs/settlement.mjs',
    '/receipt-keys.json': 'host/capmesh/protocol/receipt_keys.json',
    '/evidence/device-signed-purchase.json': 'docs/evidence/device-signed-purchase.json',
    '/evidence/device-signed-contact-states.json': 'docs/evidence/device-signed-contact-states.json',
    '/assets/fieldproof-signed-receipt.webm': 'docs/assets/fieldproof-signed-receipt.webm',
    '/assets/fieldproof-demo.webm': 'docs/assets/fieldproof-demo.webm',
    '/assets/fieldproof-walkthrough.webm': 'docs/assets/fieldproof-walkthrough.webm',
    '/assets/fieldproof-submission.webm': 'docs/assets/fieldproof-submission.webm',
    '/evidence/devnet-purchase.json': 'docs/evidence/devnet-purchase.json',
    '/evidence/contact-states.json': 'docs/evidence/contact-states.json',
  })) app.get(route, (_req, res) => res.sendFile(file, { root: assetsRoot }));
  app.get('/health', (_req, res) => res.json({ ready: true, network: NETWORK, payTo,
    capability: 'state.observe', location: 'demo-gate', price_base_units: '1000',
    sensor, receipt_identity: sensor === 'gpio9-contact' ? 'pinned-device-p256' : 'public-demo-hmac',
    mode: simulated ? 'simulated settlement; no funds moved' : 'Solana Devnet; physical contact demo' }));
  app.get('/demand', (_req, res) => res.json(store.demand()));
  app.get('/manifest', (_req, res) => res.json({ product: 'FieldProof', metric: 'gate.closed',
    location: 'demo-gate', sensor,
    price: '0.001 USDC', confidence: null, create_request: '/requests' }));
  app.post('/requests', (req, res) => {
    const { nonce, location = 'demo-gate', max_age_seconds = 10 } = req.body || {};
    if (!Number.isInteger(nonce) || nonce < 1 || nonce > 0x7fffffff || location !== 'demo-gate' ||
        !Number.isInteger(max_age_seconds) || max_age_seconds < 1 || max_age_seconds > 30) {
      return res.status(400).json({ error: 'Use a positive 32-bit nonce, demo-gate, and freshness from 1 to 30 seconds' });
    }
    const purchase = { id: randomUUID().replaceAll('-', '').slice(0, 16), nonce, location,
      max_age_seconds, expires_at: Math.floor(Date.now() / 1000) + 120 };
    try { store.create(purchase); }
    catch (error) {
      if (String(error.message).includes('UNIQUE')) return res.status(409).json({ error: 'Nonce already belongs to a purchase' });
      throw error;
    }
    res.status(201).json({ ...purchase, observe_url: `${origin}/observe/${purchase.id}` });
  });
  app.get('/observe/:id', async (req, res) => {
    const purchase = store.get(req.params.id);
    if (!purchase) return res.status(404).json({ error: 'Unknown observation purchase' });
    const resource = { url: `${origin}/observe/${purchase.id}`, description: 'Fresh gate contact evidence at demo-gate', mimeType: 'application/json' };
    const challenge = async error => {
      const required = await paymentServer.createPaymentRequiredResponse(requirements, resource, error);
      res.set('PAYMENT-REQUIRED', encodePaymentRequiredHeader(required));
      return res.status(402).json(required);
    };
    const header = req.get('PAYMENT-SIGNATURE');
    if (!header) return challenge();
    let payload;
    try { payload = decodePaymentSignatureHeader(header); } catch { return challenge('Malformed payment payload'); }
    if (payload.x402Version !== 2 || payload.resource?.url !== resource.url ||
        !isDeepStrictEqual(payload.accepted, requirements[0]) ||
        typeof payload.payload?.transaction !== 'string' || payload.payload.transaction.length > 12000) {
      return challenge('Payment does not match this resource and its requirements');
    }
    let proofHash;
    try {
      const bytes = Buffer.from(payload.payload.transaction, 'base64');
      // The facilitator replaces its signature. Deduplicate the signed message, which defines the payment.
      const message = simulated && bytes.toString('utf8').startsWith('FIELDPROOF-SIM:')
        ? bytes : getTransactionDecoder().decode(bytes).messageBytes;
      proofHash = createHash('sha256').update(message).digest('hex');
    } catch { return challenge('Malformed Solana transaction'); }
    if (purchase.state !== 'quoted') {
      if (purchase.proof_hash !== proofHash) return res.status(409).json({ error: 'Purchase already uses another payment' });
      if (purchase.settlement) res.set('PAYMENT-RESPONSE', encodePaymentResponseHeader(JSON.parse(purchase.settlement)));
      if (purchase.state === 'delivered') {
        const cached = JSON.parse(purchase.result);
        const measured = cached.receipt?.completed_at;
        const now = Math.floor(Date.now() / 1000);
        const fresh = Number.isInteger(measured) && now - measured <= purchase.max_age_seconds && measured <= now + 2;
        return res.json({ ...cached, evidence_cached: true, decision: {
          ...cached.decision, age_seconds: Number.isInteger(measured) ? Math.max(0, now - measured) : null,
          ...(fresh ? {} : { decision: 'WAIT', reason: 'Cached evidence expired. Create a new observation request.' }),
        } });
      }
      return res.status(409).json({ error: purchase.error || 'Purchase requires settlement or delivery review', state: purchase.state });
    }
    if (Math.floor(Date.now() / 1000) > purchase.expires_at) return res.status(410).json({ error: 'Purchase expired. Create a new request.' });
    let verified;
    try { verified = await paymentServer.verifyPayment(payload, requirements[0]); }
    catch { return res.status(503).json({ error: 'Payment verification unavailable. No measurement occurred.' }); }
    if (!verified.isValid) return challenge('Payment verification failed');
    if (!store.reserve(purchase.id, proofHash)) return res.status(409).json({ error: 'Payment or purchase is already in progress or consumed' });
    let settlement;
    try {
      settlement = await paymentServer.settlePayment(payload, requirements[0]);
      if (!settlement.success) {
        store.finish(purchase.id, 'payment_failed', { settlement, error: 'Settlement failed. No measurement occurred.' });
        return challenge('Settlement failed');
      }
      if (settlement.network !== NETWORK || !settlement.transaction) throw new Error('Invalid settlement response');
    } catch {
      store.finish(purchase.id, 'settlement_unknown', { error: 'Settlement outcome is unknown. Review before retrying.' });
      return res.status(503).json({ error: 'Settlement outcome is unknown. No measurement occurred. Keep the purchase ID.', purchase_id: purchase.id });
    }
    store.finish(purchase.id, 'measuring', { settlement });
    res.set('PAYMENT-RESPONSE', encodePaymentResponseHeader(settlement));
    try {
      const evidence = await observe({ ...purchase, simulated });
      const result = { ...evidence, purchase_id: purchase.id,
        payment_mode: simulated ? 'simulated; no funds moved' : 'Solana Devnet USDC', settlement, evidence_cached: false };
      store.finish(purchase.id, 'delivered', { settlement, result });
      return res.json(result);
    } catch (error) {
      console.error('Observation delivery failed:', error.name);
      store.finish(purchase.id, 'delivery_failed', { settlement, error: 'Payment settled. Evidence delivery failed. Refund review required.' });
      return res.status(503).json({ error: 'Payment settled. Evidence delivery failed. Keep the purchase ID for refund review.', purchase_id: purchase.id });
    }
  });
  if (simulated) {
    app.post('/simulate/:id', async (req, res) => {
      const purchase = store.get(req.params.id);
      if (!purchase) return res.status(404).json({ error: 'Unknown simulation purchase' });
      const resource = { url: `${origin}/observe/${purchase.id}` };
      const transaction = Buffer.from(`FIELDPROOF-SIM:${purchase.id}`).toString('base64');
      const payload = { x402Version: 2, resource, accepted: requirements[0], payload: { transaction } };
      try {
        const response = await fetch(resource.url, { headers: { 'PAYMENT-SIGNATURE': encodePaymentSignatureHeader(payload) }, signal: AbortSignal.timeout(35000) });
        const body = await response.json();
        res.status(response.status).json(body);
      } catch { res.status(503).json({ error: 'Simulation request failed. Check the gateway process.' }); }
    });
  }
  app.use((error, _req, res, _next) => {
    res.status(error.type === 'entity.parse.failed' ? 400 : 500).json({ error: 'The request failed. Check the local gateway log.' });
  });
  return app;
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.CAPMESH_GATEWAY_PORT || 4021);
  const paymentServer = await createPaymentServer(new HTTPFacilitatorClient({ url: process.env.FACILITATOR_URL || 'https://x402.org/facilitator' }));
  const store = new PurchaseStore(resolve(root, '.local/purchases.sqlite'));
  const app = await createGateway({ paymentServer, store, origin: `http://127.0.0.1:${port}`, payTo: process.env.SOLANA_PAY_TO || PAY_TO });
  app.listen(port, '127.0.0.1', () => console.log(`FieldProof gateway on http://127.0.0.1:${port}`));
}
