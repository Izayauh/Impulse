const { dueForSequence, listLeads, requireEnv, sendSequenceEmail } = require('../_lib/beta');

function isAuthorized(req) {
  const secret = process.env.CRON_SECRET;
  if (!secret) return true;
  const header = req.headers.authorization || '';
  return header === `Bearer ${secret}`;
}

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  if (!isAuthorized(req)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  try {
    requireEnv('KV_REST_API_URL');
    requireEnv('KV_REST_API_TOKEN');
    requireEnv('RESEND_API_KEY');

    const leads = await listLeads();
    const sent = [];

    for (const lead of leads) {
      const dueSteps = dueForSequence(lead);
      for (const step of dueSteps) {
        await sendSequenceEmail(step, lead);
        sent.push({ email: lead.email, step });
      }
    }

    return res.status(200).json({
      ok: true,
      checked: leads.length,
      sent_count: sent.length,
      sent,
    });
  } catch (err) {
    console.error('Beta sequence cron error:', err);
    return res.status(500).json({ ok: false, error: 'Failed to process beta email sequence.' });
  }
};
