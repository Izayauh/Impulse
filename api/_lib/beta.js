const { randomUUID } = require('node:crypto');

const DAY_MS = 24 * 60 * 60 * 1000;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const DEFAULT_FROM = 'Impulse <beta@impulse-app.com>';

function requireEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function optionalEnv(name, fallback = '') {
  const value = process.env[name];
  return value ? String(value) : fallback;
}

function nowIso() {
  return new Date().toISOString();
}

function normalizeEmail(email) {
  if (!email || typeof email !== 'string') return '';
  return email.trim().toLowerCase();
}

function isValidEmail(email) {
  return EMAIL_RE.test(normalizeEmail(email));
}

function publicBaseUrl() {
  return optionalEnv('PUBLIC_APP_URL', 'https://impulse-eight-lake.vercel.app').replace(/\/+$/, '');
}

function releaseUrl() {
  return optionalEnv('PUBLIC_DOWNLOAD_URL', 'https://github.com/Izayauh/Impulse/releases/latest');
}

function upstashHeaders(json = false) {
  const headers = {
    Authorization: `Bearer ${requireEnv('KV_REST_API_TOKEN')}`,
  };
  if (json) headers['Content-Type'] = 'application/json';
  return headers;
}

async function kvRequest(method, path, body) {
  const baseUrl = requireEnv('KV_REST_API_URL').replace(/\/+$/, '');
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: upstashHeaders(body !== undefined),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Upstash request failed: ${response.status} ${path}`);
  }
  return response.json();
}

function parseKvValue(raw) {
  // kvSet stores values via JSON.stringify, and Upstash returns them as raw
  // strings — without parsing, object fields like `active` read as undefined.
  if (typeof raw !== 'string') return raw;
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

async function kvGet(key) {
  const body = await kvRequest('GET', `/get/${encodeURIComponent(key)}`);
  return parseKvValue(body.result ?? null);
}

async function kvSet(key, value) {
  await kvRequest('POST', `/set/${encodeURIComponent(key)}`, value);
}

async function kvSadd(key, value) {
  await kvRequest('GET', `/sadd/${encodeURIComponent(key)}/${encodeURIComponent(value)}`);
}

async function kvSmembers(key) {
  const body = await kvRequest('GET', `/smembers/${encodeURIComponent(key)}`);
  return Array.isArray(body.result) ? body.result : [];
}

function leadKey(email) {
  return `lead:${normalizeEmail(email)}`;
}

function emailKey(email) {
  return `email:${normalizeEmail(email)}`;
}

function keyKey(licenseKey) {
  return `key:${licenseKey}`;
}

function formatDate(value) {
  try {
    return new Date(value).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return value || 'Unknown date';
  }
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function leadDefaults(email) {
  const normalized = normalizeEmail(email);
  return {
    email: normalized,
    license_key: null,
    created_at: nowIso(),
    source: 'website-beta',
    status: 'signed_up',
    sequence_step: 'welcome',
    last_emailed_at: null,
    activated_at: null,
    activation_count: 0,
    last_seen_at: null,
    last_validated_at: null,
    last_instance_name: null,
    unsubscribed: false,
    unsubscribe_token: randomUUID(),
    sent_steps: {},
    notes: [],
  };
}

async function getLeadByEmail(email) {
  const normalized = normalizeEmail(email);
  if (!normalized) return null;
  const lead = await kvGet(leadKey(normalized));
  if (!lead) return null;
  return { ...leadDefaults(normalized), ...lead };
}

async function saveLead(lead) {
  const normalized = normalizeEmail(lead.email);
  const payload = { ...leadDefaults(normalized), ...lead, email: normalized };
  await kvSet(leadKey(normalized), payload);
  await kvSadd('leads:emails', normalized);
  if (payload.license_key) {
    await kvSadd('leads:license_keys', payload.license_key);
  }
  return payload;
}

async function createOrRefreshLead(email, fields = {}) {
  const normalized = normalizeEmail(email);
  const existing = await getLeadByEmail(normalized);
  const lead = {
    ...(existing || leadDefaults(normalized)),
    ...fields,
    email: normalized,
  };
  return saveLead(lead);
}

async function getKeyRecord(licenseKey) {
  if (!licenseKey) return null;
  return kvGet(keyKey(licenseKey));
}

async function saveKeyRecord(licenseKey, value) {
  await kvSet(keyKey(licenseKey), value);
}

function buildUnsubscribeUrl(token) {
  return `${publicBaseUrl()}/api/unsubscribe?token=${encodeURIComponent(token)}`;
}

function emailFrame({ title, intro, bodyHtml, footerHtml = '', lead }) {
  const unsubscribe = lead?.unsubscribe_token
    ? `<p style="color:#999;font-size:12px;margin-top:24px;">Prefer not to get beta follow-ups? <a href="${buildUnsubscribeUrl(lead.unsubscribe_token)}" style="color:#666;">Unsubscribe here</a>.</p>`
    : '';
  return `
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:560px;margin:0 auto;padding:40px 20px;">
      <h1 style="font-size:24px;font-weight:700;margin-bottom:8px;">${title}</h1>
      <p style="color:#666;font-size:16px;line-height:1.6;margin-bottom:24px;">${intro}</p>
      ${bodyHtml}
      ${footerHtml}
      <hr style="border:none;border-top:1px solid #eee;margin:32px 0;" />
      <p style="color:#999;font-size:13px;">Questions or feedback? Reply to this email. We read every message.</p>
      ${unsubscribe}
    </div>
  `;
}

function renderEmail(step, lead) {
  const safeKey = escapeHtml(lead.license_key || '');
  const safeEmail = escapeHtml(lead.email || '');
  const downloadLink = releaseUrl();
  const activatedDate = lead.activated_at ? formatDate(lead.activated_at) : null;

  if (step === 'welcome') {
    return {
      subject: 'Your Impulse Beta License Key',
      html: emailFrame({
        title: 'Welcome to the Impulse Beta',
        intro: "Thanks for signing up. Here's your license key so you can activate the app right away.",
        lead,
        bodyHtml: `
          <div style="background:#f5f5f5;border:2px solid #e0e0e0;border-radius:12px;padding:24px;text-align:center;margin-bottom:32px;">
            <p style="color:#999;font-size:12px;text-transform:uppercase;letter-spacing:2px;margin:0 0 12px;">Your License Key</p>
            <p style="font-family:monospace;font-size:22px;font-weight:700;color:#111;margin:0;word-break:break-all;background:#fff;border-radius:8px;padding:12px 16px;border:1px solid #ddd;">${safeKey}</p>
          </div>
          <ol style="color:#444;font-size:15px;line-height:1.8;padding-left:20px;">
            <li><a href="${downloadLink}" style="color:#111;">Download the Windows beta</a></li>
            <li>Run the installer and launch Impulse</li>
            <li>Paste your license key when prompted</li>
            <li>Hold <strong>Win+Ctrl</strong> to start dictating</li>
          </ol>
        `,
      }),
    };
  }

  if (step === 'purchase') {
    return {
      subject: 'Your Impulse licence key',
      html: emailFrame({
        title: 'Thanks for buying Impulse',
        intro: "You bought it once and it's yours. No subscription, no renewal, and it keeps working offline.",
        lead,
        bodyHtml: `
          <div style="background:#f5f5f5;border:2px solid #e0e0e0;border-radius:12px;padding:24px;text-align:center;margin-bottom:32px;">
            <p style="color:#999;font-size:12px;text-transform:uppercase;letter-spacing:2px;margin:0 0 12px;">Your Licence Key</p>
            <p style="font-family:monospace;font-size:22px;font-weight:700;color:#111;margin:0;word-break:break-all;background:#fff;border-radius:8px;padding:12px 16px;border:1px solid #ddd;">${safeKey}</p>
          </div>
          <ol style="color:#444;font-size:15px;line-height:1.8;padding-left:20px;">
            <li><a href="${downloadLink}" style="color:#111;">Download Impulse for Windows</a></li>
            <li>Run the installer and launch Impulse</li>
            <li>Paste your licence key when prompted</li>
            <li>Hold <strong>Ctrl+Win</strong> and talk, or tap <strong>Ctrl+Win+Alt</strong> for hands-free</li>
          </ol>
          <p style="color:#444;font-size:15px;line-height:1.7;">
            Keep this email. The same key activates Impulse on any computer you own.
            If it does not work on your machine, reply to this email and you will get a full refund.
          </p>
        `,
      }),
    };
  }

  if (step === 'day1_setup') {
    return {
      subject: 'Need help getting Impulse set up?',
      html: emailFrame({
        title: 'Quick setup help',
        intro: "You signed up yesterday, but it looks like you may not have activated yet. Here's the shortest path to first dictation.",
        lead,
        bodyHtml: `
          <ul style="color:#444;font-size:15px;line-height:1.8;padding-left:20px;">
            <li>Download the latest beta build: <a href="${downloadLink}" style="color:#111;">Windows installer</a></li>
            <li>Use this license key: <strong style="font-family:monospace;">${safeKey}</strong></li>
            <li>If activation fails, reply with the error and we can fix it fast</li>
          </ul>
        `,
      }),
    };
  }

  if (step === 'day3_nudge') {
    return {
      subject: 'Still planning to try Impulse?',
      html: emailFrame({
        title: 'Your beta spot is still open',
        intro: 'A few days have passed, so this is a simple reminder that your beta key is ready whenever you are.',
        lead,
        bodyHtml: `
          <p style="color:#444;font-size:15px;line-height:1.8;">Your key for <strong>${safeEmail}</strong> is still active:</p>
          <p style="font-family:monospace;font-size:20px;font-weight:700;color:#111;background:#f5f5f5;border:1px solid #ddd;border-radius:8px;padding:12px 16px;">${safeKey}</p>
          <p style="color:#444;font-size:15px;line-height:1.8;">Download the current build here: <a href="${downloadLink}" style="color:#111;">${downloadLink}</a></p>
        `,
      }),
    };
  }

  if (step === 'activated_tips') {
    return {
      subject: 'Impulse is activated. Here are 3 quick wins.',
      html: emailFrame({
        title: 'You are in',
        intro: activatedDate
          ? `Impulse was activated on ${activatedDate}. These tips will get you value faster.`
          : 'Impulse is activated. These tips will get you value faster.',
        lead,
        bodyHtml: `
          <ol style="color:#444;font-size:15px;line-height:1.8;padding-left:20px;">
            <li>Use <strong>Win+Ctrl</strong> for fast dictation anywhere.</li>
            <li>Try the <strong>Clean</strong> stylization profile first.</li>
            <li>Open the dashboard to review transcripts, achievements, and license state.</li>
          </ol>
        `,
      }),
    };
  }

  if (step === 'day7_feedback') {
    return {
      subject: 'How is the Impulse beta going so far?',
      html: emailFrame({
        title: 'We want your feedback',
        intro: 'After a week, the most useful thing for us is direct feedback from real beta users.',
        lead,
        bodyHtml: `
          <p style="color:#444;font-size:15px;line-height:1.8;">Reply with any of the following:</p>
          <ul style="color:#444;font-size:15px;line-height:1.8;padding-left:20px;">
            <li>What worked immediately</li>
            <li>What felt confusing or broken</li>
            <li>What would make you use it daily</li>
          </ul>
        `,
      }),
    };
  }

  return null;
}

async function sendEmail({ to, subject, html }) {
  const response = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${requireEnv('RESEND_API_KEY')}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: optionalEnv('RESEND_FROM_EMAIL', DEFAULT_FROM),
      reply_to: optionalEnv('RESEND_REPLY_TO', ''),
      to,
      subject,
      html,
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Resend send failed: ${response.status} ${body}`);
  }
  return response.json();
}

