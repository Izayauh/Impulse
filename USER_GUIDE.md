# 🎤 WhisperLocal - User Guide

A powerful, privacy-focused speech-to-text dictation system using OpenAI's Whisper running locally on your computer.

## ✨ Features

- **100% Local & Private** - All processing happens on your computer, no cloud services
- **GPU Accelerated** - Uses CUDA for fast transcription on NVIDIA GPUs
- **System-wide Dictation** - Works in any application
- **Real-time Feedback** - Visual status bar shows recording and transcription status
- **Smart Model Selection** - Automatically picks the best model for your dictation length
- **Modern Dashboard** - Track your usage with statistics and achievements

## 🚀 Quick Start

### Installation (Recommended)

1. **Download the installer** from the releases page
2. **Run `WhisperLocal-Setup.exe`**
3. **Follow the setup wizard**:
   - Select your microphone
   - Learn the simple controls
   - Optionally create desktop shortcut
4. **Start dictating!**

No Python installation required. Everything is bundled in the installer.

### Installation (For Developers)

If you prefer to run from source:

1. Install Python 3.8 or later
2. Run `start_dictation.bat` (auto-installs dependencies)
3. Follow the on-screen instructions

### First Time Setup

On first run, the setup wizard will guide you through:
1. **Microphone Selection** - Choose and test your preferred microphone
2. **Quick Tutorial** - Learn the simple hotkey controls
3. **Preferences** - Desktop shortcut and auto-start options

## 🎯 Usage

### Basic Controls

| Action | Hotkey |
|--------|--------|
| **Record** | Hold `WIN + CTRL` |
| **Transcribe & Paste** | Release `WIN + CTRL` |
| **Settings** | `WIN + CTRL + S` |
| **Exit** | `ESC` |
| **Self-Test** | `F8` or `CTRL + ALT + J` |
| **Debug Probe** | `F9` or `CTRL + ALT + D` |

### How to Dictate

