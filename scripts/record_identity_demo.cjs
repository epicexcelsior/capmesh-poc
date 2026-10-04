// Record verified evidence and browser experiments. This script never pays or invokes hardware.
const { chromium } = require(process.argv[2] || 'playwright');
const { existsSync, mkdirSync, readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const root = resolve(__dirname, '..');
const output = resolve(root, process.argv[3] || '.local/identity-recording');
const origin = process.argv[4] || 'http://127.0.0.1:4021';
if (existsSync(resolve(output, 'fieldproof-signed-receipt.webm'))) throw new Error('Recording output already exists. Select a new directory.');
const evidence = JSON.parse(readFileSync(resolve(root, 'docs/evidence/device-signed-purchase.json')));
const checks = JSON.parse(readFileSync(resolve(root, 'docs/evidence/receipt-identity-checks.json')));
mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 },
    recordVideo: { dir: output, size: { width: 1280, height: 900 } } });
  const page = await context.newPage();
  const start = Date.now();
  let complete = false;
  async function caption(text) {
    await page.evaluate(text => {
      let note = document.getElementById('recording-caption');
      if (!note) {
        note = document.createElement('div'); note.id = 'recording-caption';
        Object.assign(note.style, { position: 'fixed', bottom: '0', left: '0', right: '0', zIndex: '100',
          background: '#183146', color: '#eef4f8', padding: '18px 30px', font: '18px/1.5 sans-serif', borderTop: '3px solid #067b65' });
        document.body.append(note);
      }
      note.textContent = text;
    }, text);
  }
  async function pause(seconds) { await page.waitForTimeout(seconds * 1000); }
  try {
    const healthResponse = await fetch(new URL('/health', origin), { signal: AbortSignal.timeout(5000) });
    if (!healthResponse.ok) throw new Error('The local gateway is unavailable.');
    const health = await healthResponse.json();
    if (!['simulated settlement; no funds moved', 'Solana Devnet; physical contact demo'].includes(health.mode)) {
      throw new Error('The gateway has an unsupported recording mode.');
    }
    const simulatedQuote = health.mode === 'simulated settlement; no funds moved';
    await page.goto(origin);
    await page.waitForFunction(() => !document.getElementById('quote').disabled);
    await caption('Company hypothesis: machines use physical infrastructure another operator owns. This prototype buys one contact observation. BOOT represents the contact.');
    await pause(12);
    await page.click('#quote');
    await page.waitForFunction(() => document.getElementById('reason').textContent.includes('402 quote'));
    await page.evaluate(() => {
      const payload = document.getElementById('receipt');
      payload.closest('details').open = true;
      payload.style.maxHeight = '240px';
      window.scrollTo(0, document.querySelector('.desk').offsetTop - 24);
    });
    await caption(`x402 V2 quote: 0.001 Devnet USDC. ${simulatedQuote ? 'This quote uses a simulated facilitator.' : 'This quote uses the Devnet gateway.'} No payment occurs here. Next: an earlier real paid purchase.`);
    await pause(12);
    await page.evaluate(evidence => {
      const section = document.createElement('section'); section.className = 'section';
      const label = document.createElement('div'); label.className = 'label'; label.textContent = 'Recorded verified purchase / test funds';
      const heading = document.createElement('h2'); heading.textContent = 'Paid on Devnet. Measured on the ESP32.';
      const pre = document.createElement('pre');
      pre.textContent = JSON.stringify({ measured_at_utc: new Date(evidence.purchase.receipt.completed_at * 1000).toISOString(),
        price_usdc: '0.001', purchase_id: evidence.purchase.purchase_id,
        accepted_when_fresh: evidence.purchase.decision, age_at_acceptance_seconds: evidence.purchase.evidence_age_seconds,
        receipt_identity: evidence.purchase.receipt_identity, settlement: evidence.purchase.settlement,
        confirmed_slot: evidence.chain_check.slot, token_changes: evidence.chain_check.token_changes }, null, 2);
      section.append(label, heading, pre); document.querySelector('main').prepend(section); window.scrollTo(0, 0);
    }, evidence);
    await caption('Recorded paid test: the independent CLI buyer accepted the device-signed receipt at seven seconds of age. RPC confirmed exactly 1,000 USDC base units transferred.');
    await pause(22);
    await page.goto(new URL('/proof?present=1', origin).href);
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'VALID');
    await page.evaluate(() => window.scrollTo(0, 0));
    await caption('Your browser verifies the actual P-256 signature. The original receipt is authentic, but now expired. A signature cannot extend a buyer freshness limit.');
    await pause(18);
    await page.click('#tamper');
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'REJECTED');
    await caption('Attack 1: flip the reported contact state. The unchanged device signature fails. The buyer remains at WAIT.');
    await pause(13);
    await page.click('#challenge');
    await page.waitForFunction(() => document.getElementById('binding').textContent === 'REJECTED');
    await caption('Attack 2: use the original receipt for another nonce. Its signature remains valid, but the buyer challenge does not match.');
    await pause(13);
    await page.click('#identity');
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'REJECTED');
    await caption('Attack 3: verify with another public key. Discovery cannot replace the buyer pin. The receipt fails authentication.');
    await pause(13);
    await page.click('#original');
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'VALID');
    await page.evaluate(checks => {
      const section = document.createElement('section'); section.className = 'notice';
      const heading = document.createElement('h2'); heading.textContent = 'Recorded hardware checks after reset';
      const pre = document.createElement('pre');
      pre.textContent = JSON.stringify({ key_survived_reset: checks.persistence.key_after_reset_matches_pin,
        new_observation_after_reset: checks.after_reset.decision.receipt_identity,
        attacks: checks.after_reset.attacks, attacks_passed: checks.after_reset.attacks_passed }, null, 2);
      section.append(heading, pre); document.querySelector('main').append(section); section.scrollIntoView();
    }, checks);
    await caption('The signing key survived reset. Real BLE checks rejected replay, altered state, another challenge, and a receipt forged with the public command HMAC.');
    await pause(17);
    await page.evaluate(() => {
      const section = document.createElement('section'); section.className = 'notice';
      const heading = document.createElement('h2'); heading.textContent = 'One fleet. One operator. Then test reuse.';
      const p = document.createElement('p'); p.textContent = 'Test one visiting robot workflow at an authorized external facility. A second independent facility tests integration reuse. Charge for integration and support before relying on transaction volume.';
      const limit = document.createElement('p'); limit.textContent = 'Current limits: unencrypted device storage, one observer, host-anchored time, no site access control, no customer pilot, no peaq activation.';
      const main = document.querySelector('main');
      main.style.paddingBottom = '160px';
      section.append(heading, p, limit); main.append(section); section.scrollIntoView({ block: 'center' });
    });
    await caption('Current result: payment plus a fresh signed observation. Next: validate the buyer, permitted service, and recurring budget. peaq readiness and offline inputs work. No identity is activated.');
    while (Date.now() - start < 150000) await pause(Math.min(10, (150000 - (Date.now() - start)) / 1000));
    if (Date.now() - start > 175000) throw new Error('Recording exceeded the three-minute limit');
    complete = true;
  } finally {
    const video = page.video();
    await context.close();
    if (complete) await video.saveAs(resolve(output, 'fieldproof-signed-receipt.webm'));
    await video.delete(); await browser.close();
    if (complete) console.log('Saved 150-second signed-receipt walkthrough. Recorded purchase and live browser verification. No audio, payment, or hardware invocation during capture.');
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
