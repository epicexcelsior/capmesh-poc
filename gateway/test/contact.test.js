import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createServer } from 'node:http';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';
import { contactContract, DEFAULT_CONTACT, loadReceiptPins, receiptKey } from '../contact.js';

test('contact selection rejects reserved chip pins, simulated evidence, and inherited terms', () => {
  assert.deepEqual(contactContract(), DEFAULT_CONTACT);
  assert.deepEqual(contactContract({ provider: 'another-board', sensor: 'gpio18-contact' }), { provider: 'another-board', sensor: 'gpio18-contact' });
  for (const sensor of ['gpio4-contact', 'gpio8-contact', 'gpio10-contact', 'gpio12-contact', 'gpio15-contact', 'gpio24-contact', 'simulated-contact']) {
    assert.throws(() => contactContract({ provider: 'board', sensor }), /supported contact/);
  }
  assert.throws(() => contactContract({ provider: '../board', sensor: 'gpio18-contact' }), /supported contact/);
  const inherited = Object.assign(Object.create({ sensor: 'gpio18-contact' }), { provider: 'board', extra: true });
  assert.throws(() => contactContract(inherited), /supported contact/);
  assert.equal(contactContract({ provider: 'fixture', sensor: 'simulated-contact' }, { simulated: true }).sensor, 'simulated-contact');
});

test('trusted public pins reject invalid points and provider IDs', t => {
  const dir = mkdtempSync(join(tmpdir(), 'fieldproof-pins-'));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const path = join(dir, 'pins.json');
  const pin = loadReceiptPins()[DEFAULT_CONTACT.provider];
  const valid = { algorithm: 'ecdsa-p256-sha256', providers: { 'board-one': pin } };
  writeFileSync(path, JSON.stringify(valid));
  assert.deepEqual(loadReceiptPins(path), valid.providers);
  for (const data of [{ ...valid, algorithm: 'hmac' }, { ...valid, providers: {} },
    { ...valid, providers: { 'invalid/id': pin } }, { ...valid, providers: { board: '04' + '00'.repeat(64) } },
    { ...valid, providers: { board: null } }]) {
    writeFileSync(path, JSON.stringify(data));
    assert.throws(() => loadReceiptPins(path));
  }
  assert.throws(() => receiptKey('04' + '00'.repeat(64)));
});

test('gateway CLI rejects an unknown provider before contacting its facilitator', async t => {
  let requests = 0;
  const facilitator = createServer((_req, res) => {
    requests++;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ kinds: [], extensions: [], signers: {} }));
  });
  facilitator.listen(0, '127.0.0.1');
  await once(facilitator, 'listening');
  t.after(async () => { facilitator.closeAllConnections(); await new Promise(resolve => facilitator.close(resolve)); });
  const child = spawn(process.execPath, [fileURLToPath(new URL('../server.js', import.meta.url))], {
    env: { ...process.env, FIELDPROOF_PROVIDER_ID: 'not-provisioned', FIELDPROOF_CONTACT_SENSOR: 'gpio18-contact',
      FIELDPROOF_RECEIPT_PINS: '', FACILITATOR_URL: `http://127.0.0.1:${facilitator.address().port}` },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stderr = '';
  child.stderr.on('data', chunk => { stderr += chunk; });
  const timer = setTimeout(() => child.kill('SIGKILL'), 5000);
  try {
    const [code, signal] = await once(child, 'close');
    assert.equal(signal, null);
    assert.notEqual(code, 0);
    assert.match(stderr, /no provisioned P-256 receipt key/);
    assert.equal(requests, 0);
  } finally { clearTimeout(timer); }
});