async function sendSequenceEmail(step, lead) {
  const template = renderEmail(step, lead);
  if (!template) return false;
  await sendEmail({
    to: lead.email,
    subject: template.subject,
    html: template.html,
  });
  const sentSteps = { ...(lead.sent_steps || {}), [step]: nowIso() };
  await saveLead({
    ...lead,
    sent_steps: sentSteps,
    sequence_step: step,
    last_emailed_at: nowIso(),
  });
  return true;
}

function needsStep(lead, step) {
  return !lead.unsubscribed && !(lead.sent_steps && lead.sent_steps[step]);
}

function dueForSequence(lead, now = Date.now()) {
  if (!lead || lead.unsubscribed) return [];
  const createdAt = Date.parse(lead.created_at || '');
  const activatedAt = lead.activated_at ? Date.parse(lead.activated_at) : NaN;
  const due = [];

  if (!lead.activated_at) {
    if (Number.isFinite(createdAt) && now - createdAt >= DAY_MS && needsStep(lead, 'day1_setup')) {
      due.push('day1_setup');
    }
    if (Number.isFinite(createdAt) && now - createdAt >= 3 * DAY_MS && needsStep(lead, 'day3_nudge')) {
      due.push('day3_nudge');
    }
  }

  if (lead.activated_at && Number.isFinite(activatedAt) && now - activatedAt >= 10 * 60 * 1000 && needsStep(lead, 'activated_tips')) {
    due.push('activated_tips');
  }

  if (Number.isFinite(createdAt) && now - createdAt >= 7 * DAY_MS && needsStep(lead, 'day7_feedback')) {
    due.push('day7_feedback');
  }

  return due;
}

