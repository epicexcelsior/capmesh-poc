// This server is an explicitly simulated facilitator. It cannot settle funds.
import { createGateway, createPaymentServer, observeHardware, NETWORK, PAY_TO } from './server.js';
import { PurchaseStore } from './store.js';

const port = Number(process.env.CAPMESH_GATEWAY_PORT || 4022);
const physical = process.argv.includes('--physical');
const facilitator = {
  getSupported: async () => ({ kinds: [{ x402Version: 2, scheme: 'exact', network: NETWORK, extra: { feePayer: PAY_TO } }], extensions: [], signers: {} }),
  verify: async payload => ({ isValid: Buffer.from(payload.payload.transaction, 'base64').toString().startsWith('FIELDPROOF-SIM:') }),
  settle: async payload => ({ success: true, network: NETWORK,
    transaction: `SIMULATED:${Buffer.from(payload.payload.transaction, 'base64').toString()}` }),
};
const paymentServer = await createPaymentServer(facilitator);
const store = new PurchaseStore(physical ? '.local/sim-payment-physical.sqlite' : '.local/sim-purchases.sqlite');
const app = await createGateway({ paymentServer, store, simulated: true, origin: `http://127.0.0.1:${port}`,
  observe: purchase => observeHardware({ ...purchase, simulated: !physical, closed: process.argv.includes('--closed') }),
});
app.listen(port, '127.0.0.1', () => {
  console.log(`FieldProof SIMULATED PAYMENT / ${physical ? 'REAL CONTACT' : 'SIMULATED CONTACT'} on http://127.0.0.1:${port}`);
});
