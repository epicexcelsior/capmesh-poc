import { DatabaseSync } from 'node:sqlite';
import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

export class PurchaseStore {
  constructor(path = '.local/purchases.sqlite') {
    if (path !== ':memory:') mkdirSync(dirname(path), { recursive: true });
    this.db = new DatabaseSync(path);
    try {
      this.db.exec(`PRAGMA busy_timeout=5000; PRAGMA journal_mode=WAL;
      CREATE TABLE IF NOT EXISTS purchases (
        id TEXT PRIMARY KEY, nonce INTEGER NOT NULL UNIQUE, location TEXT NOT NULL,
        max_age_seconds INTEGER NOT NULL, expires_at INTEGER NOT NULL, state TEXT NOT NULL,
        proof_hash TEXT UNIQUE, settlement TEXT, result TEXT, error TEXT, contact_contract TEXT,
        receipt_public_key TEXT);`);
      // Serialize schema inspection and migration across gateway processes.
      this.db.exec('BEGIN IMMEDIATE');
      const columns = this.db.prepare('PRAGMA table_info(purchases)').all();
      if (!columns.some(column => column.name === 'contact_contract')) {
        this.db.exec('ALTER TABLE purchases ADD COLUMN contact_contract TEXT');
      }
      if (!columns.some(column => column.name === 'receipt_public_key')) {
        this.db.exec('ALTER TABLE purchases ADD COLUMN receipt_public_key TEXT');
      }
      this.db.exec('COMMIT');
    } catch (error) {
      if (this.db.isTransaction) this.db.exec('ROLLBACK');
      this.db.close();
      throw error;
    }
  }
  create(purchase) {
    this.db.prepare('INSERT INTO purchases (id, nonce, location, max_age_seconds, expires_at, state, contact_contract, receipt_public_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?)')
      .run(purchase.id, purchase.nonce, purchase.location, purchase.max_age_seconds, purchase.expires_at, 'quoted',
        purchase.contact ? JSON.stringify(purchase.contact) : null, purchase.receipt_public_key || null);
    return this.get(purchase.id);
  }
  get(id) {
    const row = this.db.prepare('SELECT * FROM purchases WHERE id = ?').get(id);
    if (row) row.contact = row.contact_contract ? JSON.parse(row.contact_contract) : null;
    return row;
  }
  reserve(id, proofHash) {
    // The unique proof constraint also applies across different gateway processes.
    try {
      return this.db.prepare("UPDATE purchases SET state = 'settling', proof_hash = ? WHERE id = ? AND state = 'quoted'")
        .run(proofHash, id).changes === 1;
    } catch (error) {
      if (String(error.message).includes('UNIQUE')) return false;
      throw error;
    }
  }
  finish(id, state, { settlement = null, result = null, error = null } = {}) {
    this.db.prepare('UPDATE purchases SET state = ?, settlement = COALESCE(?, settlement), result = ?, error = ? WHERE id = ?')
      .run(state, settlement && JSON.stringify(settlement), result && JSON.stringify(result), error, id);
  }
  demand() {
    return this.db.prepare('SELECT location, state, COUNT(*) AS requests FROM purchases GROUP BY location, state ORDER BY state').all();
  }
  close() { this.db.close(); }
}
