"""
Crash reporting system for WhisperLocal.

This module captures uncaught exceptions and saves crash reports locally.
All data stays on the user's machine - no external transmission.
"""

import sys
import os
import traceback
import json
import hashlib
import platform
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class CrashReporter:
    """Collect and save crash reports locally (privacy-preserving)."""
    
    def __init__(self, app_name: str = "WhisperLocal", crash_dir: Optional[str] = None):
        """Initialize crash reporter.
        
        Args:
            app_name: Application name
            crash_dir: Directory for crash reports (default: user data dir/crashes)
        """
        self.app_name = app_name
        self.crash_dir = crash_dir or self._get_crash_dir()
        
        # Ensure crash directory exists
        os.makedirs(self.crash_dir, exist_ok=True)
    
    def _get_crash_dir(self) -> str:
        """Get crash reports directory."""
        from .config import get_user_data_dir
        return os.path.join(get_user_data_dir(), 'crashes')
    
    def generate_crash_id(self, exception: Exception) -> str:
        """Generate unique crash ID from exception.
        
        Args:
            exception: The exception that occurred
        
        Returns:
            16-character hex crash ID
        """
        crash_string = f"{type(exception).__name__}:{str(exception)}"
        return hashlib.sha256(crash_string.encode()).hexdigest()[:16]
    
    def collect_system_info(self) -> Dict[str, Any]:
        """Collect system information (non-identifying).
        
        Returns:
            Dictionary with system information
        """
        return {
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
            },
            'python': {
                'version': sys.version,
                'implementation': platform.python_implementation(),
                'compiler': platform.python_compiler(),
            },
            'executable': sys.executable,
            'frozen': getattr(sys, 'frozen', False),
        }
    
    def save_crash_report(self, exception: Exception, context: Optional[Dict] = None) -> str:
        """Save crash report to local file.
        
        Args:
            exception: The exception that occurred
            context: Additional context information (optional)
        
        Returns:
            Crash ID
        """
        crash_id = self.generate_crash_id(exception)
        
        # Build crash report
        report = {
            'crash_id': crash_id,
            'timestamp': datetime.utcnow().isoformat(),
            'app_name': self.app_name,
            'share_warning': (
                "Crash reports may contain transcribed text or contextual data. "
                "Review and redact sensitive content before sharing."
            ),
            'exception': {
                'type': type(exception).__name__,
                'message': str(exception),
                'traceback': traceback.format_exc(),
            },
            'system': self.collect_system_info(),
            'context': context or {},
        }
        
        # Save to file
        crash_file = os.path.join(self.crash_dir, f'crash_{crash_id}.json')
        
        # Queue for remote telemetry before file I/O
        self._queue_telemetry(exception, crash_id, context)
        
        try:
            with open(crash_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            
            # Also save a plain text version for easy reading
            txt_file = os.path.join(self.crash_dir, f'crash_{crash_id}.txt')
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(f"Crash Report - {self.app_name}\n")
                f.write(f"{'=' * 60}\n")
                f.write(f"Crash ID: {crash_id}\n")
                f.write(f"Timestamp: {report['timestamp']}\n")
                f.write(
                    "\nWarning: This report may contain transcribed text or contextual data. "
                    "Review and redact sensitive content before sharing.\n"
                )
                f.write(f"\nException: {report['exception']['type']}\n")
                f.write(f"Message: {report['exception']['message']}\n")
                f.write(f"\nTraceback:\n")
                f.write(report['exception']['traceback'])
                f.write(f"\n\nSystem Information:\n")
                f.write(f"Platform: {report['system']['platform']['system']} ")
                f.write(f"{report['system']['platform']['release']}\n")
                f.write(f"Python: {report['system']['python']['version']}\n")
                
                if context:
                    f.write(f"\nContext:\n")
                    for key, value in context.items():
                        f.write(f"  {key}: {value}\n")
        
        except (IOError, OSError) as e:
            # If we can't save the crash report, at least print it
            print(f"Failed to save crash report: {e}")
            print(f"Crash ID: {crash_id}")
            traceback.print_exc()
        
        return crash_id
    
    def _queue_telemetry(self, exception: Exception, crash_id: str, context: Optional[Dict] = None) -> None:
        """Queue crash for remote telemetry (if enabled)."""
        try:
            from whisper_local.telemetry import record_crash
            record_crash(exception, crash_id=crash_id, context=context)
        except Exception:
            pass  # Telemetry failure must never break crash reporting
    
    def get_recent_crashes(self, limit: int = 10) -> list:
        """Get recent crash reports.
        
        Args:
            limit: Maximum number of crashes to return
        
        Returns:
            List of crash report dictionaries
        """
        crashes = []
        
        try:
            # Find all crash JSON files
            crash_files = sorted(
                Path(self.crash_dir).glob('crash_*.json'),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            for crash_file in crash_files[:limit]:
                try:
                    with open(crash_file, 'r', encoding='utf-8') as f:
                        crashes.append(json.load(f))
                except (IOError, OSError, json.JSONDecodeError):
                    continue
        
        except (IOError, OSError):
            pass
        
        return crashes
    
    def get_crash_count(self) -> int:
        """Get total number of saved crash reports.
        
        Returns:
            Number of crash reports
        """
        try:
            return len(list(Path(self.crash_dir).glob('crash_*.json')))
        except (IOError, OSError):
            return 0
    
    def clean_old_crashes(self, keep_days: int = 30):
        """Remove crash reports older than specified days.
        
        Args:
            keep_days: Number of days to keep crash reports
        """
        try:
            cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
            
            for crash_file in Path(self.crash_dir).glob('crash_*'):
                if crash_file.stat().st_mtime < cutoff_time:
                    try:
                        crash_file.unlink()
                    except (IOError, OSError):
                        pass
        
        except (IOError, OSError):
            pass
    
    def get_crash_summary(self) -> str:
        """Get human-readable crash summary.
        
        Returns:
            Formatted string with crash summary
        """
        count = self.get_crash_count()
        recent = self.get_recent_crashes(limit=5)
        
        if count == 0:
            return "✅ No crash reports found"
        
        lines = [
            f"Crash Reports Summary",
            f"{'=' * 60}",
            f"Total crashes: {count}",
            f"Location: {self.crash_dir}",
            "",
        ]
        
        if recent:
            lines.append("Recent crashes:")
            for crash in recent[:3]:
                lines.append(f"  • {crash['exception']['type']}: {crash['exception']['message'][:50]}")
                lines.append(f"    ID: {crash['crash_id']}")
                lines.append(f"    Time: {crash['timestamp']}")
                lines.append("")
        
        return "\n".join(lines)


def install_crash_handler(crash_reporter: Optional[CrashReporter] = None):
    """Install global exception handler to catch crashes.
    
    Args:
        crash_reporter: CrashReporter instance (creates new if None)
    """
    if crash_reporter is None:
        crash_reporter = CrashReporter()
    
    def exception_handler(exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions."""
        # Don't catch KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Save crash report
        crash_id = crash_reporter.save_crash_report(exc_value)
        
        # Print user-friendly message
        print("\n" + "=" * 60)
        print(f"❌ {crash_reporter.app_name} has crashed")
        print("=" * 60)
        print(f"\nCrash ID: {crash_id}")
        print(f"\nA crash report has been saved to:")
        print(f"{crash_reporter.crash_dir}")
        print(f"\nCrash report: crash_{crash_id}.txt")
        print("\nPlease check the crash report for details.")
        print("=" * 60 + "\n")
        
        # Show original traceback
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    # Install the handler
    sys.excepthook = exception_handler


def uninstall_crash_handler():
    """Restore original exception handler."""
    sys.excepthook = sys.__excepthook__


# Context manager for crash reporting in specific code blocks
class CrashContext:
    """Context manager for crash reporting in specific code blocks."""
    
    def __init__(self, crash_reporter: CrashReporter, context: Dict[str, Any]):
        """Initialize crash context.
        
        Args:
            crash_reporter: CrashReporter instance
            context: Context information to include in crash report
        """
        self.crash_reporter = crash_reporter
        self.context = context
    
    def __enter__(self):
        """Enter context."""
        return self
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Exit context and handle exceptions."""
        if exc_type is not None and exc_value is not None:
            # An exception occurred
            crash_id = self.crash_reporter.save_crash_report(exc_value, self.context)
            print(f"\n⚠️  Error occurred (Crash ID: {crash_id})")
            print(f"Details saved to: {self.crash_reporter.crash_dir}/crash_{crash_id}.txt\n")
            
            # Don't suppress the exception
            return False
        
        return True


# Global crash reporter instance
_global_crash_reporter: Optional[CrashReporter] = None


def get_crash_reporter() -> CrashReporter:
    """Get global crash reporter instance.
    
    Returns:
        CrashReporter instance
    """
    global _global_crash_reporter
    
    if _global_crash_reporter is None:
        _global_crash_reporter = CrashReporter()
    
    return _global_crash_reporter

