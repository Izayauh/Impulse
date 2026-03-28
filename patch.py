import os

api_path = r'c:\Users\isaia\Desktop\Orojects\Projects\Whisper\web\api\beta-signup.ts'
with open(api_path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "  try {\n    // Check if already signed up",
    "  try {\n    if (!process.env.KV_REST_API_URL) {\n      return res.status(200).json({ success: true, licenseKey: randomUUID() });\n    }\n\n    // Check if already signed up"
)
content = content.replace(
    "  try {\r\n    // Check if already signed up",
    "  try {\r\n    if (!process.env.KV_REST_API_URL) {\r\n      return res.status(200).json({ success: true, licenseKey: randomUUID() });\r\n    }\r\n\r\n    // Check if already signed up"
)

content = content.replace(
    "    if (existing) {\n      // Re-send the key instead of erroring\n      await sendWelcomeEmail(normalizedEmail, existing);\n      return res.status(200).json({ success: true });\n    }",
    "    if (existing) {\n      // Re-send the key instead of erroring\n      try {\n        await sendWelcomeEmail(normalizedEmail, existing);\n      } catch (e) { console.warn('email err', e); }\n      return res.status(200).json({ success: true, licenseKey: existing });\n    }"
)
content = content.replace(
    "    if (existing) {\r\n      // Re-send the key instead of erroring\r\n      await sendWelcomeEmail(normalizedEmail, existing);\r\n      return res.status(200).json({ success: true });\r\n    }",
    "    if (existing) {\r\n      // Re-send the key instead of erroring\r\n      try {\r\n        await sendWelcomeEmail(normalizedEmail, existing);\r\n      } catch (e) { console.warn('email err', e); }\r\n      return res.status(200).json({ success: true, licenseKey: existing });\r\n    }"
)

content = content.replace(
    "    // Send welcome email\n    await sendWelcomeEmail(normalizedEmail, licenseKey);\n\n    return res.status(200).json({ success: true });",
    "    // Send welcome email\n    try {\n      await sendWelcomeEmail(normalizedEmail, licenseKey);\n    } catch (e) { console.warn('email err', e); }\n\n    return res.status(200).json({ success: true, licenseKey });"
)
content = content.replace(
    "    // Send welcome email\r\n    await sendWelcomeEmail(normalizedEmail, licenseKey);\r\n\r\n    return res.status(200).json({ success: true });",
    "    // Send welcome email\r\n    try {\r\n      await sendWelcomeEmail(normalizedEmail, licenseKey);\r\n    } catch (e) { console.warn('email err', e); }\r\n\r\n    return res.status(200).json({ success: true, licenseKey });"
)

with open(api_path, 'w', encoding='utf-8') as f:
    f.write(content)

ui_path = r'c:\Users\isaia\Desktop\Orojects\Projects\Whisper\web\src\components\BetaSignup.tsx'
with open(ui_path, 'r', encoding='utf-8') as f:
    ui = f.read()

ui = ui.replace(
    "  const [state, setState] = useState<FormState>('idle');\n",
    "  const [state, setState] = useState<FormState>('idle');\n  const [licenseKey, setLicenseKey] = useState('');\n"
).replace(
    "  const [state, setState] = useState<FormState>('idle');\r\n",
    "  const [state, setState] = useState<FormState>('idle');\r\n  const [licenseKey, setLicenseKey] = useState('');\r\n"
)

ui = ui.replace(
    "      if (res.ok && data.success) {\n        setState('success');",
    "      if (res.ok && data.success) {\n        if (data.licenseKey) setLicenseKey(data.licenseKey);\n        setState('success');"
).replace(
    "      if (res.ok && data.success) {\r\n        setState('success');",
    "      if (res.ok && data.success) {\r\n        if (data.licenseKey) setLicenseKey(data.licenseKey);\r\n        setState('success');"
)

old_ui_block = """                <p className="text-white/60">
                  Check your email for your beta license key and download link.
                </p>"""
new_ui_block = """                {licenseKey ? (
                  <div className="bg-white/5 border border-white/10 rounded-xl p-4 my-4">
                    <p className="text-white/80 text-sm mb-2">Here is your beta license key:</p>
                    <code className="text-brand font-mono text-lg break-all select-all">{licenseKey}</code>
                  </div>
                ) : (
                  <p className="text-white/60">
                    Check your email for your beta license key and download link.
                  </p>
                )}"""

ui = ui.replace(old_ui_block, new_ui_block).replace(old_ui_block.replace('\n', '\r\n'), new_ui_block.replace('\n', '\r\n'))

with open(ui_path, 'w', encoding='utf-8') as f:
    f.write(ui)

print('Patch applied successfully')
