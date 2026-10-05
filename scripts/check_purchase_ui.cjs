// Exercise a simulated purchase. This script refuses gateways with physical evidence or real payment.
const { chromium } = require(process.argv[2] || 'playwright');
const assert = require('node:assert/strict');
const { mkdirSync } = require('node:fs');
const { resolve } = require('node:path');
const root = resolve(__dirname, '..');
const origin = process.argv[3] || 'http://127.0.0.1:4022';

(async () => {
  const url = new URL(origin);
  const presenting = url.searchParams.get('present') === '1';
  assert.equal(url.protocol, 'http:');
  assert.equal(url.hostname, '127.0.0.1', 'Use only the local prototype simulator');
  assert.equal(url.username + url.password, '');
  const health = await (await fetch(new URL('/health', origin), { signal: AbortSignal.timeout(5000) })).json();
  assert.equal(health.mode, 'simulated settlement; no funds moved');
  assert.equal(health.sensor, 'simulated-contact');
  assert.equal(health.receipt_identity, 'public-demo-hmac');
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    let releaseHealth;
    const healthGate = new Promise(resolve => { releaseHealth = resolve; });
    await page.route('**/health', async route => { await healthGate; await route.continue(); });
    try {
      await page.goto(origin);
      assert.equal(await page.isDisabled('#quote'), true, 'Quote creation must wait for contact configuration');
    } finally { releaseHealth(); }
    await page.waitForFunction(() => !document.getElementById('quote').disabled);
    await page.unroute('**/health');
    assert.match(await page.textContent('#instruction'), new RegExp(health.provider));
    const requestCreated = page.waitForResponse(response => new URL(response.url()).pathname === '/requests');
    await page.click('#quote');
    const request = await requestCreated;
    assert.equal(request.status(), 201);
    const purchase = await request.json();
    assert.deepEqual(purchase.contact, health.contact);
    assert.equal(purchase.receipt_public_key, null);
    await page.waitForFunction(() => !document.getElementById('observe').hidden);
    await page.click('#observe');
    await page.waitForFunction(() => document.getElementById('state').textContent !== '—');
    const receipt = JSON.parse(await page.textContent('#receipt'));
    assert.equal(receipt.receipt.provider, health.provider);
    assert.equal(receipt.receipt.result.sensor, 'simulated-contact');
    const expected = receipt.receipt.result.closed ? 'WAIT' : 'DISPATCH';
    assert.equal(await page.textContent('#decision'), expected);
    assert.equal(receipt.payment_mode, 'simulated; no funds moved');
    assert.equal(receipt.decision.evidence_mode, 'simulated');
    assert.match(await page.textContent(presenting ? '#presentation-source' : '#contact-note'), presenting ? /Simulated contact input/ : /evidence is simulated/);
    assert.match(await page.textContent('#mode'), /SIMULATED PAYMENT · NO FUNDS MOVED/);
    if (expected === 'DISPATCH') {
      await page.click('#quote');
      await page.waitForFunction(() => document.getElementById('reason').textContent === '402 quote received. No evidence yet.');
      assert.equal(await page.textContent('#decision'), 'WAIT');
      assert.equal(await page.getAttribute('#decision', 'class'), 'decision wait', 'A new quote must remove the prior DISPATCH style');
      assert.equal(await page.textContent('#state'), '—');
      assert.equal(await page.textContent('#age'), '—');
      await page.click('#observe');
      await page.waitForFunction(() => document.getElementById('decision').textContent === 'DISPATCH');
    }
    if (presenting) {
      assert.equal(await page.isVisible('.hero'), false);
      assert.equal(await page.isVisible('.stage-title'), true);
      assert.equal(await page.textContent('#observe'), 'Request observation');
      for (const viewport of [{ width: 1280, height: 900 }, { width: 1920, height: 1080 }]) {
        await page.setViewportSize(viewport);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        assert.ok(await page.locator('.desk').evaluate(node => node.getBoundingClientRect().bottom <= innerHeight), 'The decision must fit the desktop recording frame');
      }
      await page.setViewportSize({ width: 1280, height: 900 });
    }
    mkdirSync(resolve(root, '.local'), { recursive: true });
    await page.screenshot({ path: resolve(root, presenting ? '.local/purchase-focus-desktop.png' : '.local/purchase-desktop.png'), fullPage: true });
    await page.waitForFunction(() => document.getElementById('reason').textContent.includes('Evidence expired'), {}, { timeout: 16000 });
    assert.equal(await page.textContent('#decision'), 'WAIT');
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: resolve(root, presenting ? '.local/purchase-focus-mobile.png' : '.local/purchase-mobile.png'), fullPage: true });
    assert.deepEqual(errors, []);
    console.log(`Simulated browser purchase passed: ${health.provider}, configured terms, ${expected}, expired WAIT, desktop/mobile, no page errors. No funds or hardware.`);
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
