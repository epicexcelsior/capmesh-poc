import { querySettlement, recordedPaymentDetails } from './settlement.mjs';

const el = id => document.getElementById(id);
const controls = ['original', 'tamper', 'challenge', 'identity'];
let recorded, pin, differentKey;
let running = false;

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

async function experiment(mode = 'original') {
  if (running || !recorded) return;
  running = true;
  controls.forEach(id => { el(id).disabled = true; });
  const labels = { original: 'Original recorded answer', tamper: 'Altered contact state',
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
    const bound = r.protocol === 'capmesh/0.1' && r.status === 'success' && r.provider === 'esp32-c6-96a2' &&
      r.capability === 'state.observe' && r.request_id === challenge.id && r.nonce === challenge.nonce &&
      r.parameters.location === challenge.location && Object.keys(r.parameters).length === 1;
    const s = r.result;
    const contract = s.metric === 'gate.closed' && s.sensor === 'gpio9-contact' && typeof s.closed === 'boolean' &&
      s.total_samples === 5 && s.stable_samples === 5;
    const now = Math.floor(Date.now() / 1000);
    const fresh = Number.isInteger(r.started_at) && Number.isInteger(r.completed_at) &&
      r.started_at >= challenge.created_at - 2 && r.started_at <= r.completed_at && r.completed_at <= now + 2 &&
      now - r.completed_at <= challenge.max_age_seconds;
    status('signature', authentic ? 'VALID' : 'REJECTED', authentic ? 'pass' : 'fail');
    status('binding', bound ? 'MATCHES' : 'REJECTED', bound ? 'pass' : 'fail');
    status('contract', contract ? '5/5 AGREE' : 'REJECTED', contract ? 'pass' : 'fail');
    status('freshness', fresh ? 'FRESH' : 'EXPIRED', fresh ? 'pass' : 'expired');
    const accepted = authentic && bound && contract && fresh;
    el('decision').textContent = accepted && !s.closed ? 'DISPATCH' : 'WAIT';
    el('reason').textContent = !authentic ? 'The receipt does not match the pinned signing key.'
      : !bound ? 'This receipt cannot answer a different buyer challenge.'
        : !contract ? 'The contact does not satisfy the buyer contract.'
          : !fresh ? 'The original signature is valid. The recorded evidence is too old for dispatch.'
            : s.closed ? 'Fresh contact evidence says closed.' : 'Fresh contact evidence says open.';
    el('state').textContent = s.closed ? 'CLOSED' : 'OPEN';
    el('payload').textContent = JSON.stringify({ experiment: mode, challenge, receipt: r }, null, 2);
  } catch {
    status('signature', 'REJECTED', 'fail');
    el('decision').textContent = 'WAIT';
    el('reason').textContent = 'Receipt verification failed. Check the evidence and public pin.';
  } finally {
    running = false;
    controls.forEach(id => { el(id).disabled = false; });
  }
}

async function init() {
  const [evidenceResponse, pinsResponse] = await Promise.all([
    fetch(new URL('./evidence/device-signed-purchase.json', import.meta.url)),
    fetch(new URL('./receipt-keys.json', import.meta.url)),
  ]);
  if (!evidenceResponse.ok || !pinsResponse.ok) throw new Error('Committed evidence or buyer configuration is unavailable.');
  recorded = (await evidenceResponse.json()).purchase;
  const pins = await pinsResponse.json();
  if (pins.algorithm !== 'ecdsa-p256-sha256') throw new Error('Unsupported buyer identity algorithm.');
  const sec1 = pins.providers['esp32-c6-96a2'];
  if (!/^04[0-9a-f]{128}$/.test(sec1 || '')) throw new Error('The buyer configuration has no valid device pin.');
  const bytes = Uint8Array.from(sec1.match(/../g), pair => parseInt(pair, 16));
  pin = await crypto.subtle.importKey('raw', bytes, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['verify']);
  differentKey = (await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign', 'verify'])).publicKey;
  el('pin').textContent = JSON.stringify({ algorithm: pins.algorithm, provider: 'esp32-c6-96a2', sec1_hex: sec1 }, null, 2);
  el('measured').textContent = new Date(recorded.receipt.completed_at * 1000).toISOString().replace('T', ' ').replace('.000Z', ' UTC');
  el('transaction').href = 'https://explorer.solana.com/tx/' + encodeURIComponent(recorded.settlement.transaction) + '?cluster=devnet';
  const payment = recordedPaymentDetails(recorded);
  el('payment-payer').textContent = payment.payer;
  el('payment-merchant').textContent = payment.merchant;
  el('payment-amount').textContent = payment.amount_usdc.toFixed(3);
  el('payment-explorer').href = el('transaction').href;
  controls.forEach(id => { el(id).onclick = () => experiment(id); });
  el('chain-query').disabled = false;
  el('chain-query').onclick = async () => {
    el('chain-query').disabled = true;
    status('chain-status', 'CHECKING', 'expired');
    el('chain-summary').textContent = 'Checking the actual recorded transfer. No funds move.';
    el('chain-result').textContent = 'Querying Solana Devnet. No payment or hardware request occurs.';
    try {
      const result = await querySettlement(recorded);
      status('chain-status', 'VERIFIED TRANSFER', 'pass');
      el('chain-summary').textContent = `Verified: buyer −0.001 USDC → merchant +0.001 USDC. Confirmed slot ${result.slot}.`;
      el('chain-result').textContent = JSON.stringify(result, null, 2);
    } catch (error) {
      status('chain-status', 'NOT VERIFIED', 'expired');
      el('chain-result').textContent = error.name === 'TimeoutError'
        ? 'The Devnet RPC query timed out after 15 seconds. Try again.'
        : error.message;
      el('chain-summary').textContent = el('chain-result').textContent;
    } finally { el('chain-query').disabled = false; }
  };
  await experiment();
  await inspectContactStates();
}

init().catch(error => { el('reason').textContent = error.message; });
