// Deterministic browser contract tests. No payment, device, or live chain claim.
const { chromium } = require(process.argv[2] || 'playwright');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const assert = require('node:assert/strict');
const root = resolve(__dirname, '..');
const purchase = JSON.parse(readFileSync(resolve(root, 'docs/evidence/device-signed-purchase.json'))).purchase;
const rpc = JSON.parse(readFileSync(resolve(root, 'gateway/test/fixtures/settlement-rpc.json')));
const output = value => ({ name: 'buyer-fixture.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(value)) });

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [], requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => requests.push({ method: request.method(), url: request.url() }));
    await page.addInitScript(now => {
      window.fixtureNow = now;
      Date.now = () => window.fixtureNow;
      const verify = crypto.subtle.verify.bind(crypto.subtle);
      crypto.subtle.verify = async (...args) => {
        const result = await verify(...args);
        if (window.pauseSignature) await new Promise(resolve => { window.releaseSignature = resolve; });
        return result;
      };
    }, (purchase.receipt.completed_at + 2) * 1000);
    let available = false, queries = 0, releaseRpc;
    await page.route('**/buyer-run', route => route.fulfill(available
      ? { contentType: 'application/json', body: JSON.stringify(purchase) }
      : { status: 404, body: '{}' }));
    await page.route('https://api.devnet.solana.com/', async route => {
      const body = route.request().postDataJSON();
      assert.equal(body.method, 'getTransaction');
      assert.equal(body.params[0], purchase.settlement.transaction);
      queries += 1;
      if (queries === 2) await new Promise(resolve => { releaseRpc = resolve; });
      await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ jsonrpc: '2.0', id: body.id, result: rpc }) });
    });
    const url = new URL('/proof?live=1&present=1', process.argv[3] || 'http://127.0.0.1:4021');
    await page.goto(url.href);
    await page.waitForFunction(() => document.getElementById('stage-source').textContent.startsWith('Waiting'));
    assert.equal(await page.textContent('#decision'), 'WAIT');
    assert.equal(await page.textContent('#scene-claim'), 'Receipt claim: UNAVAILABLE');
    assert.equal(await page.isDisabled('#original'), true);
    assert.equal(await page.isDisabled('#chain-query'), true);
    assert.equal(queries, 0);
    assert.equal(requests.some(r => r.url.endsWith('/evidence/device-signed-purchase.json')), false);
    available = true;
    await page.waitForFunction(() => document.getElementById('decision').textContent === 'DISPATCH');
    assert.equal(await page.textContent('#live-payment-check'), 'VERIFIED');
    assert.equal(await page.textContent('#signature'), 'VALID');
    assert.equal(queries, 1);
    const workspace = await page.locator('.workspace').boundingBox();
    assert.ok(workspace.y + workspace.height <= 900, 'Live receipt checks must fit the desktop viewport');
    await page.evaluate(() => { window.fixtureNow += 11000; });
    await page.waitForFunction(() => document.getElementById('freshness').textContent === 'EXPIRED');
    assert.equal(await page.textContent('#decision'), 'WAIT');
    assert.equal(await page.textContent('#scene-decision'), 'WAIT');

    await page.click('#focus');
    await page.locator('.intro details').evaluate(node => { node.open = true; });
    await page.evaluate(now => { window.fixtureNow = now; }, (purchase.receipt.completed_at + 2) * 1000);
    await page.setInputFiles('#run-file', output(purchase));
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'VALID' && !document.getElementById('original').disabled);
    assert.equal(await page.textContent('#freshness'), 'FRESH');
    assert.equal(await page.textContent('#live-payment-check'), 'NOT VERIFIED');
    assert.equal(await page.textContent('#decision'), 'WAIT', 'A loaded file cannot inherit a prior payment check');
    await page.click('#chain-query');
    await page.waitForFunction(() => document.getElementById('chain-status').textContent === 'CHECKING');
    await page.setInputFiles('#run-file', output(Array(64).fill(1)));
    await page.waitForFunction(() => document.getElementById('reason').textContent.startsWith('Rejected buyer output'));
    while (!releaseRpc) await new Promise(resolve => setTimeout(resolve, 10));
    const pendingResponse = page.waitForResponse('https://api.devnet.solana.com/');
    releaseRpc();
    await pendingResponse;
    assert.equal(await page.textContent('#chain-status'), 'NOT QUERIED');
    assert.equal(await page.textContent('#decision'), 'WAIT');
    assert.equal(await page.isDisabled('#original'), true);

    await page.setInputFiles('#run-file', output(purchase));
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'VALID' && !document.getElementById('original').disabled);
    await page.evaluate(() => { window.pauseSignature = true; });
    await page.click('#tamper');
    await page.waitForFunction(() => typeof window.releaseSignature === 'function');
    await page.setInputFiles('#run-file', output({ status: 'failed' }));
    await page.waitForFunction(() => document.getElementById('reason').textContent.startsWith('Rejected buyer output'));
    await page.evaluate(() => { window.pauseSignature = false; window.releaseSignature(); });
    assert.equal(await page.textContent('#signature'), 'NOT VERIFIED');
    assert.equal(await page.textContent('#scene-claim'), 'Receipt claim: UNAVAILABLE');
    assert.equal(await page.isDisabled('#original'), true);
    assert.equal(await page.textContent('#decision'), 'WAIT');
    let releaseArchive;
    await page.route('**/evidence/device-signed-purchase.json', async route => {
      await new Promise(resolve => { releaseArchive = resolve; });
      await route.fulfill({ status: 503, body: '{}' });
    });
    await page.click('#use-recorded');
    await page.waitForFunction(() => document.getElementById('reason').textContent === 'Loading committed evidence.');
    await page.setInputFiles('#run-file', output(purchase));
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'VALID' && !document.getElementById('original').disabled);
    while (!releaseArchive) await new Promise(resolve => setTimeout(resolve, 10));
    const archiveResponse = page.waitForResponse('**/evidence/device-signed-purchase.json');
    releaseArchive();
    await archiveResponse;
    assert.equal(await page.textContent('#signature'), 'VALID');
    assert.equal(await page.isDisabled('#original'), false);
    assert.match(await page.textContent('#receipt-source'), /^Buyer run /);
    assert.deepEqual(errors, []);
    assert.equal(requests.filter(r => r.method !== 'GET' && !r.url.startsWith('https://api.devnet.solana.com/')).length, 0);
    console.log('Buyer-run browser fixtures passed: no archived substitution, one read-only query, required chain check, live expiry, output replacement, wallet rejection, stale asynchronous result rejection, desktop fit, and no payment/device requests.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
