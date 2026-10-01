// Record actual local browser interactions. Requires an installed Playwright package and Chromium.
const { resolve } = require('node:path');
const { mkdirSync } = require('node:fs');
const { execFileSync } = require('node:child_process');
const { chromium } = require(process.argv[2] || 'playwright');
const root = resolve(__dirname, '..');
const submission = process.argv.includes('--submission');
const output = resolve(root, process.argv[3] && !process.argv[3].startsWith('--') ? process.argv[3] : 'docs/assets');
mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, recordVideo: { dir: output, size: { width: 1280, height: 900 } } });
  const page = await context.newPage();
  const start = Date.now();
  let complete = false;
  async function caption(text) {
    await page.evaluate(text => {
      let note = document.querySelector('#recording-caption');
      if (!note) {
        note = document.createElement('div'); note.id = 'recording-caption';
        Object.assign(note.style, { position: 'fixed', bottom: '0', left: '0', right: '0', zIndex: '100',
          background: '#17252b', color: '#fff', padding: '18px 30px', font: '18px/1.5 sans-serif', borderTop: '3px solid #4cb5aa' });
        document.body.append(note);
      }
      note.textContent = text;
    }, text);
  }
  async function scene(origin, mode) {
    await page.goto(origin);
    await page.waitForFunction(() => !document.querySelector('#quote').disabled);
    if (submission) await caption(mode === 'physical'
      ? 'Real ESP32-C6 input, simulated settlement. The released BOOT button represents an open gate contact.'
      : mode === 'closed' ? 'Closed-contact rehearsal: both contact and settlement are simulated. The buyer returns WAIT.'
        : 'A machine buys one fresh physical fact. This first scene simulates contact and settlement.');
    await page.waitForTimeout(3000);
    await page.click('#quote');
    await page.waitForFunction(() => !document.querySelector('#observe').hidden);
    await page.waitForTimeout(3000);
    await page.click('#observe');
    await page.waitForFunction(() => !document.querySelector('#observe').disabled);
    if (mode !== 'closed') {
      await page.waitForFunction(() => document.querySelector('#decision').textContent === 'DISPATCH');
      if (mode === 'physical') await page.waitForFunction(() => document.querySelector('#instruction').textContent.includes('physical-contact-demo'));
      console.log('Recorded fresh open evidence and DISPATCH');
    } else {
      await page.waitForFunction(() => document.querySelector('#state').textContent === 'CLOSED');
      console.log('Recorded closed evidence and WAIT');
    }
    await page.waitForTimeout(4000);
  }
  try {
    if (submission) {
      await page.goto('http://127.0.0.1:4022');
      await page.waitForFunction(() => !document.querySelector('#quote').disabled);
      await caption('FieldProof: fresh physical evidence before an autonomous logistics agent acts. One location, one contact, one dispatch decision.');
      await page.waitForTimeout(14000);
      const created = await fetch('http://127.0.0.1:4021/requests', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nonce: require('node:crypto').randomInt(1, 0x7fffffff) }) });
      if (created.status !== 201) throw new Error('Public gateway quote creation failed');
      const purchase = await created.json();
      const quote = await fetch(purchase.observe_url);
      if (quote.status !== 402) throw new Error('Public gateway did not require payment');
      const required = await quote.json();
      await page.evaluate(required => {
        const section = document.createElement('section'); section.className = 'section';
        const h = document.createElement('h2'); h.textContent = 'Live public-facilitator payment requirement';
        const pre = document.createElement('pre'); pre.textContent = JSON.stringify(required, null, 2);
        section.append(h, pre); document.querySelector('main').prepend(section); window.scrollTo(0, 0);
      }, required);
      await caption('Actual x402 V2 quote: Solana Devnet USDC, 0.001 USDC. This scene retrieves a quote and executes no payment. Paid-chain evidence is documented separately.');
      await page.waitForTimeout(17000);
    }
    await scene('http://127.0.0.1:4022', 'open');
    await page.waitForFunction(() => document.querySelector('#reason').textContent.includes('expired'));
    console.log('Recorded expired evidence and WAIT');
    if (submission) await caption('Freshness is a buyer constraint. After ten seconds, the same receipt produces WAIT. A cached response never refreshes its timestamp.');
    await page.waitForTimeout(3000);
    if (submission) {
      await scene('http://127.0.0.1:4023', 'physical');
      await caption('The device binds location, result, nonce, samples, and time to its receipt. Five matching samples are agreement, not calibrated confidence.');
      await page.waitForTimeout(7000);
    }
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
    if (submission) await caption('Executed checks reject the cheaper stale provider, replayed evidence, changed challenges, changed states, and repeated device requests.');
    await page.waitForTimeout(12000);
    await page.goto('http://127.0.0.1:4022');
    await page.waitForFunction(() => !document.querySelector('#quote').disabled);
    if (submission) await caption('Machine-economy mechanism: the observer sells useful evidence, the buyer limits spending and freshness, and unmet demand guides future installations. No peaq activation or production trust claim.');
    const duration = submission ? 150000 : 70000;
    while (Date.now() - start < duration) await page.waitForTimeout(Math.min(duration - (Date.now() - start), 30000));
    if (submission && Date.now() - start > 175000) throw new Error('The submission recording exceeded the three-minute budget');
    complete = true;
  } finally {
    const video = page.video();
    await context.close();
    const name = submission ? 'fieldproof-submission.webm' : 'fieldproof-demo.webm';
    if (complete) await video.saveAs(resolve(output, name));
    await video.delete();
    await browser.close();
    if (complete) console.log(`Saved ${name}`);
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
