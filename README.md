# 🎤 Impulse

**Privacy-focused, GPU-accelerated speech-to-text dictation for Windows**

Transform your voice into text instantly - completely offline, using OpenAI's Whisper AI running locally on your computer.

---

## 📥 Download & Install

### Option 1: Installer (Recommended for most users)

**[Download Impulse-Setup.exe](https://github.com/Izayauh/whisper/releases/latest)**

1. Download the installer (~3.5 GB)
2. Run `Impulse-Setup.exe`
3. Follow the setup wizard
4. Start dictating!

No Python, no configuration, no technical knowledge required.

### Option 2: From Source (For developers)

```powershell
# Clone the repository
git clone https://github.com/Izayauh/whisper.git
cd whisper

# Run the canonical Windows launcher
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

- ✅ **100% Local** - No internet connection required
- ✅ **No Cloud** - Speech never leaves your computer
- ✅ **No Telemetry** - Zero data collection
- ✅ **Open Source** - Fully auditable code

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

1. Check the log file: `%LOCALAPPDATA%\Impulse\flow.log`
2. See [`USER_GUIDE.md`](USER_GUIDE.md) for detailed help
3. Open an issue on GitHub

---

## 📈 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

**Made with ❤️ for privacy-conscious users**
