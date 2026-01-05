# WhisperLocal API Documentation

Complete API reference for the WhisperLocal package.

---

## Table of Contents

1. [Configuration](#configuration)
2. [Statistics](#statistics)
3. [Logging](#logging)
4. [Performance Monitoring](#performance-monitoring)
5. [Auto-Update](#auto-update)
6. [Crash Reporting](#crash-reporting)
7. [Health Checks](#health-checks)

---

## Configuration

### Config Class

Singleton class for application configuration.

```python
from whisper_local import config

# Access configuration
print(config.app_name)        # "WhisperLocal"
print(config.app_version)      # "1.0.0"
print(config.sample_rate)      # 16000
print(config.whisper_binary)   # Auto-detected path
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `app_name` | str | Application name |
| `app_version` | str | Application version |
| `sample_rate` | int | Audio sample rate (Hz) |
| `channels` | int | Audio channels (1=mono) |
| `whisper_binary` | str | Path to whisper-cli.exe |
| `model_base` | str | Path to base model |
| `model_medium` | str | Path to medium model |
| `model_large` | str | Path to large model |

### Helper Functions

```python
from whisper_local import get_bundle_dir, get_app_dir, get_user_data_dir

bundle_dir = get_bundle_dir()  # Where bundled resources are
app_dir = get_app_dir()        # Where exe/script is
user_dir = get_user_data_dir() # User-writable directory
```

---

## Statistics

### StatsTracker Class

Track usage statistics and achievements.

```python
from whisper_local import StatsTracker

tracker = StatsTracker()
tracker.record_transcription("Hello world", "base.en")

# Get statistics
today = tracker.get_today_words()
week = tracker.get_week_words()
summary = tracker.get_summary()
```

#### Methods

##### `record_transcription(text: str, model: str)`

Record a transcription event.

**Parameters:**
- `text` (str): The transcribed text
- `model` (str): Model used (base.en, medium.en, large-v3)

**Example:**
```python
tracker.record_transcription("Hello world", "base.en")
```

##### `get_today_words() -> int`

Get word count for today.

**Returns:** Integer word count

##### `get_week_words() -> int`

Get word count for the last 7 days.

**Returns:** Integer word count

##### `get_week_data() -> List[Tuple[str, int]]`

Get last 7 days of word counts.

**Returns:** List of (day_name, word_count) tuples

##### `get_summary() -> Dict`

Get complete statistics summary.

**Returns:** Dictionary with all stats

---

## Logging

### Setup Logging

```python
from whisper_local import setup_logging

logger = setup_logging("WhisperLocal", "app.log")
logger.info("Application started")
logger.error("Something went wrong")
```

### Structured Logging

```python
from whisper_local import StructuredLogger

structured = StructuredLogger("WhisperLocal", "app.log")

# Log events
structured.log_transcription("base.en", 0.5, 25, success=True)
structured.log_error("transcription_failed", "Binary not found")
structured.log_performance("model_load", 2.3)
```

#### StructuredLogger Methods

##### `log_event(event_type: str, data: Dict)`

Log a structured event.

##### `log_transcription(model: str, duration: float, words: int, success: bool)`

Log transcription event.

##### `log_error(error_type: str, message: str, details: Optional[Dict])`

Log error event.

##### `log_performance(operation: str, duration: float)`

Log performance metric.

---

## Performance Monitoring

### PerformanceMonitor Class

Monitor application performance.

```python
from whisper_local import perf_monitor

# Measure operation
with perf_monitor.measure('transcription'):
    result = transcribe_audio(wav_file)

# Get statistics
stats = perf_monitor.get_stats('transcription')
print(f"Mean time: {stats['mean']:.3f}s")

# Print summary
print(perf_monitor.get_summary())
```

#### Methods

##### `measure(operation: str)` (context manager)

Measure operation duration.

**Example:**
```python
with perf_monitor.measure('model_load'):
    load_model()
```

##### `record(operation: str, duration: float)`

Record a manual measurement.

##### `get_stats(operation: str) -> Dict`

Get statistics for an operation.

**Returns:**
```python
{
    'count': 50,
    'mean': 0.523,
    'median': 0.500,
    'min': 0.200,
    'max': 1.500,
    'std_dev': 0.250,
    'total': 26.150
}
```

##### `get_all_stats() -> Dict[str, Dict]`

Get statistics for all operations.

##### `get_summary() -> str`

Get human-readable summary.

---

## Auto-Update

### UpdateChecker Class

Check for application updates.

```python
from whisper_local import UpdateChecker

checker = UpdateChecker()

# Check for updates
result = checker.check_for_updates()

if result['update_available']:
    print(f"New version: {result['latest_version']}")
    print(f"Download: {result['download_url']}")
    print(f"Release notes: {result['release_notes']}")
```

#### Methods

##### `check_for_updates(timeout: int = 5) -> Dict`

Check if update is available.

**Returns:**
```python
{
    'update_available': bool,
    'current_version': str,
    'latest_version': str,
    'download_url': str,
    'release_notes': str,
    'release_date': str,
    'error': Optional[str]
}
```

##### `should_check_for_updates(check_interval_hours: int = 24) -> bool`

Determine if it's time to check for updates.

##### `download_update(download_url: str, output_path: str, progress_callback: Optional[callable]) -> Tuple[bool, Optional[str]]`

Download update installer.

**Returns:** (success, error_message)

##### `get_update_summary() -> str`

Get human-readable update status.

### Helper Functions

```python
from whisper_local import check_for_updates_async, show_update_notification

# Check in background
check_for_updates_async(lambda result: print(result))

# Show notification
show_update_notification(update_info)
```

---

## Crash Reporting

### CrashReporter Class

Capture and save crash reports locally.

```python
from whisper_local import CrashReporter, install_crash_handler

# Install global handler
reporter = CrashReporter()
install_crash_handler(reporter)

# Manual crash reporting
try:
    risky_operation()
except Exception as e:
    crash_id = reporter.save_crash_report(e, context={'operation': 'test'})
    print(f"Crash ID: {crash_id}")
```

#### Methods

##### `save_crash_report(exception: Exception, context: Optional[Dict]) -> str`

Save crash report to file.

**Returns:** Crash ID

##### `get_recent_crashes(limit: int = 10) -> List[Dict]`

Get recent crash reports.

##### `get_crash_count() -> int`

Get total number of crash reports.

##### `clean_old_crashes(keep_days: int = 30)`

Remove old crash reports.

##### `get_crash_summary() -> str`

Get human-readable crash summary.

### Context Manager

```python
from whisper_local import CrashContext, get_crash_reporter

reporter = get_crash_reporter()

with CrashContext(reporter, {'operation': 'transcription'}):
    # Code that might crash
    transcribe_audio(wav_file)
```

### Global Functions

```python
from whisper_local import install_crash_handler, uninstall_crash_handler, get_crash_reporter

# Install handler
install_crash_handler()

# Get global instance
reporter = get_crash_reporter()

# Uninstall handler
uninstall_crash_handler()
```

---

## Health Checks

### HealthCheck Class

System health diagnostics.

```python
from whisper_local import HealthCheck, get_health_check

health = get_health_check()

# Run all checks
result = health.run_all_checks()
print(f"Overall status: {result['overall_status']}")

# Get summary
print(health.get_health_summary())

# Save report
report_path = health.save_health_report()
```

#### Methods

##### `run_all_checks() -> Dict`

Run all registered health checks.

**Returns:**
```python
{
    'timestamp': str,
    'overall_status': str,  # 'healthy', 'degraded', 'unhealthy', 'unknown'
    'checks': {
        'whisper_binary': {...},
        'ai_models': {...},
        'audio_devices': {...},
        'file_permissions': {...},
        'disk_space': {...},
        'dependencies': {...}
    }
}
```

##### `check_whisper_binary() -> Dict`

Check if Whisper binary exists.

##### `check_models() -> Dict`

Check if AI models are available.

##### `check_audio_devices() -> Dict`

Check audio input devices.

##### `check_file_permissions() -> Dict`

Check file system permissions.

##### `check_disk_space() -> Dict`

Check available disk space.

##### `check_dependencies() -> Dict`

Check required dependencies.

##### `get_health_summary() -> str`

Get human-readable health summary.

##### `save_health_report(output_file: Optional[str]) -> str`

Save health report to file.

**Returns:** Path to saved report

### HealthStatus Constants

```python
from whisper_local import HealthStatus

HealthStatus.HEALTHY     # "healthy"
HealthStatus.DEGRADED    # "degraded"
HealthStatus.UNHEALTHY   # "unhealthy"
HealthStatus.UNKNOWN     # "unknown"
```

---

## Complete Example

```python
from whisper_local import (
    config,
    StatsTracker,
    setup_logging,
    StructuredLogger,
    perf_monitor,
    UpdateChecker,
    install_crash_handler,
    get_health_check
)

# Setup
logger = setup_logging("WhisperLocal", config.log_file)
structured = StructuredLogger("WhisperLocal", config.log_file)
install_crash_handler()

# Health check
health = get_health_check()
if health.run_all_checks()['overall_status'] != 'healthy':
    print("Warning: System health issues detected")
    print(health.get_health_summary())

# Check for updates
checker = UpdateChecker()
if checker.should_check_for_updates():
    update_info = checker.check_for_updates()
    if update_info['update_available']:
        print(f"Update available: {update_info['latest_version']}")

# Statistics
stats = StatsTracker()

# Performance monitoring
with perf_monitor.measure('transcription'):
    # Your code here
    result = transcribe_audio(wav_file)

# Record transcription
stats.record_transcription(result, "base.en")
structured.log_transcription("base.en", 0.5, len(result.split()), True)

# Print summaries
print(perf_monitor.get_summary())
print(f"Words today: {stats.get_today_words()}")
```

---

## License

MIT License - See LICENSE file for details.

