# 🎤 Impulse

**Private, local speech-to-text dictation for Windows**

Hold a key, talk, and the text appears in whatever window has focus. Transcription runs entirely on your machine using Whisper — no audio and no text ever leaves your computer.

> **Beta Notice:** This is a pre-release beta. A free license key is issued on signup at [impulsedictation.com](https://impulsedictation.com). Please report bugs via GitHub Issues.

---

## 📥 Download & Install

### Option 1: Windows Installer (Recommended for most users)

**[Open the latest Windows release page](https://github.com/Izayauh/Impulse/releases/latest)**

1. Download the single Windows bootstrap installer when it is available
2. Run the installer and stay online while setup downloads the runtime/model payload
3. Follow the setup wizard - you'll be prompted to enter your beta license key

Fallback: if the release only includes split assets, download `Impulse-Setup-<version>.exe` and every matching `.bin` part, keep them in the same folder, then run the installer.

No Python, no configuration, no technical knowledge required.

### Option 2: From Source (For developers)

```powershell
# Clone the repository
git clone https://github.com/Izayauh/Impulse.git
cd whisper

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
- ⚡ **GPU Accelerated** - Fast transcription with NVIDIA CUDA
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

Impulse automatically selects the best model based on your dictation length:

| Dictation Length | Model Used | Speed | Quality |
|------------------|------------|-------|---------|
| < 25 words | base.en | ⚡⚡⚡ Fastest | Good |
| 25-75 words | medium.en | ⚡⚡ Fast | Better |
| > 75 words | large-v3 | ⚡ Thorough | Best |

This gives you the best of both worlds: quick response for short commands, high accuracy for longer dictation.

---

## 🔐 Privacy

Impulse is designed for privacy:

- ✅ **100% Local** — Transcription never leaves your computer
- ✅ **No Cloud** — Speech processed entirely on-device
- ✅ **Opt-In Telemetry** — Anonymous beta usage reporting, disabled by default after beta
- ✅ **Open Source** — Fully auditable code

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
- NVIDIA GPU users get 2-5x speed improvement

### Application won't start
- Ensure you're running Windows 10 or later (64-bit)
- Try reinstalling the application
- Check the log file in `%LOCALAPPDATA%\Impulse\flow.log`

See [`USER_GUIDE.md`](USER_GUIDE.md) for detailed troubleshooting.

---

## 📁 Project Structure

```
Impulse/
├── Impulse.exe           # Main application (installed version)
├── whisper-cli.exe            # Whisper inference engine
├── models/                    # AI models
│   ├── ggml-base.en.bin       # Fast model (142 MB)
│   ├── ggml-medium.en.bin     # Balanced model (1.5 GB)
│   └── ggml-large-v3.bin      # Quality model (3.1 GB)
├── *.dll                      # Runtime libraries
└── User Guide.txt             # Documentation
```

---

## 🛠️ Building from Source

### Prerequisites

- Python 3.8+
- PyInstaller: `pip install pyinstaller`
- Inno Setup (for installer): [Download](https://jrsoftware.org/isdl.php)

### Build Commands

```powershell
# Install dependencies
pip install sounddevice soundfile keyboard pyperclip pyautogui pillow pystray numpy pyinstaller

# Build standalone executable
.\build_installer.ps1

# Or build without installer
python -m PyInstaller build_config.spec
```

---

## 📝 License

MIT License - Based on [Whisper.cpp](https://github.com/ggerganov/whisper.cpp)

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
