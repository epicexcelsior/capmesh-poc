// Record the judge's short path through the exported inspector. Read-only, no hardware or payment.
const { chromium } = require(process.argv[2] || 'playwright');
const { existsSync, mkdirSync, writeFileSync } = require('node:fs');
const { resolve } = require('node:path');
const output = resolve(process.argv[3] || '.local/receipt-story');
const site = new URL(process.argv[4] || 'http://127.0.0.1:8789/judge-demo-final/');
if (!['http:', 'https:'].includes(site.protocol) || !site.pathname.endsWith('/') ||
    site.search || site.hash || site.username || site.password) {
  throw new Error('Use an HTTP or HTTPS directory URL ending in /, without credentials, query, or fragment.');
}
if (existsSync(output)) throw new Error('Recording directory already exists. Select a new name.');
mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 },
    recordVideo: { dir: output, size: { width: 1280, height: 900 } }, serviceWorkers: 'block' });
  const page = await context.newPage();
  const started = Date.now();
  const errors = [], rpcRequests = [];
  let complete = false, settlement;
  page.on('pageerror', error => errors.push(error.message));
  await context.route('**/*', async route => {
    const request = route.request(), url = new URL(request.url());
    if (url.origin === site.origin && request.method() === 'GET' && url.pathname.startsWith(site.pathname)) {
      return route.continue();
    }
    if (url.href === 'https://api.devnet.solana.com/' && request.method() === 'POST') {
      const body = request.postDataJSON();
      if (body.method === 'getTransaction' && rpcRequests.length === 0) {
        rpcRequests.push(body);
        return route.continue();
      }
    }
    errors.push(`Blocked unexpected request: ${request.method()} ${url.origin}${url.pathname}`);
    await route.abort();
  });
  async function caption(text) {
    await page.evaluate(text => {
      let note = document.getElementById('recording-caption');
      if (!note) {
        note = document.createElement('div'); note.id = 'recording-caption';
        Object.assign(note.style, { position: 'fixed', bottom: '0', left: '0', right: '0', zIndex: '100',
          background: '#183146', color: '#eef4f8', padding: '18px 30px', font: '19px/1.5 sans-serif',
          borderTop: '3px solid #067b65' });
        document.body.append(note);
      }
      note.textContent = text;
    }, text);
  }
  async function pause(seconds) { await page.waitForTimeout(seconds * 1000); }
  async function receipt() {
    await page.goto(new URL('index.html?present=1', site).href);
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'VALID');
    await page.evaluate(() => window.scrollTo(0, document.getElementById('receipt').offsetTop - 18));
  }
  try {
    // The diagram lives inside an HTML page so captions work in normal HTML, not an SVG document.
    await page.goto(new URL('guide.html#transaction', site).href);
    await page.locator('#transaction figure').scrollIntoViewIfNeeded();
    await caption('A visiting robot needs a current answer from another operator. Solana records payment. Bluetooth carries the physical question and signed answer.');
    await pause(9);
    await page.goto(new URL('index.html#payment', site).href);
    await page.waitForFunction(() => !document.getElementById('chain-query').disabled);
    await caption('Actual recorded payment: 0.001 Devnet USDC. This query verifies the October 1 transaction. It sends no funds and measures no hardware.');
    await page.click('#chain-query');
    await page.waitForFunction(() => ['VERIFIED TRANSFER', 'NOT VERIFIED'].includes(document.getElementById('chain-status').textContent), null, { timeout: 20000 });
    if (await page.textContent('#chain-status') !== 'VERIFIED TRANSFER') throw new Error('Actual Devnet payment query failed. No completed video was saved.');
    settlement = JSON.parse(await page.textContent('#chain-result'));
    await page.locator('#payment').scrollIntoViewIfNeeded();
    await pause(12);
    await receipt();
    await caption('The real receipt claims OPEN. Its signature is valid. Its ten-second useful-time window expired, so the buyer remains at WAIT.');
    await pause(12);
    for (const [id, check, expected, text] of [
      ['tamper', 'signature', 'REJECTED', 'Flip the contact state. The device signature fails. The illustration follows the altered claim, but the buyer remains at WAIT.'],
      ['challenge', 'binding', 'REJECTED', 'Change the buyer challenge. The original signature remains valid, but the answer cannot serve this different question. WAIT.'],
      ['identity', 'signature', 'REJECTED', 'Use another public key. The receipt fails authentication. Discovery cannot replace the key the buyer already trusts. WAIT.'],
    ]) {
      await page.click('#' + id);
      await page.waitForFunction(([id, expected]) => document.getElementById(id).textContent === expected, [check, expected]);
      if (await page.textContent('#scene-decision') !== 'WAIT') throw new Error('The illustration did not preserve rejection.');
      await caption(text);
      await pause(7);
    }
    await page.click('#original');
    await page.waitForFunction(() => document.getElementById('signature').textContent === 'VALID');
    await page.click('#focus');
    await page.waitForFunction(() => document.getElementById('contact-status').textContent.startsWith('VERIFIED INPUT PAIR'));
    await page.locator('section[aria-label="Recorded physical input checks"]').scrollIntoViewIfNeeded();
    await caption('Two separate real input checks: BOOT held means CLOSED. BOOT released means OPEN. Both signatures verify. These checks moved no funds.');
    await pause(9);
    await page.evaluate(() => window.scrollTo(0,
      document.querySelector('section[aria-label="Physical-service direction"]').offsetTop - 24));
    await caption('Next: one fleet and one authorized facility, then test integration reuse. Customer demand remains unvalidated. peaq identity activation remains incomplete.');
    await pause(12);
    if (errors.length || rpcRequests.length !== 1 || Date.now() - started > 175000) {
      throw new Error('The recording failed its request, page-error, or duration checks: ' + JSON.stringify(errors));
    }
    complete = true;
  } finally {
    const video = page.video();
    await context.close();
    if (complete) {
      await video.saveAs(resolve(output, 'fieldproof-receipt-story.webm'));
      writeFileSync(resolve(output, 'recording.json'), JSON.stringify({ captured_at_utc: new Date().toISOString(),
        mode: 'RECORDED EVIDENCE / ACTUAL READ-ONLY DEVNET QUERY', site: site.href,
        duration_ms: Date.now() - started, rpc_requests: rpcRequests, settlement,
        page_errors: errors, hardware_used: false, funds_sent: false, audio: false }, null, 2) + '\n');
      console.log('Saved short visual receipt story and actual chain-query record. No payment, hardware invocation, or audio.');
    }
    await video.delete();
    await browser.close();
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
