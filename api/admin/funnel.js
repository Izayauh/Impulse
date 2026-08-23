const { kvGet, kvSmembers } = require('../_lib/beta');

function isAuthorized(req) {
  const token = process.env.BETA_ADMIN_TOKEN;
  if (!token) return false;
  const header = req.headers.authorization || '';
  return header === `Bearer ${token}`;
}

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  if (!isAuthorized(req)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  try {
    const ids = await kvSmembers('funnel:ids');
    const counts = { first_launch: 0, license_blocked: 0, activated: 0, first_dictation: 0 };
    const installs = [];

    for (const id of ids.slice(0, 500)) {
      const record = await kvGet(`funnel:${id}`);
      if (!record || !Array.isArray(record.events)) continue;

      const steps = [...new Set(record.events.map((e) => e.event))];
      for (const step of steps) {
        if (step in counts) counts[step] += 1;
      }
      const lastEvent = record.events[record.events.length - 1] || {};
      installs.push({
        install_id: id,
        first_seen: record.first_seen || null,
        last_seen: record.last_seen || null,
        steps,
        app_version: lastEvent.app_version || null,
        os: lastEvent.os || null,
        blocked_reasons: [
          ...new Set(
            record.events
              .filter((e) => e.event === 'license_blocked')
              .map((e) => e.props && e.props.reason)
              .filter(Boolean)
          ),
        ],
      });
    }

    installs.sort((a, b) => String(b.last_seen).localeCompare(String(a.last_seen)));
    return res.status(200).json({ ok: true, total_installs: installs.length, counts, installs });
  } catch (err) {
    console.error('Admin funnel error:', err);
    return res.status(500).json({ ok: false, error: 'Failed to load funnel.' });
  }
};
