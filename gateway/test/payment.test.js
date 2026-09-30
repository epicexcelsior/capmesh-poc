import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { mkdtempSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createGateway, createPaymentServer, NETWORK, PAY_TO, USDC } from '../server.js';
import { PurchaseStore } from '../store.js';
import { decodePaymentRequiredHeader, encodePaymentSignatureHeader } from '@x402/core/http';

async function fixture(t, { valid = true, settled = true, unknown = false, deliveryFails = false, path = ':memory:' } = {}) {
  const events = [];
  const facilitator = {
    getSupported: async () => ({ kinds: [{ x402Version: 2, scheme: 'exact', network: NETWORK, extra: { feePayer: PAY_TO } }], extensions: [], signers: {} }),
    verify: async () => { events.push('verify'); return { isValid: valid, payer: PAY_TO }; },
    settle: async () => { events.push('settle'); if (unknown) throw new Error('timeout');
      return { success: settled, transaction: 'SIMULATED-TRANSACTION', network: NETWORK, payer: PAY_TO }; },
  };
  const paymentServer = await createPaymentServer(facilitator);
  const store = new PurchaseStore(path);
  const app = await createGateway({ paymentServer, store, simulated: true, observe: async () => {
    events.push('measure');
    if (deliveryFails) throw new Error('device unavailable');
    return { decision: { decision: 'DISPATCH', evidence_mode: 'simulated' }, receipt: { simulated: true, completed_at: Math.floor(Date.now() / 1000) } };
  } });
  const server = app.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const url = `http://127.0.0.1:${server.address().port}`;
  t.after(async () => { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); store.close(); });
  async function purchase(nonce = 123) {
    const created = await fetch(`${url}/requests`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nonce }) });
    assert.equal(created.status, 201);
    const request = await created.json();
    const route = `${url}/observe/${request.id}`;
    const response = await fetch(route);
    assert.equal(response.status, 402);
    const challenge = decodePaymentRequiredHeader(response.headers.get('PAYMENT-REQUIRED'));
    return { route, request, payload: { x402Version: 2, accepted: challenge.accepts[0], resource: challenge.resource,
      payload: { transaction: Buffer.from('simulated-signed-transaction').toString('base64') } }, challenge };
  }
  const pay = (route, payload) => fetch(route, { headers: { 'PAYMENT-SIGNATURE': encodePaymentSignatureHeader(payload) } });
  return { url, events, store, purchase, pay };
}

test('unpaid and malformed payments never measure', async t => {
  const f = await fixture(t);
  const p = await f.purchase();
  assert.equal(p.challenge.accepts[0].network, NETWORK);
  assert.equal(p.challenge.accepts[0].asset, USDC);
  assert.equal(p.challenge.accepts[0].amount, '1000');
  assert.deepEqual(f.events, []);
  const bad = await fetch(p.route, { headers: { 'PAYMENT-SIGNATURE': 'garbage' } });
  assert.equal(bad.status, 402);
  assert.deepEqual(f.events, []);
});
test('wrong amount and resource fail before verification', async t => {
  const f = await fixture(t);
  const p = await f.purchase();
  for (const payload of [{ ...p.payload, accepted: { ...p.payload.accepted, amount: '1' } },
                         { ...p.payload, resource: { ...p.payload.resource, url: 'https://other.invalid/' } }]) {
    assert.equal((await f.pay(p.route, payload)).status, 402);
  }
  assert.deepEqual(f.events, []);
});
test('invalid facilitator verification never settles or measures', async t => {
  const f = await fixture(t, { valid: false });
  const p = await f.purchase();
  assert.equal((await f.pay(p.route, p.payload)).status, 402);
  assert.deepEqual(f.events, ['verify']);
});
test('settlement precedes measurement and retry returns the original evidence', async t => {
  const f = await fixture(t);
  const p = await f.purchase();
  const paid = await f.pay(p.route, p.payload);
  assert.equal(paid.status, 200);
  assert.ok(paid.headers.get('PAYMENT-RESPONSE'));
  assert.equal((await paid.json()).payment_mode, 'simulated; no funds moved');
  assert.deepEqual(f.events, ['verify', 'settle', 'measure']);
  const retry = await f.pay(p.route, p.payload);
  assert.equal(retry.status, 200);
  assert.equal((await retry.json()).evidence_cached, true);
  assert.deepEqual(f.events, ['verify', 'settle', 'measure']);
});
test('a second purchase cannot reuse the transaction by rewriting resource JSON', async t => {
  const f = await fixture(t);
  const first = await f.purchase();
  assert.equal((await f.pay(first.route, first.payload)).status, 200);
  const second = await f.purchase(456);
  assert.equal((await f.pay(second.route, second.payload)).status, 409);
  assert.equal(f.events.filter(e => e === 'settle').length, 1);
  assert.equal(f.events.filter(e => e === 'measure').length, 1);
});
test('an expired cached receipt returns WAIT without repeating payment or measurement', async t => {
  const f = await fixture(t);
  const p = await f.purchase();
  const response = await f.pay(p.route, p.payload);
  const original = await response.json();
  original.receipt.completed_at -= 100;
  f.store.finish(p.request.id, 'delivered', { result: original });
  const retry = await f.pay(p.route, p.payload);
  const cached = await retry.json();
  assert.equal(cached.decision.decision, 'WAIT');
  assert.equal(cached.evidence_cached, true);
  assert.equal(f.events.filter(e => e === 'measure').length, 1);
  assert.equal(f.events.filter(e => e === 'settle').length, 1);
});
test('concurrent requests settle and measure once', async t => {
  const f = await fixture(t);
  const p = await f.purchase();
  const responses = await Promise.all([f.pay(p.route, p.payload), f.pay(p.route, p.payload)]);
  assert.ok(responses.some(r => r.status === 200));
  assert.equal(f.events.filter(e => e === 'settle').length, 1);
  assert.equal(f.events.filter(e => e === 'measure').length, 1);
});
for (const [name, options, status, state] of [
  ['failed settlement', { settled: false }, 402, 'payment_failed'],
  ['unknown settlement', { unknown: true }, 503, 'settlement_unknown'],
  ['failed delivery', { deliveryFails: true }, 503, 'delivery_failed'],
]) {
  test(`${name} preserves review state and never retries side effects`, async t => {
    const f = await fixture(t, options);
    const p = await f.purchase();
    assert.equal((await f.pay(p.route, p.payload)).status, status);
    assert.equal(f.store.get(p.request.id).state, state);
    assert.equal((await f.pay(p.route, p.payload)).status, 409);
    assert.equal(f.events.filter(e => e === 'settle').length, 1);
    assert.equal(f.events.filter(e => e === 'measure').length, options.deliveryFails ? 1 : 0);
  });
}
test('purchase ledger survives restart and enforces unique proof across writers', () => {
  const dir = mkdtempSync(join(tmpdir(), 'fieldproof-'));
  const path = join(dir, 'purchases.sqlite');
  try {
    const first = new PurchaseStore(path);
    first.create({ id: 'p1', nonce: 1, location: 'demo-gate', max_age_seconds: 10, expires_at: 9999999999 });
    assert.equal(first.reserve('p1', 'proof'), true);
    first.close();
    const reopened = new PurchaseStore(path);
    const concurrent = new PurchaseStore(path);
    reopened.create({ id: 'p2', nonce: 2, location: 'demo-gate', max_age_seconds: 10, expires_at: 9999999999 });
    assert.equal(concurrent.reserve('p2', 'proof'), false);
    assert.equal(reopened.get('p1').state, 'settling');
    reopened.close(); concurrent.close();
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
