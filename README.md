# 🎤 Impulse

**Private, local speech-to-text dictation for Windows**

Hold a key, talk, and the text appears in whatever window has focus. Transcription runs entirely on your machine using Whisper — no audio and no text ever leaves your computer.

> **Beta Notice:** This is pre-release software. A license is required; see [impulsedictation.com](https://impulsedictation.com) for current availability. Please report bugs via GitHub Issues.

---

## 📥 Download & Install

### Option 1: Windows Installer (Recommended for most users)

**[Open the latest Windows release page](https://github.com/Izayauh/Impulse/releases/latest)**

1. Download the single Windows bootstrap installer when it is available
2. Run the installer and stay online while setup downloads the runtime/model payload
3. Follow the setup wizard and activate Impulse with your license key

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
- ⚡ **Responsive** - Uses compatible NVIDIA CUDA hardware when available and falls back to CPU
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

## 📊 Smart Model Selection

Impulse chooses a transcription model based on the hardware it can actually use:

| Runtime | Model | Behavior |
|---------|-------|----------|
| CPU | `base.en` | Smaller model for dependable local transcription |
| Verified CUDA GPU | `turbo` | Faster, higher-capacity transcription when the CUDA runtime passes startup checks |

If GPU initialization fails, Impulse automatically uses the CPU path instead of leaving dictation unavailable.

---

## 🔐 Privacy

Impulse is designed for privacy:

- ✅ **100% Local** — Transcription never leaves your computer
- ✅ **No Cloud** — Speech processed entirely on-device
- ✅ **Opt-In Telemetry** — Anonymous beta usage reporting, disabled by default after beta
- ✅ **Source Available** — Published code can be inspected and audited

See our full [Privacy Policy](PRIVACY.md).

---

## 📋 System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| OS | Windows 10 (64-bit) | Windows 11 |
| RAM | 4 GB | 8 GB |
| Disk | 4 GB | 5 GB |
| GPU | None (CPU works) | NVIDIA with CUDA |

---

## 🔧 Troubleshooting

### "No speech detected"
- Press `WIN + CTRL + S` to open microphone settings
- Click "Test Mic" and speak - you should see the level bar move
- Try selecting a different microphone device

### Slow transcription
- First run is slower (loading AI models into memory)
- Subsequent runs are much faster
- Compatible NVIDIA CUDA systems may transcribe faster; Impulse logs and uses CPU fallback when CUDA is unavailable

### Application won't start
- Ensure you're running Windows 10 or later (64-bit)
- Try reinstalling the application
- Check the log file in `%LOCALAPPDATA%\Impulse\flow.log`

See [`USER_GUIDE.md`](USER_GUIDE.md) for detailed troubleshooting.

---

## 📁 Project Structure

```
Impulse/
├── Impulse.exe                # Main application
├── _internal/
│   ├── whisper-cli.exe        # Offline fallback engine
│   ├── models/
│   │   └── ggml-base.en.bin   # Bundled offline fallback model
│   └── *.dll                  # Packaged runtime libraries
└── User Guide.txt             # Documentation
```

The primary `faster-whisper` model is cached in the user's application data after it is first needed; it is not duplicated in the installer.

---

## 🛠️ Building from Source

### Prerequisites

- Python 3.10+ (Python 3.11 matches the release workflow)
- PyInstaller: `pip install pyinstaller`
- Inno Setup (for installer): [Download](https://jrsoftware.org/isdl.php)

### Build Commands

```powershell
# Install pinned dependencies
pip install -r requirements.txt

# Build standalone executable
.\scripts\release\build_installer.ps1

# Or build without installer
python -m PyInstaller scripts\release\build_config.spec
```

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
