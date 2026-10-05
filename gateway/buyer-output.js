import { open } from 'node:fs/promises';

// Reserve before the action. An existing result or wallet file cannot be overwritten after payment.
export async function saveBuyerRun(path, action) {
  const file = await open(path, 'wx', 0o600);
  try {
    let result;
    try { result = await action(); }
    catch (error) {
      await file.writeFile(JSON.stringify({ status: 'failed', error: error.message }) + '\n');
      await file.sync();
      throw error;
    }
    await file.writeFile(JSON.stringify(result, null, 2) + '\n');
    await file.sync();
    return result;
  } finally { await file.close(); }
}
