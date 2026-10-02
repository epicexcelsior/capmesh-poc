// Read-only browser checks against committed evidence. Requires installed Playwright and Chromium.
const { chromium } = require(process.argv[2] || 'playwright');
const { mkdirSync, readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const assert = require('node:assert/strict');
const root = resolve(__dirname, '..');

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(new URL(process.argv[4] || '/proof', process.argv[3] || 'http://127.0.0.1:4021').href);
    await page.waitForFunction(() => !document.getElementById('original').disabled);
    assert.equal(await page.textContent('#signature'), 'VALID');
    assert.equal(await page.textContent('#binding'), 'MATCHES');
    assert.equal(await page.textContent('#freshness'), 'EXPIRED');
    assert.equal(await page.textContent('#decision'), 'WAIT');
    await page.waitForFunction(() => document.getElementById('contact-status').textContent.startsWith('VERIFIED INPUT PAIR'));
    assert.match(await page.textContent('#contact-results'), /BOOT held → CLOSED/);
    assert.match(await page.textContent('#contact-results'), /BOOT released → OPEN/);
    assert.equal(await page.locator('#contact-results li').count(), 2);
    mkdirSync(resolve(root, '.local'), { recursive: true });
    await page.screenshot({ path: resolve(root, '.local/receipt-desktop.png'), fullPage: true });
    await page.click('#tamper');
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'REJECTED');
    assert.equal(await page.textContent('#decision'), 'WAIT');
    await page.click('#challenge');
    await page.waitForFunction(() => document.getElementById('binding').textContent === 'REJECTED');
    assert.equal(await page.textContent('#signature'), 'VALID');
    await page.click('#identity');
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'REJECTED');
    await page.click('#original');
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'VALID');
    // Deterministic RPC fixtures exercise the browser states. They do not assert a live chain lookup.
    const fixture = JSON.parse(readFileSync(resolve(root, 'gateway/test/fixtures/settlement-rpc.json'), 'utf8'));
    let queries = 0;
    await page.route('https://api.devnet.solana.com/', async route => {
      const request = route.request();
      assert.equal(request.method(), 'POST');
      const body = request.postDataJSON();
      assert.equal(body.method, 'getTransaction');
      assert.equal(body.params[1].commitment, 'confirmed');
      queries += 1;
      await route.fulfill(queries === 2
        ? { status: 429, body: 'Rate limit fixture' }
        : { contentType: 'application/json', body: JSON.stringify({ jsonrpc: '2.0', id: body.id, result: fixture }) });
    });
    await page.click('#chain-query');
    await page.waitForFunction(() => document.getElementById('chain-status').textContent === 'VERIFIED TRANSFER');
    assert.match(await page.textContent('#chain-result'), /"merchant_delta_base_units": "1000"/);
    assert.equal(await page.textContent('#decision'), 'WAIT');
    await page.click('#chain-query');
    await page.waitForFunction(() => document.getElementById('chain-status').textContent === 'NOT VERIFIED');
    assert.match(await page.textContent('#chain-result'), /HTTP 429/);
    assert.equal(await page.isDisabled('#chain-query'), false);
    assert.equal(await page.textContent('#signature'), 'VALID');
    assert.equal(await page.textContent('#decision'), 'WAIT');
    await page.click('#chain-query');
    await page.waitForFunction(() => document.getElementById('chain-status').textContent === 'VERIFIED TRANSFER');
    assert.equal(queries, 3);
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: resolve(root, '.local/receipt-mobile.png'), fullPage: true });
    assert.deepEqual(errors, []);
    // A damaged input archive must fail visibly without disabling the paid-receipt inspector.
    const contacts = JSON.parse(readFileSync(resolve(root, 'docs/evidence/device-signed-contact-states.json'), 'utf8'));
    const mutations = [
      evidence => { evidence.held.receipt.result.closed = false; },
      evidence => { evidence.released.challenge.nonce += 1; },
      evidence => { evidence.held.receipt.receipt_signature = 'v3:AAAA'; },
    ];
    for (const mutate of mutations) {
      const evidence = structuredClone(contacts);
      mutate(evidence);
      await page.route('**/evidence/device-signed-contact-states.json', route =>
        route.fulfill({ contentType: 'application/json', body: JSON.stringify(evidence) }));
      await page.reload();
      await page.waitForFunction(() => document.getElementById('contact-status').textContent.startsWith('NOT VERIFIED'));
      await page.waitForFunction(() => document.getElementById('signature').textContent === 'VALID');
      assert.equal(await page.locator('#contact-results li').count(), 0);
      assert.equal(await page.textContent('#decision'), 'WAIT');
      await page.unroute('**/evidence/device-signed-contact-states.json');
    }
    assert.deepEqual(errors, []);
    console.log('Browser receipt checks passed: original, expiry, receipt attacks, both signed input states, damaged input archives, RPC fixture success, HTTP 429 and retry, unchanged WAIT, mobile width.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
