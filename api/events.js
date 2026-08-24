const { clientIp, kvGet, kvSadd, kvSet, rateLimit } = require('./_lib/beta');

// Anonymous setup-funnel events from opted-in beta clients.
// No auth by design (fresh installs have no credentials); the payload is
// strictly validated, size-clamped, and capped per install instead.
const VALID_EVENTS = new Set(['first_launch', 'license_blocked', 'activated', 'first_dictation']);
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const MAX_EVENTS_PER_INSTALL = 100;

function clampString(value, max) {
  return typeof value === 'string' ? value.slice(0, max) : null;
}

function clampProps(props) {
  if (!props || typeof props !== 'object' || Array.isArray(props)) return {};
  try {
    return JSON.stringify(props).length <= 500 ? props : {};
  } catch {
    return {};
  }
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const limit = await rateLimit('events', clientIp(req), { max: 120, windowSeconds: 3600 });
  if (!limit.allowed) {
    return res.status(429).json({ error: 'Too many events.' });
  }

  const { install_id, event, ts, app_version, os, props } = req.body ?? {};
  if (!UUID_RE.test(String(install_id || ''))) {
    return res.status(400).json({ ok: false, error: 'invalid install_id' });
  }
  if (!VALID_EVENTS.has(String(event || ''))) {
    return res.status(400).json({ ok: false, error: 'invalid event' });
  }

  try {
    const id = String(install_id).toLowerCase();
    const key = `funnel:${id}`;
    const record = (await kvGet(key)) || { install_id: id, events: [] };
    if (!Array.isArray(record.events)) record.events = [];

    record.events.push({
      event,
      ts: new Date().toISOString(),
      client_ts: clampString(ts, 40),
      app_version: clampString(app_version, 40),
      os: clampString(os, 120),
      props: clampProps(props),
    });
    if (record.events.length > MAX_EVENTS_PER_INSTALL) {
      record.events = record.events.slice(-MAX_EVENTS_PER_INSTALL);
    }
    record.last_seen = new Date().toISOString();
    if (!record.first_seen) record.first_seen = record.last_seen;

    await kvSet(key, record);
    await kvSadd('funnel:ids', id);
    return res.status(200).json({ ok: true });
  } catch (err) {
    console.error('Funnel event error:', err);
    return res.status(500).json({ ok: false, error: 'storage error' });
  }
};
