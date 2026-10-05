import { querySettlement, recordedPaymentDetails, publicBuyerRun } from './settlement.mjs';

const el = id => document.getElementById(id);
const controls = ['original', 'tamper', 'challenge', 'identity'];
let recorded, pin, differentKey;
let running = false;
let loadedRun = false, paymentVerified = false, lastChecks = null, sourceRevision = 0, watchCycle = 0;

function focusDemo(enabled) {
  document.body.classList.toggle('presentation', enabled);
  el('focus').setAttribute('aria-pressed', String(enabled));
  el('focus').textContent = enabled ? 'Show full page' : 'Focus demo';
}
el('focus').onclick = () => focusDemo(!document.body.classList.contains('presentation'));
focusDemo(new URL(location.href).searchParams.get('present') === '1');

function status(id, text, kind) {
  el(id).textContent = text;
  el(id).className = kind;
}

function renderScene(closed, decision) {
  const claim = typeof closed === 'boolean' ? (closed ? 'CLOSED' : 'OPEN') : 'UNAVAILABLE';
  el('scene-claim').textContent = `Receipt claim: ${claim}`;
  el('scene-decision').textContent = decision;
  el('gate-scene').dataset.claim = claim.toLowerCase();
  el('gate-scene').dataset.decision = decision.toLowerCase();
}

function renderAge(age, limit = 10, fresh = false) {
  const available = Number.isSafeInteger(age);
  const text = !available ? 'Unavailable' : age < 0 ? `${-age}s ahead`
    : age < 60 ? `${age}s old`
      : age < 3600 ? `${Math.floor(age / 60)}m ${age % 60}s old`
        : age < 86400 ? `${Math.floor(age / 3600)}h ${Math.floor(age % 3600 / 60)}m old`
          : `${Math.floor(age / 86400)}d ${Math.floor(age % 86400 / 3600)}h old`;
  el('evidence-age').textContent = text;
  el('evidence-age').title = available ? `${age} seconds since the signed measurement` : text;
  el('age-limit').textContent = `Maximum age ${limit}s`;
  const bounded = available ? Math.max(0, Math.min(limit, age)) : 0;
  el('age-fill').style.width = `${bounded / limit * 100}%`;
  el('age-track').dataset.fresh = String(fresh);
  el('age-track').setAttribute('aria-valuemax', String(limit));
  el('age-track').setAttribute('aria-valuenow', String(bounded));
  el('age-track').setAttribute('aria-valuetext', `${text}. Maximum age ${limit} seconds.`);
}

function message(r) {
  const s = r.result;
  return ['fieldproof-observation-v1', r.protocol, r.request_id, r.provider, r.capability,
    r.parameters.location, r.nonce, s.metric, s.sensor, Number(s.closed), s.stable_samples,
    s.total_samples, r.started_at, r.completed_at].join('|');
}

async function verifySignature(r, key) {
  const encoded = typeof r.receipt_signature === 'string' && r.receipt_signature.startsWith('v3:')
    ? r.receipt_signature.slice(3) : '';
  const signature = Uint8Array.from(atob(encoded), char => char.charCodeAt(0));
  return signature.length === 64 && btoa(String.fromCharCode(...signature)) === encoded &&
    crypto.subtle.verify({ name: 'ECDSA', hash: 'SHA-256' }, key, signature, new TextEncoder().encode(message(r)));
}

