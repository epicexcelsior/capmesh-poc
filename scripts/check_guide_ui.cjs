// Verify the founder guide against executed software outcomes. No hardware or payment.
const { chromium } = require(process.argv[2] || 'playwright');
const assert = require('node:assert/strict');
const { mkdirSync } = require('node:fs');
const { resolve } = require('node:path');
const { execFileSync } = require('node:child_process');
const root = resolve(__dirname, '..');
const url = process.argv[3] || 'http://127.0.0.1:8788/HOW_IT_WORKS.html';
const prefix = process.argv[4] || 'guide-source';
const fixtures = JSON.parse(execFileSync('uv', ['run', '--no-sync', '--project', 'host', 'capmesh',
  'corroborate-demo', '--scenario', 'all'], { cwd: root, encoding: 'utf8', timeout: 15000 }));

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(url);
    assert.equal(await page.locator('#reference').getAttribute('open'), null);
    const ids = await page.locator('[id]').evaluateAll(items => items.map(item => item.id));
    assert.equal(new Set(ids).size, ids.length, 'Each reference anchor must remain unique');
    for (const button of await page.locator('[data-step]').all()) {
      await button.click();
      assert.equal(await page.getAttribute('[data-step][aria-pressed="true"]', 'data-step'), await button.getAttribute('data-step'));
      assert.ok((await page.textContent('#step-body')).length > 50);
    }
    await page.click('[data-step="0"]');
    for (const name of ['physical', 'recorded', 'simulation']) {
      await page.click(`[data-mode="${name}"]`);
      assert.equal(await page.locator(`[data-panel="${name}"]`).isVisible(), true);
      assert.equal(await page.locator('[data-panel]:visible').count(), 1);
    }
    assert.equal(fixtures.length, 8);
    for (const fixture of fixtures) {
      assert.equal(fixture.hardware_used, false);
      assert.equal(fixture.mode, 'SIMULATED SIGNED FIXTURES');
      await page.click(`[data-case="${fixture.scenario}"]`);
      assert.equal(await page.textContent('#case-decision'), fixture.pair.decision);
      assert.equal(await page.getAttribute('[data-case][aria-pressed="true"]', 'data-case'), fixture.scenario);
    }
    await page.click('[data-case="open"]');
    const localLinks = await page.locator('a[href^="#"]').evaluateAll(links => links.map(link => link.getAttribute('href').slice(1)));
    for (const target of localLinks) assert.ok(ids.includes(target), `Missing guide anchor ${target}`);
    const start = new URL(url);
    start.hash = 'protocol';
    await page.goto(start.href);
    assert.equal(await page.locator('#reference').getAttribute('open'), '');
    assert.equal(await page.locator('#protocol').isVisible(), true);
    await page.goto(url);
    mkdirSync(resolve(root, '.local/submission-kit'), { recursive: true });
    await page.screenshot({ path: resolve(root, '.local/submission-kit', `${prefix}-desktop.png`) });
    await page.locator('#transaction').scrollIntoViewIfNeeded();
    await page.screenshot({ path: resolve(root, '.local/submission-kit', `${prefix}-transaction.png`) });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(url);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: resolve(root, '.local/submission-kit', `${prefix}-mobile.png`) });
    await page.click('[data-mode="physical"]');
    assert.equal(await page.locator('[data-panel="physical"]').isVisible(), true);
    await page.click('[data-case="invalid"]');
    assert.equal(await page.textContent('#case-decision'), 'WAIT');
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    assert.deepEqual(errors, []);
    console.log('Guide checks passed: six steps, three rehearsal modes, eight actual software outcomes, deep references, unique anchors, desktop/mobile, and no page errors. No hardware or payment.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
