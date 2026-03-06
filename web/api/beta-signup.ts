import type { VercelRequest, VercelResponse } from '@vercel/node';
import { Redis } from '@upstash/redis';
import { Resend } from 'resend';
import { randomUUID } from 'crypto';

const kv = new Redis({
  url: process.env.KV_REST_API_URL!,
  token: process.env.KV_REST_API_TOKEN!,
});
const resend = new Resend(process.env.RESEND_API_KEY);

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { email } = req.body ?? {};

  if (!email || typeof email !== 'string' || !EMAIL_RE.test(email.trim())) {
    return res.status(400).json({ error: 'A valid email address is required.' });
  }

  const normalizedEmail = email.trim().toLowerCase();

  try {
    // Check if already signed up
    const existing = await kv.get<string>(`email:${normalizedEmail}`);
    if (existing) {
      // Re-send the key instead of erroring
      await sendWelcomeEmail(normalizedEmail, existing);
      return res.status(200).json({ success: true });
    }

    // Generate a new beta license key
    const licenseKey = randomUUID();
    const now = new Date().toISOString();

    // Store in KV (key→metadata and email→key)
    await kv.set(`key:${licenseKey}`, {
      email: normalizedEmail,
      created_at: now,
      active: true,
    });
    await kv.set(`email:${normalizedEmail}`, licenseKey);

    // Send welcome email
    await sendWelcomeEmail(normalizedEmail, licenseKey);

    return res.status(200).json({ success: true });
  } catch (err) {
    console.error('Beta signup error:', err);
    return res.status(500).json({ error: 'Something went wrong. Please try again later.' });
  }
}

async function sendWelcomeEmail(email: string, licenseKey: string) {
  await resend.emails.send({
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
  });
}