async function inspectContactStates() {
  try {
    const response = await fetch(new URL('./evidence/device-signed-contact-states.json', import.meta.url));
    if (!response.ok) throw new Error('Recorded input evidence is unavailable.');
    const evidence = await response.json();
    const rows = [];
    for (const [state, closed] of [['held', true], ['released', false]]) {
      const r = evidence[state]?.receipt, challenge = evidence[state]?.challenge;
      if (!r || !challenge || r.protocol !== 'capmesh/0.1' || r.status !== 'success' ||
          r.provider !== 'esp32-c6-96a2' || r.capability !== 'state.observe' ||
          typeof challenge.request_id !== 'string' || !/^[A-Za-z0-9_-]{1,16}$/.test(challenge.request_id) ||
          !Number.isInteger(challenge.nonce) || challenge.nonce < 1 || challenge.nonce > 0x7fffffff ||
          r.request_id !== challenge.request_id || r.nonce !== challenge.nonce ||
          r.parameters?.location !== 'demo-gate' || Object.keys(r.parameters).length !== 1 ||
          r.result?.metric !== 'gate.closed' || r.result.sensor !== 'gpio9-contact' ||
          r.result.closed !== closed || r.result.stable_samples !== 5 || r.result.total_samples !== 5 ||
          !Number.isSafeInteger(challenge.timestamp) || !Number.isSafeInteger(challenge.expiration) ||
          challenge.expiration <= challenge.timestamp ||
          !Number.isSafeInteger(r.started_at) || !Number.isSafeInteger(r.completed_at) ||
          r.started_at < challenge.timestamp - 2 || r.completed_at < r.started_at ||
          r.completed_at > challenge.expiration || Math.floor(Date.now() / 1000) - r.completed_at <= 10 ||
          !await verifySignature(r, pin)) {
        throw new Error('The recorded input pair failed signature, challenge, state, or expiration checks.');
      }
      const row = document.createElement('li');
      row.textContent = `BOOT ${state} → ${closed ? 'CLOSED' : 'OPEN'} · VALID signature · 5/5 samples · EXPIRED → WAIT`;
      rows.push(row);
    }
    el('contact-results').replaceChildren(...rows);
    status('contact-status', 'VERIFIED INPUT PAIR · Recorded, no payment', 'pass');
  } catch (error) {
    el('contact-results').replaceChildren();
    status('contact-status', 'NOT VERIFIED · ' + error.message, 'fail');
  }
}

function refreshDecision() {
  if (!lastChecks) return;
  const { r, challenge, authentic, bound, contract } = lastChecks, s = r.result;
  const now = Math.floor(Date.now() / 1000);
  const fresh = Number.isInteger(r.started_at) && Number.isInteger(r.completed_at) &&
    r.started_at >= challenge.created_at - 2 && r.started_at <= r.completed_at && r.completed_at <= now + 2 &&
    now - r.completed_at <= challenge.max_age_seconds;
  status('freshness', fresh ? 'FRESH' : 'EXPIRED', fresh ? 'pass' : 'expired');
  renderAge(now - r.completed_at, challenge.max_age_seconds, fresh);
  status('live-payment-check', paymentVerified ? 'VERIFIED' : 'NOT VERIFIED', paymentVerified ? 'pass' : 'expired');
  const accepted = authentic && bound && contract && fresh && (!loadedRun || paymentVerified);
  el('decision').textContent = accepted && !s.closed ? 'DISPATCH' : 'WAIT';
  el('decision').className = `decision ${accepted && !s.closed ? 'pass' : 'expired'}`;
  renderScene(s.closed, el('decision').textContent);
  el('reason').textContent = !authentic ? 'The receipt does not match the pinned signing key.'
    : !bound ? 'This receipt cannot answer a different buyer challenge.'
      : !contract ? 'The contact does not satisfy the buyer contract.'
        : !fresh ? 'The original signature is valid. The observation is too old for dispatch.'
          : loadedRun && !paymentVerified ? 'Fresh signed answer. Verify its reported payment before the combined demo decision.'
            : s.closed ? 'Fresh contact evidence says closed.' : 'Fresh contact evidence says open.';
}

