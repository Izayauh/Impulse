const { clientIp, createSignupLead, isValidEmail, normalizeEmail, rateLimit, sendSequenceEmail } = require('./_lib/beta');

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Signups send email on our dime, so this is the endpoint worth bounding.
  const limit = await rateLimit('signup', clientIp(req), { max: 5, windowSeconds: 3600 });
  if (!limit.allowed) {
    res.setHeader('Retry-After', String(limit.retryAfter));
    return res.status(429).json({ error: 'Too many signup attempts. Please try again later.' });
  }

  const { email, source } = req.body ?? {};
  if (!isValidEmail(email)) {
    return res.status(400).json({ error: 'A valid email address is required.' });
  }

  const normalizedEmail = normalizeEmail(email);

  try {
    const { lead } = await createSignupLead(normalizedEmail, {
      source: typeof source === 'string' && source.trim() ? source.trim() : 'website-beta',
    });
    // Send the welcome email (don't fail the whole request if email fails)
    try {
      await sendSequenceEmail('welcome', lead);
    } catch (e) {
      console.warn('Beta welcome email failed:', e);
    }

    return res.status(200).json({
      success: true,
      licenseKey: lead.license_key,
      lead: {
        email: lead.email,
        created_at: lead.created_at,
        sequence_step: lead.sequence_step,
        status: lead.status,
      },
    });
  } catch (err) {
    console.error('Beta signup error:', err);
    return res.status(500).json({ error: 'Something went wrong. Please try again later.' });
  }
};
