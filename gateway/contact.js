// Operator/buyer configuration. A provider response cannot replace these terms.
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createPublicKey } from 'node:crypto';

export const DEFAULT_CONTACT = Object.freeze({ provider: 'esp32-c6-96a2', sensor: 'gpio9-contact' });
const pins = new Set([0, 1, 2, 3, 6, 7, 9, 18, 19, 20, 21, 22, 23]);
const sensors = new Set([...pins].map(pin => `gpio${pin}-contact`));
const root = fileURLToPath(new URL('../', import.meta.url));

export function contactContract(value = DEFAULT_CONTACT, { simulated = false } = {}) {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      Object.keys(value).length !== 2 || !Object.hasOwn(value, 'provider') || !Object.hasOwn(value, 'sensor') ||
      typeof value.provider !== 'string' ||
      !/^[A-Za-z0-9_-]{1,31}$/.test(value.provider) ||
      !(sensors.has(value.sensor) || simulated && value.sensor === 'simulated-contact')) {
    throw new Error('Select an explicit provider and supported contact sensor from trusted configuration');
  }
  return Object.freeze({ provider: value.provider, sensor: value.sensor });
}

export function receiptKey(sec1Hex) {
  if (typeof sec1Hex !== 'string' || !/^04[0-9a-f]{128}$/.test(sec1Hex)) {
    throw new Error('Buyer/operator has no provisioned P-256 receipt key');
  }
  // SPKI: id-ecPublicKey, prime256v1, uncompressed SEC1 point. OpenSSL validates the point.
  return createPublicKey({ key: Buffer.from('3059301306072a8648ce3d020106082a8648ce3d030107034200' + sec1Hex, 'hex'),
    format: 'der', type: 'spki' });
}

export function loadReceiptPins(path) {
  const source = path ? resolve(root, path) : new URL('../host/capmesh/protocol/receipt_keys.json', import.meta.url);
  const data = JSON.parse(readFileSync(source, 'utf8'));
  if (!data || data.algorithm !== 'ecdsa-p256-sha256' || !data.providers ||
      typeof data.providers !== 'object' || Array.isArray(data.providers) || !Object.keys(data.providers).length ||
      Object.keys(data.providers).some(provider => !/^[A-Za-z0-9_-]{1,31}$/.test(provider))) {
    throw new Error('Use a trusted public P-256 receipt-pin file');
  }
  for (const key of Object.values(data.providers)) receiptKey(key);
  return Object.freeze(data.providers);
}