async function experiment(mode = 'original') {
  if (running || !recorded) return;
  running = true;
  const revision = sourceRevision;
  lastChecks = null;
  renderAge(null);
  el('decision').textContent = 'WAIT';
  el('decision').className = 'decision expired';
  renderScene(undefined, 'WAIT');
  controls.forEach(id => { el(id).disabled = true; });
  const labels = { original: loadedRun ? 'Original buyer answer' : 'Original recorded answer', tamper: 'Altered contact state',
    challenge: 'Another buyer challenge', identity: 'Untrusted verification key' };
  el('experiment-label').textContent = labels[mode];
  controls.forEach(id => { el(id).setAttribute('aria-pressed', String(id === mode)); });
  try {
    const r = structuredClone(recorded.receipt);
    const challenge = structuredClone(recorded.challenge);
    if (mode === 'tamper') r.result.closed = !r.result.closed;
    if (mode === 'challenge') challenge.nonce = challenge.nonce === 0x7fffffff ? 1 : challenge.nonce + 1;
    const key = mode === 'identity' ? differentKey : pin;
    const authentic = await verifySignature(r, key);
    if (revision !== sourceRevision) return;
    const bound = r.protocol === 'capmesh/0.1' && r.status === 'success' && r.provider === 'esp32-c6-96a2' &&
      r.capability === 'state.observe' && r.request_id === challenge.id && r.nonce === challenge.nonce &&
      r.parameters.location === challenge.location && Object.keys(r.parameters).length === 1;
    const s = r.result;
    const contract = s.metric === 'gate.closed' && s.sensor === 'gpio9-contact' && typeof s.closed === 'boolean' &&
      s.total_samples === 5 && s.stable_samples === 5;
    status('signature', authentic ? 'VALID' : 'REJECTED', authentic ? 'pass' : 'fail');
    status('binding', bound ? 'MATCHES' : 'REJECTED', bound ? 'pass' : 'fail');
    status('contract', contract ? '5/5 AGREE' : 'REJECTED', contract ? 'pass' : 'fail');
    lastChecks = { r, challenge, authentic, bound, contract };
    refreshDecision();
    el('state').textContent = s.closed ? 'CLOSED' : 'OPEN';
    el('payload').textContent = JSON.stringify({ experiment: mode, challenge, receipt: r }, null, 2);
  } catch {
    if (revision !== sourceRevision) return;
    status('signature', 'REJECTED', 'fail');
    el('decision').textContent = 'WAIT';
    renderScene(undefined, 'WAIT');
    el('reason').textContent = 'Receipt verification failed. Check the evidence and public pin.';
  } finally {
    if (revision === sourceRevision) {
      running = false;
      controls.forEach(id => { el(id).disabled = !recorded; });
    }
  }
}

function clearSource(reason) {
  sourceRevision += 1;
  running = false;
  recorded = null;
  lastChecks = null;
  renderAge(null);
  paymentVerified = false;
  controls.forEach(id => { el(id).disabled = true; });
  el('chain-query').disabled = true;
  status('signature', 'NOT VERIFIED', 'fail');
  status('binding', 'UNAVAILABLE', ''); status('contract', 'UNAVAILABLE', ''); status('freshness', 'UNAVAILABLE', 'expired');
  status('chain-status', 'NOT QUERIED', ''); status('live-payment-check', 'NOT VERIFIED', 'expired');
  status('proof-payment-check', 'NOT QUERIED', '');
  el('proof-payment-amount').textContent = 'Unavailable';
  el('decision').className = 'decision expired';
  el('decision').textContent = 'WAIT'; renderScene(undefined, 'WAIT');
  el('receipt-source').textContent = 'No usable buyer output / demo-gate';
  el('reason').textContent = reason; el('source-status').textContent = reason;
  for (const id of ['state', 'measured', 'payment-payer', 'payment-merchant', 'payment-amount']) el(id).textContent = 'Unavailable';
  for (const id of ['transaction', 'payment-explorer']) el(id).removeAttribute('href');
  el('payload').textContent = 'No usable buyer output.';
  el('chain-summary').textContent = 'No current transfer check.'; el('chain-result').textContent = 'No network query yet.';
}

