import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac, generateKeyPairSync, sign } from 'node:crypto';
import { allowedOffers, buyObservation, checkEvidence } from '../buyer.js';
import { NETWORK, USDC, PAY_TO } from '../server.js';
import { createServer } from 'node:http';
import { once } from 'node:events';
import { generateKeyPairSigner, getTransactionDecoder, getBase64Encoder, getAddressEncoder } from '@solana/kit';
import { ExactSvmScheme } from '@x402/svm/exact/client';
import { encodePaymentResponseHeader } from '@x402/core/http';

const testPin = generateKeyPairSync('ec', { namedCurve: 'prime256v1' }).publicKey
  .export({ format: 'der', type: 'spki' }).subarray(-65).toString('hex');

test('buyer rejects wrong chain, asset, recipient, amount, and payment scheme', () => {
  const offer = { scheme: 'exact', network: NETWORK, asset: USDC, payTo: PAY_TO, amount: '1000' };
  assert.deepEqual(allowedOffers([offer]), [offer]);
  for (const change of [{ network: 'solana:mainnet' }, { asset: 'fake' }, { payTo: 'other' },
    { amount: '1001' }, { amount: '-1' }, { amount: '0' }, { amount: 'NaN' }, { scheme: 'upto' }]) {
    assert.deepEqual(allowedOffers([{ ...offer, ...change }]), []);
  }
});
test('buyer derives the decision from authenticated fresh contact evidence', () => {
  const r = { protocol: 'capmesh/0.1', status: 'success', request_id: 'purchase1', provider: 'esp32-c6-96a2',
    capability: 'state.observe', nonce: 123, parameters: { location: 'demo-gate' },
    result: { metric: 'gate.closed', sensor: 'gpio9-contact', closed: false, stable_samples: 5, total_samples: 5 },
    started_at: 100, completed_at: 100 };
  const message = 'fieldproof-observation-v1|capmesh/0.1|purchase1|esp32-c6-96a2|state.observe|demo-gate|123|gate.closed|gpio9-contact|0|5|5|100|100';
  const keys = generateKeyPairSync('ec', { namedCurve: 'prime256v1' });
  const publicKey = keys.publicKey.export({ format: 'der', type: 'spki' }).subarray(-65).toString('hex');
  r.receipt_signature = 'v3:' + sign('sha256', Buffer.from(message), { key: keys.privateKey, dsaEncoding: 'ieee-p1363' }).toString('base64');
  const purchase = { id: 'purchase1', nonce: 123, max_age_seconds: 10, created_at: 100 };
  assert.equal(checkEvidence({ receipt: r, decision: { decision: 'FAKE' } }, purchase, 100, publicKey).decision, 'DISPATCH');
  assert.throws(() => checkEvidence({ receipt: r }, purchase, 111, publicKey), /freshness/);
  assert.throws(() => checkEvidence({ receipt: r }, { ...purchase, nonce: 124 }, 100, publicKey), /challenge/);
  assert.throws(() => checkEvidence({ receipt: { ...r, result: { ...r.result, closed: true } } }, purchase, 100, publicKey), /authentication/);
  const otherKey = generateKeyPairSync('ec', { namedCurve: 'prime256v1' }).publicKey.export({ format: 'der', type: 'spki' }).subarray(-65).toString('hex');
  assert.throws(() => checkEvidence({ receipt: r }, purchase, 100, otherKey), /authentication/);
  const oldSignature = 'v2:' + createHmac('sha256', 'capmesh-secret-key-2026').update(message).digest('hex');
  for (const receipt_signature of [oldSignature, r.receipt_signature + '=', 'v3:AAAA']) {
    assert.throws(() => checkEvidence({ receipt: { ...r, receipt_signature } }, purchase, 100, publicKey), /authentication/);
  }
  assert.throws(() => checkEvidence({ receipt: r }, purchase, 100, ''), /provisioned/);
});

test('buyer retains the purchase ID when the connection fails during payment', async t => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (url, options) => {
    if (String(url).endsWith('/requests')) {
      const { nonce } = JSON.parse(options.body);
      return Response.json({ id: '0123456789abcdef', nonce, location: 'demo-gate', max_age_seconds: 10,
        observe_url: 'http://127.0.0.1:4021/observe/0123456789abcdef' }, { status: 201 });
    }
    throw new TypeError('Connection lost');
  };
  await assert.rejects(buyObservation(await generateKeyPairSigner(), undefined, { receiptPublicKey: testPin }), /purchase ID 0123456789abcdef/);
});

