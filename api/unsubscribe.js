const { markLeadUnsubscribedByToken } = require('./_lib/beta');

module.exports = async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).send('Method not allowed');
  }

  const token = typeof req.query.token === 'string' ? req.query.token.trim() : '';
  if (!token) {
    return res.status(400).send('Missing unsubscribe token.');
  }

  try {
    const lead = await markLeadUnsubscribedByToken(token);
    if (!lead) {
      return res.status(404).send('Unsubscribe token not found.');
    }

    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    return res.status(200).send(`
      <html>
        <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:40px;background:#111;color:#f5f5f5;">
          <h1 style="margin-bottom:12px;">You have been unsubscribed</h1>
          <p style="color:#bbb;max-width:560px;line-height:1.6;">
            ${lead.email} will no longer receive automated Impulse beta follow-up emails.
            Transactional emails tied to direct account actions may still be sent when necessary.
          </p>
        </body>
      </html>
    `);
  } catch (err) {
    console.error('Unsubscribe error:', err);
    return res.status(500).send('Failed to unsubscribe.');
  }
};