async function showPurchase(input, buyer = false) {
  const next = publicBuyerRun(input);
  clearSource('Verifying this buyer output.');
  recorded = next; loadedRun = buyer;
  el('live-payment-row').hidden = !buyer;
  el('source-banner').textContent = buyer ? 'Loaded independent buyer output · Solana Devnet' : 'Recorded hardware evidence · Solana Devnet';
  el('source-description').textContent = buyer ? 'This prototype purchases one contact observation. This inspector verifies the selected buyer output.' : 'This prototype purchases one contact observation. This inspector uses recorded evidence.';
  el('receipt-source').textContent = buyer ? `Buyer run ${next.purchase_id} / demo-gate` : 'Recorded purchase / demo-gate';
  el('stage-source').textContent = buyer ? `Buyer run ${next.purchase_id} / browser sends no funds` : 'Recorded device evidence / actual Devnet test payment';
  el('stage-heading').textContent = buyer ? 'One transaction. Independent buyer checks.' : 'One paid answer. Four buyer checks.';
  el('payment-source').textContent = buyer ? 'Loaded buyer settlement / verify it against Solana / no browser payment' : 'Actual recorded test payment · October 1 · No new payment here';
  el('source-status').textContent = buyer ? 'Loaded buyer output. The file supplies its challenge. The installed public pin verifies the device. Chain verification remains separate.' : 'Installed buyer pin remains the trust root.';
  el('measured').textContent = new Date(next.receipt.completed_at * 1000).toISOString().replace('T', ' ').replace('.000Z', ' UTC');
  el('transaction').href = 'https://explorer.solana.com/tx/' + encodeURIComponent(next.settlement.transaction) + '?cluster=devnet';
  const payment = recordedPaymentDetails(next);
  el('payment-payer').textContent = payment.payer; el('payment-merchant').textContent = payment.merchant;
  el('payment-amount').textContent = payment.amount_usdc.toFixed(3);
  el('proof-payment-amount').textContent = `${payment.amount_usdc.toFixed(3)} Devnet USDC`;
  el('payment-explorer').href = el('transaction').href;
  el('chain-summary').textContent = 'The displayed terms come from the buyer output. Run the read-only query to verify the transfer.';
  el('chain-query').disabled = false;
  el('chain-query').textContent = buyer ? 'Verify buyer payment' : 'Verify recorded payment';
  await experiment();
}

async function verifyPayment() {
  if (!recorded) return;
  const target = recorded, revision = sourceRevision;
  paymentVerified = false; refreshDecision();
  el('chain-query').disabled = true;
  status('chain-status', 'CHECKING', 'expired');
  status('proof-payment-check', 'CHECKING', 'expired');
  el('chain-summary').textContent = 'Checking the actual transfer. No funds move.';
  el('chain-result').textContent = 'Querying Solana Devnet. No payment or hardware request occurs.';
  try {
    const result = await querySettlement(target);
    if (revision !== sourceRevision) return;
    paymentVerified = true;
    status('chain-status', 'VERIFIED TRANSFER', 'pass');
    status('proof-payment-check', 'VERIFIED TRANSFER', 'pass');
    el('chain-summary').textContent = `Verified: buyer −0.001 USDC → merchant +0.001 USDC. Confirmed slot ${result.slot}.`;
    el('chain-result').textContent = JSON.stringify(result, null, 2);
  } catch (error) {
    if (revision !== sourceRevision) return;
    status('chain-status', 'NOT VERIFIED', 'expired');
    status('proof-payment-check', 'NOT VERIFIED', 'expired');
    el('chain-result').textContent = error.name === 'TimeoutError' ? 'The Devnet RPC query timed out after 15 seconds. Try again.' : error.message;
    el('chain-summary').textContent = el('chain-result').textContent;
  } finally {
    if (revision === sourceRevision) { el('chain-query').disabled = false; refreshDecision(); }
  }
}

