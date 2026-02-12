# WhisperLocal Testing Checklist

Use this checklist to test the installer before release.

## Build Instructions

1. Install prerequisites:
   ```powershell
   pip install pyinstaller
   # Download Inno Setup from https://jrsoftware.org/isdl.php
   ```

2. Run the build script:
   ```powershell
   .\build_installer.ps1
   ```

3. Find the installer at: `dist\WhisperLocal-Setup-1.0.0.exe`

---

## Test Environments

### Environment 1: Clean Windows 10 (No Python, No CUDA)
- [ ] VirtualBox/VMware with fresh Windows 10 22H2
- [ ] No Python installed
- [ ] No NVIDIA drivers (Intel/AMD graphics)

### Environment 2: Clean Windows 11 (No Python, No CUDA)
- [ ] VirtualBox/VMware with fresh Windows 11
- [ ] No Python installed
- [ ] No NVIDIA drivers

### Environment 3: Windows with NVIDIA GPU + CUDA
- [ ] Physical or VM with NVIDIA GPU passthrough
- [ ] CUDA toolkit installed
- [ ] Latest NVIDIA drivers

### Environment 4: Standard User Account
- [ ] Non-administrator Windows account
- [ ] Verify installation to user profile works

---

## Installation Tests

- [ ] **Installer launches** without errors
- [ ] **UAC prompt** appears appropriately (or not for per-user install)
- [ ] **Progress bar** shows during file extraction
- [ ] **Installation completes** without errors
- [ ] **Desktop shortcut** created (if selected)
- [ ] **Start Menu entry** created
- [ ] **Uninstall entry** appears in Windows Settings > Apps

---

## First Run Tests

- [ ] **Application launches** after installation
- [ ] **First-run wizard** appears
- [ ] **Microphone list** populated correctly
- [ ] **Mic test** shows audio level
- [ ] **Tutorial screens** display correctly
- [ ] **Finish** button completes setup

---

## Functionality Tests

### Basic Dictation
- [ ] **Status pill** appears near taskbar
- [ ] **WIN+CTRL hold** shows "Listening..."
- [ ] **Speaking** records audio
- [ ] **Release** shows "Transcribing..."
- [ ] **Text pastes** into target application
- [ ] **Status returns** to "Ready"

### Dashboard
- [ ] **Click pill** opens dashboard
- [ ] **Statistics** display correctly
- [ ] **Recent transcripts** list populated
- [ ] **Copy Last** button works
- [ ] **Settings** button opens settings
- [ ] **Window dragging** works

### Settings
- [ ] **WIN+CTRL+S** opens settings
- [ ] **Device list** shows all microphones
- [ ] **Device selection** works
- [ ] **Mic test** shows levels
- [ ] **Apply** saves selection

### Error Handling
- [ ] **No mic** - Shows friendly error
- [ ] **Muted mic** - Shows "No speech detected"
- [ ] **Very short** recording - Handles gracefully
- [ ] **Long recording** (>30s) - Completes successfully

---

## GPU Tests (NVIDIA systems only)

- [ ] **CUDA detected** in log file
- [ ] **GPU warmup** completes on startup
- [ ] **Transcription speed** ~5-10x faster than CPU
- [ ] **No CUDA errors** in log

---

## CPU Fallback Tests

- [ ] **Non-NVIDIA system** uses CPU gracefully
- [ ] **Transcription works** (slower but functional)
- [ ] **No GPU error messages** shown to user

---

## Uninstallation Tests

- [ ] **Uninstall from Settings** works
- [ ] **Prompt for data deletion** appears
- [ ] **Application files** removed from Program Files
- [ ] **Desktop shortcut** removed
- [ ] **Start Menu entry** removed
- [ ] **Registry entries** cleaned up

---

## Edge Cases

- [ ] **Multiple displays** - Pill positions correctly
- [ ] **High DPI (150%, 200%)** - UI scales properly
- [ ] **Different taskbar positions** (top, left, right)
- [ ] **Already running** - Shows error, doesn't duplicate
- [ ] **Rapid hotkey presses** - No crashes

---

## Log Verification

Check `%LOCALAPPDATA%\WhisperLocal\flow.log` for:
- [ ] No ERROR entries during normal operation
- [ ] Model loading messages
- [ ] Device selection confirmation
- [ ] Transcription timing information

---

## Performance Benchmarks

Record approximate times on each test system:

| System | Model Load | Short Dict | Long Dict |
|--------|------------|------------|-----------|
| Win10 CPU | ___s | ___s | ___s |
| Win11 CPU | ___s | ___s | ___s |
| GPU System | ___s | ___s | ___s |

---

## Sign-Off

- [ ] All critical tests pass
- [ ] No blocking issues found
- [ ] Ready for release

**Tested by:** _______________  
**Date:** _______________  
**Version:** 1.0.0

