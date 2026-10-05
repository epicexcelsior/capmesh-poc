// Browser fixtures for the local control. No signing, hardware, or live-chain claim.
const { chromium } = require(process.argv[2] || 'playwright');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const assert = require('node:assert/strict');
const root = resolve(__dirname, '..');
const run = JSON.parse(readFileSync(resolve(root, 'docs/evidence/device-signed-purchase.json'))).purchase;
const rpc = JSON.parse(readFileSync(resolve(root, 'gateway/test/fixtures/settlement-rpc.json')));
const origin = new URL(process.argv[3] || 'http://127.0.0.1:4021');
if (origin.protocol !== 'http:' || origin.hostname !== '127.0.0.1') throw new Error('Use the local fixture gateway');

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    let posts = 0, operation = null, done = false, review = false, rpcFailed = false;
    await page.route('**/local-buyer/**', async route => {
      const request = route.request(), path = new URL(request.url()).pathname;
      const json = value => route.fulfill({ contentType: 'application/json', body: JSON.stringify(value) });
      if (path === '/local-buyer/config' && request.method() === 'GET') return json({
        payer: run.settlement.payer, payTo: 'CaQAKBcwf7G5vXeu2RNuNGJafnJ8724Uj4wv9ivfxfQA',
        price_usdc: '0.001', maximum: 10, remaining: operation ? 9 : 10,
        busy: false, blocked: review, active_operation_id: null, last_operation_id: operation, token: 'fixture-only',
      });
      if (path === '/local-buyer/purchase' && request.method() === 'POST') {
        assert.equal(request.headers()['x-fieldproof-buyer-token'], 'fixture-only');
        const body = request.postDataJSON();
        assert.deepEqual(Object.keys(body), ['operation_id']);
        operation = body.operation_id; posts++;
        return route.fulfill({ status: 202, contentType: 'application/json', body: '{}' });
      }
      if (path === '/local-buyer/purchase/' + operation && request.method() === 'GET') return json({
        operation_id: operation, purchase_id: run.purchase_id, elapsed_ms: 1200,
        status: review ? 'review' : done ? 'done' : 'pending',
        events: ['request', 'quote', 'paying', 'settled', ...(done ? ['verified'] : [])]
          .map((phase, i) => ({ phase, elapsed_ms: i * 200 })),
        ...(done ? { run } : {}), ...(review ? { error: 'Purchase requires review. No automatic paid retry.' } : {}),
      });
      await route.abort();
      assert.fail('Unexpected local-buyer request');
    });
    await page.route('https://api.devnet.solana.com/', route => {
      const body = route.request().postDataJSON();
      assert.equal(body.method, 'getTransaction');
      return route.fulfill(rpcFailed ? { status: 503, body: '{}' }
        : { contentType: 'application/json', body: JSON.stringify({ jsonrpc: '2.0', id: body.id, result: rpc }) });
    });
    await page.goto(new URL('/proof?present=1', origin).href);
    await page.waitForFunction(() => !document.getElementById('local-buy').disabled);
    assert.equal(posts, 0);
    await page.click('#local-buy');
    await page.waitForFunction(() => document.getElementById('buyer-events').textContent.includes('Solana settled'));
    assert.equal(await page.isDisabled('#local-buy'), true);
    assert.equal(await page.getAttribute('#flow-read', 'data-state'), 'active');
    assert.equal(await page.locator('#flow-read').evaluate(node => getComputedStyle(node, '::before').animationName), 'none');
    assert.equal(await page.locator('#age-fill').evaluate(node => getComputedStyle(node).transitionDuration), '0s');
    done = true;
    await page.waitForFunction(() => !document.getElementById('local-buy').disabled);
    assert.equal(await page.textContent('#proof-payment-check'), 'VERIFIED TRANSFER');
    assert.equal(await page.textContent('#signature'), 'VALID');
    assert.equal(await page.textContent('#decision'), 'WAIT', 'The archived fixture stays expired');
    assert.match(await page.textContent('#buyer-events'), /Transfer verified/);
    assert.equal(posts, 1);
    await page.reload();
    await page.waitForFunction(() => !document.getElementById('local-buy').disabled);
    assert.equal(posts, 1, 'Reload must not purchase');
    rpcFailed = true;
    await page.click('#focus');
    await page.click('#chain-query');
    await page.waitForFunction(() => document.getElementById('buyer-events').textContent.includes('Transfer unverified'));
    assert.equal(await page.getAttribute('#flow-check', 'data-state'), 'fail');
    assert.equal(await page.textContent('#decision'), 'WAIT');
    await page.click('#focus');
    for (const size of [{ width: 1280, height: 900 }, { width: 390, height: 844 }]) {
      await page.setViewportSize(size);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    }
    review = true;
    await page.click('#local-buy');
    await page.waitForFunction(() => document.getElementById('buyer-progress').dataset.error === 'true');
    assert.equal(await page.isDisabled('#local-buy'), true);
    assert.ok((await page.locator('#buyer-progress').boundingBox()).height > 1, 'Failure must remain visible');
    assert.match(await page.textContent('#buyer-progress'), /Purchase ID/);
    await page.waitForTimeout(800);
    assert.equal(posts, 2, 'Failure must not retry');
    await page.reload();
    await page.waitForFunction(() => document.getElementById('buyer-progress').textContent.includes('Operation ID:'));
    assert.equal(await page.isDisabled('#local-buy'), true);
    assert.ok((await page.locator('#buyer-progress').boundingBox()).height > 1, 'Review instruction must survive reload');
    assert.match(await page.textContent('#buyer-progress'), new RegExp(operation));
    assert.equal(posts, 2, 'Reload after failure must not purchase');
    assert.deepEqual(errors, []);
    console.log('Local-buyer fixtures passed: actual-event rendering, reduced motion, receipt/payment checks, reload without purchase, visible RPC/review failures, no paid retry, desktop/mobile. No funds or hardware.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
