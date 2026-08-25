// Run with: node tests/api/purchase.test.js
// This endpoint mints licence keys, so the tests that matter most are the ones
// proving it refuses to do so for anything it cannot verify.
const assert = require('node:assert');
const crypto = require('node:crypto');
const Module = require('node:module');
const path = require('node:path');

const SECRET = 'test-webhook-secret';
process.env.PURCHASE_WEBHOOK_SECRET = SECRET;

// Stub the beta lib so no test touches KV, Resend, or real state.
const calls = { leads: [], emails: [], kv: {} };
const libPath = path.resolve(__dirname, '../../api/_lib/beta.js');
const origLoad = Module._load;
Module._load = function (request, parent, isMain) {
  if (parent && request.includes('_lib/beta')) {
    return {
      createSignupLead: async (email) => {
        calls.leads.push(email);
        return { lead: { email, license_key: 'KEY-' + calls.leads.length } };
      },
      saveLead: async (lead) => { calls.saved = lead; },
      sendSequenceEmail: async (step, lead) => { calls.emails.push({ step, to: lead.email }); return true; },
      isValidEmail: (e) => typeof e === 'string' && /.+@.+\..+/.test(e),
      normalizeEmail: (e) => String(e).trim().toLowerCase(),
      kvGet: async (k) => calls.kv[k] || null,
      kvSet: async (k, v) => { calls.kv[k] = v; },
    };
  }
  return origLoad.apply(this, arguments);
};
const handler = require('../../api/purchase.js');
Module._load = origLoad;

function makeReq(bodyObj, headers = {}, method = 'POST') {
  const raw = Buffer.from(JSON.stringify(bodyObj));
  const req = { method, headers };
  req[Symbol.asyncIterator] = async function* () { yield raw; };
  return { req, raw };
}
function makeRes() {
  const res = { statusCode: null, body: null };
  res.status = (c) => { res.statusCode = c; return res; };
  res.json = (b) => { res.body = b; return res; };
  return res;
}
function lsSign(raw) { return crypto.createHmac('sha256', SECRET).update(raw).digest('hex'); }

const ORDER = {
  meta: { event_name: 'order_created' },
  data: { id: 'ord_1', attributes: { user_email: 'Buyer@Example.com', status: 'paid' } },
};

let passed = 0;
async function test(name, fn) {
  calls.leads = []; calls.emails = []; calls.kv = {}; calls.saved = null;
  try { await fn(); console.log(`  ok  ${name}`); passed++; }
  catch (e) { console.error(`  FAIL ${name}\n       ${e.message}`); process.exitCode = 1; }
}

(async () => {
  console.log('purchase webhook');

  await test('rejects an unsigned request', async () => {
    const { req } = makeReq(ORDER);
    const res = makeRes();
    await handler(req, res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(calls.leads.length, 0, 'must not issue a licence');
  });

  await test('rejects a forged signature', async () => {
    const { req } = makeReq(ORDER, { 'x-signature': 'deadbeef'.repeat(8) });
    const res = makeRes();
    await handler(req, res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(calls.leads.length, 0);
  });

  await test('rejects a body altered after signing', async () => {
    const { raw } = makeReq(ORDER);
    const sig = lsSign(raw);
    const tampered = { ...ORDER, data: { ...ORDER.data, attributes: { user_email: 'attacker@evil.com', status: 'paid' } } };
    const { req } = makeReq(tampered, { 'x-signature': sig });
    const res = makeRes();
    await handler(req, res);
    assert.strictEqual(res.statusCode, 401);
    assert.strictEqual(calls.leads.length, 0);
  });

  await test('issues a licence for a valid signed order', async () => {
    const { raw } = makeReq(ORDER);
    const { req } = makeReq(ORDER, { 'x-signature': lsSign(raw) });
    const res = makeRes();
    await handler(req, res);
    assert.strictEqual(res.statusCode, 200);
    assert.deepStrictEqual(calls.leads, ['buyer@example.com'], 'email is normalised');
    assert.strictEqual(calls.emails[0].step, 'purchase');
    assert.strictEqual(calls.saved.status, 'purchased');
  });

  await test('a retry of the same order does not issue twice', async () => {
    const { raw } = makeReq(ORDER);
    const sig = lsSign(raw);
    for (let i = 0; i < 3; i++) {
      const { req } = makeReq(ORDER, { 'x-signature': sig });
      await handler(req, makeRes());
    }
    assert.strictEqual(calls.leads.length, 1, 'one payment must mean one key');
    assert.strictEqual(calls.emails.length, 1);
  });

  await test('ignores refunds and other non-purchase events', async () => {
    const refund = { meta: { event_name: 'order_refunded' }, data: { id: 'ord_2', attributes: { user_email: 'b@e.com', status: 'refunded' } } };
    const { raw } = makeReq(refund);
    const { req } = makeReq(refund, { 'x-signature': lsSign(raw) });
    const res = makeRes();
    await handler(req, res);
    assert.strictEqual(res.statusCode, 200);
    assert.strictEqual(calls.leads.length, 0, 'a refund must not grant a licence');
  });

  await test('accepts a signed Paddle transaction', async () => {
    const evt = { event_type: 'transaction.completed', data: { id: 'txn_9', status: 'completed', customer: { email: 'p@example.com' } } };
    const raw = Buffer.from(JSON.stringify(evt));
    const ts = '1700000000';
    const h1 = crypto.createHmac('sha256', SECRET).update(`${ts}:${raw.toString('utf8')}`).digest('hex');
    const { req } = makeReq(evt, { 'paddle-signature': `ts=${ts};h1=${h1}` });
    const res = makeRes();
    await handler(req, res);
    assert.strictEqual(res.statusCode, 200);
    assert.deepStrictEqual(calls.leads, ['p@example.com']);
  });

  await test('rejects non-POST', async () => {
    const { req } = makeReq(ORDER, {}, 'GET');
    const res = makeRes();
    await handler(req, res);
    assert.strictEqual(res.statusCode, 405);
  });

  console.log(`\n${passed} passed`);
})();
