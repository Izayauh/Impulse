const crypto = require('node:crypto');
const {
  createSignupLead,
  isValidEmail,
  kvGet,
  kvSet,
  normalizeEmail,
  saveLead,
  sendSequenceEmail,
} = require('./_lib/beta');

/**
 * Purchase webhook: turns a completed payment into a licence key.
 *
 * Impulse is sold once, with no subscription, so the only event that matters is
 * the order being created. Everything downstream (key generation, storage,
 * delivery) is the same path a beta signup already takes.
 *
 * This endpoint mints licences, so it is verified before it is trusted:
 * without a valid signature an unauthenticated POST would hand out free keys.
 */

// Vercel parses JSON bodies by default, but signature verification needs the
// exact bytes that were signed, so the raw body is read manually.
module.exports.config = { api: { bodyParser: false } };

async function readRawBody(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(typeof chunk === 'string' ? Buffer.from(chunk) : chunk);
  }
  return Buffer.concat(chunks);
}

function timingSafeEqualHex(a, b) {
  const bufA = Buffer.from(a, 'utf8');
  const bufB = Buffer.from(b, 'utf8');
  if (bufA.length !== bufB.length) return false;
  return crypto.timingSafeEqual(bufA, bufB);
}

/** LemonSqueezy signs the raw body with HMAC-SHA256 in the X-Signature header. */
function verifyLemonSqueezy(raw, req, secret) {
  const provided = String(req.headers['x-signature'] || '');
  if (!provided) return false;
  const expected = crypto.createHmac('sha256', secret).update(raw).digest('hex');
  return timingSafeEqualHex(expected, provided);
}

/** Paddle Billing signs as `ts=<unix>;h1=<hmac of ts:body>`. */
function verifyPaddle(raw, req, secret) {
  const header = String(req.headers['paddle-signature'] || '');
  if (!header) return false;
  const parts = Object.fromEntries(
    header.split(';').map((kv) => kv.split('=').map((s) => s.trim()))
  );
  if (!parts.ts || !parts.h1) return false;
  const expected = crypto
    .createHmac('sha256', secret)
    .update(`${parts.ts}:${raw.toString('utf8')}`)
    .digest('hex');
  return timingSafeEqualHex(expected, parts.h1);
}

/** Pull the buyer's email and a stable order id out of either provider's shape. */
function extractOrder(payload) {
  // LemonSqueezy
  const lsAttrs = payload?.data?.attributes;
  if (lsAttrs && payload?.meta?.event_name) {
    return {
      provider: 'lemonsqueezy',
      event: payload.meta.event_name,
      email: lsAttrs.user_email || lsAttrs.email || null,
      orderId: String(payload.data.id || lsAttrs.order_id || ''),
      isPaid: ['paid', 'active', 'completed'].includes(String(lsAttrs.status || '').toLowerCase()),
    };
  }
  // Paddle Billing
  if (payload?.event_type) {
    const d = payload.data || {};
    return {
      provider: 'paddle',
      event: payload.event_type,
      email: d.customer?.email || d.customer_email || null,
      orderId: String(d.id || d.transaction_id || ''),
      isPaid: ['completed', 'paid', 'billed'].includes(String(d.status || '').toLowerCase()),
    };
  }
  return null;
}

const PURCHASE_EVENTS = new Set([
  'order_created',        // LemonSqueezy
  'transaction.completed', // Paddle
]);

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const secret = process.env.PURCHASE_WEBHOOK_SECRET;
  if (!secret) {
    // Fail closed. A misconfigured deploy must not mint free licences.
    console.error('PURCHASE_WEBHOOK_SECRET is not set; refusing webhook');
    return res.status(500).json({ error: 'Webhook not configured' });
  }

  let raw;
  try {
    raw = await readRawBody(req);
  } catch (err) {
    return res.status(400).json({ error: 'Could not read body' });
  }

  const verified =
    verifyLemonSqueezy(raw, req, secret) || verifyPaddle(raw, req, secret);
  if (!verified) {
    console.warn('Rejected purchase webhook with bad signature');
    return res.status(401).json({ error: 'Invalid signature' });
  }

  let payload;
  try {
    payload = JSON.parse(raw.toString('utf8'));
  } catch (err) {
    return res.status(400).json({ error: 'Invalid JSON' });
  }

  const order = extractOrder(payload);
  if (!order) {
    return res.status(400).json({ error: 'Unrecognised payload' });
  }

  // Anything that is not a completed purchase (refunds, subscription noise) is
  // acknowledged so the provider stops retrying, but issues nothing.
  if (!PURCHASE_EVENTS.has(order.event) || !order.isPaid) {
    return res.status(200).json({ ok: true, ignored: order.event });
  }

  if (!isValidEmail(order.email)) {
    console.error('Purchase webhook had no usable email', order.orderId);
    return res.status(200).json({ ok: true, ignored: 'no-email' });
  }

  const email = normalizeEmail(order.email);

  // Providers retry on any non-2xx, so the same order can arrive several times.
  // Without this guard a retry would issue a second key for one payment.
  const seenKey = `purchase:${order.provider}:${order.orderId}`;
  try {
    const seen = await kvGet(seenKey);
    if (seen) {
      return res.status(200).json({ ok: true, duplicate: true });
    }
  } catch (err) {
    console.error('Idempotency check failed, continuing:', err);
  }

  try {
    const { lead } = await createSignupLead(email, { source: `purchase:${order.provider}` });

    await saveLead({
      ...lead,
      status: 'purchased',
      purchased_at: new Date().toISOString(),
      purchase_provider: order.provider,
      purchase_order_id: order.orderId,
    });

    await sendSequenceEmail('purchase', lead);
    await kvSet(seenKey, { email, at: new Date().toISOString() });

    console.log(`Issued licence for ${order.provider} order ${order.orderId}`);
    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error('Failed to issue licence for purchase:', err);
    // 500 so the provider retries; the idempotency key is only written on success.
    return res.status(500).json({ ok: false, error: 'Could not issue licence' });
  }
};
