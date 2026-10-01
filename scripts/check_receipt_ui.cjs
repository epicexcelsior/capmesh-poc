// Read-only browser checks against committed evidence. Requires installed Playwright and Chromium.
const { chromium } = require(process.argv[2] || 'playwright');
const { mkdirSync } = require('node:fs');
const { resolve } = require('node:path');
const assert = require('node:assert/strict');
const root = resolve(__dirname, '..');

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(new URL('/proof', process.argv[3] || 'http://127.0.0.1:4021').href);
    await page.waitForFunction(() => !document.getElementById('original').disabled);
    assert.equal(await page.textContent('#signature'), 'VALID');
    assert.equal(await page.textContent('#binding'), 'MATCHES');
    assert.equal(await page.textContent('#freshness'), 'EXPIRED');
    assert.equal(await page.textContent('#decision'), 'WAIT');
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
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: resolve(root, '.local/receipt-mobile.png'), fullPage: true });
    assert.deepEqual(errors, []);
    console.log('Browser receipt checks passed: original, expired, tampered, changed challenge, another key, restored original, mobile width.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
