import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { mkdtempSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { spawn } from 'node:child_process';
import { DatabaseSync } from 'node:sqlite';
import { address, appendTransactionMessageInstruction, compileTransaction, createTransactionMessage,
  generateKeyPairSigner, getAddressEncoder, getTransactionDecoder, getTransactionEncoder,
  setTransactionMessageFeePayer, setTransactionMessageLifetimeUsingBlockhash } from '@solana/kit';
import { createGateway, createPaymentServer, NETWORK, PAY_TO, USDC } from '../server.js';
import { PurchaseStore } from '../store.js';
import { decodePaymentRequiredHeader, encodePaymentSignatureHeader } from '@x402/core/http';

async function fixture(t, { valid = true, settled = true, unknown = false, deliveryFails = false, path = ':memory:', sensor = 'simulated-contact' } = {}) {
  const events = [];
  const facilitator = {
    getSupported: async () => ({ kinds: [{ x402Version: 2, scheme: 'exact', network: NETWORK, extra: { feePayer: PAY_TO } }], extensions: [], signers: {} }),
    verify: async () => { events.push('verify'); return { isValid: valid, payer: PAY_TO }; },
    settle: async () => { events.push('settle'); if (unknown) throw new Error('timeout');
      return { success: settled, transaction: 'SIMULATED-TRANSACTION', network: NETWORK, payer: PAY_TO }; },
  };
  const paymentServer = await createPaymentServer(facilitator);
  const store = new PurchaseStore(path);
  const app = await createGateway({ paymentServer, store, simulated: true, sensor, observe: async () => {
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
      payload: { transaction: Buffer.from('FIELDPROOF-SIM:fixture-proof').toString('base64') } }, challenge };
  }
  const pay = (route, payload) => fetch(route, { headers: { 'PAYMENT-SIGNATURE': encodePaymentSignatureHeader(payload) } });
  return { url, events, store, purchase, pay };
}

test('physical contact metadata stays separate from simulated settlement', async t => {
  const f = await fixture(t, { sensor: 'gpio9-contact' });
  const health = await (await fetch(`${f.url}/health`)).json();
  const manifest = await (await fetch(`${f.url}/manifest`)).json();
  assert.equal(health.sensor, 'gpio9-contact');
  assert.equal(manifest.sensor, 'gpio9-contact');
  assert.equal(health.mode, 'simulated settlement; no funds moved');
  assert.deepEqual(f.events, []);
});

test('unpaid and malformed payments never measure', async t => {
  const f = await fixture(t);
  const p = await f.purchase();
  assert.equal(p.challenge.accepts[0].network, NETWORK);
  assert.equal(p.challenge.accepts[0].asset, USDC);
  assert.equal(p.challenge.accepts[0].amount, '1000');
  assert.deepEqual(f.events, []);
  const bad = await fetch(p.route, { headers: { 'PAYMENT-SIGNATURE': 'garbage' } });
  assert.equal(bad.status, 402);
  p.payload.payload.transaction = Buffer.from('not-a-solana-transaction').toString('base64');
  assert.equal((await f.pay(p.route, p.payload)).status, 402);
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
test('changing the facilitator signature cannot purchase a second observation with the same signed message', async t => {
  const buyer = await generateKeyPairSigner();
  let message = setTransactionMessageFeePayer(address(PAY_TO), createTransactionMessage({ version: 0 }));
  message = setTransactionMessageLifetimeUsingBlockhash({
    blockhash: '11111111111111111111111111111111', lastValidBlockHeight: 100n,
  }, message);
  message = appendTransactionMessageInstruction({ programAddress: address('11111111111111111111111111111111'),
    accounts: [{ address: buyer.address, role: 2 }], data: new Uint8Array() }, message);
  const tx = compileTransaction(message);
  const [signatures] = await buyer.signTransactions([tx]);
  const original = Uint8Array.from(getTransactionEncoder().encode({ ...tx, signatures: { ...tx.signatures, ...signatures } }));
  const altered = Uint8Array.from(original);
  altered[1] ^= 1; // The facilitator replaces its own signature before broadcasting.
  const decoded = getTransactionDecoder().decode(altered);
  assert.deepEqual(decoded.messageBytes, tx.messageBytes);
  const key = await crypto.subtle.importKey('raw', getAddressEncoder().encode(buyer.address), 'Ed25519', false, ['verify']);
  assert.equal(await crypto.subtle.verify('Ed25519', key, decoded.signatures[buyer.address], decoded.messageBytes), true);
  const f = await fixture(t);
  const first = await f.purchase();
  first.payload.payload.transaction = Buffer.from(original).toString('base64');
  assert.equal((await f.pay(first.route, first.payload)).status, 200);
  const second = await f.purchase(456);
  second.payload.payload.transaction = Buffer.from(altered).toString('base64');
  assert.equal((await f.pay(second.route, second.payload)).status, 409);
  first.payload.payload.transaction = Buffer.from(altered).toString('base64');
  const retry = await f.pay(first.route, first.payload);
  assert.equal(retry.status, 200);
  assert.equal((await retry.json()).evidence_cached, true);
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

test('purchase ledger waits for a concurrent startup lock before enabling WAL', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'fieldproof-startup-'));
  const path = join(dir, 'purchases.sqlite');
  const writer = new DatabaseSync(path);
  writer.exec('CREATE TABLE probe(id INTEGER); BEGIN EXCLUSIVE;');
  const child = spawn(process.execPath, ['--input-type=module', '-e',
    `import { PurchaseStore } from ${JSON.stringify(new URL('../store.js', import.meta.url).href)};
     console.log('opening'); new PurchaseStore(process.argv[1]).close();`, path],
    { stdio: ['ignore', 'pipe', 'pipe'] });
  let stderr = '', release;
  child.stderr.on('data', chunk => { stderr += chunk; });
  const closed = once(child, 'close');
  try {
    await once(child.stdout, 'data');
    release = setTimeout(() => writer.exec('COMMIT'), 200);
    const [code] = await closed;
    assert.equal(code, 0, stderr);
  } finally {
    clearTimeout(release);
    if (writer.isTransaction) writer.exec('ROLLBACK');
    writer.close();
    rmSync(dir, { recursive: true, force: true });
  }
});
