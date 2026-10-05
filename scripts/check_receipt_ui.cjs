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
    assert.match(await page.textContent('#evidence-age'), /old$/);
    assert.equal(await page.textContent('#age-limit'), 'Maximum age 10s');
    assert.equal(await page.textContent('#proof-payment-check'), 'NOT QUERIED');
    assert.equal(await page.textContent('#decision'), 'WAIT');
    assert.equal(await page.textContent('#scene-decision'), 'WAIT');
    assert.equal(await page.textContent('#scene-claim'), 'Receipt claim: OPEN');
    assert.equal(await page.getAttribute('#gate-scene', 'data-decision'), 'wait');
    assert.match(await page.textContent('#measured'), /^2026-10-01 19:08:54 UTC$/);
    assert.equal(await page.textContent('#payment-amount'), '0.001');
    assert.equal(await page.textContent('#payment-payer'), '2U7Bz5u4bVMsUtNcF4b4xdWG7K3N7WmbsGCqMQmjevMf');
    assert.equal(await page.textContent('#payment-merchant'), 'CaQAKBcwf7G5vXeu2RNuNGJafnJ8724Uj4wv9ivfxfQA');
    assert.equal(await page.getAttribute('#payment-explorer', 'href'), await page.getAttribute('#transaction', 'href'));
    await page.waitForFunction(() => document.getElementById('contact-status').textContent.startsWith('VERIFIED INPUT PAIR'));
    assert.match(await page.textContent('#contact-results'), /BOOT held → CLOSED/);
    assert.match(await page.textContent('#contact-results'), /BOOT released → OPEN/);
    assert.equal(await page.locator('#contact-results li').count(), 2);
    mkdirSync(resolve(root, '.local'), { recursive: true });
    await page.screenshot({ path: resolve(root, '.local/receipt-desktop.png'), fullPage: true });
    await page.click('#focus');
    assert.equal(await page.getAttribute('#focus', 'aria-pressed'), 'true');
    assert.equal(await page.locator('.intro').isVisible(), false);
    assert.equal(await page.locator('.stage-title').isVisible(), true);
    assert.equal(await page.locator('#payment').isVisible(), true);
    assert.equal(await page.textContent('#decision'), 'WAIT');
    assert.equal(await page.textContent('#freshness'), 'EXPIRED');
    const workspace = await page.locator('.workspace').boundingBox();
    assert.ok(workspace.y + workspace.height <= 900, 'Focused checks and experiments must fit the desktop viewport');
    await page.screenshot({ path: resolve(root, '.local/receipt-presenter-desktop.png') });
    await page.click('#tamper');
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'REJECTED');
    assert.equal(await page.textContent('#decision'), 'WAIT');
    assert.equal(await page.textContent('#experiment-label'), 'Altered contact state');
    assert.equal(await page.textContent('#scene-claim'), 'Receipt claim: CLOSED');
    assert.equal(await page.textContent('#scene-decision'), 'WAIT');
    assert.equal(await page.getAttribute('#tamper', 'aria-pressed'), 'true');
    assert.equal(await page.getAttribute('#original', 'aria-pressed'), 'false');
    await page.click('#challenge');
    await page.waitForFunction(() => document.getElementById('binding').textContent === 'REJECTED');
    assert.equal(await page.textContent('#signature'), 'VALID');
    assert.equal(await page.textContent('#experiment-label'), 'Another buyer challenge');
    await page.click('#identity');
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'REJECTED');
    await page.click('#original');
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'VALID');
    assert.equal(await page.textContent('#scene-claim'), 'Receipt claim: OPEN');
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: resolve(root, '.local/receipt-presenter-mobile.png'), fullPage: true });
    await page.click('#focus');
    assert.equal(await page.locator('.intro').isVisible(), true);
    assert.equal(await page.getAttribute('#focus', 'aria-pressed'), 'false');
    assert.equal(await page.textContent('#freshness'), 'EXPIRED');
    await page.setViewportSize({ width: 1280, height: 900 });
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
    assert.equal(await page.textContent('#proof-payment-check'), 'VERIFIED TRANSFER');
    assert.match(await page.textContent('#chain-result'), /"merchant_delta_base_units": "1000"/);
    assert.match(await page.textContent('#chain-summary'), /buyer −0.001 USDC → merchant \+0.001 USDC/);
    assert.equal(await page.textContent('#decision'), 'WAIT');
    await page.click('#chain-query');
    await page.waitForFunction(() => document.getElementById('chain-status').textContent === 'NOT VERIFIED');
    assert.equal(await page.textContent('#proof-payment-check'), 'NOT VERIFIED');
    assert.match(await page.textContent('#chain-result'), /HTTP 429/);
    assert.match(await page.textContent('#chain-summary'), /HTTP 429/);
    assert.doesNotMatch(await page.textContent('#chain-summary'), /Verified:/);
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
    const focusedUrl = new URL(page.url());
    focusedUrl.searchParams.set('present', '1');
    await page.goto(focusedUrl.href);
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'VALID');
    assert.equal(await page.getAttribute('#focus', 'aria-pressed'), 'true');
    assert.equal(await page.textContent('#decision'), 'WAIT');
    assert.equal(await page.textContent('#freshness'), 'EXPIRED');
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
    // A fixed historical browser clock tests the accepted branch. It is not current physical evidence.
    const recorded = JSON.parse(readFileSync(resolve(root, 'docs/evidence/device-signed-purchase.json'), 'utf8'));
    const historical = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    historical.on('pageerror', error => errors.push(error.message));
    await historical.clock.setFixedTime(new Date((recorded.purchase.receipt.completed_at + 5) * 1000));
    await historical.goto(page.url());
    await historical.waitForFunction(() => document.getElementById('decision').textContent === 'DISPATCH');
    assert.equal(await historical.textContent('#evidence-age'), '5s old');
    assert.equal(await historical.getAttribute('#age-track', 'aria-valuenow'), '5');
    assert.equal(await historical.textContent('#scene-decision'), 'DISPATCH');
    assert.equal(await historical.getAttribute('#gate-scene', 'data-decision'), 'dispatch');
    await historical.click('#tamper');
    await historical.waitForFunction(() => document.getElementById('signature').textContent === 'REJECTED');
    assert.equal(await historical.textContent('#decision'), 'WAIT');
    assert.equal(await historical.textContent('#scene-decision'), 'WAIT');
    await historical.close();
    // Unavailable source evidence cannot leave an illustrated OPEN claim or permit inspection.
    const unavailable = await browser.newPage();
    unavailable.on('pageerror', error => errors.push(error.message));
    await unavailable.route('**/evidence/device-signed-purchase.json', route => route.fulfill({ status: 404, body: 'Missing fixture' }));
    await unavailable.goto(page.url());
    await unavailable.waitForFunction(() => document.getElementById('signature').textContent === 'NOT VERIFIED');
    assert.equal(await unavailable.textContent('#scene-claim'), 'Receipt claim: UNAVAILABLE');
    assert.equal(await unavailable.textContent('#scene-decision'), 'WAIT');
    assert.equal(await unavailable.textContent('#evidence-age'), 'Unavailable');
    assert.equal(await unavailable.isDisabled('#original'), true);
    assert.equal(await unavailable.isDisabled('#chain-query'), true);
    await unavailable.close();
    assert.deepEqual(errors, []);
    console.log('Browser receipt checks passed: original, expiry, receipt attacks, synchronized claim/decision illustration, historical-clock accepted branch, focus toggle and direct link, desktop fit, both signed input states, damaged input archives, RPC fixtures and HTTP 429 recovery, mobile width.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
