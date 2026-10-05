import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, stat, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { saveBuyerRun } from '../buyer-output.js';

test('buyer reserves a private new output before its action and refuses an existing file', async t => {
  const dir = await mkdtemp(join(tmpdir(), 'fieldproof-output-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const path = join(dir, 'run.json');
  let calls = 0;
  const result = { purchase_id: 'public-evidence' };
  assert.deepEqual(await saveBuyerRun(path, async () => {
    calls += 1;
    assert.equal((await stat(path)).mode & 0o777, 0o600);
    return result;
  }), result);
  assert.deepEqual(JSON.parse(await readFile(path, 'utf8')), result);
  await assert.rejects(saveBuyerRun(path, async () => { calls += 1; }), { code: 'EEXIST' });
  assert.equal(calls, 1);
  assert.deepEqual(JSON.parse(await readFile(path, 'utf8')), result);
});

test('buyer records failure without retrying and refuses a wallet output collision', async t => {
  const dir = await mkdtemp(join(tmpdir(), 'fieldproof-output-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const path = join(dir, 'failed.json');
  let calls = 0;
  await assert.rejects(saveBuyerRun(path, async () => { calls++; throw new Error('Retain purchase ID abc'); }), /purchase ID abc/);
  assert.deepEqual(JSON.parse(await readFile(path, 'utf8')), { status: 'failed', error: 'Retain purchase ID abc' });
  await assert.rejects(saveBuyerRun(path, async () => { calls++; }), { code: 'EEXIST' });
  assert.equal(calls, 1);
  const wallet = join(dir, 'wallet.json');
  await writeFile(wallet, '[1,2,3]'); // Disposable invalid fixture, no signing material.
  await assert.rejects(saveBuyerRun(wallet, async () => { calls++; }), { code: 'EEXIST' });
  assert.equal(await readFile(wallet, 'utf8'), '[1,2,3]');
  assert.equal(calls, 1);
});
