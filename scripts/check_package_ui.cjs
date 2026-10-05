// Signed test fixtures, fixed clock, and RPC fixtures. No physical input or funds.
const { chromium } = require(process.argv[2] || 'playwright');
const { readFileSync, mkdirSync } = require('node:fs');
const { resolve } = require('node:path');
const { generateKeyPairSync, sign } = require('node:crypto');
const assert = require('node:assert/strict');
const root = resolve(__dirname, '..');
const original = JSON.parse(readFileSync(resolve(root, 'docs/evidence/device-signed-purchase.json'))).purchase;
const rpc = JSON.parse(readFileSync(resolve(root, 'gateway/test/fixtures/settlement-rpc.json')));
const keys = generateKeyPairSync('ec', { namedCurve: 'prime256v1' });
const pin = keys.publicKey.export({ format: 'der', type: 'spki' }).subarray(-65).toString('hex');
function fixture(closed) {
  const p = structuredClone(original), r = p.receipt, s = r.result;
  p.purpose = 'package-pickup';
  p.challenge.contact = { provider: r.provider, sensor: 'gpio20-contact' };
  s.sensor = 'gpio20-contact'; s.closed = closed;
  const message = ['fieldproof-observation-v1', r.protocol, r.request_id, r.provider, r.capability,
    r.parameters.location, r.nonce, s.metric, s.sensor, Number(closed), 5, 5, r.started_at, r.completed_at].join('|');
  r.receipt_signature = 'v3:' + sign('sha256', Buffer.from(message), { key: keys.privateKey, dsaEncoding: 'ieee-p1363' }).toString('base64');
  return p;
}
const upload = p => ({ name: 'package-fixture.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(p)) });
(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [], writes = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => { if (r.method() === 'POST' && !r.url().startsWith('https://api.devnet.solana.com/')) writes.push(r.url()); });
    await page.addInitScript(now => { window.fixtureNow = now; Date.now = () => window.fixtureNow; }, (original.receipt.completed_at + 2) * 1000);
    await page.route('**/receipt-keys.json', route => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ algorithm: 'ecdsa-p256-sha256', providers: { 'esp32-c6-96a2': pin } }) }));
    let available = false;
    await page.route('**/buyer-run', route => route.fulfill(available ? { contentType: 'application/json', body: JSON.stringify(fixture(false)) } : { status: 404, body: '{}' }));
    await page.route('https://api.devnet.solana.com/', route => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ jsonrpc: '2.0', id: 'fieldproof-payment-check', result: rpc }) }));
    await page.goto(new URL('/proof?view=package&present=1', process.argv[3] || 'http://127.0.0.1:4021').href);
    await page.waitForFunction(() => document.getElementById('receipt-source').textContent.startsWith('Waiting'));
    assert.equal(await page.textContent('#decision'), 'WAIT');
    assert.equal(await page.textContent('#scene-claim'), 'Receipt claim: UNAVAILABLE');
    available = true;
    await page.waitForFunction(() => document.getElementById('proof-payment-check').textContent === 'VERIFIED TRANSFER');
    assert.equal(await page.textContent('#signature'), 'VALID');
    assert.equal(await page.textContent('#scene-claim'), 'Receipt claim: PACKAGE_ABSENT');
    assert.equal(await page.textContent('#decision'), 'WAIT');
    assert.equal(await page.locator('.package-box').isVisible(), false);
    const box = await page.locator('.workspace').boundingBox();
    assert.ok(box.y + box.height <= 900);
    mkdirSync(resolve(root, '.local/package-contact'), { recursive: true });
    await page.screenshot({ path: resolve(root, '.local/package-contact/fixture-absent.png') });
    await page.click('#focus');
    await page.locator('.intro details').evaluate(node => { node.open = true; });
    assert.equal(await page.isDisabled('#use-recorded'), true);
    await page.setInputFiles('#run-file', upload(fixture(true)));
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'VALID' && document.getElementById('scene-claim').textContent.endsWith('PACKAGE_PRESENT'));
    assert.equal(await page.textContent('#decision'), 'WAIT', 'Payment verification cannot carry across files');
    await page.click('#chain-query');
    await page.waitForFunction(() => document.getElementById('decision').textContent === 'DISPATCH');
    assert.equal(await page.locator('.package-box').isVisible(), true);
    await page.click('#focus');
    await page.screenshot({ path: resolve(root, '.local/package-contact/fixture-present.png') });
    await page.click('#tamper');
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'REJECTED');
    assert.equal(await page.textContent('#decision'), 'WAIT');
    await page.click('#original');
    await page.waitForFunction(() => document.getElementById('decision').textContent === 'DISPATCH');
    await page.evaluate(() => { window.fixtureNow += 9000; });
    await page.waitForFunction(() => document.getElementById('freshness').textContent === 'EXPIRED');
    assert.equal(await page.textContent('#signature'), 'VALID');
    assert.equal(await page.textContent('#decision'), 'WAIT');
    await page.click('#focus');
    await page.setInputFiles('#run-file', upload(original));
    await page.waitForFunction(() => document.getElementById('reason').textContent.startsWith('Rejected buyer output'));
    assert.equal(await page.textContent('#decision'), 'WAIT');
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert.deepEqual(errors, []); assert.deepEqual(writes, []);
    process.stdout.write('Package browser fixtures passed: absent, present, new payment check, tamper, expiry, GPIO9 rejection, desktop/mobile. No physical input or funds.\n');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
