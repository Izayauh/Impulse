import type { VercelRequest, VercelResponse } from '@vercel/node';
import { Redis } from '@upstash/redis';

const kv = new Redis({
  url: process.env.KV_REST_API_URL!,
  token: process.env.KV_REST_API_TOKEN!,
});

interface KeyData {
  email: string;
  created_at: string;
  active: boolean;
}

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { license_key, instance_name } = req.body ?? {};

  if (!license_key || typeof license_key !== 'string') {
    return res.status(400).json({ valid: false, error: 'license_key is required.' });
  }

  try {
    const data = await kv.get<KeyData>(`key:${license_key.trim()}`);

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

    // Return a response compatible with what the desktop app expects
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
}