async function watchBuyerRun() {
  const cycle = ++watchCycle, deadline = Date.now() + 120000;
  clearSource('Waiting for one independent buyer output. This browser sends no funds and invokes no hardware.');
  el('stage-source').textContent = 'Waiting for a new independent buyer run / no browser payment';
  el('receipt-source').textContent = 'Waiting for buyer output / demo-gate';
  while (cycle === watchCycle && Date.now() < deadline) {
    try {
      const response = await fetch('/buyer-run', { cache: 'no-store', signal: AbortSignal.timeout(3000) });
      if (cycle !== watchCycle) return;
      if (response.ok) {
        const text = await response.text();
        if (cycle !== watchCycle) return;
        if (text.length > 32768) throw new Error('Buyer output exceeds the inspection limit.');
        await showPurchase(JSON.parse(text), true);
        if (cycle !== watchCycle) return;
        await verifyPayment(); // One automatic read-only query. No payment retry occurs.
        return;
      }
      if (response.status !== 404) el('reason').textContent = 'Buyer output is incomplete or failed. Preserve the independent buyer terminal result.';
    } catch {
      if (cycle === watchCycle) el('reason').textContent = 'Buyer output is unavailable or failed validation. No recorded fallback was substituted.';
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  if (cycle === watchCycle) clearSource('The two-minute buyer monitor ended. Check the gateway output path, then reload this view.');
}

async function init() {
  const pinsResponse = await fetch(new URL('./receipt-keys.json', import.meta.url));
  if (!pinsResponse.ok) throw new Error('Installed buyer configuration is unavailable.');
  const pins = await pinsResponse.json();
  if (pins.algorithm !== 'ecdsa-p256-sha256') throw new Error('Unsupported buyer identity algorithm.');
  const sec1 = pins.providers['esp32-c6-96a2'];
  if (!/^04[0-9a-f]{128}$/.test(sec1 || '')) throw new Error('The buyer configuration has no valid device pin.');
  const bytes = Uint8Array.from(sec1.match(/../g), pair => parseInt(pair, 16));
  pin = await crypto.subtle.importKey('raw', bytes, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['verify']);
  differentKey = (await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign', 'verify'])).publicKey;
  el('pin').textContent = JSON.stringify({ algorithm: pins.algorithm, provider: 'esp32-c6-96a2', sec1_hex: sec1 }, null, 2);
  controls.forEach(id => { el(id).onclick = () => experiment(id); });
  el('chain-query').onclick = verifyPayment;
  const archived = async () => {
    const cycle = ++watchCycle;
    clearSource('Loading committed evidence.');
    try {
      const response = await fetch(new URL('./evidence/device-signed-purchase.json', import.meta.url));
      if (!response.ok) throw new Error('Committed evidence is unavailable.');
      const input = await response.json();
      if (cycle === watchCycle) await showPurchase(input);
    } catch { if (cycle === watchCycle) clearSource('Committed evidence is unavailable.'); }
  };
  el('use-recorded').disabled = false;
  el('use-recorded').onclick = archived;
  el('run-file').disabled = false;
  el('run-file').onchange = async () => {
    const file = el('run-file').files[0]; if (!file) return;
    const cycle = ++watchCycle;
    clearSource('Loading selected buyer output.');
    try {
      if (file.size > 32768) throw new Error('File too large');
      const input = JSON.parse(await file.text());
      if (cycle === watchCycle) await showPurchase(input, true);
    } catch { if (cycle === watchCycle) clearSource('Rejected buyer output. Use the buyer result JSON, never a wallet keypair.'); }
    el('run-file').value = '';
  };
  setInterval(refreshDecision, 250);
  if (new URL(location.href).searchParams.get('live') === '1') void watchBuyerRun();
  else await archived();
  await inspectContactStates();
}

init().catch(error => {
  clearSource(error.message);
});