async function listLeads() {
  const emails = await kvSmembers('leads:emails');
  const leads = await Promise.all(emails.map((email) => getLeadByEmail(email)));
  return leads.filter(Boolean).sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')));
}

async function markLeadUnsubscribedByToken(token) {
  const leads = await listLeads();
  const match = leads.find((lead) => lead.unsubscribe_token === token);
  if (!match) return null;
  const updated = await saveLead({
    ...match,
    unsubscribed: true,
    status: match.activated_at ? 'active' : 'signed_up',
  });
  return updated;
}

async function createSignupLead(email, fields = {}) {
  const normalized = normalizeEmail(email);
  const existingLicenseKey = await kvGet(emailKey(normalized));
  if (existingLicenseKey) {
    const existingLead = await createOrRefreshLead(normalized, {
      ...fields,
      license_key: existingLicenseKey,
    });
    return { lead: existingLead, created: false };
  }

  const licenseKey = randomUUID();
  const now = nowIso();
  const lead = await createOrRefreshLead(normalized, {
    ...fields,
    license_key: licenseKey,
    created_at: now,
    status: 'signed_up',
  });

  await saveKeyRecord(licenseKey, {
    email: normalized,
    created_at: now,
    active: true,
  });
  await kvSet(emailKey(normalized), licenseKey);
  return { lead, created: true };
}

