# Changelog

All notable changes to Impulse will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.8] - 2026-09-04

### Fixed

- The stop-take sound now plays in the installed app. The bundled message-send.mp3 sat at the bundle root while the app looked beside its own module, so every installer since the first frozen build fell back to a plain beep. The release gate now checks the file is where the app reads it.

## [1.0.7] - 2026-09-04

### Changed

- **Dashboard redesign**: words-first Home (today's count, best-day record bar, 14-day graph, recent dictations with copy), sidebar shell, Settings as a tabbed page, two themes (dark and light) on bundled Geist fonts. Achievements, challenges, XP and level rendering removed.
- **Pill**: four moments (listening, working sweep, one-second landed count, idle). No halo or pink border.
- **Settings**: microphone select lists real input devices; Stop-after-silence slider removed (no engine consumer).

### Fixed

- Silent takes no longer reach Whisper: noise-floor gate tied to the sensitivity slider.
- Fabricated text: VAD filter, single-temperature decode, non-speech segment filter and repeated-phrase collapse. Silero VAD model now bundled in the frozen build.
- Sensitivity and microphone settings re-read at the start of every take.
- Start menu no longer opens on the Win-key hotkey release.
- Home stats merge older JSON-only history so past days are not read as zero.
- Dashboard window opens at a true 1100x740 client area.

## [1.0.0-beta.1] - 2026-03-03

### Added

- **Standalone Installer**: One-click installation for Windows 10/11 users
  - No Python installation required
  - All dependencies bundled (AI models, CUDA libraries)
  - Automatic desktop shortcut and Start Menu integration
  - Optional auto-start on Windows boot

- **First-Run Setup Wizard**: Guided setup for new users
  - Welcome screen with feature overview
  - Microphone selection and testing
  - Quick tutorial with visual instructions
  - One-click configuration

- **Smart Model Selection**: Automatic quality vs speed optimization
  - Uses fast model (base.en) for short phrases (<25 words)
  - Uses balanced model (medium.en) for medium dictations (25-75 words)
  - Uses high-quality model (large-v3) for long content (75+ words)

- **Modern Dark Theme UI**: Pink/black aesthetic with smooth animations
  - Floating pill status indicator near taskbar
  - Full dashboard with statistics and recent transcripts
  - Gamification features (streaks, milestones, word counts)

- **GPU Acceleration**: CUDA support for NVIDIA GPUs
  - Automatic GPU detection and warmup
  - Graceful fallback to CPU if GPU unavailable
  - Flash Attention support for 2x faster inference

- **🎮 GPU Load Monitoring**: Real-time adaptive model selection (NEW!)
  - Monitors GPU utilization every 2 seconds
  - Automatically switches to lighter models when GPU is busy (70%+ load)
  - Forces base.en model during critical GPU load (85%+)
  - Prevents game stuttering and frame drops
  - Detects non-NVIDIA GPUs (AMD, Intel) and uses compatible models
  - Background monitoring with minimal overhead (<0.1% CPU)

- **Privacy-First Design**: 100% local processing
  - No internet connection required after installation
  - No data collection or telemetry
  - All speech processed on-device

- **System-Wide Dictation**: Works in any Windows application
  - Simple WIN+CTRL hotkey to record
  - Automatic paste into active window
  - Clipboard fallback if paste fails

- **User-Friendly Error Handling**: Clear messages for non-technical users
  - Helpful troubleshooting suggestions
  - Settings wizard for common issues
  - Detailed logging for advanced debugging

### Beta Notes

- **License required.** A beta key is required at first run.
- **Beta expires April 30, 2026.** The app will stop transcribing after this date until updated.
- **Telemetry opt-in.** Anonymous usage events may be collected with your permission.
- **Hotkey reliability.** Uses Win32 `GetAsyncKeyState` instead of the `keyboard` library, which silently fails on Windows 11.
- **Latch mode.** `WIN+CTRL+ALT` toggles hands-free recording without holding keys.
- **Ollama optional.** "Polished" stylization requires a local Ollama instance; falls back gracefully if unavailable.

### Known Limitations

- English only (base.en, medium.en, large-v3 models)
- Windows 10/11 only — macOS and Linux not yet supported
- Custom hotkeys not yet configurable in UI (hardcoded WIN+CTRL)

### Technical Details

- Based on [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) for efficient inference
- Uses PyInstaller for standalone executable bundling
- Inno Setup for Windows installer creation
- Tkinter-based UI with custom theming

### System Requirements

- Windows 10 or Windows 11 (64-bit)
- 4 GB RAM minimum (8 GB recommended)
- 4 GB disk space for installation
- Microphone (USB, 3.5mm, or Bluetooth)
- NVIDIA GPU with CUDA support (optional, for faster transcription)

---

## [Unreleased]

### Planned

- macOS and Linux support
- Custom hotkey configuration in UI
- Voice commands for punctuation
- Multiple language support

---

*For bug reports and feature requests, please open an issue on GitHub.*
