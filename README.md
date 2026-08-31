# 🎤 Impulse

**Private, local speech-to-text dictation for Windows**

Hold a key, talk, and the text appears in whatever window has focus. Transcription runs entirely on your machine using Whisper — no audio and no text ever leaves your computer.

> Impulse is **$29, once**. No subscription. Buy it at [impulsedictation.com](https://impulsedictation.com), or try the free beta key from the same page first. Please report bugs via GitHub Issues.

---

## 📥 Download & Install

### Option 1: Windows Installer (Recommended for most users)

**[Open the latest Windows release page](https://github.com/Izayauh/Impulse/releases/latest)**

1. Download the single Windows bootstrap installer when it is available
2. Run the installer and stay online while setup downloads the runtime/model payload
3. Follow the setup wizard - you'll be prompted to enter your license key

Fallback: if the release only includes split assets, download `Impulse-Setup-<version>.exe` and every matching `.bin` part, keep them in the same folder, then run the installer.

No Python, no configuration, no technical knowledge required.

### Option 2: From Source (For developers)

```powershell
# Clone the repository
git clone https://github.com/Izayauh/Impulse.git
cd Impulse

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
.\run_impulse.bat
```

---

## ✨ Features

- 🔒 **100% Private** - All processing happens on your computer
- ⚡ **Fast on CPU** - No graphics card needed; a warm dictation lands in seconds
- 🌍 **System-wide** - Works in any application
- 🎯 **Simple Controls** - Just hold WIN + CTRL to dictate
- 🎨 **Modern UI** - Dark theme with statistics dashboard
- 📝 **Smart Model Selection** - Auto-picks best speed/quality balance

---

## 🚀 Quick Start

1. **Position your cursor** where you want text
2. **Hold WIN + CTRL** and speak clearly
3. **Release** to transcribe and paste

That's it! Your spoken words appear as text.

---

## 🎯 Controls

| Action | Hotkey |
|--------|--------|
| Record & Dictate | Hold `WIN + CTRL` |
| Toggle Latch Mode (hands-free) | `WIN + CTRL + ALT` |
| Open Dashboard | Click the floating status pill |
| Settings | `WIN + CTRL + S` |
| Exit | `ESC` |

---

## 📊 Model Selection

Two models, three modes. Set the mode in Settings:

| Mode | Model | Notes |
|------|-------|-------|
| `auto` (default) | picked at runtime | Uses `turbo` only on a machine that can genuinely accelerate it, and `base` everywhere else |
| `turbo` | large-v3-turbo | Highest quality. Needs a working CUDA stack to be worth it |
| `base` | base.en | Stays responsive on any CPU. What most machines run |

`auto` decides from what your machine actually did, not from what it reports. A card that is visible but cannot run inference is treated as no card, because the slowest thing Impulse can do is run the heavy model on a CPU.

---

## 🔐 Privacy

Impulse is designed for privacy:

- ✅ **100% Local** — Transcription never leaves your computer
- ✅ **No Cloud** — Speech processed entirely on-device
- ✅ **Opt-In Telemetry** — Off by default. Anonymous, and only if you turn it on
- ✅ **Readable Source** — Published so you can verify all of the above yourself

See our full [Privacy Policy](PRIVACY.md).

---

## 📋 System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| OS | Windows 10 (64-bit) | Windows 11 |
| RAM | 4 GB | 8 GB |
| Disk | 4 GB | 5 GB |
| GPU | Not required | Not required |

---

## 🔧 Troubleshooting

### "No speech detected"
- Press `WIN + CTRL + S` to open microphone settings
- Click "Test Mic" and speak - you should see the level bar move
- Try selecting a different microphone device

### Slow transcription
- First run is slower: the model is downloaded and loaded into memory
- Subsequent runs are much faster
- If every dictation is slow, check that Settings is on `auto` or `base` rather than pinned to `turbo`

### Application won't start
- Ensure you're running Windows 10 or later (64-bit)
- Try reinstalling the application
- Check the log file in `%LOCALAPPDATA%\Impulse\flow.log`

See [`USER_GUIDE.md`](USER_GUIDE.md) for detailed troubleshooting.

---

## 📁 Project Structure

```
Impulse/
├── Impulse.exe                     # Main application
├── User Guide.txt                  # Documentation
├── Privacy Policy.txt
├── Third-Party Notices.txt
└── _internal/
    ├── whisper-cli.exe             # whisper.cpp, the offline fallback engine
    ├── models/ggml-base.en.bin     # Bundled offline model (142 MB)
    ├── *.dll                       # Runtime libraries
    └── whisper_local/ui/           # Dashboard assets
```

The primary engine is faster-whisper, whose model is downloaded on first run.
`whisper-cli.exe` and the bundled `ggml-base.en.bin` are the offline fallback,
so dictation still works with no network.

---

## 🛠️ Building from Source

### Prerequisites

- Python 3.10-3.12 (CI builds on all three)
- Inno Setup (for the installer): [Download](https://jrsoftware.org/isdl.php)

### Build Commands

```powershell
# Dependencies, including the pinned PyInstaller
pip install -r requirements.txt

# Build the frozen app to dist\Impulse\
python -m PyInstaller --clean --noconfirm scripts\release\build_config.spec

# Or build the frozen app and the installer together
powershell -ExecutionPolicy Bypass -File scripts\release\build_installer.ps1 -Clean
```

### Verifying a build

Releases are gated on the artifact working, not on the test suite passing. The
same checks run locally:

```powershell
python scripts\release\verify_package.py manifest dist\Impulse
python scripts\release\verify_package.py make-sample sample.wav
python scripts\release\verify_package.py selftest dist\Impulse\Impulse.exe sample.wav
```

`manifest` checks the packaged tree for every file the app reads at runtime;
`selftest` transcribes real audio through the frozen binary and fails if the
transcript does not come back.

---

## 📝 License

Impulse is **source-available commercial software**, not open source. The source
is published so anyone can read it and verify what the app does with their
voice — which matters when the entire claim is that nothing leaves your machine.

A licence is **bought once and kept**. There is no subscription. See [LICENSE](LICENSE).

Bundled third-party components remain under their own licences, including
LGPL v3. See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

---

## 🆘 Support

1. Check the log file: `%LOCALAPPDATA%\Impulse\logs\flow.log`
2. See [`USER_GUIDE.md`](USER_GUIDE.md) for detailed help
3. Open an issue on GitHub

---

## 📈 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

**Made with ❤️ for privacy-conscious users**
