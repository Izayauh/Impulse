const { leadsToCsv, listLeads } = require('../_lib/beta');

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
    const leads = await listLeads();
    const format = String(req.query.format || 'json').toLowerCase();

    if (format === 'csv') {
      res.setHeader('Content-Type', 'text/csv; charset=utf-8');
      res.setHeader('Content-Disposition', 'attachment; filename="impulse-beta-leads.csv"');
      return res.status(200).send(leadsToCsv(leads));
    }

    const summary = {
      total: leads.length,
      active: leads.filter((lead) => lead.status === 'active').length,
      signed_up: leads.filter((lead) => lead.status === 'signed_up').length,
      unsubscribed: leads.filter((lead) => lead.unsubscribed).length,
    };

    return res.status(200).json({ ok: true, summary, leads });
  } catch (err) {
    console.error('Admin leads export error:', err);
    return res.status(500).json({ ok: false, error: 'Failed to load leads.' });
  }
};
