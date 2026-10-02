import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DEVNET_RPC, querySettlement, verifySettlement } from '../../docs/settlement.mjs';

// Minimal public RPC fixture derived from the recorded October 1 transaction.
const fixture = JSON.parse(readFileSync(new URL('./fixtures/settlement-rpc.json', import.meta.url)));
const purchase = JSON.parse(readFileSync(new URL('../../docs/evidence/device-signed-purchase.json', import.meta.url))).purchase;

test('chain check confirms the exact recorded transfer, independently of the stored chain summary', () => {
  const proof = verifySettlement(structuredClone(fixture), purchase);
  assert.equal(proof.payer_delta_base_units, '-1000');
  assert.equal(proof.merchant_delta_base_units, '1000');
  assert.equal(proof.slot, 506374923);
});

test('chain check rejects failed transactions, another signature, mint, owner, amount, and instruction', () => {
  const changes = [
    r => { r.meta.err = { InstructionError: [2, 'failed'] }; },
    r => { r.transaction.signatures[0] = 'another-transaction'; },
    r => { r.meta.postTokenBalances[0].mint = 'another-mint'; },
    r => { r.meta.postTokenBalances[0].owner = purchase.settlement.payer; },
    r => { r.meta.postTokenBalances[0].uiTokenAmount.amount = '86615401'; },
    r => { r.meta.preTokenBalances[0].uiTokenAmount.amount = 86614400; },
    r => { r.meta.postTokenBalances.push(r.meta.postTokenBalances[0]); },
    r => { r.transaction.message.instructions[0].parsed.info.authority = 'another-payer'; },
    r => { r.transaction.message.instructions[0].programId = 'impostor-token-program'; },
    r => { r.transaction.message.instructions[0].parsed.info.tokenAmount.amount = '999'; },
    r => { r.meta.innerInstructions = [{ instructions: null }]; },
    r => { r.transaction.message.instructions.unshift(null); },
  ];
  for (const change of changes) {
    const result = structuredClone(fixture);
    change(result);
    assert.throws(() => verifySettlement(result, purchase));
  }
  assert.throws(() => verifySettlement(null, purchase), /cannot find/);
  assert.throws(() => verifySettlement(fixture, { settlement: { ...purchase.settlement, network: 'mainnet' } }), /supported/);
});

test('chain check accepts a matching inner transfer instruction', () => {
  const result = structuredClone(fixture);
  result.meta.innerInstructions = [{ index: 0, instructions: result.transaction.message.instructions }];
  result.transaction.message.instructions = [];
  assert.equal(verifySettlement(result, purchase).merchant_delta_base_units, '1000');
});

test('RPC request is read-only, Devnet-only, and correlates the response', async () => {
  let calls = 0;
  const fetcher = async (url, options) => {
    calls++;
    assert.equal(url, DEVNET_RPC);
    const body = JSON.parse(options.body);
    assert.equal(body.method, 'getTransaction');
    assert.deepEqual(body.params, [purchase.settlement.transaction,
      { commitment: 'confirmed', encoding: 'jsonParsed', maxSupportedTransactionVersion: 0 }]);
    return Response.json({ jsonrpc: '2.0', id: body.id, result: fixture });
  };
  assert.equal((await querySettlement(purchase, fetcher)).network, 'Solana Devnet');
  await assert.rejects(querySettlement({ settlement: { ...purchase.settlement, network: 'mainnet' } }, fetcher), /supported/);
  assert.equal(calls, 1);
  await assert.rejects(querySettlement(purchase, async () => Response.json({ jsonrpc: '2.0', id: 'wrong', result: fixture })), /correlated/);
  await assert.rejects(querySettlement(purchase, async () => new Response('', { status: 429 })), /HTTP 429/);
  await assert.rejects(querySettlement(purchase, async () => { throw new Error('Network unavailable'); }), /Network unavailable/);
  await assert.rejects(querySettlement(purchase, async () => { throw new TypeError('Failed to fetch'); }), /cannot reach Solana Devnet/);
  await assert.rejects(querySettlement(purchase, async () => new Response('not json')), /invalid JSON/);
  await assert.rejects(querySettlement(purchase, async () => new Response('x'.repeat(262145))), /inspection limit/);
});