test('buyer retains the purchase ID when settled evidence delivery is truncated', async t => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (url, options) => {
    if (String(url).endsWith('/requests')) {
      const { nonce } = JSON.parse(options.body);
      return Response.json({ id: '0123456789abcdef', nonce, location: 'demo-gate', max_age_seconds: 10,
        observe_url: 'http://127.0.0.1:4021/observe/0123456789abcdef' }, { status: 201 });
    }
    const body = new ReadableStream({ start(controller) { controller.error(new TypeError('Delivery truncated')); } });
    return new Response(body, { headers: { 'PAYMENT-RESPONSE': encodePaymentResponseHeader({
      success: true, network: NETWORK, transaction: 'TEST-SETTLEMENT', payer: PAY_TO,
    }) } });
  };
  await assert.rejects(buyObservation(await generateKeyPairSigner(), undefined, { receiptPublicKey: testPin }), /purchase ID 0123456789abcdef/);
});

test('buyer refuses a gateway that extends its freshness limit before payment', async t => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  let calls = 0;
  globalThis.fetch = async (_url, options) => {
    calls += 1;
    const { nonce } = JSON.parse(options.body);
    return Response.json({ id: '0123456789abcdef', nonce, location: 'demo-gate', max_age_seconds: 3600,
      observe_url: 'http://127.0.0.1:4021/observe/0123456789abcdef' }, { status: 201 });
  };
  await assert.rejects(buyObservation(await generateKeyPairSigner(), undefined, { receiptPublicKey: testPin }), /freshness/);
  assert.equal(calls, 1);
});

test('buyer refuses spending without a provisioned device key', async t => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  let calls = 0;
  globalThis.fetch = async () => { calls++; throw new Error('Unexpected network request'); };
  await assert.rejects(buyObservation(await generateKeyPairSigner(), undefined, { receiptPublicKey: '' }), /provisioned/);
  assert.equal(calls, 0);
});

test('the pinned SDK stack builds a verifiable buyer signature without a live chain', async t => {
  const mint = Buffer.alloc(82);
  mint[44] = 6; // SPL Mint decimals.
  mint[45] = 1; // Initialized Mint.
  const rpc = createServer(async (req, res) => {
    let raw = '';
    for await (const chunk of req) raw += chunk;
    const message = JSON.parse(raw);
    assert.equal(message.method, 'getAccountInfo');
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ jsonrpc: '2.0', id: message.id, result: { context: { slot: 1 }, value: {
      data: [mint.toString('base64'), 'base64'], executable: false, lamports: 1,
      owner: 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', rentEpoch: 0, space: 82,
    } } }));
  });
  rpc.listen(0, '127.0.0.1');
  await once(rpc, 'listening');
  t.after(async () => { rpc.closeAllConnections(); await new Promise(resolve => rpc.close(resolve)); });
  const signer = await generateKeyPairSigner();
  const scheme = new ExactSvmScheme(signer, { rpcUrl: `http://127.0.0.1:${rpc.address().port}` });
  const payment = await scheme.createPaymentPayload(2, { scheme: 'exact', network: NETWORK, asset: USDC,
    payTo: PAY_TO, amount: '1000', maxTimeoutSeconds: 120,
    extra: { feePayer: PAY_TO, recentBlockhash: '11111111111111111111111111111111', lastValidBlockHeight: '100' } });
  const tx = getTransactionDecoder().decode(getBase64Encoder().encode(payment.payload.transaction));
  const key = await crypto.subtle.importKey('raw', getAddressEncoder().encode(signer.address), 'Ed25519', false, ['verify']);
  assert.equal(await crypto.subtle.verify('Ed25519', key, tx.signatures[signer.address], tx.messageBytes), true);
  const altered = Uint8Array.from(tx.messageBytes);
  altered[altered.length - 1] ^= 1;
  assert.equal(await crypto.subtle.verify('Ed25519', key, tx.signatures[signer.address], altered), false);
});
