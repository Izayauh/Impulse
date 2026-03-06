const { randomUUID } = require('node:crypto');

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function requireEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function upstashHeaders() {
  return {
    Authorization: `Bearer ${requireEnv('KV_REST_API_TOKEN')}`,
    'Content-Type': 'application/json',
  };
}

async function kvGet(key) {
  const baseUrl = requireEnv('KV_REST_API_URL').replace(/\/+$/, '');
  const res = await fetch(`${baseUrl}/get/${encodeURIComponent(key)}`, {
    headers: upstashHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Upstash get failed: ${res.status}`);
  }
  const body = await res.json();
  return body.result ?? null;
}

async function kvSet(key, value) {
  const baseUrl = requireEnv('KV_REST_API_URL').replace(/\/+$/, '');
  const res = await fetch(`${baseUrl}/set/${encodeURIComponent(key)}`, {
    method: 'POST',
    headers: upstashHeaders(),
    body: JSON.stringify(value),
  });
  if (!res.ok) {
    throw new Error(`Upstash set failed: ${res.status}`);
  }
}

async function sendWelcomeEmail(email, licenseKey) {
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${requireEnv('RESEND_API_KEY')}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: process.env.RESEND_FROM_EMAIL || 'Impulse <beta@impulse-app.com>',
      to: email,
      subject: 'Your Impulse Beta License Key',
      html: `
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 20px;">
          <h1 style="font-size: 24px; font-weight: 700; margin-bottom: 8px;">Welcome to the Impulse Beta</h1>
          <p style="color: #666; font-size: 16px; line-height: 1.6; margin-bottom: 32px;">
            Thanks for signing up! Here's your license key to activate the app.
          </p>

          <div style="background: #f5f5f5; border: 2px solid #e0e0e0; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 32px;">
            <p style="color: #999; font-size: 12px; text-transform: uppercase; letter-spacing: 2px; margin: 0 0 12px;">Your License Key</p>
            <p style="font-family: monospace; font-size: 22px; font-weight: 700; color: #111; margin: 0; word-break: break-all; user-select: all; -webkit-user-select: all; -moz-user-select: all; cursor: pointer; background: #fff; border-radius: 8px; padding: 12px 16px; border: 1px solid #ddd;">
              ${licenseKey}
            </p>
            <p style="color: #aaa; font-size: 11px; margin: 8px 0 0;">Click the key to select it, then copy</p>
          </div>

          <h2 style="font-size: 18px; font-weight: 600; margin-bottom: 12px;">Getting started</h2>
          <ol style="color: #444; font-size: 15px; line-height: 1.8; padding-left: 20px;">
            <li>Download Impulse for Windows from the beta page</li>
            <li>Run the installer and launch Impulse</li>
            <li>Paste your license key when prompted</li>
            <li>Hold <strong>Win+Ctrl</strong> to start dictating!</li>
          </ol>

          <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0;" />
          <p style="color: #999; font-size: 13px;">
            Questions or feedback? Reply to this email — we read every message.
          </p>
        </div>
      `,
    }),
  });

  if (!res.ok) {
    throw new Error(`Resend send failed: ${res.status}`);
  }
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { email } = req.body ?? {};
  if (!email || typeof email !== 'string' || !EMAIL_RE.test(email.trim())) {
    return res.status(400).json({ error: 'A valid email address is required.' });
  }

  const normalizedEmail = email.trim().toLowerCase();

  try {
    const existing = await kvGet(`email:${normalizedEmail}`);
    if (existing) {
      await sendWelcomeEmail(normalizedEmail, existing);
      return res.status(200).json({ success: true });
    }

    const licenseKey = randomUUID();
    const now = new Date().toISOString();

    await kvSet(`key:${licenseKey}`, {
      email: normalizedEmail,
      created_at: now,
      active: true,
    });
    await kvSet(`email:${normalizedEmail}`, licenseKey);
    await sendWelcomeEmail(normalizedEmail, licenseKey);

    return res.status(200).json({ success: true });
  } catch (err) {
    console.error('Beta signup error:', err);
    return res.status(500).json({ error: 'Something went wrong. Please try again later.' });
  }
};