async function recordValidationSuccess(licenseKey, instanceName) {
  const keyRecord = await getKeyRecord(licenseKey);
  if (!keyRecord || !keyRecord.email) return null;
  const lead = (await getLeadByEmail(keyRecord.email)) || leadDefaults(keyRecord.email);
  const firstActivation = !lead.activated_at;
  const now = nowIso();
  const updated = await saveLead({
    ...lead,
    license_key: licenseKey,
    status: 'active',
    activated_at: lead.activated_at || now,
    activation_count: Number(lead.activation_count || 0) + (firstActivation ? 1 : 0),
    last_validated_at: now,
    last_seen_at: now,
    last_instance_name: instanceName || lead.last_instance_name || null,
  });
  return updated;
}

function csvEscape(value) {
  const text = String(value ?? '');
  if (/[",\n]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

function leadsToCsv(leads) {
  const headers = [
    'email',
    'license_key',
    'status',
    'created_at',
    'activated_at',
    'activation_count',
    'last_seen_at',
    'last_validated_at',
    'last_emailed_at',
    'sequence_step',
    'unsubscribed',
    'source',
    'last_instance_name',
  ];
  const rows = leads.map((lead) =>
    headers.map((header) => csvEscape(lead[header])).join(',')
  );
  return [headers.join(','), ...rows].join('\n');
}

/**
 * Fixed-window rate limit backed by the same KV store.
 *
 * The public endpoints (signup, validate, events) were previously unbounded, so
 * a trivial script could flood signups and burn the Resend send quota, which
 * costs real money and can damage the sending domain's reputation.
 *
 * Fails OPEN: if KV is unreachable we serve the request rather than locking
 * every user out of activation because a cache is down.
 */
async function rateLimit(bucket, identifier, { max, windowSeconds }) {
  if (!identifier) return { allowed: true, remaining: max };

  const window = Math.floor(Date.now() / 1000 / windowSeconds);
  const key = `rl:${bucket}:${identifier}:${window}`;

  try {
    const current = Number((await kvGet(key)) || 0);
    if (current >= max) {
      return { allowed: false, remaining: 0, retryAfter: windowSeconds };
    }
    await kvRequest('POST', `/set/${encodeURIComponent(key)}/${current + 1}?EX=${windowSeconds * 2}`);
    return { allowed: true, remaining: max - current - 1 };
  } catch (err) {
    console.error('rateLimit check failed, allowing request:', err);
    return { allowed: true, remaining: max };
  }
}

/** Best-effort client identity behind Vercel's proxy. */
function clientIp(req) {
  const fwd = req.headers['x-forwarded-for'];
  if (typeof fwd === 'string' && fwd.trim()) return fwd.split(',')[0].trim();
  return req.headers['x-real-ip'] || req.socket?.remoteAddress || null;
}

module.exports = {
  DAY_MS,
  clientIp,
  createSignupLead,
  csvEscape,
  dueForSequence,
  isValidEmail,
  kvGet,
  kvSadd,
  kvSet,
  kvSmembers,
  leadDefaults,
  leadsToCsv,
  listLeads,
  markLeadUnsubscribedByToken,
  normalizeEmail,
  rateLimit,
  publicBaseUrl,
  recordValidationSuccess,
  releaseUrl,
  renderEmail,
  requireEnv,
  saveLead,
  sendSequenceEmail,
  sendEmail,
};
