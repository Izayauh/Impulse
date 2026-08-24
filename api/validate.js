const { clientIp, kvGet, rateLimit, recordValidationSuccess } = require('./_lib/beta');

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }


  const limit = await rateLimit('validate', clientIp(req), { max: 60, windowSeconds: 3600 });
  if (!limit.allowed) {
    res.setHeader('Retry-After', String(limit.retryAfter));
    return res.status(429).json({ error: 'Too many validation attempts.' });
  }
  const { license_key, instance_name } = req.body ?? {};
  if (!license_key || typeof license_key !== 'string') {
    return res.status(400).json({ valid: false, error: 'license_key is required.' });
  }

  try {
    const data = await kvGet(`key:${license_key.trim()}`);
    if (!data) {
      return res.status(200).json({
        valid: false,
        error: 'Invalid or unknown license key.',
      });
    }

    if (!data.active) {
      return res.status(200).json({
        valid: false,
        error: 'This license key has been deactivated.',
      });
    }

    const lead = await recordValidationSuccess(license_key.trim(), instance_name || null);
    return res.status(200).json({
      valid: true,
      meta: {
        email: data.email,
        created_at: data.created_at,
        instance_name: instance_name || null,
        activated_at: lead?.activated_at || null,
      },
    });
  } catch (err) {
    console.error('Validate error:', err);
    return res.status(500).json({ valid: false, error: 'Validation service error.' });
  }
};
