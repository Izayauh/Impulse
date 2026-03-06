# Privacy Policy

**Last Updated: March 2026**

## Our Commitment to Your Privacy

Impulse is designed with privacy as a core principle. Your voice and the words you speak are personal and should never leave your computer without your explicit consent.

---

## Data Collection

### What We DON'T Collect

Impulse does **NOT** collect, store, transmit, or share any of the following:

- Your voice recordings
- Your transcribed text
- Your microphone audio
- Personal information
- IP addresses
- Location data

### What Stays on Your Computer

All of the following remain exclusively on your local machine:

- Voice recordings (temporary WAV file, overwritten after each transcription)
- Transcribed text (delivered only to your clipboard or active application)
- Usage statistics (word counts, streaks — stored in `%LOCALAPPDATA%\WhisperLocal\`)
- Application settings and preferences
- Log files for troubleshooting

---

## Beta Telemetry (Opt-In)

During the beta period, Impulse may collect **anonymous usage events** to help identify bugs and improve the product. This is **opt-in** — you are asked during first-run setup and can change your preference at any time in Settings.

Beta telemetry, **if you opt in**, collects:

- Anonymous session events (e.g. "transcription completed", "model used")
- Error/crash identifiers (no stack traces containing personal paths)
- Performance timing (e.g. transcription latency)

Beta telemetry **never** collects:

- Voice recordings or transcription content
- File paths or application names from your computer
- Any personally identifiable information

Telemetry is disabled entirely in production releases.

---

## How Transcription Works

1. **Recording** — When you hold WIN+CTRL, your voice is recorded to a temporary WAV file on your computer.
2. **Transcription** — The Whisper AI model, running entirely on your computer, converts your speech to text.
3. **Cleanup** — The temporary audio file is overwritten on the next recording.
4. **No Network** — Transcription never contacts the internet.

---

## Internet Connectivity

Impulse connects to the internet only for:

| Purpose | When | What's sent |
|---------|------|-------------|
| License validation | On activation, then every 24 hours | License key, anonymous machine ID |
| Beta telemetry | Every 5 minutes (if opted in) | Anonymous usage events only |
| Update check | On startup (checker only, no auto-install) | Current version number |

All other functionality works completely offline.

---

## Local Files

| File | Purpose | Location |
|------|---------|----------|
| `license.json` | Cached license state | `%LOCALAPPDATA%\WhisperLocal\state\` |
| `machine_id.txt` | Anonymous device identifier (UUID) | `%LOCALAPPDATA%\WhisperLocal\state\` |
| `whisper_stats.json` | Usage statistics | `%LOCALAPPDATA%\WhisperLocal\state\` |
| `config.json` | Application settings | `%LOCALAPPDATA%\WhisperLocal\state\` |
| `flow.log` | Diagnostic log | `%LOCALAPPDATA%\WhisperLocal\logs\` |
| `flow_input.wav` | Temporary audio | `%LOCALAPPDATA%\WhisperLocal\audio\` |

### Deleting Your Data

To remove all Impulse data:

1. Uninstall via Windows Settings → Apps
2. Manually delete: `%LOCALAPPDATA%\WhisperLocal\`

---

## Third-Party Components

Impulse uses open-source components under MIT and similar licenses. None collect or transmit user data in our implementation:

- **Whisper.cpp** — Speech recognition engine
- **GGML** — Tensor library for model inference
- **LemonSqueezy** — License validation API (receives only license key + anonymous machine ID)

---

## Changes to This Policy

If we make changes, we will update the "Last Updated" date and note it in CHANGELOG.md. We will never compromise on core privacy: your voice stays on your computer.

---

## Contact

Open an issue on our GitHub repository with any privacy questions.

---

**Summary**: Your voice never leaves your computer. Transcription is 100% local. The only network calls are license validation and optional anonymous beta telemetry.
