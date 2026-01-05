import os, subprocess, time, threading, queue, datetime, shlex
import sys, shutil, tempfile, uuid
import logging
import traceback
import logging.handlers

# Import GPU monitoring module
try:
    from whisper_local.gpu_monitor import gpu_monitor
except ImportError:
    # Fallback if running as script
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from whisper_local.gpu_monitor import gpu_monitor
    except ImportError:
        # Create a dummy GPU monitor if import fails
        class DummyGPUMonitor:
            def is_nvidia_gpu(self): return False
            def is_gpu_busy(self): return False
            def is_gpu_critical_load(self): return False
            def get_recommended_model_tier(self): return "medium"
            def get_load_status_text(self): return "GPU: Unavailable"
            def should_use_light_model(self, word_count=0): return False
            def start_monitoring(self): pass
            def stop_monitoring(self): pass
            def get_gpu_vendor(self): return "unknown"
        gpu_monitor = DummyGPUMonitor()

# Windows subprocess flag to hide console windows (prevents command prompt popup)
if sys.platform == 'win32':
    CREATE_NO_WINDOW = 0x08000000
else:
    CREATE_NO_WINDOW = 0
import sounddevice as sd
import soundfile as sf
import keyboard
import pyperclip
import pyautogui
import tkinter as tk
from tkinter import Canvas, font as tkfont
import ctypes
from ctypes import wintypes
import numpy as np
from PIL import Image, ImageDraw
import pystray
import re
import json
import math

# ============================================================================
# APPLICATION METADATA
# ============================================================================
APP_NAME = "WhisperLocal"
APP_VERSION = "1.0.0"
APP_AUTHOR = "WhisperLocal"

# ============================================================================
# DPI SCALING DETECTION
# ============================================================================
def get_dpi_scale_factor():
    """
    Detect Windows DPI scaling factor.
    Returns a scale factor (1.0 = 100%, 1.5 = 150%, 2.0 = 200%, 2.5 = 250%, etc.)
    """
    try:
        # Windows 10/11: Set process DPI awareness before getting DPI
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            # Fallback for older Windows versions
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except (AttributeError, OSError):
                pass
        
        # Get the DPI for the system (primary monitor)
        # 96 DPI = 100% scaling (Windows baseline)
        dpi = ctypes.windll.user32.GetDpiForSystem()
        scale = dpi / 96.0
        
        # Clamp scale factor to reasonable range (100% to 350%)
        scale = max(1.0, min(3.5, scale))
        
        return scale
    except Exception:
        # Fallback to 1.0 if anything fails
        return 1.0

# Initialize DPI scale factor globally (called once at startup)
DPI_SCALE = get_dpi_scale_factor()

def scaled(value):
    """Scale a dimension value by the DPI factor."""
    return int(value * DPI_SCALE)

def scaled_font(size):
    """Scale a font size by the DPI factor."""
    return int(size * DPI_SCALE)

# ============================================================================
# AUDIO RECORDING CONSTANTS
# ============================================================================
# Audio input format (matches Whisper's expected format)
SAMPLE_RATE_HZ = 16000  # 16kHz sample rate for Whisper compatibility
AUDIO_CHANNELS = 1  # Mono recording for speech

# Voice Activity Detection (VAD) thresholds
# RMS_THRESH: Root Mean Square threshold for detecting voice activity
# Lower values = more sensitive, higher values = less background noise pickup
# Typical speaking voice is 0.01-0.05 RMS, whispers are 0.002-0.01
RMS_THRESHOLD_VOICED = 0.002  # Minimum RMS to consider audio as "voiced"
SILENCE_RMS_THRESHOLD_CONFIG = 0.008  # Threshold for silence detection (higher = stricter)

# Timing constants for recording
MIN_SPEECH_DURATION_SEC = 0.2  # Minimum duration of speech to process (filters clicks/pops)
AUDIO_BLOCK_DURATION_SEC = 0.05  # Audio block size for RMS calculation (50ms)
PREROLL_DURATION_SEC = 2.0  # Audio buffer before speech detection (not currently used)
POSTROLL_DURATION_SEC = 0.15  # Continue recording after key release (captures final words)

# ============================================================================
# TRANSCRIPTION CONSTANTS
# ============================================================================
# Subprocess timeout - maximum time for whisper-cli to complete
# Longer recordings and larger models need more time
WHISPER_PROCESS_TIMEOUT_SEC = 120  # 2 minutes max per transcription

# Word count thresholds for dynamic model selection
# Shorter utterances use faster models, longer use more accurate ones
WORD_THRESHOLD_FAST = 25  # <25 words: use base.en (fastest, ~100ms)
WORD_THRESHOLD_BALANCED = 75  # 25-75 words: use medium.en (balanced, ~500ms)
# 75+ words: use large-v3 (best quality, ~2-5s)

# ============================================================================
# UI INTERACTION CONSTANTS
# ============================================================================
# Debouncing for hotkey detection to prevent accidental double-triggers
HOTKEY_DEBOUNCE_MS = 150  # Minimum ms between hotkey state changes

# Animation timing
UI_ANIMATION_FPS = 15  # Frame rate for pulse animations (reduced for CPU efficiency)
UI_QUEUE_POLL_MS = 50  # How often to check UI update queue
HOTKEY_POLL_MS = 10  # How often to check hotkey state

# Status message display duration
STATUS_SUCCESS_DISPLAY_SEC = 1.5  # How long to show success messages

# Clipboard operation delay
CLIPBOARD_SETTLE_DELAY_SEC = 0.05  # Delay after clipboard copy before paste

# ============================================================================
# INPUT VALIDATION CONSTANTS
# ============================================================================
# Limits to prevent DoS from malformed subprocess output
MAX_TRANSCRIPT_SIZE_BYTES = 1024 * 1024  # 1 MB max transcript size
MAX_TRANSCRIPT_LINE_COUNT = 10000  # Maximum lines to process
MAX_LINE_LENGTH_CHARS = 10000  # Maximum characters per line

# ============================================================================
# PYINSTALLER PATH RESOLUTION
# ============================================================================
def is_frozen():
    """Check if running as a PyInstaller bundle."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def get_bundle_dir():
    """Get the directory where bundled resources are located."""
    if is_frozen():
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_app_dir():
    """Get the application directory (where the exe is located, or script dir in dev)."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_user_data_dir():
    """Get the user data directory for config, logs, and temp files."""
    if is_frozen():
        # Use AppData/Local for user-specific data
        appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        data_dir = os.path.join(appdata, APP_NAME)
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
    return os.path.dirname(os.path.abspath(__file__))

def get_config_file():
    """Get the path to the config file."""
    return os.path.join(get_user_data_dir(), "config.json")

def is_first_run():
    """Check if this is the first run of the application."""
    return not os.path.exists(get_config_file())

def mark_first_run_complete():
    """Mark that the first run setup has been completed."""
    config_file = get_config_file()
    config = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Warning: Config file corrupted, using defaults: {e}")
        except (IOError, OSError) as e:
            print(f"Warning: Could not read config file: {e}")
    config['first_run_complete'] = True
    config['version'] = APP_VERSION
    config['install_date'] = datetime.datetime.now().isoformat()
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    except (IOError, OSError) as e:
        print(f"Warning: Could not save config: {e}")

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
def _setup_logging():
    """Configure application-wide logging.
    
    Creates a logger with:
    - File handler: Writes to flow.log in user data directory
    - Console handler: Prints INFO+ to stdout
    
    Log format includes timestamp, level, and message.
    """
    log_file = os.path.join(get_user_data_dir(), "flow.log")
    
    # Create logger
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.DEBUG)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # File handler - DEBUG level, rotating
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB max
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except (IOError, OSError) as e:
        print(f"Warning: Could not create log file: {e}")
    
    # Console handler - INFO level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logger
logger = _setup_logging()

# ============================================================================
# FAST WIN32 CLIPBOARD & INPUT - Zero-latency paste
# ============================================================================
# Win32 constants
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_V = 0x56

# Win32 structures for SendInput
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    _anonymous_ = ("_input",)
    _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT)]

