# Changelog

All notable changes to WhisperLocal will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-XX

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

### Planned Features

- macOS and Linux support
- Custom hotkey configuration
- Voice commands for punctuation
- Multiple language support
- Auto-updater

---

*For bug reports and feature requests, please open an issue on GitHub.*