1. **Position your cursor** where you want the text to appear
2. **Hold WIN + CTRL** and speak clearly into your microphone
3. **Release WIN + CTRL** when you're done speaking
4. The system will:
   - Process your speech (you'll see "⚙️ Transcribing...")
   - Automatically paste the text at your cursor position
   - Show "✅ Pasted!" when complete

### Status Bar Indicators

The status bar shows your current state:

| Status | Meaning |
|--------|---------|
| 🎤 Ready | System is ready, waiting for input |
| 🎙️ Listening... | Currently recording your voice |
| ⚙️ Transcribing... | Processing speech to text |
| ✅ Pasted! | Text successfully pasted |
| 🔇 No speech detected | Recording was too quiet or short |
| ❌ Failed | Transcription error occurred |

### Tips for Best Results

1. **Speak clearly** and at a normal pace
2. **Avoid background noise** - use a quiet environment
3. **Use a good microphone** - headset mics work best
4. **Wait for "Ready"** before recording again
5. **Keep recordings under 30 seconds** for best speed
6. **Check microphone settings** if you get "No speech detected"

## ⚙️ Configuration

### Changing Microphone

1. Press `WIN + CTRL + S` to open settings
2. Select your preferred microphone from the list
3. Click "Apply"
4. Click "Test" to verify it's working

### Environment Variables

You can customize behavior with these environment variables:

```batch
# Set custom Whisper binary location
set FLOW_WHISPER_BIN=C:\path\to\whisper-cli.exe

# Set GPU layers (default: 99 for full GPU)
set FLOW_WHISPER_ARGS=-ngl 99

# Set custom microphone device (by index or name)
set FLOW_INPUT_DEVICE=2
# OR
set FLOW_INPUT_DEVICE=USB

# Enable CUDA (default: enabled)
set GGML_CUDA_ENABLE=1
```

### Advanced Configuration

Edit `flow_local_dictation.py` to customize:

- **Hotkey**: Change `HOTKEY_HOLD` (line 56)
- **Model**: Change `MODEL_PATH_REL` (line 50)
- **Silence threshold**: Adjust `SILENCE_RMS_THRESHOLD` (line 74)
- **Post-processing**: Enable/disable filters (lines 61-63)

## 🔧 Troubleshooting

### "No input-capable audio devices found"

**Solution:**
1. Ensure your microphone is plugged in
2. Check Windows Sound Settings → Input
3. Set your microphone as the default device
4. Restart the application

### "Whisper binary not found"

**Solution:**
1. Ensure `whisper-cli.exe` or `main.exe` is in the project folder
2. Check if files were blocked by antivirus
3. Re-download the binary files

### "No speech detected" every time

**Solutions:**
1. Open Settings (`WIN + CTRL + S`) and click "Test"
2. Check if RMS value is > 0.005 when speaking
3. Increase microphone volume in Windows
4. Try a different microphone
5. Adjust `SILENCE_RMS_THRESHOLD` in the script

### GPU not being used

**Solutions:**
1. Verify CUDA is installed: `nvidia-smi` in command prompt
2. Check `gpu_last.log` for errors
3. Run `gpu_run.ps1` to test GPU functionality
4. Ensure you have CUDA 11.7+ installed
5. Update NVIDIA drivers

### Transcription is slow

**Solutions:**
1. Use GPU acceleration (NVIDIA GPU required)
2. Switch to a smaller model:
   - `ggml-base.en.bin` (fastest, less accurate)
   - `ggml-medium.en.bin` (balanced)
   - `ggml-large-v3.bin` (slowest, most accurate)
3. Edit line 50 in `flow_local_dictation.py` to change model

### Text pastes incorrectly

**Solutions:**
1. Ensure cursor is in correct position before releasing hotkey
2. Wait for "✅ Pasted!" confirmation
3. Check clipboard manually (`CTRL + V`) if auto-paste fails
4. Some applications may block automated pasting

## 📊 System Tray

The application runs in the system tray with these options:

- **Toggle Listening** - Pause/resume dictation
- **Self-test (JFK)** - Test with sample audio
- **Run Debug Probe** - Generate diagnostic logs
- **Quit** - Exit the application

## 📁 File Structure

```
Whisper/
├── flow_local_dictation.py   # Main application
├── start_dictation.bat        # Windows launcher (CMD)
├── start_dictation.ps1        # Windows launcher (PowerShell)
├── whisper-cli.exe            # Whisper binary
├── main.exe                   # Alternative Whisper binary
├── ggml-*.dll                 # GPU acceleration libraries
├── models/                    # Whisper AI models
│   ├── ggml-base.en.bin       # Fast, less accurate
│   ├── ggml-medium.en.bin     # Balanced
│   └── ggml-large-v3.bin      # Slow, most accurate
├── flow.log                   # Application log file
└── Whisper.ico                # Application icon
```

## 🔍 Logs and Debugging

### Log Files

- **flow.log** - Main application log with timestamps
- **gpu_last.log** - Latest GPU test results
- **flow_out.txt** - Last transcription output

### Debug Commands

- **F8** or **CTRL + ALT + J** - Run self-test with JFK sample
- **F9** or **CTRL + ALT + D** - Generate debug probe files in `./debug/`

### Checking Logs

```powershell
# View recent log entries
Get-Content flow.log -Tail 50

# Search for errors
Select-String -Path flow.log -Pattern "error|ERROR|fail"
```

## 🎨 Customization

### Changing Hotkey

Edit `flow_local_dictation.py`, line 56:

```python
HOTKEY_HOLD = "windows+ctrl"    # Default
# HOTKEY_HOLD = "alt+ctrl"      # Alternative
# HOTKEY_HOLD = "shift+ctrl"    # Alternative
```

### Changing Model

Edit `flow_local_dictation.py`, line 50:

```python
# For speed (less accurate):
MODEL_PATH_REL = os.path.join("models", "ggml-base.en.bin")

# For balance:
MODEL_PATH_REL = os.path.join("models", "ggml-medium.en.bin")

# For accuracy (slower):
MODEL_PATH_REL = os.path.join("models", "ggml-large-v3.bin")
```

### Status Bar Position

The status bar automatically positions itself near the taskbar. It adapts to:
- Bottom taskbar (centered above)
- Top taskbar (centered below)
- Left taskbar (to the right)
- Right taskbar (to the left)

## 📝 Model Information

### Available Models

| Model | Size | Speed | Accuracy | Language |
|-------|------|-------|----------|----------|
| `ggml-base.en.bin` | ~142 MB | Fastest | Good | English only |
| `ggml-medium.en.bin` | ~1.5 GB | Fast | Better | English only |
| `ggml-large-v3.bin` | ~3.1 GB | Slow | Best | Multilingual |

### Downloading Additional Models

Visit: https://huggingface.co/ggerganov/whisper.cpp

Place downloaded `.bin` files in the `models/` folder.

## 🆘 Support

### Common Issues

1. **Python not found**
   - Install from python.org
   - Ensure "Add to PATH" is checked during installation

2. **Missing packages**
   - Run: `python -m pip install sounddevice soundfile keyboard pyperclip pyautogui pillow pystray numpy`

3. **Permission errors**
   - Run as Administrator
   - Check antivirus isn't blocking Python

4. **GPU errors**
   - Install CUDA Toolkit 11.7 or later
   - Update NVIDIA drivers
   - Check GPU compatibility (Compute Capability 7.0+)

### Getting Help

1. Check `flow.log` for error messages
2. Run self-test with `F8`
3. Generate debug info with `F9`
4. Check microphone settings with `WIN + CTRL + S`

## 🔐 Privacy & Security

- **100% Local Processing** - No data sent to cloud services
- **No Internet Required** - Works completely offline
- **No Data Collection** - Your speech is never stored or transmitted
- **Open Source** - Based on Whisper.cpp, fully auditable code

## ⚡ Performance Tips

### For Maximum Speed

1. Use GPU acceleration (NVIDIA GPU)
2. Use `ggml-base.en.bin` model
3. Keep recordings short (< 15 seconds)
4. Close other GPU-intensive applications

### For Maximum Accuracy

1. Use `ggml-large-v3.bin` model
2. Use a high-quality microphone
3. Speak in a quiet environment
4. Speak clearly and at normal pace
5. Enable accuracy mode for longer dictations (automatic for >15s)

## 📋 Keyboard Commands Reference

### Voice Commands (spoken during recording)

- "new line" → Line break
- "new paragraph" → Double line break
- "comma" → , 
- "period" → . 
- "exclamation" → ! 
- "question mark" → ? 

### System Hotkeys

- `WIN + CTRL` (hold) - Record
- `WIN + CTRL + S` - Settings
- `ESC` - Exit
- `F8` / `CTRL + ALT + J` - Self-test
- `F9` / `CTRL + ALT + D` - Debug probe
- `CTRL + ALT + B` - Enable bullet list mode

## 🔄 Updates & Maintenance

### Updating Python Packages

```batch
python -m pip install --upgrade sounddevice soundfile keyboard pyperclip pyautogui pillow pystray numpy
```

### Checking Version

```batch
python --version
python -m pip list
```

### Clearing Cache

Delete these files to reset:
- `flow.log`
- `flow_input.wav`
- `flow_out.txt`
- `gpu_last.log`

## 📞 Emergency Commands

If the application becomes unresponsive:

1. Press `ESC` to attempt clean exit
2. Press `CTRL + C` in the console window
3. Use Task Manager to end `python.exe` process
4. Check `flow.log` for error information

---

**Version:** 2.0  
**Last Updated:** December 2025  
**License:** MIT  
**Based on:** [Whisper.cpp](https://github.com/ggerganov/whisper.cpp)