def fast_clipboard_copy(text: str) -> bool:
    """Direct Win32 clipboard copy - faster than pyperclip.
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        
        if not user32.OpenClipboard(None):
            return False
        try:
            user32.EmptyClipboard()
            # Encode as UTF-16LE (Windows native)
            data = text.encode('utf-16-le') + b'\x00\x00'
            h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not h_mem:
                return False
            p_mem = kernel32.GlobalLock(h_mem)
            if not p_mem:
                kernel32.GlobalFree(h_mem)
                return False
            ctypes.memmove(p_mem, data, len(data))
            kernel32.GlobalUnlock(h_mem)
            user32.SetClipboardData(CF_UNICODETEXT, h_mem)
            return True
        finally:
            user32.CloseClipboard()
    except (OSError, ctypes.ArgumentError, UnicodeEncodeError) as e:
        # OSError: Win32 API failures
        # ArgumentError: Invalid ctypes arguments
        # UnicodeEncodeError: Text encoding issues
        log_line(f"Clipboard copy failed: {type(e).__name__}: {e}")
        return False

def fast_send_paste() -> bool:
    """Direct SendInput for Ctrl+V - faster than pyautogui.
    
    Note: May be blocked by Windows UIPI (User Interface Privilege Isolation)
    when pasting to elevated windows.
    
    Returns:
        True if successful, False otherwise.
    """
    try:
        user32 = ctypes.windll.user32
        
        # Create input events: Ctrl down, V down, V up, Ctrl up
        inputs = (INPUT * 4)()
        
        # Ctrl down
        inputs[0].type = INPUT_KEYBOARD
        inputs[0].ki.wVk = VK_CONTROL
        
        # V down
        inputs[1].type = INPUT_KEYBOARD
        inputs[1].ki.wVk = VK_V
        
        # V up
        inputs[2].type = INPUT_KEYBOARD
        inputs[2].ki.wVk = VK_V
        inputs[2].ki.dwFlags = KEYEVENTF_KEYUP
        
        # Ctrl up
        inputs[3].type = INPUT_KEYBOARD
        inputs[3].ki.wVk = VK_CONTROL
        inputs[3].ki.dwFlags = KEYEVENTF_KEYUP
        
        user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))
        return True
    except (OSError, ctypes.ArgumentError) as e:
        # OSError: Win32 API failures  
        # ArgumentError: Invalid ctypes arguments
        log_line(f"SendInput paste failed: {type(e).__name__}: {e}")
        return False

def instant_paste(text: str) -> bool:
    """Reliable paste using pyperclip + pyautogui.
    
    Note: Win32 SendInput gets blocked by Windows UIPI after first use,
    so this uses pyautogui which works more reliably.
    
    Args:
        text: The text to paste.
        
    Returns:
        True if successful, False otherwise.
    """
    try:
        pyperclip.copy(text)
        time.sleep(0.05)  # Small delay to ensure clipboard is ready
        pyautogui.hotkey("ctrl", "v")
        return True
    except pyperclip.PyperclipException as e:
        log_line(f"Clipboard error: {e}")
        return False
    except (OSError, RuntimeError) as e:
        # OSError: System clipboard access issues
        # RuntimeError: pyautogui failures
        log_line(f"Paste failed: {type(e).__name__}: {e}")
        return False

# ============================================================================
# THEME CONSTANTS - Pink/Black Dark Mode (DPI-Aware)
# ============================================================================
class Theme:
    # Background colors (no scaling needed for colors)
    BG_DARKEST = "#0A0A0A"      # Deepest black
    BG_DARK = "#0D0D0D"         # Main background
    BG_CARD = "#141414"         # Card backgrounds
    BG_ELEVATED = "#1A1A1A"     # Elevated surfaces
    BG_HOVER = "#222222"        # Hover states
    
    # Pink accent colors
    PINK_PRIMARY = "#FF1493"    # Hot pink (main accent)
    PINK_LIGHT = "#FF69B4"      # Lighter pink
    PINK_GLOW = "#FF149355"     # Pink with transparency for glow
    PINK_SOFT = "#FF85C8"       # Soft pink for highlights
    PINK_DARK = "#CC1177"       # Darker pink for pressed states
    
    # Text colors
    TEXT_PRIMARY = "#FFFFFF"    # Primary text
    TEXT_SECONDARY = "#B0B0B0"  # Secondary text
    TEXT_MUTED = "#666666"      # Muted text
    TEXT_PINK = "#FF69B4"       # Pink text for emphasis
    
    # Status colors
    SUCCESS = "#00E676"         # Green for success
    WARNING = "#FFB300"         # Amber for warnings
    ERROR = "#FF5252"           # Red for errors
    INFO = "#40C4FF"            # Blue for info
    
    # Borders
    BORDER_SUBTLE = "#2A2A2A"   # Subtle borders
    BORDER_PINK = "#FF149933"   # Pink border with transparency
    
    # Fonts
    FONT_FAMILY = "Segoe UI"
    FONT_FAMILY_MONO = "Consolas"
    
    # DPI-scaled sizes (computed at class load time)
    # Base sizes at 100% DPI, scaled by DPI_SCALE
    PILL_WIDTH = scaled(180)
    PILL_HEIGHT = scaled(36)
    PILL_RADIUS = scaled(18)
    
    DASHBOARD_WIDTH = scaled(420)
    DASHBOARD_HEIGHT = scaled(580)
    
    SETTINGS_WIDTH = scaled(480)
    SETTINGS_HEIGHT = scaled(460)
    
    WIZARD_WIDTH = scaled(600)
    WIZARD_HEIGHT = scaled(500)
    
    TITLE_BAR_HEIGHT = scaled(40)
    
    # Scaled font sizes
    FONT_SIZE_XS = scaled_font(9)
    FONT_SIZE_SM = scaled_font(10)
    FONT_SIZE_MD = scaled_font(11)
    FONT_SIZE_LG = scaled_font(12)
    FONT_SIZE_XL = scaled_font(14)
    FONT_SIZE_XXL = scaled_font(16)
    FONT_SIZE_STAT = scaled_font(22)
    
    # Scaled padding/spacing
    PAD_XS = scaled(4)
    PAD_SM = scaled(8)
    PAD_MD = scaled(12)
    PAD_LG = scaled(16)
    PAD_XL = scaled(20)
    PAD_XXL = scaled(30)

# ============================================================================
# STATS TRACKING SYSTEM
# ============================================================================
STATS_FILE = os.path.join(get_user_data_dir(), "whisper_stats.json")

class StatsTracker:
    def __init__(self):
        self.data = self._load()
    
    def _load(self):
        """Load stats from JSON file."""
        default = {
            "total_words": 0,
            "total_sessions": 0,
            "first_use": None,
            "daily_words": {},  # {"2024-01-15": 123, ...}
            "streak": 0,
            "last_use_date": None,
            "milestones": [],   # ["1K", "10K", ...]
            "recent_transcripts": [],  # Last 5 transcripts
            "model_usage": {    # Track which models are used
                "base.en": 0,
                "medium.en": 0,
                "large-v3": 0,
            },
        }
        try:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle new fields
                    for key in default:
                        if key not in loaded:
                            loaded[key] = default[key]
                    return loaded
        except json.JSONDecodeError as e:
            print(f"Stats file corrupted, using defaults: {e}")
        except (IOError, OSError) as e:
            print(f"Could not read stats file: {e}")
        return default
    
    def _save(self):
        """Save stats to JSON file."""
        try:
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except (IOError, OSError) as e:
            print(f"Stats save error: {e}")
        except (TypeError, ValueError) as e:
            print(f"Stats serialization error: {e}")
    
    def record_transcription(self, text: str, model_used: str = None):
        """Record a successful transcription.
        
        Args:
            text: The transcribed text
            model_used: Which model was used (e.g., "base.en", "medium.en", "large-v3")
        """
        if not text:
            return
        
        word_count = len(text.split())
        
        # Track model usage
        if model_used:
            # Normalize model name to key format
            model_key = model_used.split(" ")[0]  # Handle "base.en (fallback)" -> "base.en"
            if "model_usage" not in self.data:
                self.data["model_usage"] = {"base.en": 0, "medium.en": 0, "large-v3": 0}
            if model_key in self.data["model_usage"]:
                self.data["model_usage"][model_key] += 1
        today = datetime.date.today().isoformat()
        
        # Update totals
        self.data["total_words"] += word_count
        self.data["total_sessions"] += 1
        
        # First use
        if not self.data["first_use"]:
            self.data["first_use"] = today
        
        # Daily words
        if today not in self.data["daily_words"]:
            self.data["daily_words"][today] = 0
        self.data["daily_words"][today] += word_count
        
        # Streak calculation
        last_date = self.data["last_use_date"]
        if last_date:
            last = datetime.date.fromisoformat(last_date)
            today_date = datetime.date.today()
            diff = (today_date - last).days
            if diff == 1:
                self.data["streak"] += 1
            elif diff > 1:
                self.data["streak"] = 1
            # Same day: streak unchanged
        else:
            self.data["streak"] = 1
        
        self.data["last_use_date"] = today
        
        # Check milestones
        total = self.data["total_words"]
        milestones_map = [
            (1000, "1K"), (5000, "5K"), (10000, "10K"),
            (25000, "25K"), (50000, "50K"), (100000, "100K"),
            (250000, "250K"), (500000, "500K"), (1000000, "1M")
        ]
        for threshold, label in milestones_map:
            if total >= threshold and label not in self.data["milestones"]:
                self.data["milestones"].append(label)
        
        # Recent transcripts (keep last 5)
        preview = text[:100] + "..." if len(text) > 100 else text
        self.data["recent_transcripts"].insert(0, {
            "text": preview,
            "full_text": text,  # Store complete text for copying
            "words": word_count,
            "time": datetime.datetime.now().strftime("%H:%M")
        })
        self.data["recent_transcripts"] = self.data["recent_transcripts"][:5]
        
        self._save()
    
    def get_today_words(self):
        today = datetime.date.today().isoformat()
        return self.data["daily_words"].get(today, 0)
    
    def get_week_words(self):
        total = 0
        today = datetime.date.today()
        for i in range(7):
            day = (today - datetime.timedelta(days=i)).isoformat()
            total += self.data["daily_words"].get(day, 0)
        return total
    
    def get_week_data(self):
        """Get last 7 days of word counts for graph."""
        data = []
        today = datetime.date.today()
        for i in range(6, -1, -1):
            day = today - datetime.timedelta(days=i)
            day_name = day.strftime("%a")
            words = self.data["daily_words"].get(day.isoformat(), 0)
            data.append((day_name, words))
        return data
    
    def get_week_comparison(self):
        """Get percentage change vs last week."""
        this_week = self.get_week_words()
        today = datetime.date.today()
        last_week_total = 0
        for i in range(7, 14):
            day = (today - datetime.timedelta(days=i)).isoformat()
            last_week_total += self.data["daily_words"].get(day, 0)
        
        if last_week_total == 0:
            return None  # No comparison possible
        
        change = ((this_week - last_week_total) / last_week_total) * 100
        return change

# Global stats tracker instance
stats_tracker = StatsTracker()

# Enable CUDA by default unless explicitly disabled via environment
os.environ.setdefault("GGML_CUDA_ENABLE", "1")

# ============================================================================
# PATH RESOLUTION FOR BUNDLED AND DEV ENVIRONMENTS
# ============================================================================
# Get directories based on whether we're running bundled or in dev
_bundle_dir = get_bundle_dir()  # Where bundled resources are (models, DLLs)
_app_dir = get_app_dir()        # Where the exe/script is located
_user_dir = get_user_data_dir() # User-writable directory for logs, temp files

# Auto-detect whisper binary - check bundle dir first, then app dir
_default_bin = os.path.join(_bundle_dir, "whisper-cli.exe")
if not os.path.isfile(_default_bin):
    _default_bin = os.path.join(_bundle_dir, "main.exe")
if not os.path.isfile(_default_bin):
    _default_bin = os.path.join(_app_dir, "whisper-cli.exe")
if not os.path.isfile(_default_bin):
    _default_bin = os.path.join(_app_dir, "main.exe")

os.environ.setdefault("FLOW_WHISPER_BIN", _default_bin)
os.environ.setdefault("WHISPER_BIN", os.environ["FLOW_WHISPER_BIN"])
os.environ.setdefault("FLOW_WHISPER_ARGS", "-ngl 99")

_bin = os.environ.get("FLOW_WHISPER_BIN")
if _bin and not os.path.isfile(_bin):
    print(f"Warning: FLOW_WHISPER_BIN not found: {_bin}, will try to auto-detect...")

# ============================================================================
# GPU DETECTION FOR PERFORMANCE OPTIMIZATION
# ============================================================================
def detect_gpu_available() -> bool:
    """Detect if NVIDIA GPU with CUDA is available.
    
    Checks for CUDA DLL and validates GPU with nvidia-smi.
    Used to optimize model selection for CPU vs GPU systems.
    
    Returns:
        True if GPU acceleration is available, False for CPU-only
    """
    try:
        # Check if CUDA DLL exists in bundle or app directory
        cuda_dll_paths = [
            os.path.join(_bundle_dir, "ggml-cuda.dll"),
            os.path.join(_app_dir, "ggml-cuda.dll"),
            "ggml-cuda.dll",
        ]
        cuda_dll_found = any(os.path.exists(p) for p in cuda_dll_paths)
        if not cuda_dll_found:
            return False
        
        # Try to run nvidia-smi to verify GPU is functional
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            timeout=3,
            creationflags=CREATE_NO_WINDOW,
        )
        return result.returncode == 0
    except Exception:
        return False

# Detect GPU at startup - determines model selection strategy
GPU_AVAILABLE = detect_gpu_available()

# Prefer winotify for reliable Windows 10/11 notifications; fall back gracefully if unavailable
try:
    from winotify import Notification, audio
except Exception:
    Notification = None
    audio = None

# --- Single-instance guard (Windows) ---
import tempfile, uuid, msvcrt
import atexit

_SINGLETON_LOCK = None
_SINGLETON_LOCK_PATH = None

def _release_single_instance():
    """Release the singleton lock file on exit."""
    global _SINGLETON_LOCK
    if _SINGLETON_LOCK is not None:
        try:
            msvcrt.locking(_SINGLETON_LOCK.fileno(), msvcrt.LK_UNLCK, 1)
        except (OSError, ValueError):
            pass  # Lock may already be released or file closed
        try:
            _SINGLETON_LOCK.close()
        except (OSError, ValueError):
            pass
        _SINGLETON_LOCK = None

def _acquire_single_instance():
    """Acquire singleton lock to prevent multiple instances."""
    global _SINGLETON_LOCK, _SINGLETON_LOCK_PATH
    _SINGLETON_LOCK_PATH = os.path.join(tempfile.gettempdir(), f"{APP_NAME.lower()}_dictation.lock")
    _SINGLETON_LOCK = open(_SINGLETON_LOCK_PATH, "w")
    try:
        msvcrt.locking(_SINGLETON_LOCK.fileno(), msvcrt.LK_NBLCK, 1)
        # Register cleanup handler to release lock on exit
        atexit.register(_release_single_instance)
    except OSError:
        _SINGLETON_LOCK.close()
        _SINGLETON_LOCK = None
        print("Already running. Exiting.")
        sys.exit(0)

# Singleton lock is now acquired in __main__ block instead of at module level
# to prevent conflicts when this module is imported by first_run_wizard

# --- Config ---
# Model paths for dynamic selection based on word count (relative paths)
MODEL_BASE = os.path.join("models", "ggml-base.en.bin")
MODEL_MEDIUM = os.path.join("models", "ggml-medium.en.bin")
MODEL_LARGE = os.path.join("models", "ggml-large-v3.bin")

# Word count thresholds - using centralized constants
WORD_THRESHOLD_BASE = WORD_THRESHOLD_FAST
WORD_THRESHOLD_MEDIUM = WORD_THRESHOLD_BALANCED

# Legacy default (will be dynamically selected)
MODEL_PATH_REL = MODEL_LARGE  # fallback if dynamic selection fails
WHISPER_BIN = os.environ.get("WHISPER_BIN") or os.path.join(".", "main.exe")

# Audio settings - using centralized constants
SAMPLE_RATE = SAMPLE_RATE_HZ
CHANNELS = AUDIO_CHANNELS

# Use user data directory for temp files (writable location)
WAV_TMP = os.path.join(_user_dir, "flow_input.wav")
TEXT_TMP_BASE = os.path.join(_user_dir, "flow_out")  # base name for whisper-cli text output

HOTKEY_HOLD = "ctrl+shift"    # hold to talk; release to transcribe (changed from windows+ctrl to avoid Windows menu conflict)
NOTIFY = True

# --- Text Post-Processing Modes ---
# Smart, offline-only post-processing toggles
MODE_FILLER = True
MODE_PUNCT = True
MODE_BULLET_NEXT = False  # one-shot list maker (also triggered by keywords)

# --- Advanced Config ---
# Optional input device override: integer index or substring of device name.
# Can also be set via env var FLOW_INPUT_DEVICE (e.g., "2" or "USB").
INPUT_DEVICE = os.environ.get("FLOW_INPUT_DEVICE", None)

# Use centralized timeout constant
WHISPER_TIMEOUT_SEC = WHISPER_PROCESS_TIMEOUT_SEC

# Silence detection - using centralized constants
SILENCE_RMS_THRESHOLD = SILENCE_RMS_THRESHOLD_CONFIG
MIN_SPOKEN_BLOCKS = 3

# Log file for diagnostics (user-writable location)
LOG_FILE = os.path.join(_user_dir, "flow.log")

# Whisper binary detection candidates (check bundle dir, app dir, and current directory)
WHISPER_CANDIDATES = [
    os.path.join(_bundle_dir, "whisper-cli.exe"),
    os.path.join(_bundle_dir, "main.exe"),
    os.path.join(_app_dir, "whisper-cli.exe"),
    os.path.join(_app_dir, "main.exe"),
    os.path.join(".", "whisper-cli.exe"),
    os.path.join(".", "main.exe"),
    # Legacy dev environment paths (optional)
    os.path.join("whisper.cpp", "build", "bin", "Release", "whisper-cli.exe") if os.path.exists("whisper.cpp") else None,
    os.path.join("whisper.cpp", "build", "bin", "Debug", "whisper-cli.exe") if os.path.exists("whisper.cpp") else None,
]
# Filter out None values from conditional paths
WHISPER_CANDIDATES = [c for c in WHISPER_CANDIDATES if c is not None]

# Resolved at startup
resolved_whisper_bin = None

# Concurrency & debounce
STATE_LOCK = threading.Lock()
transcribing_flag = threading.Event()
last_edge_ts = 0.0
EDGE_COOLDOWN_MS = HOTKEY_DEBOUNCE_MS  # Using centralized constant

recording_flag = threading.Event()
rec_thread = None
ui_queue = queue.Queue()

# Resolved device (set at startup diagnostics)
selected_input_device_idx = None
selected_input_device_name = None

# Dashboard window reference
dashboard_window = None

# Last transcription for easy copy access
last_transcription = None

# Focus state captured at recording start (for reliable paste targeting)
target_window_on_record_start = None

# Timer reference for canceling pending status resets
pending_status_timer = None

# ============================================================================
# FLOATING PILL STATUS BAR
# ============================================================================
class FloatingPill:
    """Minimal, pill-shaped floating status indicator with animations."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", Theme.BG_DARKEST)
        try:
            self.root.wm_attributes("-toolwindow", True)
        except Exception:
            pass
        
        self.width = Theme.PILL_WIDTH
        self.height = Theme.PILL_HEIGHT
        self.root.configure(bg=Theme.BG_DARKEST)
        
        # Canvas for custom drawing
        self.canvas = Canvas(
            self.root, 
            width=self.width, 
            height=self.height, 
            highlightthickness=0, 
            bg=Theme.BG_DARKEST
        )
        self.canvas.pack()
        
        # State
        self.current_state = "ready"
        self.animation_id = None
        self.pulse_phase = 0
        self.glow_intensity = 0
        
        # Draw initial state
        self._draw_pill("ready")
        self._position_near_taskbar()
        
        # Bind click to open dashboard
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Button-3>", self._on_right_click)
        
        # Context menu
        self.context_menu = tk.Menu(self.root, tearoff=0, bg=Theme.BG_ELEVATED, fg=Theme.TEXT_PRIMARY)
        self.context_menu.add_command(label="Open Dashboard", command=self._open_dashboard)
        self.context_menu.add_command(label="Settings", command=lambda: open_settings_window(self.root))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Exit", command=self._quit)
    
    def _draw_pill(self, state, pulse=0):
        """Draw the pill shape with current state."""
        self.canvas.delete("all")
        
        w, h = self.width, self.height
        r = Theme.PILL_RADIUS
        
        # Colors based on state
        colors = {
            "ready": (Theme.BG_ELEVATED, Theme.PINK_PRIMARY, "●  Ready"),
            "listening": (Theme.PINK_DARK, Theme.PINK_LIGHT, "●  Listening..."),
            "transcribing": (Theme.BG_ELEVATED, Theme.INFO, "◐  Processing..."),
            "success": (Theme.BG_ELEVATED, Theme.SUCCESS, "✓  Done!"),
            "error": (Theme.BG_ELEVATED, Theme.ERROR, "✕  Error"),
            "warning": (Theme.BG_ELEVATED, Theme.WARNING, "⚠  No speech"),
        }
        
        bg_color, accent_color, text = colors.get(state, colors["ready"])
        
        # Scaled dimensions for drawing
        border_offset = scaled(2)
        glow_base = scaled(3)
        dot_base_radius = scaled(4)
        
        # Glow effect for listening state
        if state == "listening":
            glow_size = glow_base + int(pulse * scaled(2))
            glow_alpha = 0.3 + pulse * 0.2
            # Draw glow layers
            for i in range(glow_size, 0, -1):
                alpha = int((glow_alpha / glow_size) * i * 255)
                glow_color = self._blend_color(Theme.PINK_PRIMARY, Theme.BG_DARKEST, i / glow_size)
                self._draw_rounded_rect(
                    border_offset - i, border_offset - i, w - border_offset + i, h - border_offset + i, r + i,
                    fill=glow_color, outline=""
                )
        
        # Main pill background
        self._draw_rounded_rect(border_offset, border_offset, w - border_offset, h - border_offset, r, fill=bg_color, outline=accent_color)
        
        # Accent dot/icon
        dot_x = scaled(18)
        dot_y = h // 2
        if state == "listening":
            # Pulsing dot
            dot_r = dot_base_radius + int(pulse * scaled(2))
            self.canvas.create_oval(
                dot_x - dot_r, dot_y - dot_r,
                dot_x + dot_r, dot_y + dot_r,
                fill=accent_color, outline=""
            )
        else:
            # Static indicator
            self.canvas.create_oval(
                dot_x - dot_base_radius, dot_y - dot_base_radius,
                dot_x + dot_base_radius, dot_y + dot_base_radius,
                fill=accent_color, outline=""
            )
        
        # Status text
        self.canvas.create_text(
            w // 2 + scaled(8), h // 2,
            text=text.split("  ")[1] if "  " in text else text,
            fill=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM, "bold"),
            anchor="center"
        )
    
    def _draw_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Draw a rounded rectangle on the canvas."""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
            x1 + radius, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)
    
    def _blend_color(self, color1, color2, ratio):
        """Blend two hex colors."""
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        def rgb_to_hex(rgb):
            return '#{:02x}{:02x}{:02x}'.format(*rgb)
        
        rgb1 = hex_to_rgb(color1)
        rgb2 = hex_to_rgb(color2)
        blended = tuple(int(c1 * ratio + c2 * (1 - ratio)) for c1, c2 in zip(rgb1, rgb2))
        return rgb_to_hex(blended)
    
    def _position_near_taskbar(self):
        """Position the pill near the taskbar."""
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32

        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_int), ("top", ctypes.c_int), ("right", ctypes.c_int), ("bottom", ctypes.c_int)]
        class APPBARDATA(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("hWnd", ctypes.c_void_p), ("uCallbackMessage", ctypes.c_uint), ("uEdge", ctypes.c_uint), ("rc", RECT), ("lParam", ctypes.c_int)]

        ABM_GETTASKBARPOS = 0x00000005
        ABE_LEFT, ABE_TOP, ABE_RIGHT, ABE_BOTTOM = 0, 1, 2, 3
        abd = APPBARDATA()
        abd.cbSize = ctypes.sizeof(APPBARDATA)
        res = shell32.SHAppBarMessage(ABM_GETTASKBARPOS, ctypes.byref(abd))
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)

        # Scaled offset from taskbar edge
        taskbar_offset = scaled(12)
        
        x = (sw - self.width) // 2
        y = sh - self.height - taskbar_offset
        if res:
            edge = abd.uEdge
            rc = abd.rc
            if edge == ABE_BOTTOM:
                y = rc.top - self.height - taskbar_offset
                x = (sw - self.width) // 2
            elif edge == ABE_TOP:
                y = rc.bottom + taskbar_offset
                x = (sw - self.width) // 2
            elif edge == ABE_LEFT:
                x = rc.right + taskbar_offset
                y = sh - self.height - taskbar_offset
            elif edge == ABE_RIGHT:
                x = rc.left - self.width - taskbar_offset
                y = sh - self.height - taskbar_offset

        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
    
    def set_status(self, state, text=None, bg=None, fg=None, border=None):
        """Update the pill status with animation."""
        # Map old-style calls to new states
        state_map = {
            "🎤 Ready": "ready",
            "🎤 Initializing...": "ready",
            "🎙️ Listening...": "listening",
            "⚙️ Transcribing...": "transcribing",
            "✅ Pasted!": "success",
            "❌ Failed": "error",
            "❌ Mic not ready": "error",
            "❌ Paste error": "error",
            "🔇 No speech detected": "warning",
            "🔇 Empty transcript": "warning",
            "⚠️ Issues detected": "warning",
        }
        
        # Check if state is actually a text string (old API)
        if state in state_map:
            new_state = state_map[state]
        elif state in ["ready", "listening", "transcribing", "success", "error", "warning"]:
            new_state = state
        else:
            new_state = "ready"
        
        self.current_state = new_state
        
        # Stop existing animation
        if self.animation_id:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None
        
        # Start pulsing animation for listening state
        if new_state == "listening":
            self._animate_pulse()
        else:
            self._draw_pill(new_state)
    
    def _animate_pulse(self):
        """Animate the pulsing effect for listening state."""
        self.pulse_phase += 0.2  # Slightly faster phase for smoother visual at lower FPS
        pulse = (math.sin(self.pulse_phase) + 1) / 2  # 0 to 1
        self._draw_pill("listening", pulse)
        
        if self.current_state == "listening":
            self.animation_id = self.root.after(67, self._animate_pulse)  # 15fps (reduced from 20fps)
    
    def _on_click(self, event):
        """Handle left click - open dashboard."""
        self._open_dashboard()
    
    def _on_right_click(self, event):
        """Handle right click - show context menu."""
        self.context_menu.tk_popup(event.x_root, event.y_root)
    
    def _open_dashboard(self):
        """Open the main dashboard window."""
        global dashboard_window
        if dashboard_window is None or not dashboard_window.winfo_exists():
            dashboard_window = DashboardWindow(self.root)
        else:
            dashboard_window.lift()
            dashboard_window.focus_force()
    
    def _quit(self):
        """Quit the application."""
        self.root.destroy()
    
    def pump_queue(self):
        """Process UI queue updates."""
        try:
            while True:
                fn, args = ui_queue.get_nowait()
                try:
                    fn(*args)
                except Exception:
                    pass
        except queue.Empty:
            pass
        self.root.after(50, self.pump_queue)  # Reduced from 30ms - less CPU overhead
    
    def bind_context_menu(self, on_settings):
        """Compatibility method - already handled internally."""
        pass


# ============================================================================
# DASHBOARD WINDOW
# ============================================================================
class DashboardWindow(tk.Toplevel):
    """Main dashboard window with stats and gamification."""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("Whisper Local")
        self.geometry(f"{Theme.DASHBOARD_WIDTH}x{Theme.DASHBOARD_HEIGHT}")
        self.configure(bg=Theme.BG_DARK)
        self.resizable(False, False)
        
        # Remove window decorations for custom title bar
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        # Position in center of screen
        self._center_window()
        
        # Custom title bar
        self._create_title_bar()
        
        # Main content
        self._create_content()
        
        # Allow dragging
        self._drag_data = {"x": 0, "y": 0}
        self.title_bar.bind("<Button-1>", self._start_drag)
        self.title_bar.bind("<B1-Motion>", self._on_drag)
        
        # Refresh stats periodically
        self._refresh_stats()
    
    def _center_window(self):
        """Center the window on screen."""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - Theme.DASHBOARD_WIDTH) // 2
        y = (sh - Theme.DASHBOARD_HEIGHT) // 2
        self.geometry(f"{Theme.DASHBOARD_WIDTH}x{Theme.DASHBOARD_HEIGHT}+{x}+{y}")
    
    def _create_title_bar(self):
        """Create custom title bar."""
        self.title_bar = tk.Frame(self, bg=Theme.BG_ELEVATED, height=Theme.TITLE_BAR_HEIGHT)
        self.title_bar.pack(fill="x")
        self.title_bar.pack_propagate(False)
        
        # App icon/logo
        logo_label = tk.Label(
            self.title_bar, 
            text="◉", 
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XXL),
            fg=Theme.PINK_PRIMARY,
            bg=Theme.BG_ELEVATED
        )
        logo_label.pack(side="left", padx=(Theme.PAD_MD, Theme.PAD_XS + 2))
        
        # Title
        title_label = tk.Label(
            self.title_bar,
            text="Whisper Local",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_MD, "bold"),
            fg=Theme.TEXT_PRIMARY,
            bg=Theme.BG_ELEVATED
        )
        title_label.pack(side="left")
        
        # Close button
        close_btn = tk.Label(
            self.title_bar,
            text="✕",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_LG),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_ELEVATED,
            cursor="hand2"
        )
        close_btn.pack(side="right", padx=Theme.PAD_MD)
        close_btn.bind("<Button-1>", lambda e: self.destroy())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg=Theme.ERROR))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg=Theme.TEXT_SECONDARY))
        
        # Minimize button
        min_btn = tk.Label(
            self.title_bar,
            text="─",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_LG),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_ELEVATED,
            cursor="hand2"
        )
        min_btn.pack(side="right", padx=Theme.PAD_XS)
        min_btn.bind("<Button-1>", lambda e: self.iconify())
        min_btn.bind("<Enter>", lambda e: min_btn.config(fg=Theme.TEXT_PRIMARY))
        min_btn.bind("<Leave>", lambda e: min_btn.config(fg=Theme.TEXT_SECONDARY))
    
    def _create_content(self):
        """Create main content area."""
        content = tk.Frame(self, bg=Theme.BG_DARK)
        content.pack(fill="both", expand=True, padx=Theme.PAD_LG, pady=Theme.PAD_LG)
        
        # Stats cards row
        cards_frame = tk.Frame(content, bg=Theme.BG_DARK)
        cards_frame.pack(fill="x", pady=(0, Theme.PAD_LG))
        
        self.today_card = self._create_stat_card(cards_frame, "Today", "0", "words")
        self.today_card.pack(side="left", expand=True, fill="x", padx=(0, Theme.PAD_SM))
        
        self.week_card = self._create_stat_card(cards_frame, "This Week", "0", "words")
        self.week_card.pack(side="left", expand=True, fill="x", padx=(0, Theme.PAD_SM))
        
        self.total_card = self._create_stat_card(cards_frame, "Total", "0", "words")
        self.total_card.pack(side="left", expand=True, fill="x")
        
        # Streak and milestone row
        gamify_frame = tk.Frame(content, bg=Theme.BG_DARK)
        gamify_frame.pack(fill="x", pady=(0, Theme.PAD_LG))
        
        self.streak_card = self._create_streak_card(gamify_frame)
        self.streak_card.pack(side="left", expand=True, fill="x", padx=(0, Theme.PAD_SM))
        
        self.milestone_card = self._create_milestone_card(gamify_frame)
        self.milestone_card.pack(side="left", expand=True, fill="x")
        
        # Activity graph
        graph_label = tk.Label(
            content,
            text="Last 7 Days",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_DARK,
            anchor="w"
        )
        graph_label.pack(fill="x", pady=(0, Theme.PAD_SM))
        
        self.graph_canvas = Canvas(
            content,
            height=scaled(110),
            bg=Theme.BG_CARD,
            highlightthickness=1,
            highlightbackground=Theme.BORDER_SUBTLE
        )
        self.graph_canvas.pack(fill="x", pady=(0, Theme.PAD_LG))
        
        # Bind configure event to redraw graph when canvas is ready
        self.graph_canvas.bind("<Configure>", lambda e: self._draw_graph(stats_tracker.get_week_data()))
        
        # Recent transcripts
        recent_label = tk.Label(
            content,
            text="Recent",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_DARK,
            anchor="w"
        )
        recent_label.pack(fill="x", pady=(0, Theme.PAD_SM))
        
        self.recent_frame = tk.Frame(content, bg=Theme.BG_CARD, highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE)
        self.recent_frame.pack(fill="both", expand=True, pady=(0, Theme.PAD_MD))
        
        # Status label for feedback
        self.status_label = tk.Label(
            content,
            text="",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
            fg=Theme.SUCCESS,
            bg=Theme.BG_DARK,
            anchor="center"
        )
        self.status_label.pack(fill="x", pady=(0, Theme.PAD_SM))
        
        # Quick actions
        actions_frame = tk.Frame(content, bg=Theme.BG_DARK)
        actions_frame.pack(fill="x")
        
        self.copy_last_btn = self._create_action_button(actions_frame, "📋 Copy Last", self._copy_last_message)
        self.copy_last_btn.pack(side="left", expand=True, fill="x", padx=(0, Theme.PAD_SM))
        self._create_action_button(actions_frame, "⚙ Settings", lambda: open_settings_window(self)).pack(side="left", expand=True, fill="x", padx=(0, Theme.PAD_SM))
        self._create_action_button(actions_frame, "↻ Refresh", self._refresh_stats).pack(side="left", expand=True, fill="x")
    
    def _create_stat_card(self, parent, label, value, unit):
        """Create a stat card widget."""
        card = tk.Frame(parent, bg=Theme.BG_CARD, highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE)
        card.pack_propagate(False)
        card.configure(height=scaled(90))
        
        inner = tk.Frame(card, bg=Theme.BG_CARD)
        inner.pack(expand=True, fill="both", padx=Theme.PAD_MD, pady=Theme.PAD_MD)
        
        label_widget = tk.Label(
            inner,
            text=label,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
            fg=Theme.TEXT_MUTED,
            bg=Theme.BG_CARD,
            anchor="w"
        )
        label_widget.pack(anchor="w", pady=(0, scaled(2)))
        
        value_widget = tk.Label(
            inner,
            text=value,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_STAT, "bold"),
            fg=Theme.PINK_PRIMARY,
            bg=Theme.BG_CARD,
            anchor="w"
        )
        value_widget.pack(anchor="w", pady=(0, scaled(1)))
        
        unit_widget = tk.Label(
            inner,
            text=unit,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_CARD,
            anchor="w"
        )
        unit_widget.pack(anchor="w")
        
        # Store reference for updating
        card.value_label = value_widget
        
        return card
    
    def _create_streak_card(self, parent):
        """Create streak display card."""
        card = tk.Frame(parent, bg=Theme.BG_CARD, highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE)
        card.configure(height=scaled(80))
        card.pack_propagate(False)
        
        inner = tk.Frame(card, bg=Theme.BG_CARD)
        inner.pack(expand=True, fill="both", padx=Theme.PAD_MD, pady=Theme.PAD_MD)
        
        # Flame emoji + streak count
        streak_row = tk.Frame(inner, bg=Theme.BG_CARD)
        streak_row.pack(anchor="w", pady=(0, scaled(2)))
        
        flame = tk.Label(
            streak_row,
            text="🔥",
            font=(Theme.FONT_FAMILY, scaled_font(18)),
            bg=Theme.BG_CARD
        )
        flame.pack(side="left")
        
        self.streak_value = tk.Label(
            streak_row,
            text="0",
            font=(Theme.FONT_FAMILY, scaled_font(20), "bold"),
            fg=Theme.WARNING,
            bg=Theme.BG_CARD,
            anchor="w"
        )
        self.streak_value.pack(side="left", padx=(Theme.PAD_XS, 0))
        
        streak_label = tk.Label(
            inner,
            text="day streak",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_CARD,
            anchor="w"
        )
        streak_label.pack(anchor="w")
        
        return card
    
    def _create_milestone_card(self, parent):
        """Create milestone badges card."""
        card = tk.Frame(parent, bg=Theme.BG_CARD, highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE)
        card.configure(height=scaled(80))
        card.pack_propagate(False)
        
        inner = tk.Frame(card, bg=Theme.BG_CARD)
        inner.pack(expand=True, fill="both", padx=Theme.PAD_MD, pady=Theme.PAD_MD)
        
        milestone_label = tk.Label(
            inner,
            text="Milestones",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
            fg=Theme.TEXT_MUTED,
            bg=Theme.BG_CARD,
            anchor="w"
        )
        milestone_label.pack(anchor="w", pady=(0, Theme.PAD_XS))
        
        self.badges_frame = tk.Frame(inner, bg=Theme.BG_CARD)
        self.badges_frame.pack(anchor="w", fill="both", expand=True)
        
        return card
    
    def _create_action_button(self, parent, text, command):
        """Create an action button."""
        btn = tk.Label(
            parent,
            text=text,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM),
            fg=Theme.TEXT_PRIMARY,
            bg=Theme.BG_ELEVATED,
            cursor="hand2",
            pady=Theme.PAD_SM + 2
        )
        btn.bind("<Button-1>", lambda e: command())
        btn.bind("<Enter>", lambda e: btn.config(bg=Theme.BG_HOVER))
        btn.bind("<Leave>", lambda e: btn.config(bg=Theme.BG_ELEVATED))
        return btn
    
    def _draw_graph(self, data):
        """Draw the activity bar graph."""
        self.graph_canvas.delete("all")
        
        w = self.graph_canvas.winfo_width()
        h = self.graph_canvas.winfo_height()
        
        if w < 10 or h < 10:  # Not yet rendered
            return
        
        padding = scaled(25)
        bottom_margin = scaled(25)
        top_margin = scaled(20)
        label_offset = scaled(10)
        value_offset = scaled(7)
        usable_width = w - 2 * padding
        bar_spacing = usable_width / len(data)
        bar_width = bar_spacing * 0.6  # 60% of space for bar, 40% for gap
        max_val = max(d[1] for d in data) if any(d[1] for d in data) else 1
        
        for i, (day, value) in enumerate(data):
            x = padding + i * bar_spacing + (bar_spacing - bar_width) / 2
            bar_height = (value / max_val) * (h - bottom_margin - top_margin) if max_val > 0 else 0
            
            # Bar
            self.graph_canvas.create_rectangle(
                x, h - bottom_margin - bar_height,
                x + bar_width, h - bottom_margin,
                fill=Theme.PINK_PRIMARY if value > 0 else Theme.BG_ELEVATED,
                outline="",
                width=0
            )
            
            # Day label
            self.graph_canvas.create_text(
                x + bar_width / 2, h - label_offset,
                text=day,
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
                fill=Theme.TEXT_MUTED
            )
            
            # Value label (if non-zero)
            if value > 0:
                self.graph_canvas.create_text(
                    x + bar_width / 2, h - bottom_margin - bar_height - value_offset,
                    text=str(value),
                    font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
                    fill=Theme.TEXT_SECONDARY
                )
    
    def _update_recent(self, transcripts):
        """Update recent transcripts list."""
        # Clear existing
        for widget in self.recent_frame.winfo_children():
            widget.destroy()
        
        if not transcripts:
            empty_label = tk.Label(
                self.recent_frame,
                text="No transcripts yet",
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM),
                fg=Theme.TEXT_MUTED,
                bg=Theme.BG_CARD,
                pady=Theme.PAD_XL + 5
            )
            empty_label.pack()
            return
        
        for i, t in enumerate(transcripts[:5]):
            item = tk.Frame(self.recent_frame, bg=Theme.BG_CARD)
            item.pack(fill="x", padx=Theme.PAD_MD, pady=scaled(7))
            
            # Time
            time_label = tk.Label(
                item,
                text=t.get("time", ""),
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
                fg=Theme.TEXT_MUTED,
                bg=Theme.BG_CARD,
                width=7,
                anchor="w"
            )
            time_label.pack(side="left", padx=(0, Theme.PAD_SM))
            
            # Text preview
            text_preview = t.get("text", "")
            if len(text_preview) > 40:
                text_preview = text_preview[:40] + "..."
            
            text_label = tk.Label(
                item,
                text=text_preview,
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
                fg=Theme.TEXT_SECONDARY,
                bg=Theme.BG_CARD,
                anchor="w"
            )
            text_label.pack(side="left", fill="x", expand=True, padx=(0, Theme.PAD_SM))
            
            # Word count
            words_label = tk.Label(
                item,
                text=f"{t.get('words', 0)}w",
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
                fg=Theme.PINK_SOFT,
                bg=Theme.BG_CARD,
                anchor="e",
                width=5
            )
            words_label.pack(side="left", padx=(0, Theme.PAD_XS))
            
            # Copy button
            full_text = t.get("full_text", t.get("text", ""))
            copy_btn = tk.Label(
                item,
                text="⎘",
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_MD),
                fg=Theme.TEXT_MUTED,
                bg=Theme.BG_CARD,
                cursor="hand2",
                padx=Theme.PAD_XS
            )
            copy_btn.pack(side="right")
            
            # Store reference to the button for feedback updates
            def make_copy_handler(btn, txt):
                def handler(e):
                    self._copy_to_clipboard(txt, btn)
                return handler
            
            copy_btn.bind("<Button-1>", make_copy_handler(copy_btn, full_text))
            copy_btn.bind("<Enter>", lambda e, btn=copy_btn: btn.config(fg=Theme.PINK_PRIMARY))
            copy_btn.bind("<Leave>", lambda e, btn=copy_btn: btn.config(fg=Theme.TEXT_MUTED))
    
    def _copy_to_clipboard(self, text, btn=None):
        """Copy text to clipboard with visual feedback."""
        try:
            pyperclip.copy(text)
            if btn:
                original_text = btn.cget("text")
                original_fg = btn.cget("fg")
                btn.config(text="✓", fg=Theme.SUCCESS)
                def reset_btn():
                    try:
                        if btn.winfo_exists():
                            btn.config(text=original_text, fg=original_fg)
                    except Exception:
                        pass
                self.after(1000, reset_btn)
        except Exception as e:
            print(f"Copy error: {e}")
    
    def _copy_last_message(self):
        """Copy the most recent transcription to clipboard."""
        global last_transcription
        text_to_copy = None
        
        # Try global last_transcription first
        if last_transcription:
            text_to_copy = last_transcription
        else:
            # Fallback to most recent from stats
            transcripts = stats_tracker.data.get("recent_transcripts", [])
            if transcripts:
                text_to_copy = transcripts[0].get("full_text", transcripts[0].get("text", ""))
        
        if text_to_copy:
            try:
                pyperclip.copy(text_to_copy)
                # Show success feedback
                self.status_label.config(text="✓ Copied to clipboard!", fg=Theme.SUCCESS)
                self.copy_last_btn.config(bg=Theme.SUCCESS, fg=Theme.BG_DARK)
                def reset_feedback():
                    try:
                        if self.winfo_exists():
                            self.status_label.config(text="")
                            self.copy_last_btn.config(bg=Theme.BG_ELEVATED, fg=Theme.TEXT_PRIMARY)
                    except Exception:
                        pass
                self.after(1500, reset_feedback)
            except Exception as e:
                self.status_label.config(text=f"Copy failed: {str(e)[:30]}", fg=Theme.ERROR)
        else:
            self.status_label.config(text="No message to copy", fg=Theme.WARNING)
    
    def _update_milestones(self, milestones):
        """Update milestone badges."""
        for widget in self.badges_frame.winfo_children():
            widget.destroy()
        
        if not milestones:
            no_badge = tk.Label(
                self.badges_frame,
                text="Keep going!",
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM),
                fg=Theme.TEXT_MUTED,
                bg=Theme.BG_CARD,
                anchor="w"
            )
            no_badge.pack(anchor="w")
            return
        
        # Create a container frame for badges to ensure proper wrapping
        badge_container = tk.Frame(self.badges_frame, bg=Theme.BG_CARD)
        badge_container.pack(anchor="w", fill="both", expand=True)
        
        for i, m in enumerate(milestones[-4:]):  # Show last 4
            badge = tk.Label(
                badge_container,
                text=f" {m} ",
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM, "bold"),
                fg=Theme.BG_DARK,
                bg=Theme.PINK_PRIMARY,
                padx=scaled(6),
                pady=scaled(2)
            )
            badge.pack(side="left", padx=(0, scaled(6)) if i < len(milestones[-4:]) - 1 else (0, 0))
    
    def _refresh_stats(self):
        """Refresh all statistics."""
        # Update stat cards
        self.today_card.value_label.config(text=f"{stats_tracker.get_today_words():,}")
        self.week_card.value_label.config(text=f"{stats_tracker.get_week_words():,}")
        self.total_card.value_label.config(text=f"{stats_tracker.data['total_words']:,}")
        
        # Update streak
        self.streak_value.config(text=str(stats_tracker.data["streak"]))
        
        # Update milestones
        self._update_milestones(stats_tracker.data["milestones"])
        
        # Update graph
        self._draw_graph(stats_tracker.get_week_data())
        
        # Update recent
        self._update_recent(stats_tracker.data["recent_transcripts"])
    
    def _start_drag(self, event):
        """Start window drag."""
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
    
    def _on_drag(self, event):
        """Handle window dragging."""
        x = self.winfo_x() + (event.x - self._drag_data["x"])
        y = self.winfo_y() + (event.y - self._drag_data["y"])
        self.geometry(f"+{x}+{y}")


# ============================================================================
# MODERN SETTINGS WINDOW
# ============================================================================
def open_settings_window(parent):
    """Open the modernized settings window."""
    win = tk.Toplevel(parent if isinstance(parent, tk.Tk) else parent.master if hasattr(parent, 'master') else parent)
    win.title("Settings")
    win.geometry(f"{Theme.SETTINGS_WIDTH}x{Theme.SETTINGS_HEIGHT}")
    win.configure(bg=Theme.BG_DARK)
    win.resizable(False, False)
    win.attributes("-topmost", True)
    
    # Remove decorations for custom title bar
    win.overrideredirect(True)
    
    # Center window
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - Theme.SETTINGS_WIDTH) // 2
    y = (sh - Theme.SETTINGS_HEIGHT) // 2
    win.geometry(f"{Theme.SETTINGS_WIDTH}x{Theme.SETTINGS_HEIGHT}+{x}+{y}")
    
    # Custom title bar
    title_bar = tk.Frame(win, bg=Theme.BG_ELEVATED, height=Theme.TITLE_BAR_HEIGHT)
    title_bar.pack(fill="x")
    title_bar.pack_propagate(False)
    
    title_label = tk.Label(
        title_bar,
        text="⚙  Settings",
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_MD, "bold"),
        fg=Theme.TEXT_PRIMARY,
        bg=Theme.BG_ELEVATED
    )
    title_label.pack(side="left", padx=Theme.PAD_MD)
    
    close_btn = tk.Label(
        title_bar,
        text="✕",
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_LG),
        fg=Theme.TEXT_SECONDARY,
        bg=Theme.BG_ELEVATED,
        cursor="hand2"
    )
    close_btn.pack(side="right", padx=Theme.PAD_MD)
    close_btn.bind("<Button-1>", lambda e: win.destroy())
    close_btn.bind("<Enter>", lambda e: close_btn.config(fg=Theme.ERROR))
    close_btn.bind("<Leave>", lambda e: close_btn.config(fg=Theme.TEXT_SECONDARY))
    
    # Dragging
    drag_data = {"x": 0, "y": 0}
    def start_drag(e):
        drag_data["x"] = e.x
        drag_data["y"] = e.y
    def on_drag(e):
        nx = win.winfo_x() + (e.x - drag_data["x"])
        ny = win.winfo_y() + (e.y - drag_data["y"])
        win.geometry(f"+{nx}+{ny}")
    title_bar.bind("<Button-1>", start_drag)
    title_bar.bind("<B1-Motion>", on_drag)
    
    # Content
    content = tk.Frame(win, bg=Theme.BG_DARK)
    content.pack(fill="both", expand=True, padx=Theme.PAD_LG, pady=Theme.PAD_LG)
    
    # Hotkey info section
    hotkey_info = tk.Label(
        content,
        text=f"🎙️  Hold {HOTKEY_HOLD.upper().replace('+', ' + ')} to record",
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM),
        fg=Theme.TEXT_SECONDARY,
        bg=Theme.BG_CARD,
        pady=Theme.PAD_SM + 2,
        padx=Theme.PAD_MD
    )
    hotkey_info.pack(fill="x", pady=(0, Theme.PAD_LG))
    
    # Microphone section header
    mic_header = tk.Label(
        content,
        text="MICROPHONE",
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS, "bold"),
        fg=Theme.PINK_PRIMARY,
        bg=Theme.BG_DARK
    )
    mic_header.pack(anchor="w", pady=(0, Theme.PAD_SM))
    
    # Device listbox with scrollbar
    list_frame = tk.Frame(content, bg=Theme.BG_CARD, highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE)
    list_frame.pack(fill="both", expand=True, pady=(0, Theme.PAD_MD))
    
    idxs, labels = device_index_and_names()
    
    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side="right", fill="y")
    
    listbox = tk.Listbox(
        list_frame,
        bg=Theme.BG_CARD,
        fg=Theme.TEXT_PRIMARY,
        selectbackground=Theme.PINK_PRIMARY,
        selectforeground=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM),
        borderwidth=0,
        highlightthickness=0,
        yscrollcommand=scrollbar.set
    )
    listbox.pack(fill="both", expand=True, padx=Theme.PAD_SM, pady=Theme.PAD_SM)
    scrollbar.config(command=listbox.yview)
    
    for label in labels:
        listbox.insert(tk.END, label)
    
    # Pre-select current device
    try:
        if selected_input_device_idx is not None:
            cur = f"[{selected_input_device_idx}]"
            for i, lab in enumerate(labels):
                if lab.startswith(cur):
                    listbox.selection_set(i)
                    listbox.see(i)
                    break
    except Exception:
        pass
    
    # Status label
    status_var = tk.StringVar(value="")
    status_label = tk.Label(
        content,
        textvariable=status_var,
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
        fg=Theme.TEXT_SECONDARY,
        bg=Theme.BG_DARK
    )
    status_label.pack(anchor="w", pady=(0, Theme.PAD_MD))
    
    # Audio level indicator
    level_frame = tk.Frame(content, bg=Theme.BG_DARK)
    level_frame.pack(fill="x", pady=(0, Theme.PAD_MD))
    
    level_label = tk.Label(
        level_frame,
        text="Audio Level:",
        font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_XS),
        fg=Theme.TEXT_SECONDARY,
        bg=Theme.BG_DARK
    )
    level_label.pack(side="left")
    
    level_bar_width = scaled(200)
    level_bar_height = scaled(12)
    level_bar = tk.Canvas(level_frame, width=level_bar_width, height=level_bar_height, bg=Theme.BG_ELEVATED, highlightthickness=0)
    level_bar.pack(side="left", padx=(Theme.PAD_SM, 0))
    level_fill = level_bar.create_rectangle(0, 0, 0, level_bar_height, fill=Theme.PINK_PRIMARY, outline="")
    
    # Button row
    btn_frame = tk.Frame(content, bg=Theme.BG_DARK)
    btn_frame.pack(fill="x")
    
    def create_button(parent, text, command, accent=False):
        btn = tk.Label(
            parent,
            text=text,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SM),
            fg=Theme.TEXT_PRIMARY if not accent else Theme.BG_DARK,
            bg=Theme.BG_ELEVATED if not accent else Theme.PINK_PRIMARY,
            cursor="hand2",
            padx=Theme.PAD_LG,
            pady=Theme.PAD_SM
        )
        btn.bind("<Button-1>", lambda e: command())
        if accent:
            btn.bind("<Enter>", lambda e: btn.config(bg=Theme.PINK_LIGHT))
            btn.bind("<Leave>", lambda e: btn.config(bg=Theme.PINK_PRIMARY))
        else:
            btn.bind("<Enter>", lambda e: btn.config(bg=Theme.BG_HOVER))
            btn.bind("<Leave>", lambda e: btn.config(bg=Theme.BG_ELEVATED))
        return btn
    
    def do_refresh():
        nonlocal idxs, labels
        idxs, labels = device_index_and_names()
        listbox.delete(0, tk.END)
        for label in labels:
            listbox.insert(tk.END, label)
        status_var.set("Device list refreshed")
    
    def do_apply():
        sel = listbox.curselection()
        if not sel:
            status_var.set("Select a device first")
            return
        idx = idxs[sel[0]]
        os.environ["FLOW_INPUT_DEVICE"] = str(idx)
        resolve_input_device()
        if selected_input_device_idx == idx:
            status_var.set(f"✓ Selected: {selected_input_device_name}")
        else:
            status_var.set("Failed to select device")
    
    test_running = [False]
    def do_test():
        if test_running[0]:
            return
        if selected_input_device_idx is None:
            status_var.set("No device selected")
            return
        
        test_running[0] = True
        status_var.set("Testing...")
        
        def test_audio():
            try:
                for _ in range(20):  # Test for 2 seconds
                    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32", device=selected_input_device_idx) as stream:
                        block, _ = stream.read(int(SAMPLE_RATE * 0.1))
                        rms = float(np.sqrt(np.mean(block * block) + 1e-12))
                        level_pct = min(rms * 500, level_bar_width)  # Scale for visibility
                        level_bar.coords(level_fill, 0, 0, level_pct, level_bar_height)
                        level_bar.update()
                        time.sleep(0.1)
                status_var.set(f"Test complete")
            except Exception as e:
                status_var.set(f"Error: {str(e)[:30]}")
            finally:
                test_running[0] = False
                level_bar.coords(level_fill, 0, 0, 0, level_bar_height)
        
        threading.Thread(target=test_audio, daemon=True).start()
    
    create_button(btn_frame, "Refresh", do_refresh).pack(side="left", padx=(0, Theme.PAD_SM))
    create_button(btn_frame, "Test Mic", do_test).pack(side="left", padx=(0, Theme.PAD_SM))
    create_button(btn_frame, "Apply", do_apply, accent=True).pack(side="right")


# --- Helpers & Diagnostics ---
def res_path(rel):
    """Resolve path to bundled resource file."""
    base = get_bundle_dir()
    return os.path.join(base, rel)

# Resolve model paths after res_path is defined
MODEL_PATH_BASE = res_path(MODEL_BASE)
MODEL_PATH_MEDIUM = res_path(MODEL_MEDIUM)
MODEL_PATH_LARGE = res_path(MODEL_LARGE)
MODEL_PATH = MODEL_PATH_LARGE  # Legacy fallback
model_info_logged = False

def safe_print(*args, **kwargs):
    """Print to console safely, handling encoding errors.
    
    Uses the centralized logger for consistent output.
    """
    msg = " ".join(str(a) for a in args)
    try:
        logger.info(msg)
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Fallback for encoding issues
        try:
            enc = sys.stdout.encoding or "utf-8"
            sys.stdout.write((msg + "\n").encode(enc, errors="replace").decode(errors="replace"))
        except (AttributeError, UnicodeError):
            pass

def log_line(message: str, level: str = "info"):
    """Log a message using the centralized logger.
    
    This is the primary logging function. All log messages go to both
    file (flow.log) and console.
    
    Args:
        message: The message to log
        level: Log level ('debug', 'info', 'warning', 'error', 'critical')
    """
    level_map = {
        'debug': logger.debug,
        'info': logger.info,
        'warning': logger.warning,
        'error': logger.error,
        'critical': logger.critical,
    }
    log_func = level_map.get(level.lower(), logger.info)
    log_func(message)


def set_status_safe(text, bg, fg="#ffffff", border=None):
    """Queue a status change without crashing on UI errors."""
    try:
        ui_queue.put((gui.set_status, (text, bg, fg, border)))
    except Exception:
        pass


def notify(msg):
    if NOTIFY:
        try:
            if Notification is not None:
                n = Notification(app_id=APP_NAME, title=APP_NAME, msg=msg)
                if audio is not None:
                    n.set_audio(audio.SMS, loop=False)
                n.show()
        except Exception:
            pass
    log_line(msg)


# ============================================================================
# USER-FRIENDLY ERROR HANDLING
# ============================================================================
def show_friendly_error(title: str, message: str, details: str = None, show_settings: bool = False):
    """Show a user-friendly error dialog with troubleshooting info.
    
    Args:
        title: Dialog title
        message: Main error message (user-friendly)
        details: Technical details (optional, shown in expandable section)
        show_settings: Whether to offer opening settings
    """
    try:
        from tkinter import messagebox
        
        full_message = message
        if details:
            full_message += f"\n\nTechnical details:\n{details}"
        
        if show_settings:
            full_message += "\n\nWould you like to open Settings to fix this?"
            result = messagebox.askyesno(title, full_message, icon="warning")
            if result:
                # Try to open settings
                try:
                    if gui and gui.root:
                        open_settings_window(gui.root)
                except Exception:
                    pass
        else:
            messagebox.showwarning(title, full_message)
    except Exception:
        # Fallback to console/notification
        notify(f"{title}: {message}")


def get_friendly_error_message(error_type: str, technical_error: str = None) -> tuple:
    """Get user-friendly error message for common issues.
    
    Returns:
        Tuple of (friendly_message, suggestion, show_settings)
    """
    error_map = {
        "no_microphone": (
            "No microphone detected",
            "Please connect a microphone and restart the app.\n\n"
            "If you have a microphone connected, try:\n"
            "• Check Windows Sound Settings\n"
            "• Make sure the microphone isn't muted\n"
            "• Try a different USB port",
            True
        ),
        "microphone_error": (
            "Microphone not working",
            "There's a problem with your microphone.\n\n"
            "Try:\n"
            "• Selecting a different microphone in Settings\n"
            "• Checking if other apps can use the microphone\n"
            "• Restarting the app",
            True
        ),
        "no_models": (
            "AI models not found",
            "The speech recognition models are missing.\n\n"
            "This might mean the installation is incomplete.\n"
            "Please reinstall the application.",
            False
        ),
        "no_whisper_binary": (
            "Speech engine not found",
            "The whisper-cli.exe file is missing.\n\n"
            "This might mean the installation is incomplete.\n"
            "Please reinstall the application.",
            False
        ),
        "gpu_not_available": (
            "Using CPU mode",
            "GPU acceleration is not available.\n"
            "Transcription will be slower but still works!\n\n"
            "For faster performance, install NVIDIA CUDA drivers.",
            False
        ),
        "transcription_failed": (
            "Transcription failed",
            "Something went wrong during transcription.\n\n"
            "Try:\n"
            "• Speaking more clearly\n"
            "• Recording a longer phrase\n"
            "• Checking your microphone",
            True
        ),
        "paste_failed": (
            "Could not paste text",
            "The text was transcribed but couldn't be pasted.\n"
            "The text has been copied to your clipboard.\n\n"
            "Press Ctrl+V to paste manually.",
            False
        ),
    }
    
    if error_type in error_map:
        message, suggestion, show_settings = error_map[error_type]
        return message, suggestion, show_settings
    
    # Generic fallback
    return (
        "Something went wrong",
        f"An unexpected error occurred.\n\n{technical_error or 'Please try again.'}",
        False
    )


def handle_startup_issue(issue_type: str, technical_error: str = None):
    """Handle a startup issue with user-friendly messaging."""
    message, suggestion, show_settings = get_friendly_error_message(issue_type, technical_error)
    
    # Log technical details
    if technical_error:
        log_line(f"STARTUP_ISSUE: {issue_type} - {technical_error}")
    
    # For non-critical issues, just notify
    if issue_type == "gpu_not_available":
        notify(f"ℹ️ {message}")
        return
    
    # For critical issues, show dialog
    show_friendly_error(message, suggestion, technical_error, show_settings)


# Input validation - using centralized constants
MAX_TRANSCRIPT_BYTES = MAX_TRANSCRIPT_SIZE_BYTES
MAX_TRANSCRIPT_LINES = MAX_TRANSCRIPT_LINE_COUNT
MAX_LINE_LENGTH = MAX_LINE_LENGTH_CHARS

def sanitize_transcript(text: str) -> str:
    """Remove banners, deprecation notices, and placeholder tokens from transcript.
    
    Includes input validation to prevent DoS from malformed/oversized output.
    
    Args:
        text: Raw transcript text from whisper-cli
        
    Returns:
        Cleaned transcript text with metadata removed
    """
    if not text:
        return ""
    
    # Input size validation to prevent memory exhaustion
    if len(text) > MAX_TRANSCRIPT_BYTES:
        log_line(f"WARNING: Transcript too large ({len(text)} bytes), truncating to {MAX_TRANSCRIPT_BYTES}")
        text = text[:MAX_TRANSCRIPT_BYTES]
    
    text = text.replace("[BLANK_AUDIO]", "").replace("BLANK_AUDIO", "").strip()
    lines = []
    line_count = 0
    
    for ln in text.splitlines():
        # Limit number of lines processed
        line_count += 1
        if line_count > MAX_TRANSCRIPT_LINES:
            log_line(f"WARNING: Transcript has too many lines ({line_count}+), truncating")
            break
        
        # Truncate overly long lines
        if len(ln) > MAX_LINE_LENGTH:
            ln = ln[:MAX_LINE_LENGTH]
        
        lns = ln.strip()
        if not lns:
            continue
        low = lns.lower()
        if low.startswith("warning:"):
            continue
        if "deprecated" in low:
            continue
        if ("github.com/ggerganov/whisper.cpp" in low and "deprecation" in low) or ("see https://" in low and "deprecation" in low):
            continue
        if "please use" in low and "instead" in low:
            continue
        if "whisper-cli.exe" in low or "binary 'main.exe'" in low:
            continue
        lines.append(lns)
    return "\n".join(lines).strip()


# --- Smart text post-processing helpers ---
FILLER_PATTERNS = [
    r"\b(?:um+|uh+)\b",
    r"\b(?:you know|ya know)\b",
    r"\b(?:i mean)\b",
    r"\b(?:kind of|kinda|sort of|sorta)\b",
    r"\b(?:like)\b(?!\s*(?:to|that|this|those|these|it|i|we|he|she|\d))",
]

def scrub_fillers(s: str) -> str:
    out = s
    for pat in FILLER_PATTERNS:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out

COMMAND_REPLACERS = [
    (r"\bnew\s*line\b", "\n"),
    (r"\bnew\s*paragraph\b", "\n\n"),
    (r"\bcomma\b", ", "),
    (r"\bperiod\b", ". "),
    (r"\bexclamation\b", "! "),
    (r"\bquestion mark\b", "? "),
]

def apply_commands(s: str) -> str:
    out = s
    for pat, rep in COMMAND_REPLACERS:
        out = re.sub(pat, rep, out, flags=re.IGNORECASE)
    return out

def autopunct_and_capitalize(s: str) -> str:
    parts = re.split(r"([.!?])", s)
    rebuilt = []
    for i in range(0, len(parts), 2):
        seg = parts[i].strip()
        if not seg:
            continue
        end = parts[i + 1] if i + 1 < len(parts) else ""
        if not end:
            end = "."
        seg = seg[0:1].upper() + seg[1:]
        rebuilt.append(seg + end + " ")
    return "".join(rebuilt).strip()

def to_bullets(s: str) -> str:
    if re.search(r"\b(bullets?|bullet\s*list|make\s+a\s+list|list:?)\b", s, re.IGNORECASE):
        s = re.sub(r"^\s*.*?(bullets?|list:?)\s*", "", s, flags=re.IGNORECASE)
    items = re.split(r",|\band\b", s)
    items = [it.strip(" .\t\r\n") for it in items if it.strip()]
    if len(items) <= 1:
        return s.strip()
    return "\n".join("- " + it for it in items)

def postprocess(text: str) -> str:
    return text  # no grammar, no filler, no bullets

def set_bullet_next():
    global MODE_BULLET_NEXT
    MODE_BULLET_NEXT = True
    notify("Bullet list on next paste")

def list_input_devices():
    """Return list of (index, name) for input-capable devices."""
    devices = []
    try:
        for idx, dev in enumerate(sd.query_devices()):
            if dev.get("max_input_channels", 0) > 0:
                devices.append((idx, dev.get("name", f"Device {idx}")))
    except Exception as e:
        notify(f"Device query error: {e}")
    return devices


def devices_summary_text():
    rows = []
    for idx, name in list_input_devices():
        mark = " (selected)" if idx == selected_input_device_idx else ""
        rows.append(f"[{idx}] {name}{mark}")
    return "\n".join(rows) if rows else "<no input devices>"


def device_index_and_names():
    """Return parallel lists of indices and labels for UI listbox/combobox."""
    pairs = list_input_devices()
    idxs = [p[0] for p in pairs]
    labels = [f"[{p[0]}] {p[1]}" for p in pairs]
    return idxs, labels


def resolve_input_device():
    """Resolve the input device index and validate settings. Sets globals."""
    global selected_input_device_idx, selected_input_device_name
    devices = list_input_devices()
    if not devices:
        notify("No input-capable audio devices found.")
        selected_input_device_idx = None
        selected_input_device_name = None
        return

    requested = INPUT_DEVICE
    idx = None
    name = None
    try:
        if requested is None or requested == "":
            try:
                default_idx = None
                try:
                    default_idx = sd.default.device[0] if isinstance(sd.default.device, (list, tuple)) else sd.default.device
                except Exception:
                    default_idx = None
                if default_idx is not None and default_idx >= 0:
                    idx = int(default_idx)
                    name = sd.query_devices(idx).get("name", f"Device {idx}")
                else:
                    idx, name = devices[0]
            except Exception:
                idx, name = devices[0]
        else:
            if isinstance(requested, str) and requested.isdigit():
                idx = int(requested)
                name = sd.query_devices(idx).get("name", f"Device {idx}")
            else:
                needle = str(requested).lower()
                for d_idx, d_name in devices:
                    if needle in str(d_name).lower():
                        idx, name = d_idx, d_name
                        break
                if idx is None:
                    try:
                        idx = int(requested)
                        name = sd.query_devices(idx).get("name", f"Device {idx}")
                    except Exception:
                        idx, name = devices[0]

        sd.check_input_settings(device=idx, samplerate=SAMPLE_RATE, channels=CHANNELS)
        selected_input_device_idx = idx
        selected_input_device_name = name
        notify(f"Mic: {name}")
    except Exception as e:
        notify(f"Mic selection error: {e}")
        selected_input_device_idx = None
        selected_input_device_name = None


def startup_diagnostics():
    """Run preflight checks and print a concise summary.
    
    Uses user-friendly error messages for general users while logging
    technical details for troubleshooting.
    """
    issues = []
    critical_issues = []
    
    # Check all model files
    models_found = []
    models_missing = []
    for model_path, model_name in [
        (MODEL_PATH_BASE, "base.en"),
        (MODEL_PATH_MEDIUM, "medium.en"),
        (MODEL_PATH_LARGE, "large-v3")
    ]:
        if os.path.exists(model_path):
            models_found.append(model_name)
        else:
            models_missing.append(model_name)
    
    if not models_found:
        critical_issues.append(("no_models", "No model files found in expected locations"))
    else:
        log_line(f"✓ Models available: {', '.join(models_found)}")
        if models_missing:
            log_line(f"  (Optional models not found: {', '.join(models_missing)})")
    
    # Check whisper binary
    global resolved_whisper_bin
    resolved_whisper_bin = None
    for candidate in WHISPER_CANDIDATES:
        if os.path.exists(candidate):
            resolved_whisper_bin = candidate
            break
    
    if resolved_whisper_bin is None:
        critical_issues.append(("no_whisper_binary", f"Checked: {', '.join(WHISPER_CANDIDATES[:3])}..."))
    else:
        log_line(f"✓ Whisper engine: {os.path.basename(resolved_whisper_bin)}")

    # Check audio system
    try:
        pa_ver = sd.get_portaudio_version()
        log_line(f"✓ Audio system: PortAudio {pa_ver[1] if isinstance(pa_ver, tuple) else pa_ver}")
    except Exception as e:
        issues.append(f"Audio system warning: {e}")
        log_line(f"⚠ Audio system issue: {e}")

    # Log DPI scaling information
    log_line(f"✓ Display DPI scale: {DPI_SCALE:.2f}x ({int(DPI_SCALE * 100)}%)")

    # Check microphone
    resolve_input_device()
    if selected_input_device_idx is None:
        critical_issues.append(("no_microphone", "No input devices detected by system"))
    else:
        try:
            sd.check_input_settings(device=selected_input_device_idx, samplerate=SAMPLE_RATE, channels=CHANNELS)
            log_line(f"✓ Microphone: {selected_input_device_name}")
        except Exception as e:
            issues.append(("microphone_error", str(e)))
            log_line(f"⚠ Microphone issue: {e}")

    # Handle critical issues (show dialogs for general users)
    if critical_issues:
        set_status_safe("⚠️ Setup needed", Theme.WARNING, Theme.BG_DARK, Theme.WARNING)
        
        for issue_type, technical_detail in critical_issues:
            log_line(f"CRITICAL: {issue_type} - {technical_detail}")
            handle_startup_issue(issue_type, technical_detail)
        
        log_line("Available input devices:\n" + devices_summary_text())
        return False
    
    # Handle non-critical issues (just log them)
    if issues:
        set_status_safe("🎤 Ready (with warnings)", Theme.BG_ELEVATED, Theme.TEXT_PRIMARY, Theme.WARNING)
        for issue in issues:
            if isinstance(issue, tuple):
                log_line(f"WARNING: {issue[0]} - {issue[1]}")
            else:
                log_line(f"WARNING: {issue}")
    else:
        set_status_safe("🎤 Ready", Theme.BG_ELEVATED, Theme.TEXT_PRIMARY, Theme.PINK_PRIMARY)
        log_line("✓ All diagnostics passed!")
    
    log_line(f"✓ Ready for dictation (Hold WIN+CTRL to speak)")
    return True


# Global flag to track if CUDA warmup is done
_cuda_warmed_up = False

def cuda_warmup():
    """Pre-load base model into GPU memory by running a tiny transcription."""
    global _cuda_warmed_up
    if _cuda_warmed_up:
        return
    
    if resolved_whisper_bin is None or not os.path.exists(MODEL_PATH_BASE):
        log_line("[warmup] Skipping - missing binary or base model")
        return
    
    try:
        log_line("[warmup] Starting CUDA warmup...")
        
        # Create a tiny 0.5s silent audio file for warmup
        warmup_wav = os.path.join(tempfile.gettempdir(), "whisper_warmup.wav")
        warmup_samples = int(SAMPLE_RATE * 0.5)
        warmup_audio = np.zeros((warmup_samples, CHANNELS), dtype=np.float32)
        # Add tiny noise so it's not completely silent
        warmup_audio += np.random.randn(*warmup_audio.shape).astype(np.float32) * 0.001
        sf.write(warmup_wav, warmup_audio, SAMPLE_RATE)
        
        # Run whisper with minimal processing to just load the base model
        exe = os.path.abspath(_resolve_whisper_exe(resolved_whisper_bin))
        workdir = os.path.dirname(exe) or "."
        
        cmd = [
            exe, "-m", MODEL_PATH_BASE,
            "-l", "en", "-nt",
            "-bs", "1",  # Minimal batch size for warmup
            warmup_wav
        ]
        
        env = os.environ.copy()
        env["GGML_CUDA_FORCE_CUBLAS"] = "1"
        env["CUDA_LAUNCH_BLOCKING"] = "0"
        
        # Run silently (CREATE_NO_WINDOW prevents console popup)
        subprocess.run(cmd, cwd=workdir, env=env, capture_output=True, timeout=30, creationflags=CREATE_NO_WINDOW)
        
        # Cleanup
        try:
            os.remove(warmup_wav)
        except Exception:
            pass
        
        _cuda_warmed_up = True
        log_line("[warmup] CUDA warmup complete - GPU model loaded")
        
    except Exception as e:
        log_line(f"[warmup] Warmup failed (non-critical): {e}")


def _resolve_whisper_exe(bin_path: str) -> str:
    """Resolve path to whisper binary.
    
    Search order:
    1. Environment variables (FLOW_WHISPER_BIN, WHISPER_BIN)
    2. Provided bin_path
    3. Bundle directory (for PyInstaller builds)
    4. App directory (where exe/script is located)
    5. System PATH
    6. Current working directory
    """
    # Check environment variables first
    for key in ("FLOW_WHISPER_BIN", "WHISPER_BIN"):
        p = os.getenv(key)
        if p and os.path.isfile(p):
            return p
    
    # Check provided path
    if bin_path and os.path.isfile(bin_path):
        return bin_path
    
    # Check bundle directory (PyInstaller)
    bundle_dir = get_bundle_dir()
    for exe_name in ("whisper-cli.exe", "main.exe"):
        candidate = os.path.join(bundle_dir, exe_name)
        if os.path.isfile(candidate):
            return candidate
    
    # Check app directory
    app_dir = get_app_dir()
    if app_dir != bundle_dir:
        for exe_name in ("whisper-cli.exe", "main.exe"):
            candidate = os.path.join(app_dir, exe_name)
            if os.path.isfile(candidate):
                return candidate
    
    # Check system PATH
    w = shutil.which("whisper-cli.exe") or shutil.which("main.exe")
    if w:
        return w
    
    # Check current working directory
    for exe_name in ("whisper-cli.exe", "main.exe"):
        if os.path.isfile(exe_name):
            return os.path.abspath(exe_name)
    
    raise FileNotFoundError(
        f"Whisper binary not found. Searched:\n"
        f"  - Bundle dir: {bundle_dir}\n"
        f"  - App dir: {app_dir}\n"
        f"  - System PATH\n"
        f"Please ensure whisper-cli.exe is installed correctly."
    )

def build_whisper_cmd(exe, model_path, wav_path, base_args=None):
    base_args = base_args or []
    extra_args = shlex.split(os.getenv("FLOW_WHISPER_ARGS", ""))

    if os.path.basename(exe).lower() == "whisper-cli.exe":
        filtered_args = []
        skip_next = False
        for i, arg in enumerate(extra_args):
            if skip_next:
                skip_next = False
                continue
            if arg in ("-ngl", "--n-gpu-layers"):
                skip_next = True
                continue
            filtered_args.append(arg)
        extra_args = filtered_args
        return [exe, "-m", model_path, *base_args, *extra_args, wav_path]

    return [exe, "-m", model_path, "-f", wav_path, *base_args, *extra_args]

# Recording timing - using centralized constants
MIN_SEC = MIN_SPEECH_DURATION_SEC
RMS_THRESH = RMS_THRESHOLD_VOICED
PREROLL_SEC = PREROLL_DURATION_SEC
POSTROLL_SEC = POSTROLL_DURATION_SEC

def record_loop():
    """Record while recording_flag is set; write to WAV on stop with RMS gate."""
    log_line("[rec] start")
    # Skip slow toast notification - UI pill already shows listening state
    data = []
    voiced_samples = 0
    block_dur = AUDIO_BLOCK_DURATION_SEC

    if selected_input_device_idx is None:
        set_status_safe("❌ Mic not ready", Theme.ERROR, Theme.TEXT_PRIMARY, Theme.ERROR)
        return

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32", device=selected_input_device_idx) as stream:
            while recording_flag.is_set():
                try:
                    block, _ = stream.read(int(SAMPLE_RATE * block_dur))
                except Exception as e:
                    log_line(f"Audio read error: {e}")
                    set_status_safe("Audio read error", Theme.ERROR)
                    break
                data.append(block.copy())
                rms = float(np.sqrt(np.mean(block * block) + 1e-12))
                if rms > RMS_THRESH:
                    voiced_samples += block.shape[0]
    except Exception as e:
        log_line(f"Mic open error: {e}")
        set_status_safe("Mic open error", Theme.ERROR)
        return

    if not data or (voiced_samples / SAMPLE_RATE) < MIN_SEC:
        safe_print("[rec] stop, no speech detected")
        try:
            if os.path.exists(WAV_TMP):
                os.remove(WAV_TMP)
        except Exception:
            pass
        set_status_safe("🔇 No speech detected", Theme.WARNING, Theme.BG_DARK, Theme.WARNING)
        return

    try:
        audio = np.concatenate(data, axis=0)
        # Pre-normalize for consistent levels (improves transcription speed & accuracy)
        peak = np.max(np.abs(audio))
        if peak > 0.01:  # Only normalize if there's actual audio
            audio = audio * (0.9 / peak)
        sf.write(WAV_TMP, audio, SAMPLE_RATE)
        safe_print(f"[rec] stop, saved: {WAV_TMP}")
    except Exception as e:
        log_line(f"WAV write error: {e}")
        set_status_safe("WAV write error", Theme.ERROR)


def start_recording():
    """Start audio recording in a background thread.
    
    Thread-safe: Uses STATE_LOCK to prevent race conditions with
    stop_recording_and_transcribe().
    """
    global rec_thread, target_window_on_record_start, pending_status_timer
    
    with STATE_LOCK:
        # Check if already recording or transcribing (must be first check inside lock)
        if recording_flag.is_set() or transcribing_flag.is_set():
            return
        
        # Cancel any pending status timer from previous transcription
        if pending_status_timer is not None:
            try:
                pending_status_timer.cancel()
            except (AttributeError, RuntimeError):
                pass  # Timer already fired or cancelled
            pending_status_timer = None
        
        # Capture focus BEFORE we start (before our UI updates)
        # This ensures we know where to paste when transcription completes
        try:
            user32 = ctypes.windll.user32
            target_window_on_record_start = user32.GetForegroundWindow()
        except (AttributeError, OSError):
            target_window_on_record_start = None
        
        # Clean up previous temp file
        try:
            if os.path.exists(WAV_TMP):
                os.remove(WAV_TMP)
        except OSError:
            pass  # File in use or already deleted
        
        # Set flag to indicate recording has started
        recording_flag.set()
    
    # UI update and thread start outside lock (safe since flag is already set)
    set_status_safe("🎙️ Listening...", Theme.PINK_DARK, Theme.TEXT_PRIMARY, Theme.PINK_PRIMARY)
    rec_thread = threading.Thread(target=record_loop, daemon=True)
    rec_thread.start()

def _select_whisper_params(duration_sec):
    """Aggressive GPU-optimized parameters for maximum speed with large model."""
    # Use higher batch size for modern GPUs - RTX 3000+ can handle 12-16
    if duration_sec is None or duration_sec < 15:
        return 12, None, "fast-gpu"  # Higher batch size + no best-of = maximum speed
    elif duration_sec < 30:
        return 10, 2, "balanced-gpu"  # Slightly higher batch size
    elif duration_sec < 60:
        return 8, 3, "quality-gpu"  # Max best-of capped at 3
    else:
        return 6, 2, "long-audio"  # Slightly lower for very long audio


def _parse_cuda_error(stderr_text):
    if not stderr_text:
        return None, None, None
    
    stderr_lower = stderr_text.lower()
    
    if "cuda out of memory" in stderr_lower or "cudamalloc failed" in stderr_lower:
        snippet = _extract_error_snippet(stderr_text, "memory")
        return "OOM", "CUDA out of memory", snippet
    
    if "ggml_assert" in stderr_lower:
        snippet = _extract_error_snippet(stderr_text, "ggml_assert")
        return "ASSERT", "CUDA assertion failed", snippet
    
    if "incorrect kv cache" in stderr_lower or "kv cache padding" in stderr_lower:
        snippet = _extract_error_snippet(stderr_text, "kv cache")
        return "KV_CACHE", "KV cache configuration error", snippet
    
    if "cuda error" in stderr_lower or "cudnn error" in stderr_lower:
        if "cuda error: success" not in stderr_lower and "found" not in stderr_lower:
            snippet = _extract_error_snippet(stderr_text, "cuda")
            return "CUDA_ERROR", "CUDA runtime error", snippet
    
    return None, None, None


def _extract_error_snippet(text, keyword):
    try:
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if keyword.lower() in line.lower():
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                return ' | '.join(lines[start:end])
    except Exception:
        pass
    return text[:200]


def run_whisper(filename, bin_path, model_path=None):
    """Run whisper transcription with specified model.
    
    Args:
        filename: Path to audio file
        bin_path: Path to whisper binary
        model_path: Path to model file (defaults to MODEL_PATH_LARGE)
    
    Returns:
        Tuple of (return_code, transcription_text, stderr)
    """
    if model_path is None:
        model_path = MODEL_PATH_LARGE
    
    exe = os.path.abspath(_resolve_whisper_exe(bin_path))
    workdir = os.path.dirname(exe) or "."

    out_txt = os.path.join(tempfile.gettempdir(), f"flow_out_{uuid.uuid4().hex}.txt")

    try:
        if os.path.exists(out_txt):
            os.remove(out_txt)
    except Exception:
        pass

    global model_info_logged
    if not model_info_logged:
        safe_print(f"MODEL_PATH_BASE -> {MODEL_PATH_BASE}")
        safe_print(f"MODEL_PATH_MEDIUM -> {MODEL_PATH_MEDIUM}")
        safe_print(f"MODEL_PATH_LARGE -> {MODEL_PATH_LARGE}")
        try:
            for mp, name in [(MODEL_PATH_BASE, "base"), (MODEL_PATH_MEDIUM, "medium"), (MODEL_PATH_LARGE, "large")]:
                if os.path.exists(mp):
                    sz = os.path.getsize(mp)
                    safe_print(f"MODEL_SIZE ({name}) -> {sz/1_000_000:.1f} MB")
        except Exception:
            pass
        model_info_logged = True

    duration_sec = None
    try:
        info = sf.info(filename)
        if getattr(info, "samplerate", 0) and getattr(info, "frames", 0):
            duration_sec = info.frames / float(info.samplerate)
    except Exception:
        duration_sec = None

    batch_size, best_of, mode_desc = _select_whisper_params(duration_sec)
    
    # GPU mode: Use fewer threads (GPU does the heavy lifting)
    # More CPU threads can actually slow down GPU inference due to scheduling overhead
    num_threads = "2"  # Optimal for GPU mode
    
    cmd = build_whisper_cmd(
        exe,
        model_path,
        filename,
        base_args=[
            "-l", "en",
            "-nt",
            "-mc", "0",
            "-bs", str(batch_size),
            "-t", num_threads,
            "-ngl", "999",  # Force all layers to GPU for maximum speed
            "-fa",  # Enable Flash Attention for 2x faster GPU inference
            "-otxt", "-of", out_txt[:-4],
        ],
    )

    if best_of is not None:
        cmd.extend(["-bo", str(best_of)])
    
    if duration_sec is not None:
        params_info = f"bs={batch_size}" + (f", bo={best_of}" if best_of else "")
        safe_print(f"[whisper] {duration_sec:.1f}s audio: {mode_desc} mode ({params_info})")

    env = os.environ.copy()
    env["GGML_CUDA_FORCE_CUBLAS"] = "1"
    env["CUDA_LAUNCH_BLOCKING"] = "0"  # Async GPU operations for better throughput
    log_line(f"DEBUG exe = {exe}")
    log_line(f"DEBUG wav_path = {filename}")
    log_line(f"DEBUG cmd = {cmd}")

    try:
        res = subprocess.run(
            cmd,
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=WHISPER_TIMEOUT_SEC,
            creationflags=CREATE_NO_WINDOW,  # Prevent console window popup
        )
    except subprocess.TimeoutExpired:
        log_line(f"[whisper] Process timed out after {WHISPER_TIMEOUT_SEC}s")
        return 1, "", "Transcription timed out"

    stderr_lower = (res.stderr or "").lower()
    if "cuda" in stderr_lower and "found" in stderr_lower and res.returncode == 0:
        log_line(f"CUDA_INIT: Detected CUDA initialization in stderr")
    
    def _looks_cuda_assert(s: str) -> bool:
        return ("GGML_ASSERT" in (s or "")) or ("Incorrect KV cache padding" in (s or ""))

    cuda_error_type, cuda_error_msg, cuda_snippet = _parse_cuda_error(res.stderr)
    
    if res.returncode != 0 or _looks_cuda_assert(res.stderr) or cuda_error_type:
        if cuda_error_type:
            safe_print(f"[whisper] CUDA error ({cuda_error_type}): {cuda_error_msg}")
            log_line(f"CUDA_ERROR type={cuda_error_type} msg={cuda_error_msg}")
            if cuda_snippet:
                log_line(f"CUDA_ERROR snippet: {cuda_snippet}")
        elif res.returncode != 0:
            safe_print(f"[whisper] Process failed (exit code {res.returncode}); retrying on CPU")
            log_line(f"PROCESS_ERROR exit_code={res.returncode}")
        else:
            safe_print("[whisper] CUDA failed; retrying on CPU")
        
        cpu_batch_size = min(batch_size, 5)
        cpu_best_of = min(best_of, 3) if best_of else None
        cpu_threads = str(os.cpu_count() or 4)  # Use all cores for CPU mode
        
        cpu_args = [
            "-l", "en",
            "-nt",
            "-mc", "0",
            "-bs", str(cpu_batch_size),
            "-t", cpu_threads,
            "-otxt", "-of", out_txt[:-4],
            "--no-gpu"
        ]
        
        if cpu_best_of:
            cpu_args.extend(["-bo", str(cpu_best_of)])
        
        cmd_cpu = build_whisper_cmd(exe, model_path, filename, base_args=cpu_args)
        
        safe_print(f"[whisper] CPU fallback: bs={cpu_batch_size}" + (f", bo={cpu_best_of}" if cpu_best_of else "") + f", threads={cpu_threads}")
        
        try:
            res = subprocess.run(
                cmd_cpu,
                cwd=workdir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=WHISPER_TIMEOUT_SEC,
                creationflags=CREATE_NO_WINDOW,  # Prevent console window popup
            )
        except subprocess.TimeoutExpired:
            log_line(f"[whisper] CPU fallback timed out after {WHISPER_TIMEOUT_SEC}s")
            return 1, "", "Transcription timed out (CPU fallback)"
    safe_print(f"[whisper] exit={res.returncode} stdout={len(res.stdout)}B stderr={len(res.stderr)}B out='{out_txt}'")

    text = ""
    try:
        if os.path.exists(out_txt):
            with open(out_txt, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read().strip()
    except Exception as e:
        safe_print(f"[whisper] read file error: {e}")

    if not text:
        text = (res.stdout or "").strip()

    def _looks_bad(s: str) -> bool:
        s = (s or "").lower()
        return "usage:" in s or "unknown argument" in s

    if not text and _looks_bad(res.stderr):
        safe_print("[whisper] bad-args fallback")
        cmd_fallback = build_whisper_cmd(
            exe,
            model_path,
            filename,
            base_args=["-l", "en", "-nt", "-bs", "5", "-otxt", "-of", out_txt[:-4]],
        )
        try:
            res = subprocess.run(
                cmd_fallback,
                cwd=workdir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=WHISPER_TIMEOUT_SEC,
                creationflags=CREATE_NO_WINDOW,  # Prevent console window popup
            )
        except subprocess.TimeoutExpired:
            log_line(f"[whisper] bad-args fallback timed out after {WHISPER_TIMEOUT_SEC}s")
            return 1, "", "Transcription timed out (fallback)"
        try:
            if os.path.exists(out_txt):
                with open(out_txt, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read().strip()
        except Exception:
            pass
        if not text:
            text = (res.stdout or "").strip()

    if not text:
        safe_print("[whisper] empty transcript; stderr head:")
        safe_print((res.stderr or "")[:500])

    return res.returncode, text, (res.stderr or "").strip()


def run_whisper_smart(filename, bin_path):
    """Two-pass smart model selection with CPU/GPU awareness and dynamic load monitoring.
    
    GPU Mode (NVIDIA, low load): Prioritize quality
    - < 30 words: base.en only
    - 30-80 words: base.en → medium.en
    - 80+ words: base.en → large-v3
    
    GPU Mode (NVIDIA, high load 70%+): Prioritize speed
    - < 50 words: base.en only
    - 50+ words: base.en → medium.en (skip large-v3)
    
    GPU Mode (NVIDIA, critical load 85%+): Maximum speed
    - All utterances: base.en only
    
    Non-NVIDIA GPU Mode (AMD/Intel): Prioritize compatibility
    - < 50 words: base.en only
    - 50+ words: base.en → medium.en
    - Never uses large-v3 (poor compatibility)
    
    CPU Mode (no GPU): Prioritize speed
    - < 50 words: base.en only (fast)
    - 50+ words: base.en → medium.en
    - Never uses large-v3 (too slow on CPU)
    
    Args:
        filename: Path to audio file
        bin_path: Path to whisper binary
    
    Returns:
        Tuple of (return_code, transcription_text, stderr, model_used)
    """
    start_time = time.time()
    
    # Check GPU load status
    gpu_load_status = gpu_monitor.get_load_status_text()
    safe_print(f"[whisper-smart] GPU Status: {gpu_load_status}")
    
    # Determine model selection strategy based on hardware and load
    is_nvidia = gpu_monitor.is_nvidia_gpu()
    is_gpu_busy = gpu_monitor.is_gpu_busy()  # 70%+ utilization
    is_critical_load = gpu_monitor.is_gpu_critical_load()  # 85%+ utilization
    recommended_tier = gpu_monitor.get_recommended_model_tier()
    
    # Adjust thresholds based on hardware capability and GPU load
    if GPU_AVAILABLE and is_nvidia:
        if is_critical_load:
            # Critical GPU load (85%+) - use only base.en for everything
            threshold_base = 999999  # Never upgrade from base
            threshold_medium = 999999
            use_large_model = False
            mode_label = "GPU-CRITICAL"
            safe_print("[whisper-smart] ⚠️ GPU under critical load (85%+) - using base.en only")
        elif is_gpu_busy:
            # High GPU load (70%+) - skip large-v3, use medium for long content
            threshold_base = 50  # More conservative
            threshold_medium = 999999  # Never use large-v3
            use_large_model = False
            mode_label = "GPU-BUSY"
            safe_print("[whisper-smart] ⚠️ GPU busy (70%+) - skipping large-v3")
        else:
            # Low GPU load - full quality mode
            threshold_base = WORD_THRESHOLD_BASE  # 25 words
            threshold_medium = WORD_THRESHOLD_MEDIUM  # 75 words
            use_large_model = True
            mode_label = "GPU"
            safe_print("[whisper-smart] ✅ GPU available with low load - full quality mode")
    elif GPU_AVAILABLE and not is_nvidia:
        # Non-NVIDIA GPU (AMD/Intel) - always use light/medium models
        threshold_base = 50
        threshold_medium = 999999  # Never use large-v3
        use_large_model = False
        gpu_vendor = gpu_monitor.get_gpu_vendor()
        mode_label = f"GPU-{gpu_vendor.upper()}"
        safe_print(f"[whisper-smart] Non-NVIDIA GPU ({gpu_vendor}) - using light/medium models only")
    else:
        # CPU mode - aggressive speed optimization
        threshold_base = 50  # Wider base.en range for speed
        threshold_medium = 999999  # Never trigger large-v3
        use_large_model = False
        mode_label = "CPU"
        safe_print("[whisper-smart] CPU mode - speed-optimized")
    
    safe_print(f"[whisper-smart] {mode_label} mode: threshold_base={threshold_base}, use_large={use_large_model}")
    
    # Phase 1: Fast pass with base.en to count words
    safe_print("[whisper-smart] Phase 1: Quick transcription with base.en...")
    rc_base, text_base, err_base = run_whisper(filename, bin_path, model_path=MODEL_PATH_BASE)
    
    phase1_time = time.time() - start_time
    
    if rc_base != 0:
        # Base model failed - fall back appropriately
        if use_large_model:
            safe_print(f"[whisper-smart] Base model failed (rc={rc_base}), using large-v3 fallback")
            rc, text, err = run_whisper(filename, bin_path, model_path=MODEL_PATH_LARGE)
            total_time = time.time() - start_time
            safe_print(f"[whisper-smart] Fallback complete: {total_time:.2f}s")
            return rc, text, err, "large-v3 (fallback)"
        else:
            # CPU mode - fall back to medium.en instead
            safe_print(f"[whisper-smart] Base model failed (rc={rc_base}), using medium.en fallback (CPU mode)")
            rc, text, err = run_whisper(filename, bin_path, model_path=MODEL_PATH_MEDIUM)
            total_time = time.time() - start_time
            safe_print(f"[whisper-smart] Fallback complete: {total_time:.2f}s")
            return rc, text, err, "medium.en (fallback)"
    
    # Sanitize and count words
    clean_text = sanitize_transcript(text_base)
    if not clean_text:
        # Empty transcript - return base result
        safe_print("[whisper-smart] Empty transcript from base.en")
        return rc_base, text_base, err_base, "base.en"
    
    word_count = len(clean_text.split())
    safe_print(f"[whisper-smart] Phase 1 complete: {word_count} words in {phase1_time:.2f}s")
    
    # Phase 2: Decide if we need a better model based on hardware and word count
    if word_count < threshold_base:
        # Short utterance - base.en is perfect!
        safe_print(f"[whisper-smart] Using base.en result ({word_count} < {threshold_base} words)")
        total_time = time.time() - start_time
        safe_print(f"[whisper-smart] ✓ Total time: {total_time:.2f}s (base.en only)")
        return rc_base, text_base, err_base, "base.en"
    
    elif word_count < threshold_medium:
        # Medium length - re-transcribe with medium.en
        safe_print(f"[whisper-smart] Phase 2: Re-transcribing with medium.en ({word_count} words)")
        rc_med, text_med, err_med = run_whisper(filename, bin_path, model_path=MODEL_PATH_MEDIUM)
        total_time = time.time() - start_time
        
        if rc_med == 0:
            safe_print(f"[whisper-smart] ✓ Total time: {total_time:.2f}s (base.en + medium.en)")
            return rc_med, text_med, err_med, "medium.en"
        else:
            # Medium failed - fall back to base result
            safe_print(f"[whisper-smart] Medium.en failed, using base.en result")
            return rc_base, text_base, err_base, "base.en (medium failed)"
    
    elif use_large_model:
        # GPU mode only - long utterance gets large-v3 for best quality
        safe_print(f"[whisper-smart] Phase 2: Re-transcribing with large-v3 ({word_count} words)")
        rc_large, text_large, err_large = run_whisper(filename, bin_path, model_path=MODEL_PATH_LARGE)
        total_time = time.time() - start_time
        
        if rc_large == 0:
            safe_print(f"[whisper-smart] ✓ Total time: {total_time:.2f}s (base.en + large-v3)")
            return rc_large, text_large, err_large, "large-v3"
        else:
            # Large failed - fall back to base result
            safe_print(f"[whisper-smart] Large-v3 failed, using base.en result")
            return rc_base, text_base, err_base, "base.en (large failed)"
    
    else:
        # CPU mode - cap at medium.en for acceptable speed
        safe_print(f"[whisper-smart] CPU mode: Using medium.en ({word_count} words, large-v3 skipped)")
        rc_med, text_med, err_med = run_whisper(filename, bin_path, model_path=MODEL_PATH_MEDIUM)
        total_time = time.time() - start_time
        
        if rc_med == 0:
            safe_print(f"[whisper-smart] ✓ Total time: {total_time:.2f}s (base.en + medium.en, CPU-optimized)")
            return rc_med, text_med, err_med, "medium.en (CPU-optimized)"
        else:
            safe_print(f"[whisper-smart] Medium.en failed, using base.en result")
            return rc_base, text_base, err_base, "base.en (medium failed)"


def _transcribe_and_paste(wav_path):
    global last_transcription, target_window_on_record_start, pending_status_timer
    
    safe_print("[whisper] running...")
    set_status_safe("⚙️ Transcribing...", Theme.BG_ELEVATED, Theme.INFO, Theme.INFO)
    bin_path = (resolved_whisper_bin or WHISPER_BIN)
    
    try:
        rc, out, err, model_used = run_whisper_smart(wav_path, bin_path)
    except FileNotFoundError as e:
        # User-friendly error for missing binary
        set_status_safe("❌ Engine not found", Theme.ERROR, Theme.TEXT_PRIMARY, Theme.ERROR)
        log_line(f"TRANSCRIBE_ERROR: {e}")
        notify("Speech engine not found. Please reinstall the application.")
        return
    except Exception as e:
        # Generic transcription error
        set_status_safe("❌ Error", Theme.ERROR, Theme.TEXT_PRIMARY, Theme.ERROR)
        log_line(f"TRANSCRIBE_ERROR: {e}")
        return

    if rc != 0:
        # User-friendly status for failed transcription
        set_status_safe("❌ Try again", Theme.ERROR, Theme.TEXT_PRIMARY, Theme.ERROR)
        log_line(f"[whisper] exit={rc} stderr={err[:400]}")
        # Reset status after delay
        def reset_status():
            set_status_safe("🎤 Ready", Theme.BG_ELEVATED, Theme.TEXT_PRIMARY, Theme.PINK_PRIMARY)
        threading.Timer(2.0, reset_status).start()
        return
    
    safe_print(f"[whisper] Model used: {model_used}")

    raw = (out or "").strip()
    text = sanitize_transcript(raw)

    def _dedupe_lines(s: str) -> str:
        seen = []
        for ln in s.splitlines():
            if not seen or seen[-1] != ln:
                seen.append(ln)
        return "\n".join(seen)

    text = _dedupe_lines(text)

    banned = {"[ Silence ]", "[silence]", ""}
    if text in banned or len(text.replace("\n","" ).strip()) == 0:
        # Skip slow toast notification
        set_status_safe("🔇 Empty transcript", Theme.WARNING, Theme.BG_DARK, Theme.WARNING)
        return

    try:
        text = postprocess(text)
        
        # Store last transcription for manual copy access
        last_transcription = text
        
        # Check if our dashboard or pill had focus when recording STARTED
        # Using captured focus state to avoid issues with UI updates changing focus
        our_window_focused = False
        
        try:
            if target_window_on_record_start:
                if dashboard_window and dashboard_window.winfo_exists():
                    dashboard_hwnd = int(dashboard_window.winfo_id())
                    if target_window_on_record_start == dashboard_hwnd:
                        our_window_focused = True
                        
                if gui and gui.root and gui.root.winfo_exists():
                    pill_hwnd = int(gui.root.winfo_id())
                    if target_window_on_record_start == pill_hwnd:
                        our_window_focused = True
        except Exception:
            pass
        
        if our_window_focused:
            # Dashboard has focus - just copy to clipboard, don't auto-paste
            pyperclip.copy(text)
            # Record stats async
            threading.Thread(target=stats_tracker.record_transcription, args=(text, model_used), daemon=True).start()
            set_status_safe("📋 Copied!", Theme.SUCCESS, Theme.TEXT_PRIMARY, Theme.SUCCESS)
            pending_status_timer = threading.Timer(1.5, lambda: set_status_safe("🎤 Ready", Theme.BG_ELEVATED, Theme.TEXT_PRIMARY, Theme.PINK_PRIMARY))
            pending_status_timer.start()
            safe_print("Copied to clipboard (dashboard focused)")
        else:
            # Use pyautogui for reliable paste (Win32 SendInput blocked by Windows security)
            if instant_paste(text):
                # Record stats async (don't block the paste experience)
                threading.Thread(target=stats_tracker.record_transcription, args=(text, model_used), daemon=True).start()
                set_status_safe("✅ Pasted!", Theme.SUCCESS, Theme.TEXT_PRIMARY, Theme.SUCCESS)
                pending_status_timer = threading.Timer(1.5, lambda: set_status_safe("🎤 Ready", Theme.BG_ELEVATED, Theme.TEXT_PRIMARY, Theme.PINK_PRIMARY))
                pending_status_timer.start()
                safe_print("Pasted OK")
            else:
                raise Exception("instant_paste failed")
    except Exception as e:
        safe_print(f"Paste error: {e}")
        # Fallback: at least copy to clipboard
        try:
            pyperclip.copy(text)
            threading.Thread(target=stats_tracker.record_transcription, args=(text, model_used), daemon=True).start()
            set_status_safe("📋 Copied!", Theme.WARNING, Theme.BG_DARK, Theme.WARNING)
            safe_print("Fallback: copied to clipboard")
        except Exception:
            set_status_safe("❌ Paste error", Theme.ERROR, Theme.TEXT_PRIMARY, Theme.ERROR)
    finally:
        # Clear the captured focus state to avoid stale data
        target_window_on_record_start = None


def stop_recording_and_transcribe():
    with STATE_LOCK:
        if not recording_flag.is_set() or transcribing_flag.is_set():
            return
        transcribing_flag.set()

    try:
        time.sleep(POSTROLL_SEC)
    except Exception:
        pass

    with STATE_LOCK:
        recording_flag.clear()

    if rec_thread:
        rec_thread.join()

    if not os.path.exists(WAV_TMP) or os.path.getsize(WAV_TMP) < 1024:
        try:
            if os.path.exists(WAV_TMP):
                os.remove(WAV_TMP)
        except Exception:
            pass
        # Skip slow toast - UI already shows status
        set_status_safe("🔇 No speech", Theme.WARNING, Theme.BG_DARK, Theme.WARNING)
        with STATE_LOCK:
            transcribing_flag.clear()
        return

    _transcribe_and_paste(WAV_TMP)

    with STATE_LOCK:
        transcribing_flag.clear()

def on_hotkey_press(e):
    if not recording_flag.is_set():
        start_recording()

def on_hotkey_release(e):
    if recording_flag.is_set():
        stop_recording_and_transcribe()


# --- Diagnostics ---
def self_test_jfk():
    # Try multiple locations for test sample
    sample_locations = [
        os.path.join("whisper.cpp", "samples", "jfk.wav"),  # Legacy location
        os.path.join(_app_dir, "samples", "jfk.wav"),  # Bundled location
        os.path.join(_bundle_dir, "samples", "jfk.wav"),  # PyInstaller location
        os.environ.get("WHISPER_TEST_SAMPLE"),  # Environment variable override
    ]
    
    sample = None
    for loc in sample_locations:
        if loc and os.path.exists(loc):
            sample = loc
            break
    
    if not sample:
        notify("Self-test sample not found. Set WHISPER_TEST_SAMPLE environment variable or place jfk.wav in samples/ directory.")
        return
    if resolved_whisper_bin is None and not os.path.exists(WHISPER_BIN):
        notify("No whisper binary available for self-test")
        return
    exe = os.path.abspath(_resolve_whisper_exe(resolved_whisper_bin or WHISPER_BIN))
    cmd = build_whisper_cmd(exe, MODEL_PATH, sample, base_args=["-nt"]) 
    log_line("[self-test] running: " + " ".join(cmd))
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=WHISPER_TIMEOUT_SEC, creationflags=CREATE_NO_WINDOW)
        out = (res.stdout or "").strip() or (res.stderr or "").strip()
        if out:
            notify("Self-test OK (see log)")
            log_line("[self-test-output]\n" + out)
        else:
            notify("Self-test produced no output")
    except Exception as e:
        notify(f"Self-test error: {e}")


def run_debug_probe():
    # Try multiple locations for test sample
    sample_locations = [
        os.path.join("whisper.cpp", "samples", "jfk.wav"),  # Legacy location
        os.path.join(_app_dir, "samples", "jfk.wav"),  # Bundled location
        os.path.join(_bundle_dir, "samples", "jfk.wav"),  # PyInstaller location
        os.environ.get("WHISPER_TEST_SAMPLE"),  # Environment variable override
    ]
    
    sample = None
    for loc in sample_locations:
        if loc and os.path.exists(loc):
            sample = loc
            break
    
    if not sample:
        notify("Debug: sample not found. Set WHISPER_TEST_SAMPLE environment variable or place jfk.wav in samples/ directory.")
        return
    candidates = []
    if os.path.exists(os.path.join(".", "main.exe")):
        candidates.append(os.path.join(".", "main.exe"))
    if os.path.exists(os.path.join(".", "whisper-cli.exe")):
        candidates.append(os.path.join(".", "whisper-cli.exe"))
    if not candidates:
        notify("Debug: no local main.exe or whisper-cli.exe found")
        return
    os.makedirs("debug", exist_ok=True)
    for bin_path in candidates:
        name = os.path.basename(bin_path)
        exe = os.path.abspath(_resolve_whisper_exe(bin_path))
        cmd = build_whisper_cmd(exe, MODEL_PATH, sample, base_args=["-nt"]) 
        log_line(f"[debug] running: {' '.join(cmd)}")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=WHISPER_TIMEOUT_SEC, creationflags=CREATE_NO_WINDOW)
            raw = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
            san = sanitize_transcript(raw)
            with open(os.path.join("debug", f"flow_debug_{name}_raw.txt"), "w", encoding="utf-8") as f:
                f.write(raw)
            with open(os.path.join("debug", f"flow_debug_{name}_sanitized.txt"), "w", encoding="utf-8") as f:
                f.write(san)
            banner_present = ("deprecated" in raw.lower()) or ("please use" in raw.lower())
            log_line(f"[debug] {name}: rc={res.returncode} banner={'yes' if banner_present else 'no'}; files in ./debug/")
        except Exception as e:
            log_line(f"[debug] error running {name}: {e}")
    notify("Debug probe complete (see ./debug and log)")

tray_icon = None
listening_enabled = True

def _tray_update(title="Whisper Local", text="Idle"):
    try:
        if tray_icon:
            tray_icon.title = f"{title} — {text}"
    except Exception:
        pass

def _tray_toggle(_=None):
    global listening_enabled
    listening_enabled = not listening_enabled
    _tray_update(text=("Listening" if listening_enabled else "Paused"))

def _tray_selftest(_=None):
    try:
        self_test_jfk()
    except Exception as e:
        safe_print(f"Self-test error: {e}")

def _tray_debug(_=None):
    try:
        run_debug_probe()
    except Exception as e:
        safe_print(f"Debug error: {e}")

def _tray_open_dashboard(_=None):
    """Open dashboard from tray - thread-safe version."""
    global dashboard_window
    
    def _open_dashboard_main_thread():
        """Actually create/show dashboard - must run on main thread."""
        global dashboard_window
        try:
            if dashboard_window is None or not dashboard_window.winfo_exists():
                dashboard_window = DashboardWindow(gui.root)
            else:
                dashboard_window.lift()
                dashboard_window.focus_force()
        except Exception as e:
            safe_print(f"Dashboard error: {e}")
    
    try:
        if gui and gui.root:
            # Use ui_queue to marshal to main thread (same pattern as set_status_safe)
            ui_queue.put((_open_dashboard_main_thread, ()))
    except Exception as e:
        safe_print(f"Dashboard queue error: {e}")

def _tray_quit(_=None):
    log_line("[TRAY] User selected Quit from tray menu")
    try:
        if recording_flag.is_set():
            stop_recording_and_transcribe()
        # Stop GPU monitoring
        gpu_monitor.stop_monitoring()
    finally:
        os._exit(0)

def _tray_restart_gui(_=None):
    """Restart the GUI window without killing the whole application."""
    log_line("[TRAY] User selected Restart GUI from tray menu")
    notify("Restarting GUI...")
    
    def restart_gui_thread():
        global gui
        try:
            # Destroy old GUI if it exists
            try:
                if gui and gui.root:
                    gui.root.destroy()
            except:
                pass
            
            time.sleep(0.5)  # Brief pause before recreating
            
            # Create new GUI on main thread via queue
            def create_new_gui():
                global gui
                try:
                    gui = FloatingPill()
                    gui.set_status("ready")
                    log_line("[GUI_RESTART] New GUI created successfully")
                    notify("✅ GUI restarted! Hold WIN + CTRL to speak.")
                except Exception as e:
                    log_line(f"[GUI_RESTART_ERROR] Failed to create new GUI: {e}\n{traceback.format_exc()}", "error")
                    notify(f"❌ Failed to restart GUI: {e}")
            
            ui_queue.put((create_new_gui, ()))
        except Exception as e:
            log_line(f"[GUI_RESTART_ERROR] {e}\n{traceback.format_exc()}", "error")
    
    threading.Thread(target=restart_gui_thread, daemon=True).start()

def start_tray():
    global tray_icon
    icon_path = res_path("whisper.ico")
    try:
        img = Image.open(icon_path)
    except Exception:
        # Create a simple pink circle icon
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, 28, 28], fill=(255, 20, 147, 255))
    
    tray_icon = pystray.Icon(
        "Whisper Local",
        img,
        "Whisper Local",
        menu=pystray.Menu(
            pystray.MenuItem("Open Dashboard", _tray_open_dashboard, default=True),
            pystray.MenuItem("Toggle Listening", _tray_toggle),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Restart GUI", _tray_restart_gui),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Self-test (JFK)", _tray_selftest),
            pystray.MenuItem("Run Debug Probe", _tray_debug),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", _tray_quit)
        )
    )
    tray_icon.run_detached()
    _tray_update(text="Listening")

def main():
    safe_print("=" * 60)
    safe_print(f"◉ {APP_NAME} v{APP_VERSION}")
    safe_print("=" * 60)
    safe_print("📌 Controls:")
    safe_print("  • Hold WIN + CTRL to record")
    safe_print("  • Release to transcribe & paste")
    safe_print("  • Click floating pill to open dashboard")
    safe_print("  • WIN + CTRL + S for settings")
    safe_print("  • ESC to exit")
    safe_print("=" * 60)
    
    # Check for first run and show setup wizard
    if is_first_run():
        safe_print("First run detected - showing setup wizard...")
        try:
            from first_run_wizard import show_first_run_wizard
            
            # Show wizard before starting main app
            wizard_complete = threading.Event()
            
            def on_wizard_complete():
                wizard_complete.set()
            
            # Run wizard in main thread (tkinter requirement)
            show_first_run_wizard(on_complete=on_wizard_complete)
            
            safe_print("Setup wizard completed!")
        except ImportError as e:
            safe_print(f"Could not load wizard (running in dev mode?): {e}")
            mark_first_run_complete()
        except Exception as e:
            safe_print(f"Wizard error: {e}")
            mark_first_run_complete()
    
    global gui
    gui = FloatingPill()
    gui.set_status("ready")
    
    startup_diagnostics()
    
    # Start GPU monitoring in background
    safe_print("🔍 Starting GPU monitoring...")
    gpu_monitor.start_monitoring()
    
    # Start CUDA warmup in background (pre-load GPU model for instant first transcription)
    threading.Thread(target=cuda_warmup, daemon=True).start()
    
    try:
        device_lines = devices_summary_text()
        notify("✅ Ready! Hold WIN + CTRL to speak.")
        log_line("Startup devices:\n" + device_lines)
        safe_print(f"✅ Microphone: {selected_input_device_name}")
        
        # Show GPU/CPU mode and model selection strategy with load awareness
        gpu_vendor = gpu_monitor.get_gpu_vendor()
        is_nvidia = gpu_monitor.is_nvidia_gpu()
        
        if GPU_AVAILABLE and is_nvidia:
            gpu_status = gpu_monitor.get_load_status_text()
            safe_print(f"✅ GPU acceleration: ENABLED - {gpu_status}")
            safe_print(f"✅ Dynamic model selection (load-aware):")
            safe_print(f"   • GPU idle/low load:")
            safe_print(f"     - <{WORD_THRESHOLD_BASE} words → base.en (fastest)")
            safe_print(f"     - {WORD_THRESHOLD_BASE}-{WORD_THRESHOLD_MEDIUM} words → medium.en")
            safe_print(f"     - {WORD_THRESHOLD_MEDIUM}+ words → large-v3 (best quality)")
            safe_print(f"   • GPU busy (70%+ load): Skip large-v3, use base/medium only")
            safe_print(f"   • GPU critical (85%+ load): Base.en only for speed")
            safe_print("🔥 CUDA warmup running in background...")
            safe_print("📊 GPU load monitoring: ACTIVE")
        elif GPU_AVAILABLE and not is_nvidia:
            safe_print(f"✅ Non-NVIDIA GPU detected: {gpu_vendor.upper()}")
            safe_print(f"✅ Smart model selection (compatibility-optimized):")
            safe_print(f"   • <50 words → base.en (fast)")
            safe_print(f"   • 50+ words → medium.en (balanced)")
            safe_print(f"   • Large-v3 disabled (poor non-NVIDIA compatibility)")
        else:
            safe_print("✅ Running in CPU mode (speed-optimized)")
            safe_print(f"✅ Smart model selection (CPU-optimized):")
            safe_print(f"   • <50 words → base.en (fast)")
            safe_print(f"   • 50+ words → medium.en (balanced)")
            safe_print(f"   • Large-v3 disabled for performance")
        
        safe_print(f"✅ Whisper binary: {resolved_whisper_bin}")
        safe_print("=" * 60)
    except Exception:
        pass

    was_down = False
    
    # Health monitoring state
    health_check_count = [0]
    last_gui_response_time = [time.time()]
    keyboard_health_failures = [0]
    
    def health_check():
        """Periodic health check to detect GUI and keyboard library issues."""
        health_check_count[0] += 1
        issues = []
        
        # Check keyboard library health
        try:
            # Try to query keyboard state - this will fail if library is in bad state
            _ = keyboard.is_pressed("shift")
            keyboard_health_failures[0] = 0
        except Exception as e:
            keyboard_health_failures[0] += 1
            issues.append(f"keyboard library error: {e}")
        
        # Check if GUI is responsive (root window exists and is mapped)
        try:
            if gui.root.winfo_exists():
                gui.root.update_idletasks()  # Force process pending events
                last_gui_response_time[0] = time.time()
            else:
                issues.append("GUI root window does not exist")
        except tk.TclError as e:
            issues.append(f"GUI TclError: {e}")
        except Exception as e:
            issues.append(f"GUI error: {e}")
        
        # Log health status every 10 checks (5 minutes) or immediately on issues
        if issues:
            log_line(f"[HEALTH_CHECK #{health_check_count[0]}] ISSUES DETECTED: {', '.join(issues)}", "warning")
        elif health_check_count[0] % 10 == 0:
            uptime_min = (time.time() - last_gui_response_time[0]) / 60
            log_line(f"[HEALTH_CHECK #{health_check_count[0]}] OK - keyboard_fails={keyboard_health_failures[0]}, gui_responsive=True")
        
        # Warn if keyboard library has repeated failures
        if keyboard_health_failures[0] >= 3:
            log_line(f"[HEALTH_WARNING] Keyboard library has failed {keyboard_health_failures[0]} consecutive checks - consider restarting", "warning")
            notify("⚠️ Keyboard detection may be unreliable. Consider restarting the app.")
        
        # Schedule next health check (every 30 seconds)
        try:
            gui.root.after(30000, health_check)
        except:
            pass  # GUI may have been destroyed
    
    # Start health monitoring after a short delay
    gui.root.after(5000, health_check)

    # Wrapped debug hotkey handlers with logging
    def _safe_self_test_jfk(e=None):
        log_line("[HOTKEY] F8/Ctrl+Alt+J pressed - starting self_test_jfk")
        try:
            self_test_jfk()
        except Exception as ex:
            log_line(f"[HOTKEY_ERROR] self_test_jfk failed: {ex}\n{traceback.format_exc()}", "error")
    
    def _safe_run_debug_probe(e=None):
        log_line("[HOTKEY] F9/Ctrl+Alt+D pressed - starting run_debug_probe")
        try:
            run_debug_probe()
        except Exception as ex:
            log_line(f"[HOTKEY_ERROR] run_debug_probe failed: {ex}\n{traceback.format_exc()}", "error")
    
    keyboard.on_press_key("f8", lambda e: threading.Thread(target=_safe_self_test_jfk, daemon=True).start())
    keyboard.on_press_key("f9", lambda e: threading.Thread(target=_safe_run_debug_probe, daemon=True).start())
    keyboard.add_hotkey("ctrl+alt+j", lambda: threading.Thread(target=_safe_self_test_jfk, daemon=True).start())
    keyboard.add_hotkey("ctrl+alt+d", lambda: threading.Thread(target=_safe_run_debug_probe, daemon=True).start())
    keyboard.add_hotkey("ctrl+alt+b", lambda: set_bullet_next())

    # Track ESC key state for debouncing
    esc_pressed_start = [None]  # Use list for nonlocal mutation
    last_keyboard_check_error = [0]  # Track keyboard library errors
    keyboard_error_count = [0]  # Count consecutive errors

    def poll_hotkey():
        nonlocal was_down
        global last_edge_ts
        
        # Check for keyboard library issues
        try:
            down = listening_enabled and keyboard.is_pressed("ctrl") and keyboard.is_pressed("shift")
            keyboard_error_count[0] = 0  # Reset error count on success
        except Exception as e:
            down = False
            keyboard_error_count[0] += 1
            now = time.time()
            # Log keyboard errors, but rate-limit to avoid spam
            if now - last_keyboard_check_error[0] > 30:  # Log at most every 30 seconds
                log_line(f"[KEYBOARD_ERROR] is_pressed failed (count={keyboard_error_count[0]}): {e}", "warning")
                last_keyboard_check_error[0] = now
        
        try:
            if (keyboard.is_pressed("ctrl") and keyboard.is_pressed("shift") and keyboard.is_pressed("s")):
                open_settings_window(gui.root)
        except Exception:
            pass
        
        now = time.time()
        if down and not was_down and (now - last_edge_ts) * 1000 > EDGE_COOLDOWN_MS:
            last_edge_ts = now
            on_hotkey_press(None)
        if (not down) and was_down and (now - last_edge_ts) * 1000 > EDGE_COOLDOWN_MS:
            last_edge_ts = now
            threading.Thread(target=stop_recording_and_transcribe, daemon=True).start()
        was_down = down
        
        # Debounced ESC detection - require 500ms hold to prevent accidental exit
        try:
            esc_is_pressed = keyboard.is_pressed("esc")
            if esc_is_pressed:
                if esc_pressed_start[0] is None:
                    esc_pressed_start[0] = time.time()
                    log_line("[ESC] ESC key pressed - waiting for 500ms hold confirmation")
                elif time.time() - esc_pressed_start[0] >= 0.5:
                    log_line("[ESC] ESC held for 500ms - user confirmed exit")
                    gui.root.destroy()
                    return
            else:
                if esc_pressed_start[0] is not None:
                    hold_duration = time.time() - esc_pressed_start[0]
                    if hold_duration > 0.1:  # Only log if it was a real press, not a glitch
                        log_line(f"[ESC] ESC released after {hold_duration:.2f}s (not long enough to exit)")
                esc_pressed_start[0] = None
        except Exception as e:
            log_line(f"[KEYBOARD_ERROR] ESC check failed: {e}", "warning")
            esc_pressed_start[0] = None  # Reset on error to prevent false exits
        
        gui.root.after(10, poll_hotkey)

    gui.pump_queue()
    gui.root.after(10, poll_hotkey)
    
    log_line("[MAINLOOP] Entering mainloop")
    mainloop_exit_reason = "unknown"
    
    try:
        gui.root.mainloop()
        mainloop_exit_reason = "normal"
    except tk.TclError as e:
        mainloop_exit_reason = f"TclError: {e}"
        log_line(f"[MAINLOOP_TCLERROR] {e}", "error")
    except Exception as e:
        mainloop_exit_reason = f"Exception: {e}"
        log_line(f"[MAINLOOP_EXCEPTION] {e}\n{traceback.format_exc()}", "error")
    finally:
        # Log diagnostic info on exit
        try:
            esc_state = keyboard.is_pressed("esc")
        except:
            esc_state = "error"
        log_line(f"[MAINLOOP_EXIT] Reason: {mainloop_exit_reason}, ESC state: {esc_state}, keyboard_errors: {keyboard_error_count[0]}")
        
        # Notify user if GUI closed unexpectedly (not from ESC key)
        if mainloop_exit_reason != "normal" or (esc_state != True and esc_state != "error"):
            try:
                notify("⚠️ GUI closed. Right-click tray icon → 'Restart GUI' to restore.")
            except:
                pass
    
    if recording_flag.is_set():
        stop_recording_and_transcribe()
    safe_print("Bye.")

if __name__ == "__main__":
    _acquire_single_instance()  # Acquire singleton lock only when running directly
    start_tray()
    main()
