# WhisperLocal Launchers Guide

## 🚀 Normal Use (Silent Mode)

**Recommended for daily use** - No console window, runs silently in background.

### Windows Batch
```
START_WHISPER.bat
```
Double-click to launch. App runs with:
- ✅ System tray icon
- ✅ Floating pill indicator
- ✅ Dashboard accessible
- ❌ No console window
- ❌ No debug output visible

### PowerShell
```
START_WHISPER.ps1
```
Alternative PowerShell launcher with same silent behavior.

---

## 🐛 Debug Mode (Console Visible)

**Use for troubleshooting** - Console window shows all debug output.

### Windows Batch
```
START_WHISPER_DEBUG.bat
```
Double-click to launch. App runs with:
- ✅ System tray icon
- ✅ Floating pill indicator
- ✅ Dashboard accessible
- ✅ Console window showing debug output
- ✅ All [DEBUG] messages visible
- ✅ Real-time stats tracking logs
- ✅ Error messages and stack traces

### PowerShell
```
START_WHISPER_DEBUG.ps1
```
Alternative PowerShell debug launcher.

---

## 🔧 How It Works

### Silent Mode (`pythonw.exe`)
- Uses `pythonw.exe` instead of `python.exe`
- No console window created
- `DEBUG_MODE = False` detected automatically
- All `debug_print()` calls are suppressed
- Regular `print()` statements still work but have nowhere to output

### Debug Mode (`python.exe`)
- Uses `python.exe` with console
- Console window stays visible
- `DEBUG_MODE = True` detected automatically
- All `debug_print()` calls output to console
- Useful for:
  - Seeing stats save/load operations
  - Dashboard refresh logs
  - Transcription processing details
  - Error diagnostics

---

## 📊 Debug Output Examples

When running in debug mode, you'll see:

```
[DEBUG] Stats tracker initialized with file: C:\...\whisper_stats.json
[DEBUG] Loading stats from: C:\...\whisper_stats.json
[DEBUG] Stats loaded: 25099 total words, 367 sessions

[DEBUG] record_transcription called with 11 words
[DEBUG] Recording: 11 words on 2026-01-16
[DEBUG] Saving stats to: C:\...\whisper_stats.json
[DEBUG] Stats saved: 947 words today, 25086 total words

[DEBUG] Dashboard auto-refresh: reloading stats from C:\...\whisper_stats.json
[DEBUG] Refreshing dashboard UI: today=947, week=5234, total=25099, avg_wpm=178
```

---

## ✅ Recommended Usage

**Daily use:** `START_WHISPER.bat`
- Clean, silent operation
- No cluttered desktop windows
- Professional appearance

**When troubleshooting:**
1. Close the normal app (if running)
2. Launch `START_WHISPER_DEBUG.bat`
3. Reproduce the issue
4. Check console output for errors
5. Share console logs with support

---

## 🔄 Switching Modes

To switch from silent to debug mode:
1. Exit the app completely (right-click tray icon → Quit)
2. Launch the debug version
3. The app will detect it's running with a console and enable debug output

No code changes or configuration needed - it's automatic!
