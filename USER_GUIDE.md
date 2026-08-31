# Impulse - User Guide

**Private, local speech-to-text dictation for Windows**

---

## Quick Start

1. **Position your cursor** where you want text to appear (any app, any text field)
2. **Hold WIN + CTRL** and speak clearly
3. **Release WIN + CTRL** to transcribe and paste

Your spoken words appear as text instantly.

---

## Controls

| Action | Hotkey |
|--------|--------|
| Record & Dictate | Hold `WIN + CTRL` |
| Toggle Latch Mode (hands-free) | `WIN + CTRL + ALT` |
| Open Dashboard | Click the floating status pill |
| Settings | `WIN + CTRL + S` |
| Exit | `ESC` |

### Latch Mode

Press `WIN + CTRL + ALT` to toggle continuous recording without holding the keys. Speak freely, then press `WIN + CTRL + ALT` again to stop and transcribe. Useful for long passages.

---

## Status Pill

A small floating pill near your taskbar shows the current state:

| State | Meaning |
|-------|---------|
| (hidden) | Idle — ready to record |
| Listening... | Recording your voice |
| Transcribing... | Processing speech |
| Pasted! | Text inserted successfully |
| No speech | Recording was silent or too short |
| Unlicensed | License required — see Activation |

Click the pill to open the Dashboard.

---

## Dashboard

The Dashboard shows your statistics: words dictated, streaks, session history, and recent transcripts. Open it by clicking the status pill or from the system tray icon.

---

## Model Selection

Two models, three modes. Change the mode in Settings:

| Mode | Model | Notes |
|------|-------|-------|
| `auto` (default) | picked at runtime | Runs `turbo` only on a machine that can genuinely accelerate it, `base` everywhere else |
| `turbo` | large-v3-turbo | Highest quality. Worth pinning only with a working CUDA stack |
| `base` | base.en | Stays responsive on any CPU. What most machines run |

`auto` decides from what your machine actually managed, not from what it reports it has. A graphics card that is visible but cannot run inference is treated as no card, because the slowest thing Impulse can do is run the heavy model on a CPU.

---

## Stylization Profiles

Cycle through profiles with the hotkey in Settings (default: none assigned):

- **Off** — Raw transcript, no processing
- **Clean** — Filler words removed, punctuation restored (no internet/LLM needed)
- **Polished** — Light grammar and punctuation polish via local LLM (requires Ollama)

If Ollama is not installed, "Polished" silently falls back to the raw transcript.

---

## Activation (Beta)

This beta release requires a license key.

1. Open Settings (`WIN + CTRL + S`)
2. Go to the **License** tab
3. Enter your beta key and click **Activate**

The app validates your key online, then caches it locally. You can use Impulse offline for up to 3 days without re-checking.

**Beta expires: April 30, 2026.** After expiry the app will display a message and stop transcribing until updated.

---

## Settings

Open with `WIN + CTRL + S` or via the system tray icon.

### Microphone

- **Select device** — Pick from detected input devices
- **Test** — Record a short clip and see the level meter to confirm the mic works

### Stylization

Choose your default post-processing profile (Off / Clean / Polished).

### Telemetry

Opt in or out of anonymous beta usage reporting. See [PRIVACY.md](PRIVACY.md).

---

## Troubleshooting

### "No speech detected"

1. Press `WIN + CTRL + S` → select your microphone → click **Test**
2. The level bar should move when you speak
3. Try increasing microphone volume in Windows Sound Settings
4. If using Bluetooth, ensure the mic is set as the default input device

### Transcription is slow

- First run is slower — the model is downloaded, then loaded into memory
- Subsequent runs are much faster
- If every dictation is slow, open Settings and check the mode is `auto` or `base` rather than pinned to `turbo`

### App won't start / crashes

- Check the log file: `%LOCALAPPDATA%\Impulse\logs\flow.log`
- Ensure Windows Defender or antivirus hasn't quarantined any DLLs
- Try reinstalling — the installer is self-contained

### Dictation runs on the CPU even though I have a graphics card

This is expected on most machines. Impulse only uses a card when it has
confirmed that inference actually ran on it, rather than trusting that a card
is present, and it remembers that verdict in
`%LOCALAPPDATA%\Impulse\state\gpu_capability.json`. A card that is visible but
whose CUDA stack cannot run inference is treated as no card, because running
the heavy model on a CPU is the slowest outcome available.

`base` on a CPU is quick — a few seconds for a normal dictation — so this
costs you far less than it sounds like it should.

### Dictation pastes in wrong place

- Ensure your cursor is in the target field **before** holding WIN+CTRL
- Some applications block automated paste — the text is always copied to clipboard as a fallback, so press `CTRL+V` manually

### License activation fails

- Ensure you have an internet connection
- Check that the key hasn't already been used on another machine
- If offline, the app uses a 3-day grace period from the last successful check

---

## System Requirements

| | Minimum | Recommended |
|--|---------|-------------|
| OS | Windows 10 64-bit | Windows 11 |
| RAM | 4 GB | 8 GB |
| Disk | 4 GB | 5 GB |
| GPU | Not required | Not required |

---

## Files & Logs

| Path | Contents |
|------|----------|
| `%LOCALAPPDATA%\Impulse\logs\flow.log` | Main application log |
| `%LOCALAPPDATA%\Impulse\state\config.json` | Settings |
| `%LOCALAPPDATA%\Impulse\state\whisper_stats.json` | Usage statistics |

---

## Support

1. Check the log: `%LOCALAPPDATA%\Impulse\logs\flow.log`
2. Open an issue on GitHub

---

**Version:** 1.0.0-beta.1 | **Updated:** March 2026
