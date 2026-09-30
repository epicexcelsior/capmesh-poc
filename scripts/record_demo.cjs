// Record actual local browser interactions. Requires an installed Playwright package and Chromium.
const { resolve, dirname } = require('node:path');
const { mkdirSync } = require('node:fs');
const { execFileSync } = require('node:child_process');
const { chromium } = require(process.argv[2] || 'playwright');
const root = resolve(__dirname, '..');
const output = resolve(root, process.argv[3] || 'docs/assets');
mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, recordVideo: { dir: output, size: { width: 1280, height: 900 } } });
  const page = await context.newPage();
  const start = Date.now();
  async function scene(origin, mode) {
    await page.goto(origin);
    await page.waitForFunction(() => !document.querySelector('#quote').disabled);
    await page.waitForTimeout(3000);
    await page.click('#quote');
    await page.waitForFunction(() => !document.querySelector('#observe').hidden);
    await page.waitForTimeout(3000);
    await page.click('#observe');
    await page.waitForFunction(() => !document.querySelector('#observe').disabled);
    if (mode === 'open') {
      await page.waitForFunction(() => document.querySelector('#decision').textContent === 'DISPATCH');
      console.log('Recorded fresh open evidence and DISPATCH');
    } else {
      await page.waitForFunction(() => document.querySelector('#state').textContent === 'CLOSED');
      console.log('Recorded closed evidence and WAIT');
    }
    await page.waitForTimeout(4000);
  }
  try {
    await scene('http://127.0.0.1:4022', 'open');
    await page.waitForFunction(() => document.querySelector('#reason').textContent.includes('expired'));
    console.log('Recorded expired evidence and WAIT');
    await page.waitForTimeout(3000);
    await scene('http://127.0.0.1:4024', 'closed');
    const attacks = JSON.parse(execFileSync('uv', ['run', '--project', 'host', 'capmesh', 'observe-demo', '--simulated', '--ledger', ':memory:'], { cwd: root, encoding: 'utf8' }));
    if (!attacks.attacks_passed) throw new Error('Adversarial rehearsal failed');
    await page.evaluate(result => {
      const section = document.createElement('section');
      section.className = 'section';
      section.id = 'recorded-attacks';
      const h = document.createElement('h2'); h.textContent = 'Executed CLI evidence checks / simulated';
      const pre = document.createElement('pre');
      pre.textContent = JSON.stringify({ selected: result.provider, rejected: result.rejected_providers, attacks: result.attacks }, null, 2);
      section.append(h, pre); document.querySelector('main').append(section);
      section.scrollIntoView();
    }, attacks);
    console.log('Recorded actual stale-provider and replay-check results');
    await page.waitForTimeout(12000);
    await page.goto('http://127.0.0.1:4022');
    await page.waitForFunction(() => !document.querySelector('#quote').disabled);
    const remaining = 70000 - (Date.now() - start);
    if (remaining > 0) await page.waitForTimeout(Math.min(remaining, 40000));
  } finally {
    const video = page.video();
    await context.close();
    await video.saveAs(resolve(output, 'fieldproof-demo.webm'));
    await video.delete();
    await browser.close();
    console.log('Saved fieldproof-demo.webm');
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
