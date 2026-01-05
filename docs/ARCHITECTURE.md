# WhisperLocal Architecture

Complete architectural overview of the WhisperLocal application.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Diagram](#component-diagram)
3. [Data Flow](#data-flow)
4. [Module Structure](#module-structure)
5. [Key Design Decisions](#key-design-decisions)
6. [Security Architecture](#security-architecture)
7. [Performance Considerations](#performance-considerations)

---

## System Overview

WhisperLocal is a privacy-focused, GPU-accelerated speech-to-text dictation application for Windows. It uses OpenAI's Whisper AI running entirely locally on the user's computer.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface Layer                     │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────────┐│
│  │ Status Pill  │  │ Dashboard UI   │  │  Settings Window     ││
│  │ (Tkinter)    │  │ (Statistics)   │  │  (Mic Selection)     ││
│  └──────────────┘  └────────────────┘  └──────────────────────┘│
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                      Application Core Layer                      │
│  ┌──────────────┐  ┌────────────┐  ┌─────────────────────────┐ │
│  │  Hotkey      │  │  Stats     │  │  Configuration          │ │
│  │  Handler     │  │  Tracker   │  │  Management             │ │
│  └──────────────┘  └────────────┘  └─────────────────────────┘ │
│                                                                  │
│  ┌──────────────┐  ┌────────────┐  ┌─────────────────────────┐ │
│  │  Audio       │  │  Logging   │  │  Performance            │ │
│  │  Recorder    │  │  System    │  │  Monitor                │ │
│  └──────────────┘  └────────────┘  └─────────────────────────┘ │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                    Transcription Engine Layer                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Smart Model Selector                          │  │
│  │  (Estimates word count, selects base/medium/large)      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Subprocess  │  │  Input       │  │  Output Sanitization │  │
│  │ Management  │  │  Validation  │  │  & Post-Processing   │  │
│  └─────────────┘  └──────────────┘  └──────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                     Whisper AI Engine                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  whisper-cli.exe (C++ binary from whisper.cpp)            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Base Model  │  │ Medium Model │  │ Large Model          │  │
│  │ (Fast)      │  │ (Balanced)   │  │ (Accurate)           │  │
│  └─────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  GGML + CUDA (GPU Acceleration)                           │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## Component Diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                    whisper_local Package                           │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐│
│  │  config.py   │  │  stats.py    │  │  logging_config.py       ││
│  │              │  │              │  │                          ││
│  │  • Config    │  │  • Stats     │  │  • setup_logging()       ││
│  │    class     │  │    Tracker   │  │  • StructuredLogger      ││
│  │  • Path      │  │  • Daily     │  │  • Rotating file         ││
│  │    resolution│  │    tracking  │  │    handlers              ││
│  │  • Constants │  │  • Streaks   │  │  • JSON events           ││
│  └──────────────┘  └──────────────┘  └──────────────────────────┘│
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐│
│  │performance.py│  │  updater.py  │  │  crash_reporter.py       ││
│  │              │  │              │  │                          ││
│  │  • Perf      │  │  • Update    │  │  • CrashReporter         ││
│  │    Monitor   │  │    Checker   │  │  • Exception handler     ││
│  │  • Context   │  │  • Version   │  │  • Local reports         ││
│  │    manager   │  │    compare   │  │    only                  ││
│  │  • Stats     │  │  • Download  │  │  • Context manager       ││
│  └──────────────┘  └──────────────┘  └──────────────────────────┘│
│                                                                    │
│  ┌──────────────┐                                                 │
│  │  health.py   │                                                 │
│  │              │                                                 │
│  │  • Health    │                                                 │
│  │    Check     │                                                 │
│  │  • Component │                                                 │
│  │    status    │                                                 │
│  │  • Diagnostics│                                                │
│  └──────────────┘                                                 │
└───────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Transcription Flow

```
1. User Action
   ├─> Press WIN+CTRL (hotkey detected)
   │
2. Recording Phase
   ├─> Start audio recording (sounddevice)
   ├─> Capture microphone input (16kHz mono)
   ├─> Voice Activity Detection (VAD)
   ├─> Save to temporary WAV file
   │
3. Model Selection
   ├─> Estimate word count from duration
   ├─> Select model:
   │   • < 25 words → base.en (fastest)
   │   • 25-75 words → medium.en (balanced)
   │   • > 75 words → large-v3 (best quality)
   │
4. Transcription
   ├─> Build whisper-cli command
   ├─> Execute subprocess
   ├─> Stream output with timeout protection
   ├─> Handle errors gracefully
   │
5. Post-Processing
   ├─> Sanitize output
   │   • Remove [BLANK_AUDIO] tokens
   │   • Filter deprecation warnings
   │   • Validate size limits
   ├─> Apply text filters
   │   • Remove filler words (optional)
   │   • Apply voice commands
   ├─> Deduplicate repeated lines
   │
6. Output
   ├─> Copy to clipboard
   ├─> Paste to active window
   ├─> Update statistics
   ├─> Log performance metrics
   └─> Clean up temporary files
```

### Statistics Flow

```
Transcription Event
   │
   ├─> StatsTracker.record_transcription()
   │   │
   │   ├─> Update word counts
   │   │   • Total words
   │   │   • Daily words
   │   │   • Weekly words
   │   │
   │   ├─> Update usage stats
   │   │   • Total sessions
   │   │   • Model usage counts
   │   │   • Last use date
   │   │
   │   ├─> Check streak
   │   │   • Consecutive days
   │   │   • Update or reset
   │   │
   │   ├─> Check milestones
   │   │   • 1K, 5K, 10K, etc.
   │   │   • Award achievements
   │   │
   │   ├─> Store recent transcripts
   │   │   • Keep last 5
   │   │   • For copy/replay
   │   │
   │   └─> Save to JSON file
   │       • Atomic write
   │       • Error handling
   │
   └─> UI Update
       • Refresh dashboard
       • Show new stats
```

### Health Check Flow

```
Health Check Request
   │
   ├─> Run all registered checks
   │   │
   │   ├─> Check Whisper Binary
   │   │   • Exists?
   │   │   • Executable?
   │   │   • Status: healthy/unhealthy
   │   │
   │   ├─> Check AI Models
   │   │   • base.en present?
   │   │   • medium.en present?
   │   │   • large-v3 present?
   │   │   • Status: healthy/degraded/unhealthy
   │   │
   │   ├─> Check Audio Devices
   │   │   • Input devices available?
   │   │   • Default device set?
   │   │   • Status: healthy/unhealthy
   │   │
   │   ├─> Check File Permissions
   │   │   • Can write to user dir?
   │   │   • Can read/write test file?
   │   │   • Status: healthy/unhealthy
   │   │
   │   ├─> Check Disk Space
   │   │   • Free space > 2 GB? (healthy)
   │   │   • Free space > 500 MB? (degraded)
   │   │   • Free space < 500 MB? (unhealthy)
   │   │
   │   └─> Check Dependencies
   │       • All required modules installed?
   │       • Status: healthy/unhealthy
   │
   ├─> Determine overall status
   │   • Any unhealthy? → unhealthy
   │   • Any degraded? → degraded
   │   • All healthy? → healthy
   │
   └─> Return results
       • JSON report
       • Human-readable summary
       • Can save to file
```

---

## Module Structure

### Core Modules

| Module | Responsibilities | Key Classes/Functions |
|--------|------------------|----------------------|
| `config.py` | Configuration management, path resolution, constants | `Config`, `get_bundle_dir()`, `get_user_data_dir()` |
| `stats.py` | Usage statistics, word tracking, achievements | `StatsTracker` |
| `logging_config.py` | Logging setup, structured logging | `setup_logging()`, `StructuredLogger` |
| `performance.py` | Performance monitoring, metrics collection | `PerformanceMonitor`, `perf_monitor` |
| `updater.py` | Auto-update checks, version comparison | `UpdateChecker` |
| `crash_reporter.py` | Exception handling, crash reports | `CrashReporter`, `install_crash_handler()` |
| `health.py` | System diagnostics, health checks | `HealthCheck`, `get_health_check()` |

### Dependencies

```
External Dependencies (from requirements.txt)
├─> sounddevice (audio recording)
├─> soundfile (WAV file I/O)
├─> keyboard (hotkey detection)
├─> pyperclip (clipboard operations)
├─> pyautogui (automated pasting)
├─> Pillow (image processing for UI)
├─> pystray (system tray icon)
└─> numpy (audio data processing)

Optional Dependencies
├─> winotify (Windows toast notifications)
├─> requests (update checks, optional)
└─> packaging (version comparison)
```

---

## Key Design Decisions

### 1. Privacy-First Architecture

**Decision:** All processing happens locally, no network communication.

**Rationale:**
- Users' voice data is sensitive
- No dependency on cloud services
- Works completely offline
- GDPR/privacy compliant by design

**Implementation:**
- No analytics or telemetry
- No cloud API calls
- Local-only file storage
- Statistics never leave the machine

### 2. Smart Model Selection

**Decision:** Automatically select model based on estimated content length.

**Rationale:**
- Short phrases don't need high-accuracy models
- Long content benefits from better models
- Optimize speed vs. quality tradeoff

**Implementation:**
```python
if word_count < 25:
    model = "base.en"      # Fast (100ms)
elif word_count < 75:
    model = "medium.en"    # Balanced (500ms)
else:
    model = "large-v3"     # Accurate (2-5s)
```

### 3. Modular Architecture

**Decision:** Split monolithic code into focused modules.

**Rationale:**
- Easier to maintain and test
- Single responsibility principle
- Better code organization
- Facilitates future enhancements

**Result:**
- 7 focused modules vs. 1 monolithic file
- Each module < 400 lines
- Clear boundaries and interfaces

### 4. Type Hints Throughout

**Decision:** Add comprehensive type hints to all functions.

**Rationale:**
- Catch errors at development time
- Better IDE support
- Self-documenting code
- Easier refactoring

**Coverage:** ~95% of functions typed

### 5. Graceful Degradation

**Decision:** Application works even if optional features fail.

**Examples:**
- GPU unavailable → use CPU
- Fast model missing → use available model
- Notifications fail → log to console
- Update check fails → continue normally

---

## Security Architecture

### Input Validation

```
User Input → Validation Layer → Processing
     │              │                │
     │         ┌────▼────┐          │
     │         │ Size    │          │
     │         │ Limits  │          │
     │         └─────────┘          │
     │         ┌─────────┐          │
     │         │ Sanit   │          │
     │         │ ization │          │
     │         └─────────┘          │
     │         ┌─────────┐          │
     │         │ Format  │          │
     │         │ Check   │          │
     │         └────┬────┘          │
     │              │                │
     └──────────────┴────────────────┘
```

**Protections:**
- Max transcript size: 1 MB
- Max line count: 10,000
- Max line length: 10,000 chars
- No `shell=True` in subprocess calls
- No `eval()` or `exec()` usage
- Path normalization

### File System Security

- User data in `%LOCALAPPDATA%\WhisperLocal`
- Proper permission checks
- Temporary file cleanup
- Atomic file writes
- Error handling for all I/O

### Process Security

- Subprocess args use list format (not shell strings)
- Timeout protection (120s max)
- Resource limits respected
- Single instance lock

---

## Performance Considerations

### Memory Management

- Audio buffers: ~1 MB per recording
- Model loading: 150 MB - 3 GB (GPU memory)
- Statistics: < 1 MB
- Logs: 5 MB max (rotating)
- Crash reports: Keep last 30 days

### CPU/GPU Usage

- GPU preferred for transcription (2-5x faster)
- Automatic fallback to CPU
- Minimal CPU during idle
- Audio recording: ~1-2% CPU
- UI updates: ~1% CPU

### Disk I/O

- Temporary WAV files cleaned after use
- Statistics saved after each transcription
- Logs written asynchronously
- Models loaded once and cached

### Network (Optional)

- Update checks: < 100 KB
- Only when explicitly triggered
- Respects timeout limits
- Never blocks main thread

---

## Future Enhancements

1. **Multi-Language Support**
   - Additional Whisper models
   - Language auto-detection
   - Per-language settings

2. **Cloud Sync (Optional)**
   - End-to-end encrypted
   - Statistics synchronization
   - Opt-in only

3. **Plugin System**
   - Custom post-processors
   - Additional UI components
   - Model extensions

4. **macOS/Linux Support**
   - Cross-platform audio
   - Platform-specific hotkeys
   - Native UI components

---

## Conclusion

WhisperLocal is architected as a privacy-focused, modular, and performant application that prioritizes user experience while maintaining security and reliability. The clean separation of concerns and comprehensive error handling make it production-ready for desktop deployment.

---

**For more details, see:**
- [API Documentation](API.md)
- [Developer Guide](../CONTRIBUTING.md)
- [User Guide](../USER_GUIDE.md)

