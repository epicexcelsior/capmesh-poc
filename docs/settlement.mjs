// Independent read-only check of the recorded demonstration payment.
export const DEVNET_RPC = 'https://api.devnet.solana.com';
const NETWORK = 'solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1';
const MINT = '4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU';
const MERCHANT = 'CaQAKBcwf7G5vXeu2RNuNGJafnJ8724Uj4wv9ivfxfQA';
const TOKEN_PROGRAM = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA';
const AMOUNT = 1000n;

function validatePurchase(purchase) {
  const settlement = purchase?.settlement;
  if (settlement?.success !== true || settlement.network !== NETWORK ||
      !/^[1-9A-HJ-NP-Za-km-z]{64,88}$/.test(settlement.transaction || '') ||
      !/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(settlement.payer || '') || settlement.payer === MERCHANT) {
    throw new Error('The recorded purchase does not describe a supported Devnet settlement.');
  }
  return settlement;
}

// Describe expected recorded terms. Only querySettlement verifies them against chain data.
export function recordedPaymentDetails(purchase) {
  const settlement = validatePurchase(purchase);
  return { payer: settlement.payer, merchant: MERCHANT, transaction: settlement.transaction,
    amount_usdc: Number(AMOUNT) / 1e6, network: 'Solana Devnet' };
}

export function verifySettlement(result, purchase) {
  const settlement = validatePurchase(purchase);
  if (!result) throw new Error('The RPC cannot find this transaction at confirmed commitment.');
  if (result.meta?.err !== null || !Number.isSafeInteger(result.slot) || result.slot < 1 ||
      result.transaction?.signatures?.[0] !== settlement.transaction) {
    throw new Error('The RPC result does not confirm the expected successful transaction.');
  }
  const keys = result.transaction.message?.accountKeys;
  if (!Array.isArray(keys)) throw new Error('The RPC result has no parsed account keys.');
  const balances = phase => {
    if (!Array.isArray(phase)) throw new Error('The RPC result has no token balance records.');
    const found = new Map();
    for (const item of phase) {
      if (item.mint !== MINT) continue;
      if (!Number.isInteger(item.accountIndex) || !keys[item.accountIndex]?.pubkey ||
          item.programId !== TOKEN_PROGRAM || item.uiTokenAmount?.decimals !== 6 ||
          typeof item.uiTokenAmount?.amount !== 'string' ||
          !/^(0|[1-9][0-9]*)$/.test(item.uiTokenAmount.amount) || found.has(item.accountIndex)) {
        throw new Error('The RPC returned inconsistent USDC token balances.');
      }
      found.set(item.accountIndex, { owner: item.owner, amount: BigInt(item.uiTokenAmount.amount) });
    }
    return found;
  };
  const before = balances(result.meta.preTokenBalances);
  const after = balances(result.meta.postTokenBalances);
  const deltas = new Map();
  const accounts = new Map();
  for (const index of new Set([...before.keys(), ...after.keys()])) {
    const pre = before.get(index), post = after.get(index);
    if (pre && post && pre.owner !== post.owner) throw new Error('A USDC token account changed owner.');
    const owner = post?.owner || pre?.owner;
    if (!owner) throw new Error('A USDC token balance has no owner.');
    deltas.set(owner, (deltas.get(owner) || 0n) + (post?.amount || 0n) - (pre?.amount || 0n));
    accounts.set(keys[index].pubkey, owner);
  }
  if (deltas.get(settlement.payer) !== -AMOUNT || deltas.get(MERCHANT) !== AMOUNT) {
    throw new Error('The payer and merchant did not exchange exactly 0.001 Devnet USDC.');
  }
  const outer = result.transaction.message.instructions;
  const inner = result.meta.innerInstructions || [];
  if (!Array.isArray(outer) || !Array.isArray(inner)) throw new Error('The RPC returned malformed instructions.');
  if (inner.some(group => !Array.isArray(group?.instructions))) throw new Error('The RPC returned malformed inner instructions.');
  const instructions = [...outer, ...inner.flatMap(group => group.instructions)];
  if (instructions.some(instruction => !instruction || typeof instruction !== 'object' || Array.isArray(instruction))) {
    throw new Error('The RPC returned malformed instructions.');
  }
  const transfer = instructions.some(instruction => {
    const info = instruction.parsed?.info;
    return instruction.programId === TOKEN_PROGRAM && instruction.parsed?.type === 'transferChecked' &&
      info?.mint === MINT && info.tokenAmount?.amount === String(AMOUNT) && info.tokenAmount.decimals === 6 &&
      info.authority === settlement.payer && accounts.get(info.source) === settlement.payer &&
      accounts.get(info.destination) === MERCHANT;
  });
  if (!transfer) throw new Error('The RPC result has no matching SPL Token transfer instruction.');
  return { network: 'Solana Devnet', slot: result.slot, transaction: settlement.transaction,
    mint: MINT, payer: settlement.payer, merchant: MERCHANT,
    payer_delta_base_units: String(-AMOUNT), merchant_delta_base_units: String(AMOUNT), decimals: 6 };
}

export async function querySettlement(purchase, fetcher = fetch) {
  const settlement = validatePurchase(purchase);
  let response;
  try {
    response = await fetcher(DEVNET_RPC, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(15000), body: JSON.stringify({ jsonrpc: '2.0', id: 'fieldproof-payment-check',
        method: 'getTransaction', params: [settlement.transaction,
          { commitment: 'confirmed', encoding: 'jsonParsed', maxSupportedTransactionVersion: 0 }] }) });
  } catch (error) {
    if (error instanceof TypeError) throw new Error('The browser cannot reach Solana Devnet. Check internet access, then try again.', { cause: error });
    throw error;
  }
  if (!response.ok) throw new Error(`The Devnet RPC refused the query (HTTP ${response.status}).`);
  const text = await response.text();
  if (text.length > 262144) throw new Error('The Devnet RPC response exceeds the inspection limit.');
  let body;
  try { body = JSON.parse(text); }
  catch { throw new Error('The Devnet RPC returned invalid JSON.'); }
  if (!body || body.jsonrpc !== '2.0' || body.id !== 'fieldproof-payment-check' || Object.hasOwn(body, 'error')) {
    throw new Error('The Devnet RPC did not return a correlated transaction result.');
  }
  return verifySettlement(body.result, purchase);
}
