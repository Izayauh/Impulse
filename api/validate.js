function requireEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

async function kvGet(key) {
  const baseUrl = requireEnv('KV_REST_API_URL').replace(/\/+$/, '');
  const res = await fetch(`${baseUrl}/get/${encodeURIComponent(key)}`, {
    headers: {
      Authorization: `Bearer ${requireEnv('KV_REST_API_TOKEN')}`,
    },
  });
  if (!res.ok) {
    throw new Error(`Upstash get failed: ${res.status}`);
  }
  const body = await res.json();
  return body.result ?? null;
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
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

    return res.status(200).json({
      valid: true,
      meta: {
        email: data.email,
        created_at: data.created_at,
        instance_name: instance_name || null,
      },
    });
  } catch (err) {
    console.error('Validate error:', err);
    return res.status(500).json({ valid: false, error: 'Validation service error.' });
  }
};
