# Privacy Policy

**Last Updated: January 2025**

## Our Commitment to Your Privacy

WhisperLocal is designed with privacy as a core principle. We believe your voice and the words you speak are personal and should never leave your computer without your explicit consent.

## Data Collection

### What We DON'T Collect

WhisperLocal does **NOT** collect, store, transmit, or share any of the following:

- ❌ Your voice recordings
- ❌ Your transcribed text
- ❌ Your microphone audio
- ❌ Usage statistics or analytics
- ❌ Personal information
- ❌ Device identifiers
- ❌ IP addresses
- ❌ Location data
- ❌ Any telemetry whatsoever

### What Stays on Your Computer

All of the following remain exclusively on your local machine:

- ✅ Voice recordings (temporary, deleted after transcription)
- ✅ Transcribed text (only in your clipboard or target application)
- ✅ Usage statistics (word counts, streaks - stored locally only)
- ✅ Application settings and preferences
- ✅ Log files for troubleshooting

## How It Works

1. **Recording**: When you hold WIN+CTRL, your voice is recorded to a temporary WAV file on your computer.

2. **Transcription**: The Whisper AI model, running entirely on your computer, converts your speech to text.

3. **Cleanup**: The temporary audio file is deleted after transcription.

4. **No Network**: At no point does the application connect to the internet or any external servers.

## Internet Connectivity

WhisperLocal **does not require** an internet connection to function. The application:

- Does not make any network requests
- Does not "phone home" for updates or analytics
- Does not sync data to cloud services
- Works completely offline

## Data Storage

### Local Files

WhisperLocal stores the following files locally:

| File | Purpose | Location |
|------|---------|----------|
| `whisper_stats.json` | Your usage statistics (word counts, streaks) | `%LOCALAPPDATA%\WhisperLocal\` |
| `config.json` | Application settings | `%LOCALAPPDATA%\WhisperLocal\` |
| `flow.log` | Diagnostic log file | `%LOCALAPPDATA%\WhisperLocal\` |
| `flow_input.wav` | Temporary audio (deleted after use) | `%LOCALAPPDATA%\WhisperLocal\` |

### Deleting Your Data

To completely remove all WhisperLocal data:

1. Uninstall the application via Windows Settings
2. When prompted during uninstall, choose "Yes" to remove all settings
3. Or manually delete: `%LOCALAPPDATA%\WhisperLocal\`

## Third-Party Components

WhisperLocal uses the following open-source components:

- **Whisper.cpp**: Speech recognition engine (MIT License)
- **GGML**: Tensor library (MIT License)
- **Python Libraries**: Various open-source packages

None of these components collect or transmit user data in our implementation.

## Children's Privacy

WhisperLocal does not knowingly collect any information from anyone, including children under 13 years of age.

## Changes to This Policy

If we ever make changes to this privacy policy, we will:

- Update the "Last Updated" date at the top
- Include details in the CHANGELOG
- Never compromise on our core principle: your data stays on your computer

## Open Source

WhisperLocal is open source. You can inspect the source code to verify our privacy claims. We encourage security researchers and privacy advocates to audit our code.

## Contact

If you have questions about this privacy policy or WhisperLocal's privacy practices, please open an issue on our GitHub repository.

---

**Summary**: WhisperLocal is 100% local. Your voice never leaves your computer. We don't collect anything. Ever.

