// Record verified evidence and browser experiments. This script never pays or invokes hardware.
const { chromium } = require(process.argv[2] || 'playwright');
const { mkdirSync, readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const root = resolve(__dirname, '..');
const output = resolve(root, process.argv[3] || '.local/identity-recording');
const origin = process.argv[4] || 'http://127.0.0.1:4021';
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
    await page.goto(origin);
    await page.waitForFunction(() => !document.getElementById('quote').disabled);
    await caption('FieldProof: a buyer purchases fresh contact evidence before an immediate logistics decision. One observer, one location. BOOT represents the contact.');
    await pause(12);
    await page.click('#quote');
    await page.waitForFunction(() => document.getElementById('reason').textContent.includes('402 quote'));
    await caption('Actual x402 V2 quote: 0.001 Solana Devnet USDC. This recording creates an unpaid quote. The next scene inspects an earlier verified paid purchase.');
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
    await page.goto(new URL('/proof', origin).href);
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'VALID');
    await page.evaluate(() => window.scrollTo(0, 230));
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
      const heading = document.createElement('h2'); heading.textContent = 'Executed hardware checks after reset';
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
      const heading = document.createElement('h2'); heading.textContent = 'Earn one useful decision.';
      const p = document.createElement('p'); p.textContent = 'Next: an authorized operator, an external contact, and a recurring buyer workflow with a matching freshness window. A ten-second observation cannot predict a distant arrival.';
      const limit = document.createElement('p'); limit.textContent = 'Current limits: unencrypted device storage, one observer, host-anchored time, no site access control, no customer pilot, no peaq activation.';
      section.append(heading, p, limit); document.querySelector('main').append(section); section.scrollIntoView();
    });
    await caption('Machine-economy hypothesis: sell a permitted fact that changes a buyer decision. Measure repeat demand and delivery quality before adding coverage.');
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
