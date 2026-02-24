import os, subprocess, time, threading, queue, datetime, shlex, hashlib
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
        # Allow direct module execution for local debugging.
        pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if pkg_root not in sys.path:
            sys.path.insert(0, pkg_root)
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
import winsound

# Import HTML dashboard host
from whisper_local.ui.gui_host import DashboardAPI, open_dashboard
from whisper_local.agent.router import VoiceAgentRouter
from whisper_local.processing.code_mode import CodeModeCorrector
from whisper_local.processing.final_sanitizer import sanitize_final_glitches
from whisper_local.model_selection import (
    apply_mode as apply_model_mode,
    load_state as load_model_selection_state,
    model_selection_file,
    refresh_auto_state,
    save_state as save_model_selection_state,
)
from whisper_local.settings_manager import SettingsManager
from whisper_local.hotkey_settings import hotkey_tokens, load_hotkey, settings_file
from whisper_local.snippets import apply_snippets, snippets_file
from whisper_local.vocabulary import compose_prompt, load_vocabulary, save_vocabulary, vocabulary_file
from whisper_local.audio_ducking import AudioDuckingSessionManager

# ============================================================================
# DEBUG MODE DETECTION
# ============================================================================
def _is_debug_mode():
    """
    Detect if running in debug mode (console visible).
    Returns True if running with python.exe (console attached)
    Returns False if running with pythonw.exe (no console)
    """
    try:
        # Check if stdout is connected to a real console
        import msvcrt
        # If we can get a console handle, we're in debug mode
        return sys.stdout is not None and hasattr(sys.stdout, 'fileno')
    except (ImportError, AttributeError, OSError):
        return False

# Global debug mode flag
DEBUG_MODE = _is_debug_mode()

def debug_print(*args, **kwargs):
    """
    Print only when running in debug mode.
    Silently ignores output when running with pythonw.exe (silent mode).
    """
    if DEBUG_MODE:
        try:
            print(*args, **kwargs)
            sys.stdout.flush()  # Force immediate output
        except (OSError, AttributeError):
            pass  # Silently fail if no console

# ============================================================================
# SOUND EFFECTS
# ============================================================================
# Path to the message-send sound effect
_SOUND_EFFECT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "message-send.mp3")
_pygame_mixer_initialized = False

def play_recording_stop_sound():
    """Play a satisfying sound when recording stops to give audio feedback.

    Uses a custom MP3 sound file played at low volume for a subtle notification.
    Runs in a separate thread to avoid blocking the main flow.
    """
    global _pygame_mixer_initialized

    def _play():
        global _pygame_mixer_initialized
        try:
            import pygame

            # Initialize mixer once (with smaller buffer for lower latency)
            if not _pygame_mixer_initialized:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
                _pygame_mixer_initialized = True

            # Load and play the sound at low volume
            if os.path.exists(_SOUND_EFFECT_PATH):
                pygame.mixer.music.load(_SOUND_EFFECT_PATH)
                pygame.mixer.music.set_volume(0.15)  # 15% volume - subtle but audible
                pygame.mixer.music.play()
            else:
                # Fallback to simple beep if file not found
                winsound.Beep(880, 80)

        except ImportError:
            # pygame not installed - use fallback beeps
            try:
                winsound.Beep(523, 60)
                winsound.Beep(659, 60)
                winsound.Beep(784, 60)
                winsound.Beep(1047, 100)
            except Exception:
                pass
        except Exception:
            pass  # Silently fail if sound cannot be played

    # Run in background thread to avoid blocking
    threading.Thread(target=_play, daemon=True).start()

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
    Detect Windows DPI scaling factor and apply moderate scaling.
    Uses a square root curve to prevent excessive scaling at high DPI.
    Returns a moderate scale factor appropriate for tkinter UI.
    """
    try:
        # Get the DPI for the system (primary monitor) WITHOUT setting DPI awareness
        # Setting DPI awareness too early can interfere with keyboard hooks
        # We'll set it later when creating windows
        try:
            # Try to get DPI without setting awareness first (may not work on all Windows versions)
            dpi = ctypes.windll.user32.GetDpiForSystem()
        except (AttributeError, OSError):
            # Fallback: try with DPI awareness (but catch any errors)
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
                dpi = ctypes.windll.user32.GetDpiForSystem()
            except (AttributeError, OSError):
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                    dpi = ctypes.windll.user32.GetDpiForSystem()
                except (AttributeError, OSError):
                    # If all else fails, assume 96 DPI (100%)
                    return 1.0
        
        raw_scale = dpi / 96.0
        
        # Apply conservative scaling to keep UI readable without being too large
        # At high DPI, Windows handles much of the scaling, so we only add a small boost
        # At 150%: use 1.1x scaling
        # At 200%: use 1.15x scaling  
        # At 250%: use 1.2x scaling (more conservative for readability)
        # This keeps UI proportional and readable
        if raw_scale <= 1.0:
            scale = 1.0
        elif raw_scale <= 1.25:
            scale = 1.05  # 125% DPI → 1.05x scaling
        elif raw_scale <= 1.5:
            scale = 1.1  # 150% DPI → 1.1x scaling
        elif raw_scale <= 1.75:
            scale = 1.15  # 175% DPI → 1.15x scaling
        elif raw_scale <= 2.0:
            scale = 1.15  # 200% DPI → 1.15x scaling
        elif raw_scale <= 2.5:
            scale = 1.2  # 250% DPI → 1.2x scaling (more conservative)
        elif raw_scale <= 3.0:
            scale = 1.25  # 300% DPI → 1.25x scaling
        else:
            scale = 1.3  # 350%+ DPI → 1.3x scaling (max, very conservative)
        
        return scale
    except Exception:
        # Fallback to 1.0 if anything fails
        return 1.0

# Initialize DPI scale factor globally (called once at startup)
# Note: We don't set DPI awareness here to avoid interfering with keyboard hooks
DPI_SCALE = get_dpi_scale_factor()

def set_dpi_awareness():
    """Set DPI awareness when creating windows (call this before creating tkinter windows)."""
    try:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except (AttributeError, OSError):
                pass
    except Exception:
        pass

def scaled(value):
    """Scale a dimension value by the moderate DPI factor."""
    return int(value * DPI_SCALE)

def scaled_font(size):
    """Scale a font size by the moderate DPI factor."""
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
DUCKING_RESTORE_DELAY_MS = 90  # Debounce restore to avoid volume flicker on rapid taps
HUD_BACKEND_REQUESTED = os.environ.get("WHISPER_HUD_BACKEND", "ambient").strip().lower()

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
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_app_dir():
    """Get the application directory (where the exe is located, or script dir in dev)."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_user_data_dir():
    """Get the user data directory for config, logs, and temp files."""
    if is_frozen():
        # Use AppData/Local for user-specific data
        appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        data_dir = os.path.join(appdata, APP_NAME)
        os.makedirs(data_dir, exist_ok=True)
        debug_print(f"[DEBUG] get_user_data_dir (flow_local_dictation.py): {data_dir}")
        return data_dir
    result = os.path.join(get_app_dir(), "output")
    for rel in ("logs", "audio", "transcripts", "state"):
        os.makedirs(os.path.join(result, rel), exist_ok=True)
    debug_print(f"[DEBUG] get_user_data_dir (flow_local_dictation.py): {result}")
    return result

def get_config_file():
    """Get the path to the config file."""
    return os.path.join(get_user_data_dir(), "state", "config.json")

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
    log_file = os.path.join(get_user_data_dir(), "logs", "flow.log")
    
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
    # Floating status panel stays compact but readable at a glance.
    PILL_WIDTH = 320
    PILL_HEIGHT = 74
    PILL_RADIUS = 16
    
    DASHBOARD_WIDTH = scaled(420)
    DASHBOARD_HEIGHT = scaled(750)  # Height breakdown: Title(40) + Stats(106) + Streak(96) + Goals(96) + Graph(150) + Recent(160) + Actions(60) + Padding(42) = ~750px
    
    SETTINGS_WIDTH = scaled(480)
    SETTINGS_HEIGHT = scaled(460)
    
    WIZARD_WIDTH = scaled(600)
    WIZARD_HEIGHT = scaled(500)
    
    TITLE_BAR_HEIGHT = scaled(40)
    
    # Scaled font sizes
    FONT_SIZE_XXS = scaled_font(8)   # Extra extra small for subtle text
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
STATS_FILE = os.path.join(get_user_data_dir(), "state", "whisper_stats.json")

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
from whisper_local.stats import StatsTracker as NewStatsTracker
stats_tracker = NewStatsTracker()
debug_print(f"[DEBUG] Stats tracker initialized with file: {stats_tracker.stats_file}")

# Global session tracking (tracks words at app start, not dashboard open)
app_session_start_words = stats_tracker.data.get('total_words', 0)
debug_print(f"[SESSION] App started with {app_session_start_words} total words")

# Achievement tracking
achievement_api = DashboardAPI()
debug_print(f"[DEBUG] Achievement tracker initialized")


# ============================================================================
# ACHIEVEMENT DETECTION
# ============================================================================
def check_achievements(text, word_count, wpm, stats):
    """Check and unlock achievements based on transcription data.

    Args:
        text: The transcribed text
        word_count: Number of words in this transcription
        wpm: Words per minute (0 if not calculated)
        stats: Stats summary dict from stats_tracker

    Returns:
        List of newly unlocked achievement IDs
    """
    newly_unlocked = []

    try:
        # Get currently unlocked achievements
        unlocked = set(achievement_api.get_achievements())

        # Today's word count milestones
        today_words = stats.get('today_words', 0)

        if today_words >= 100 and 'daily_100' not in unlocked:
            if achievement_api.unlock_achievement('daily_100'):
                newly_unlocked.append('daily_100')
                debug_print("[ACHIEVEMENT] Unlocked: Daily 100 (100 words today)")

        if today_words >= 500 and 'daily_500' not in unlocked:
            if achievement_api.unlock_achievement('daily_500'):
                newly_unlocked.append('daily_500')
                debug_print("[ACHIEVEMENT] Unlocked: Daily 500 (500 words today)")

        if today_words >= 1000 and 'daily_1000' not in unlocked:
            if achievement_api.unlock_achievement('daily_1000'):
                newly_unlocked.append('daily_1000')
                debug_print("[ACHIEVEMENT] Unlocked: Daily 1000 (1000 words today)")

        # Speed milestones (WPM)
        if wpm > 0:
            if wpm >= 100 and 'speed_100' not in unlocked:
                if achievement_api.unlock_achievement('speed_100'):
                    newly_unlocked.append('speed_100')
                    debug_print(f"[ACHIEVEMENT] Unlocked: Speedster (100+ WPM, achieved {wpm} WPM)")

            if wpm >= 120 and 'speed_120' not in unlocked:
                if achievement_api.unlock_achievement('speed_120'):
                    newly_unlocked.append('speed_120')
                    debug_print(f"[ACHIEVEMENT] Unlocked: Quick Draw (120+ WPM, achieved {wpm} WPM)")

            if wpm >= 150 and 'speed_150' not in unlocked:
                if achievement_api.unlock_achievement('speed_150'):
                    newly_unlocked.append('speed_150')
                    debug_print(f"[ACHIEVEMENT] Unlocked: Lightning Fast (150+ WPM, achieved {wpm} WPM)")

        # Secret phrase achievements (case-insensitive)
        text_lower = text.lower()

        if 'hello world' in text_lower and 'secret_hello_world' not in unlocked:
            if achievement_api.unlock_achievement('secret_hello_world'):
                newly_unlocked.append('secret_hello_world')
                debug_print("[ACHIEVEMENT] Unlocked: Hello World (said the magic words)")

        if 'may the force' in text_lower and 'secret_force' not in unlocked:
            if achievement_api.unlock_achievement('secret_force'):
                newly_unlocked.append('secret_force')
                debug_print("[ACHIEVEMENT] Unlocked: Force User (May the Force be with you)")

        if 'testing' in text_lower and 'secret_testing' not in unlocked:
            if achievement_api.unlock_achievement('secret_testing'):
                newly_unlocked.append('secret_testing')
                debug_print("[ACHIEVEMENT] Unlocked: Quality Assurance (testing, testing...)")

        if 'whisper' in text_lower and 'secret_whisper' not in unlocked:
            if achievement_api.unlock_achievement('secret_whisper'):
                newly_unlocked.append('secret_whisper')
                debug_print("[ACHIEVEMENT] Unlocked: Meta (said 'whisper')")

        # Streak achievements
        streak = stats.get('streak', 0)
        if streak >= 7 and 'streak_7' not in unlocked:
            if achievement_api.unlock_achievement('streak_7'):
                newly_unlocked.append('streak_7')
                debug_print(f"[ACHIEVEMENT] Unlocked: Week Warrior ({streak} day streak)")

        if streak >= 30 and 'streak_30' not in unlocked:
            if achievement_api.unlock_achievement('streak_30'):
                newly_unlocked.append('streak_30')
                debug_print(f"[ACHIEVEMENT] Unlocked: Consistency King ({streak} day streak)")

        # Total words milestones
        total_words = stats.get('total_words', 0)

        if total_words >= 1000 and 'total_1k' not in unlocked:
            if achievement_api.unlock_achievement('total_1k'):
                newly_unlocked.append('total_1k')
                debug_print(f"[ACHIEVEMENT] Unlocked: 1K Club ({total_words} total words)")

        if total_words >= 10000 and 'total_10k' not in unlocked:
            if achievement_api.unlock_achievement('total_10k'):
                newly_unlocked.append('total_10k')
                debug_print(f"[ACHIEVEMENT] Unlocked: 10K Master ({total_words} total words)")

        if total_words >= 50000 and 'total_50k' not in unlocked:
            if achievement_api.unlock_achievement('total_50k'):
                newly_unlocked.append('total_50k')
                debug_print(f"[ACHIEVEMENT] Unlocked: Wordsmith ({total_words} total words)")

    except Exception as e:
        debug_print(f"[ACHIEVEMENT] Error checking achievements: {e}")

    return newly_unlocked


# Enable CUDA by default unless explicitly disabled via environment
os.environ.setdefault("GGML_CUDA_ENABLE", "1")

# ============================================================================
# PATH RESOLUTION FOR BUNDLED AND DEV ENVIRONMENTS
# ============================================================================
# Get directories based on whether we're running bundled or in dev
_bundle_dir = get_bundle_dir()  # Where bundled resources are (models, DLLs)
_app_dir = get_app_dir()        # Where the exe/script is located
_user_dir = get_user_data_dir() # User-writable directory for logs, temp files
AUDIO_DUCK_STATE_FILE = os.path.join(_user_dir, "state", "audio_duck_state.json")

# Auto-detect whisper binary - check runtime/bin first, then bundle/app dirs
_runtime_bin_dir = os.path.join(_app_dir, "runtime", "bin")
_default_bin = os.path.join(_runtime_bin_dir, "whisper-cli.exe")
if not os.path.isfile(_default_bin):
    _default_bin = os.path.join(_runtime_bin_dir, "main.exe")
if not os.path.isfile(_default_bin):
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
    user_token = os.environ.get("USERNAME") or os.environ.get("USER") or "default_user"
    user_token = re.sub(r"[^a-zA-Z0-9_.-]", "_", user_token)
    lock_dir = os.path.join(tempfile.gettempdir(), APP_NAME.lower(), user_token)
    os.makedirs(lock_dir, exist_ok=True)
    _SINGLETON_LOCK_PATH = os.path.join(lock_dir, "dictation.lock")
    _SINGLETON_LOCK = open(_SINGLETON_LOCK_PATH, "w")
    try:
        msvcrt.locking(_SINGLETON_LOCK.fileno(), msvcrt.LK_NBLCK, 1)
        # Register cleanup handler to release lock on exit
        atexit.register(_release_single_instance)
    except OSError:
        _SINGLETON_LOCK.close()
        _SINGLETON_LOCK = None
        print("Already running. Opening dashboard.")
        try:
            open_dashboard()
        except Exception:
            pass
        sys.exit(0)

# Singleton lock is now acquired in __main__ block instead of at module level
# to prevent conflicts when this module is imported by first_run_wizard

# --- Config ---
# Model paths for dynamic selection based on word count (relative paths)
MODEL_BASE = os.path.join("runtime", "models", "ggml-base.en.bin")
MODEL_MEDIUM = os.path.join("runtime", "models", "ggml-medium.en.bin")
MODEL_LARGE = os.path.join("runtime", "models", "ggml-large-v3.bin")

# Word count thresholds - using centralized constants
WORD_THRESHOLD_BASE = WORD_THRESHOLD_FAST
WORD_THRESHOLD_MEDIUM = WORD_THRESHOLD_BALANCED

# Legacy default (will be dynamically selected)
MODEL_PATH_REL = MODEL_LARGE  # fallback if dynamic selection fails
WHISPER_BIN = os.environ.get("WHISPER_BIN") or os.path.join("runtime", "bin", "whisper-cli.exe")

# Audio settings - using centralized constants
SAMPLE_RATE = SAMPLE_RATE_HZ
CHANNELS = AUDIO_CHANNELS

# Use user data directory for temp files (writable location)
WAV_TMP = os.path.join(_user_dir, "audio", "flow_input.wav")
TEXT_TMP_BASE = os.path.join(_user_dir, "transcripts", "flow_out")  # base name for whisper-cli text output

SETTINGS_FILE = settings_file(_user_dir)
HOTKEY_HOLD = load_hotkey(SETTINGS_FILE)  # hold to talk; release to transcribe
HOTKEY_KEYS = hotkey_tokens(HOTKEY_HOLD)
NOTIFY = True

# --- Text Post-Processing Modes ---
# Smart, offline-only post-processing toggles
MODE_FILLER = True
MODE_PUNCT = True
MODE_BULLET_NEXT = False  # one-shot list maker (also triggered by keywords)
MODE_ROUTER = os.environ.get("WHISPER_ROUTER_MODE", "0").strip().lower() in ("1", "true", "yes", "on")
ROUTER_MODEL = os.environ.get("WHISPER_ROUTER_MODEL", "llama3:8b")
try:
    ROUTER_TIMEOUT_SEC = max(3, int(os.environ.get("WHISPER_ROUTER_TIMEOUT_SEC", "12")))
except ValueError:
    ROUTER_TIMEOUT_SEC = 12
STYLIZATION_PROFILE = os.environ.get("WHISPER_STYLIZE_PROFILE", "clean").strip().lower()
OLLAMA_MODEL = os.environ.get("WHISPER_OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_ENDPOINT = os.environ.get("WHISPER_OLLAMA_ENDPOINT", "http://127.0.0.1:11434")
_flow_settings_mgr = None  # lazy SettingsManager for runtime setting reads


def _get_stylization_profile() -> str:
    """Return the active stylization profile from settings or env var."""
    global _flow_settings_mgr
    if STYLIZATION_PROFILE not in ("off", "clean"):
        return STYLIZATION_PROFILE
    try:
        if _flow_settings_mgr is None:
            from whisper_local.settings_manager import SettingsManager
            _flow_settings_mgr = SettingsManager()
        _flow_settings_mgr.reload()
        return str(_flow_settings_mgr.get_setting("stylization_profile") or "off")
    except Exception:
        return "off"

# --- Vocabulary Biasing (Section 3) ---
# The hardcoded dictionary was migrated to continual_context.json
BASE_INITIAL_PROMPT = ""
INITIAL_PROMPT = ""  # Legacy alias for compatibility.
VOCABULARY_FILE = vocabulary_file(_user_dir)
if not os.path.exists(VOCABULARY_FILE):
    save_vocabulary(VOCABULARY_FILE, [])
SNIPPETS_FILE = snippets_file(_user_dir)

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
LOG_FILE = os.path.join(_user_dir, "logs", "flow.log")

# Whisper binary detection candidates (check bundle dir, app dir, and current directory)
WHISPER_CANDIDATES = [
    os.path.join(_runtime_bin_dir, "whisper-cli.exe"),
    os.path.join(_runtime_bin_dir, "main.exe"),
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

# Legacy dashboard reference kept for compatibility with older tests.
dashboard_window = None

# Shared dashboard launcher used by tray and pill actions.
def _launch_dashboard_from_ui_trigger() -> None:
    try:
        threading.Thread(target=open_dashboard, daemon=True).start()
    except Exception as e:
        safe_print(f"Dashboard error: {e}")

# Last transcription for easy copy access
last_transcription = None
voice_router = None
transcript_action_handler = None

# Focus state captured at recording start (for reliable paste targeting)
target_window_on_record_start = None

# Context awareness - tracks active application type
active_app_context = None

# Timer reference for canceling pending status resets
pending_status_timer = None


def _are_all_keys_pressed(keys) -> bool:
    """Return True only when every key in the sequence is currently pressed."""
    return all(keyboard.is_pressed(k) for k in keys)


def _settings_mtime(path: str) -> float:
    """Best-effort file mtime for hotkey settings change detection."""
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def _hotkey_display_text(hotkey_value: str) -> str:
    """Render a persisted hotkey value as readable key labels."""
    label_map = {
        "ctrl": "CTRL",
        "alt": "ALT",
        "shift": "SHIFT",
        "windows": "WIN",
        "space": "SPACE",
        "esc": "ESC",
        "enter": "ENTER",
        "tab": "TAB",
    }
    tokens = hotkey_tokens(hotkey_value) or []
    if not tokens:
        return "CTRL + WIN"
    pretty = []
    for token in tokens:
        if token in label_map:
            pretty.append(label_map[token])
        elif re.fullmatch(r"f([1-9]|1[0-9]|2[0-4])", token):
            pretty.append(token.upper())
        elif len(token) == 1:
            pretty.append(token.upper())
        else:
            pretty.append(token.replace("_", " ").upper())
    return " + ".join(pretty)


# ============================================================================
# CONTEXT AWARENESS - Detect active application for smart formatting
# ============================================================================
class AppContext:
    """Stores context about the active application for smart text formatting."""

    # Application type categories
    CODE_EDITOR = "code_editor"
    MESSAGING = "messaging"
    EMAIL = "email"
    DOCUMENT = "document"
    TERMINAL = "terminal"
    BROWSER = "browser"
    GENERAL = "general"

    # Window title/class patterns for detection
    CODE_EDITORS = [
        "visual studio code", "vscode", "code.exe",
        "sublime text", "sublime_text",
        "notepad++", "notepad plus",
        "atom", "brackets",
        "pycharm", "intellij", "webstorm", "phpstorm", "rider",
        "cursor", "windsurf", "replit",
        "vim", "neovim", "nvim",
        "emacs",
        "android studio",
        "eclipse",
    ]

    MESSAGING_APPS = [
        "slack", "teams", "microsoft teams",
        "discord", "telegram", "whatsapp",
        "signal", "messenger", "skype",
        "zoom chat", "webex",
    ]

    EMAIL_APPS = [
        "outlook", "gmail", "mail",
        "thunderbird", "mailbird",
        "protonmail", "hey",
    ]

    DOCUMENT_APPS = [
        "word", "winword", "google docs",
        "libreoffice writer", "pages",
        "notion", "obsidian", "roam",
        "evernote", "onenote",
        "typora", "mark text",
    ]

    TERMINAL_APPS = [
        "cmd.exe", "powershell", "pwsh",
        "windows terminal", "terminal",
        "wsl", "bash", "zsh",
        "putty", "mobaxterm", "cmder",
        "hyper", "iterm", "alacritty", "kitty",
    ]

    def __init__(self, hwnd=None):
        self.hwnd = hwnd
        self.window_title = ""
        self.window_class = ""
        self.app_type = self.GENERAL
        self.process_name = ""

        if hwnd:
            self._detect_context()

    def _detect_context(self):
        """Detect the application context from window handle."""
        try:
            user32 = ctypes.windll.user32

            # Get window title
            length = user32.GetWindowTextLengthW(self.hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(self.hwnd, buf, length + 1)
                self.window_title = buf.value.lower()

            # Get window class name
            class_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(self.hwnd, class_buf, 256)
            self.window_class = class_buf.value.lower()

            # Get process name (more reliable for some apps)
            try:
                import psutil
                # Get process ID from window handle
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(self.hwnd, ctypes.byref(pid))
                if pid.value:
                    proc = psutil.Process(pid.value)
                    self.process_name = proc.name().lower()
            except (ImportError, psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            # Detect app type
            self.app_type = self._classify_app()

        except (AttributeError, OSError, Exception) as e:
            debug_print(f"[Context] Error detecting app context: {e}")

    def _classify_app(self):
        """Classify the application type based on window info."""
        combined = f"{self.window_title} {self.window_class} {self.process_name}"

        # Check code editors first (most specific formatting needs)
        for pattern in self.CODE_EDITORS:
            if pattern in combined:
                return self.CODE_EDITOR

        # Check terminal
        for pattern in self.TERMINAL_APPS:
            if pattern in combined:
                return self.TERMINAL

        # Check messaging apps
        for pattern in self.MESSAGING_APPS:
            if pattern in combined:
                return self.MESSAGING

        # Check email
        for pattern in self.EMAIL_APPS:
            if pattern in combined:
                return self.EMAIL

        # Check document apps
        for pattern in self.DOCUMENT_APPS:
            if pattern in combined:
                return self.DOCUMENT

        # Check browser (generic, but useful)
        if any(b in combined for b in ["chrome", "firefox", "edge", "safari", "brave", "opera"]):
            return self.BROWSER

        return self.GENERAL

    def should_skip_auto_punctuation(self):
        """Whether to skip automatic end-of-sentence punctuation."""
        return self.app_type in [self.CODE_EDITOR, self.TERMINAL]

    def should_preserve_casing(self):
        """Whether to preserve exact casing (for code/terminal)."""
        return self.app_type in [self.CODE_EDITOR, self.TERMINAL]

    def is_casual_context(self):
        """Whether this is a casual context (shorter, less formal)."""
        return self.app_type == self.MESSAGING

    def is_formal_context(self):
        """Whether this is a formal context (email, documents)."""
        return self.app_type in [self.EMAIL, self.DOCUMENT]


def get_active_app_context():
    """Get the context of the currently active application."""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        return AppContext(hwnd)
    except (AttributeError, OSError):
        return AppContext()


def capture_context_on_record():
    """Capture app context when recording starts."""
    global active_app_context
    active_app_context = get_active_app_context()
    debug_print(f"[Context] Captured: {active_app_context.app_type} - {active_app_context.window_title[:50]}")

# ============================================================================
# FLOATING PILL STATUS BAR
# ============================================================================
class FloatingPill:
    """Always-visible compact status panel for recording lifecycle."""

    def __init__(self):
        # Set DPI awareness before creating tkinter windows
        set_dpi_awareness()

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

        # Status state and animation
        self.current_state = "armed"
        self.status_detail = ""
        self.hotkey_display = _hotkey_display_text(HOTKEY_HOLD)
        self.animation_id = None
        self.pulse_phase = 0
        self._is_visible = False
        self._revert_timer = None

        self._palette = {
            "idle": {"accent": "#808791", "chip_bg": "#20252D", "label": "IDLE", "hint": "Listening paused. Use tray to re-arm."},
            "armed": {"accent": "#54D7C3", "chip_bg": "#13262A", "label": "ARMED", "hint": "Hold hotkey to record. Release to transcribe."},
            "recording": {"accent": "#FF5A7A", "chip_bg": "#311520", "label": "RECORDING", "hint": "Recording in progress. Keep keys held while speaking."},
            "transcribing": {"accent": "#58B6FF", "chip_bg": "#112538", "label": "TRANSCRIBING", "hint": "Processing audio and preparing output."},
            "done": {"accent": "#5CE394", "chip_bg": "#132A20", "label": "DONE", "hint": "Transcription complete."},
            "error": {"accent": "#FF6C6C", "chip_bg": "#331A1A", "label": "ERROR", "hint": "Transcription failed. Try again."},
        }

        self._draw_panel("armed")
        self._position_near_taskbar()
        self.show()

        # Bind click to open dashboard
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Button-3>", self._on_right_click)

        # Context menu
        self.context_menu = tk.Menu(self.root, tearoff=0, bg=Theme.BG_ELEVATED, fg=Theme.TEXT_PRIMARY)
        self.context_menu.add_command(label="Open Dashboard", command=self._open_dashboard)
        self.context_menu.add_command(label="Settings", command=lambda: open_settings_window(self.root))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Exit", command=self._quit)

    def _base_state(self) -> str:
        return "armed" if listening_enabled else "idle"

    def set_hotkey_hint(self, hotkey_value: str) -> None:
        """Update the displayed hotkey guidance."""
        self.hotkey_display = _hotkey_display_text(hotkey_value)
        self._draw_panel(self.current_state)

    def _draw_panel(self, state: str, pulse: float = 0.0) -> None:
        """Draw compact high-contrast status panel."""
        self.canvas.delete("all")

        spec = self._palette.get(state, self._palette["armed"])
        accent = spec["accent"]
        border_color = self._blend_color(accent, "#FFFFFF", 0.6 + (pulse * 0.4) if state == "recording" else 0.65)

        # Outer shell
        self._draw_rounded_rect(
            2, 2, self.width - 2, self.height - 2,
            Theme.PILL_RADIUS,
            fill="#101218",
            outline=border_color,
        )

        # Status chip
        chip_x1, chip_y1, chip_x2, chip_y2 = 14, 12, 138, 36
        self._draw_rounded_rect(
            chip_x1, chip_y1, chip_x2, chip_y2, 12,
            fill=spec["chip_bg"],
            outline=accent,
        )
        self.canvas.create_oval(24, 21, 32, 29, fill=accent, outline="")
        self.canvas.create_text(
            86, 24,
            text=spec["label"],
            fill="#F8FAFC",
            font=(Theme.FONT_FAMILY, 10, "bold"),
            anchor="center",
        )

        # Large hotkey guidance
        self.canvas.create_text(
            self.width - 14, 24,
            text=self.hotkey_display,
            fill="#FFFFFF",
            font=(Theme.FONT_FAMILY, 13, "bold"),
            anchor="e",
        )

        detail = self.status_detail.strip() if self.status_detail else spec["hint"]
        self.canvas.create_text(
            14, 54,
            text=detail,
            fill="#D3D8DF",
            font=(Theme.FONT_FAMILY, 10),
            anchor="w",
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
        """Position the panel near the taskbar."""
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

        # Keep panel close to the taskbar but readable.
        taskbar_offset = 12

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

    def _schedule_revert_to_base(self, delay_ms: int = 1400):
        self._cancel_revert()
        self._revert_timer = self.root.after(delay_ms, lambda: self.set_status(self._base_state()))

    def _cancel_revert(self):
        if self._revert_timer is not None:
            try:
                self.root.after_cancel(self._revert_timer)
            except Exception:
                pass
            self._revert_timer = None

    def set_status(self, state, text=None, bg=None, fg=None, border=None):
        """Update status panel state (supports legacy status text calls)."""
        state_map = {
            "idle": "idle",
            "armed": "armed",
            "recording": "recording",
            "transcribing": "transcribing",
            "done": "done",
            "error": "error",
            "ready": self._base_state(),
            "listening": "recording",
            "success": "done",
            "warning": "done",
            "🎤 Ready": self._base_state(),
            "🎤 Initializing...": self._base_state(),
            "🎙️ Listening...": "recording",
            "⚙️ Transcribing...": "transcribing",
            "✅ Pasted!": "done",
            "📋 Copied!": "done",
            "❌ Failed": "error",
            "❌ Mic not ready": "error",
            "❌ Paste error": "error",
            "❌ Engine not found": "error",
            "❌ Error": "error",
            "❌ Try again": "error",
            "🔇 No speech detected": "done",
            "🔇 No speech": "done",
            "🔇 Empty transcript": "done",
            "⚠️ Issues detected": "done",
        }

        new_state = state_map.get(state, self._base_state())
        new_detail = ""
        if isinstance(text, str):
            candidate = text.strip()
            if candidate and not re.fullmatch(r"#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?", candidate):
                new_detail = candidate
        if not new_detail and isinstance(state, str) and state not in {"idle", "armed", "recording", "transcribing", "done", "error"}:
            new_detail = state

        self.current_state = new_state
        self.status_detail = new_detail

        self._cancel_revert()
        if self.animation_id:
            try:
                self.root.after_cancel(self.animation_id)
            except Exception:
                pass
            self.animation_id = None

        self.show()

        if new_state == "recording":
            self._animate_pulse()
        else:
            self._draw_panel(new_state)

        if new_state in ("done", "error"):
            self._schedule_revert_to_base()

    def _animate_pulse(self):
        """Animate pulse while recording is active."""
        self.pulse_phase += 0.22
        pulse = (math.sin(self.pulse_phase) + 1) / 2
        self._draw_panel("recording", pulse)

        if self.current_state == "recording":
            self.animation_id = self.root.after(67, self._animate_pulse)

    def show(self):
        """Show panel."""
        if not self._is_visible:
            self._is_visible = True
            self.root.deiconify()

    def hide(self):
        """Hide panel."""
        if self._is_visible:
            self._is_visible = False
            self.root.withdraw()

    def show_for_active(self) -> None:
        """Show the pill when the user presses the record hotkey."""
        self.show()

    def hide_when_idle(self) -> None:
        """Hide the pill once it has returned to idle/armed state."""
        self.hide()

    def _on_click(self, event):
        """Handle left click - open dashboard."""
        self._open_dashboard()

    def _on_right_click(self, event):
        """Handle right click - show context menu."""
        self.context_menu.tk_popup(event.x_root, event.y_root)

    def _open_dashboard(self):
        """Open the main dashboard window."""
        _launch_dashboard_from_ui_trigger()

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
        self.root.after(50, self.pump_queue)

    def bind_context_menu(self, on_settings):
        """Compatibility method - already handled internally."""
        pass


def _create_status_hud():
    """Create the preferred status HUD (AmbientPill when Qt is available)."""
    try:
        from whisper_local.ui.AmbientPill import (
            AmbientPill,
            is_qt_available,
            qt_backend_diagnostics,
        )

        diag = qt_backend_diagnostics()
        log_line(
            "HUD_INIT request="
            + f"{HUD_BACKEND_REQUESTED} qt_available={diag.get('qt_available')} "
            + f"qt_binding={diag.get('qt_binding')} qt_error={diag.get('qt_import_error') or '-'}"
        )

        request = HUD_BACKEND_REQUESTED if HUD_BACKEND_REQUESTED in {"ambient", "legacy", "auto"} else "ambient"
        ambient_ready = bool(is_qt_available())

        if request in {"ambient", "auto"} and ambient_ready:
            hud = AmbientPill(
                ui_queue=ui_queue,
                on_open_dashboard=_launch_dashboard_from_ui_trigger,
                on_quit=lambda: _tray_quit(),
                is_armed_fn=lambda: listening_enabled,
                log_fn=log_line,
            )
            log_line(
                f"HUD_BACKEND={hud.__class__.__name__} "
                f"HUD_BACKEND_MODULE={hud.__class__.__module__}"
            )
            return hud

        if request == "ambient" and not ambient_ready:
            reason = diag.get("qt_import_error") or "Qt backend unavailable"
            log_line(f"HUD_CRITICAL ambient requested but unavailable: {reason}", "critical")
            raise RuntimeError(f"AmbientPill unavailable: {reason}")

        if request == "legacy":
            log_line("HUD_BACKEND=LegacyStatusWidget HUD_BACKEND_MODULE=flow_local_dictation")
            return FloatingPill()

        # request == auto and ambient unavailable
        reason = diag.get("qt_import_error") or "Qt backend unavailable"
        log_line(f"HUD_WARNING auto fallback to legacy: {reason}", "warning")
        log_line("HUD_BACKEND=LegacyStatusWidget HUD_BACKEND_MODULE=flow_local_dictation")
        return FloatingPill()
    except Exception as e:
        log_line(f"HUD_FATAL failed to create status HUD: {e}", "critical")
        raise


# ============================================================================
# OLD TKINTER DASHBOARD (REPLACED BY HTML HOST)
# ============================================================================
# The following code is the old Tkinter dashboard that has been replaced
# by the new pywebview-based dashboard in gui_host.py
#
# The old code has been removed from this file to avoid syntax errors.
# You can find the old Tkinter dashboard code in git history (commit before pywebview migration)
# or in the backup at flow_local_dictation.py.bak if needed.
#
# The dashboard is opened via: threading.Thread(target=open_dashboard, daemon=True).start()
# where open_dashboard is imported from gui_host.py



# ============================================================================
# MODERN SETTINGS WINDOW
# ============================================================================
def open_settings_window(parent):
    """Open the modernized settings window."""
    # Ensure DPI awareness is set
    set_dpi_awareness()
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
    settings_hotkey = load_hotkey(SETTINGS_FILE)
    hotkey_info = tk.Label(
        content,
        text=f"🎙️  Hold {settings_hotkey.upper().replace('+', ' + ')} to record",
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
MODEL_PATH_SMALL = res_path(os.path.join("runtime", "models", "ggml-small.en.bin"))
MODEL_PATH_MEDIUM = res_path(MODEL_MEDIUM)
MODEL_PATH_LARGE = res_path(MODEL_LARGE)
MODEL_PATH = MODEL_PATH_LARGE  # Legacy fallback
MODEL_SELECTION_STATE_FILE = model_selection_file(get_user_data_dir())
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

# Temporary playback ducking manager for push-to-talk sessions.
audio_ducking_manager = AudioDuckingSessionManager(
    state_file=AUDIO_DUCK_STATE_FILE,
    duck_level=0.0,
    restore_delay_ms=DUCKING_RESTORE_DELAY_MS,
    log_fn=log_line,
)
atexit.register(lambda: audio_ducking_manager.force_restore(reason="atexit"))


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

def _normalize_repeat_fragment(fragment: str) -> str:
    """Normalize text fragment for robust repetition checks."""
    return re.sub(r"[^a-z0-9]+", " ", (fragment or "").lower()).strip()

def collapse_repetition_artifacts(text: str, min_sentence_words: int = 8) -> str:
    """
    Collapse common Whisper repetition artifacts while preserving normal text.

    Targets:
    - Consecutive duplicate lines
    - Consecutive duplicate sentences with enough content to be meaningful
    """
    if not text:
        return ""

    # Pass 1: remove exact consecutive duplicate lines
    deduped_lines = []
    last_line_norm = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line_norm = _normalize_repeat_fragment(line)
        if deduped_lines and line_norm and line_norm == last_line_norm:
            continue
        deduped_lines.append(line)
        last_line_norm = line_norm

    collapsed = "\n".join(deduped_lines).strip()
    if not collapsed:
        return ""

    # Pass 2: remove consecutive duplicate sentences (long enough to avoid false positives)
    sentence_parts = re.split(r"(?<=[.!?])\s+", collapsed.replace("\n", " "))
    deduped_sentences = []
    last_sentence_norm = None

    for part in sentence_parts:
        sentence = part.strip()
        if not sentence:
            continue
        sentence_norm = _normalize_repeat_fragment(sentence)
        if (
            deduped_sentences
            and sentence_norm
            and sentence_norm == last_sentence_norm
            and len(sentence_norm.split()) >= min_sentence_words
        ):
            continue
        deduped_sentences.append(sentence)
        last_sentence_norm = sentence_norm

    return " ".join(deduped_sentences).strip()


# --- Smart text post-processing helpers (Wispr Flow-inspired) ---

# Filler word patterns - comprehensive list for natural speech cleanup
FILLER_PATTERNS = [
    # Basic filler sounds
    r"\b(?:um+|uh+|er+|ah+|eh+|hm+|hmm+|mmm+)\b",
    # Common verbal fillers
    r"\b(?:you know|ya know|y'know)\b",
    r"\b(?:i mean)\b",
    r"\b(?:kind of|kinda|sort of|sorta)\b",
    # "like" as filler (but not when followed by specific words)
    r"\b(?:like)\b(?!\s*(?:to|that|this|those|these|it|i|we|he|she|they|a|an|the|\d))",
    # Additional fillers
    r"\b(?:basically|literally|actually)\b(?=\s*,|\s+(?:um|uh|like|you know))",
    r"\b(?:so)\b(?=\s*,?\s*(?:um|uh|like|you know|basically))",
    r"\b(?:well)\b(?=\s*,?\s*(?:um|uh|like|you know))",
    r"\b(?:right)\b(?=\s*,?\s*(?:um|uh|so|like))",
    r"\b(?:okay|ok)\b(?=\s*,?\s*(?:so|um|uh|like))",
]

def scrub_fillers(s: str) -> str:
    """Remove filler words and sounds from transcription."""
    out = s
    for pat in FILLER_PATTERNS:
        out = re.sub(pat, "", out, flags=re.IGNORECASE)
    # Clean up multiple spaces and commas
    out = re.sub(r",\s*,", ",", out)  # Double commas
    out = re.sub(r"\s*,\s*\.", ".", out)  # Comma before period
    out = re.sub(r"\s{2,}", " ", out)  # Multiple spaces
    return out.strip()

# Voice command replacements - comprehensive punctuation and formatting
COMMAND_REPLACERS = [
    # Line breaks
    (r"\bnew\s*line\b", "\n"),
    (r"\bnew\s*paragraph\b", "\n\n"),
    (r"\bline\s*break\b", "\n"),
    (r"\benter\b(?!\s+(?:the|a|into|in))", "\n"),
    # Basic punctuation
    (r"\bcomma\b", ","),
    (r"\bperiod\b|(?<!\w)dot(?!\s*com)(?!\s*org)(?!\s*net)(?!\s*io)", "."),
    (r"\bfull\s*stop\b", "."),
    (r"\bexclamation(?:\s*(?:mark|point))?\b", "!"),
    (r"\bquestion\s*mark\b", "?"),
    # Advanced punctuation
    (r"\bcolon\b", ":"),
    (r"\bsemicolon\b|(?:semi[\s-]*colon)", ";"),
    (r"\b(?:hyphen|dash)\b", "-"),
    (r"\bem[\s-]*dash\b", "—"),
    (r"\bellipsis\b|(?:dot\s*dot\s*dot)", "..."),
    # Quotes and brackets
    (r"\b(?:open|left)\s*(?:quote|quotation)\b|(?:quote)\b(?=\s+\w)", '"'),
    (r"\b(?:close|right|end)\s*(?:quote|quotation)\b|(?:unquote|close\s*quote)\b", '"'),
    (r"\b(?:single\s*)?(?:open|left)\s*(?:quote|apostrophe)\b", "'"),
    (r"\b(?:single\s*)?(?:close|right|end)\s*(?:quote|apostrophe)\b", "'"),
    (r"\b(?:open|left)\s*(?:paren(?:thesis)?|bracket)\b", "("),
    (r"\b(?:close|right|end)\s*(?:paren(?:thesis)?|bracket)\b", ")"),
    (r"\b(?:open|left)\s*(?:square\s*)?bracket\b", "["),
    (r"\b(?:close|right|end)\s*(?:square\s*)?bracket\b", "]"),
    (r"\b(?:open|left)\s*(?:curly\s*)?brace\b", "{"),
    (r"\b(?:close|right|end)\s*(?:curly\s*)?brace\b", "}"),
    # Special characters
    (r"\b(?:at\s*sign|at\s*symbol)\b", "@"),
    (r"\bhash(?:\s*tag)?\b|(?:pound\s*sign)\b", "#"),
    (r"\b(?:dollar\s*sign|dollars?)\b(?!\s*\d)", "$"),
    (r"\b(?:percent(?:age)?(?:\s*sign)?)\b(?!\s*\d)", "%"),
    (r"\b(?:ampersand|and\s*sign)\b", "&"),
    (r"\b(?:asterisk|star)\b(?!\s*(?:wars|trek|rating))", "*"),
    (r"\bslash\b|(?:forward\s*slash)", "/"),
    (r"\bback\s*slash\b", r"\\"),
    (r"\bpipe\b|(?:vertical\s*bar)", "|"),
    (r"\btilde\b", "~"),
    (r"\bcaret\b", "^"),
    (r"\bunderscore\b", "_"),
    # Spacing and formatting
    (r"\btab\b", "\t"),
    (r"\bspace\b(?!\s+(?:bar|ship|station))", " "),
    (r"\bno\s*space\b", ""),
]

def apply_commands(s: str) -> str:
    """Apply voice commands for punctuation and formatting."""
    out = s
    for pat, rep in COMMAND_REPLACERS:
        out = re.sub(pat, rep, out, flags=re.IGNORECASE)
    return out

# Correction patterns - handle "actually", "no wait", "I mean" style corrections
def apply_corrections(s: str) -> str:
    """
    Handle real-time corrections like:
    - "2 pm no 4 pm" -> "4 pm"
    - "scratch that, the meeting is tomorrow" -> "the meeting is tomorrow"
    - "wait no, make it 3 o'clock" -> "make it 3 o'clock"
    - "I said Monday, I mean Tuesday" -> "I said Tuesday"
    """
    out = s

    # 1. Handle "X no/wait Y" number/time corrections
    # "2 pm no 4 pm" -> "4 pm"
    # "at 2 no 4" -> "at 4"
    out = re.sub(
        r"(\d+)\s*(?:pm|am|o'?clock)?\s*(?:,?\s*)?(?:no|not|wait|actually)\s+(\d+)\s*(pm|am|o'?clock)?",
        r"\2 \3",
        out,
        flags=re.IGNORECASE
    )

    # 2. Handle "scratch that / never mind / forget that" - remove everything before
    match = re.search(
        r"^.*?(?:scratch\s*that|never\s*mind|forget\s*(?:that|it)|let\s*me\s*(?:start\s*over|try\s*again))\s*[,.]?\s*(.+)$",
        out,
        flags=re.IGNORECASE
    )
    if match and match.group(1).strip():
        out = match.group(1).strip()

    # 3. Handle "wait no" / "no wait" at the start - keep what comes after
    match = re.search(
        r"^(?:wait\s*,?\s*no|no\s*,?\s*wait|actually\s*,?\s*no)\s*,?\s*(.+)$",
        out,
        flags=re.IGNORECASE
    )
    if match and match.group(1).strip():
        out = match.group(1).strip()

    # 4. Handle "I mean" / "or rather" corrections
    # Simple approach: keep just what comes after "I mean"
    # "Monday I mean Tuesday" -> "Tuesday"
    # "2 pm I mean 4 pm" -> "4 pm"
    # "the meeting is at 2 I mean 4 pm" -> "4 pm"
    match = re.search(
        r"(?:,\s*)?(?:I\s*mean|or\s*rather|or\s*actually)\s+(.+)$",
        out,
        flags=re.IGNORECASE
    )
    if match:
        out = match.group(1).strip()

    # Clean up any double spaces
    out = re.sub(r"\s{2,}", " ", out)

    return out.strip()

def autopunct_and_capitalize(s: str) -> str:
    """Add sentence capitalization and ensure proper punctuation."""
    if not s:
        return s

    # Split by sentence-ending punctuation while keeping the punctuation
    parts = re.split(r'([.!?])', s)
    rebuilt = []

    for i in range(0, len(parts), 2):
        seg = parts[i].strip()
        if not seg:
            continue

        # Get the punctuation that follows this segment
        end = parts[i + 1] if i + 1 < len(parts) else ""

        # Capitalize first letter of segment
        if seg:
            seg = seg[0].upper() + seg[1:] if len(seg) > 1 else seg.upper()

        rebuilt.append(seg)
        if end:
            rebuilt.append(end + " ")

    result = "".join(rebuilt).strip()

    # If no ending punctuation, don't force one (let user decide)
    return result

def to_bullets(s: str) -> str:
    """Convert comma-separated items to bullet list if requested."""
    # Check if bullet list is explicitly requested
    if re.search(r"\b(bullets?|bullet\s*list|make\s+a\s+list|as\s+a\s+list|list(?:\s*them)?:?)\b", s, re.IGNORECASE):
        # Remove the "bullet list" command text
        s = re.sub(r"^\s*.*?(bullets?|list(?:\s*them)?:?)\s*", "", s, flags=re.IGNORECASE)
    else:
        return s  # No bullet list requested

    # Split by comma or "and"
    items = re.split(r",|\band\b", s)
    items = [it.strip(" .\t\r\n") for it in items if it.strip()]

    if len(items) <= 1:
        return s.strip()

    return "\n".join("• " + it.capitalize() for it in items)

def to_numbered_list(s: str) -> str:
    """Convert items to numbered list if requested."""
    if re.search(r"\b(?:numbered\s*list|number\s*(?:these|them|the\s+items?)?)\b", s, re.IGNORECASE):
        # Remove the command text
        s = re.sub(r"^\s*.*?(?:numbered\s*list|number\s*(?:these|them|the\s+items?)?)\s*[,:]?\s*", "", s, flags=re.IGNORECASE)

        # Split by comma or "and"
        items = re.split(r",|\band\b", s)
        items = [it.strip(" .\t\r\n") for it in items if it.strip()]

        if len(items) > 1:
            return "\n".join(f"{i+1}. {it.capitalize()}" for i, it in enumerate(items))

    return s

def clean_spacing(s: str) -> str:
    """Clean up spacing around punctuation."""
    # Remove space before punctuation
    s = re.sub(r'\s+([.,!?;:)\]}])', r'\1', s)
    # Ensure space after punctuation (except before newlines or end)
    s = re.sub(r'([.,!?;:])(?=[^\s\n])', r'\1 ', s)
    # Remove space after opening brackets
    s = re.sub(r'([({\[])(\s+)', r'\1', s)
    # Clean multiple spaces
    s = re.sub(r' {2,}', ' ', s)
    # Clean space at start of lines
    s = re.sub(r'\n\s+', '\n', s)
    return s.strip()

# ============================================================================
# VOCABULARY-BASED CORRECTIONS
# ============================================================================

_VOCAB_BOUNDARY_ALNUM = r"A-Za-z0-9"


def _is_title_style(text: str) -> bool:
    """Return True when alphabetic words are in Title Case."""
    words = re.findall(r"[A-Za-z]+", text or "")
    if not words:
        return False
    return all((w[0].isupper() and w[1:].islower()) if len(w) > 1 else w[0].isupper() for w in words)


def _to_title_style(text: str) -> str:
    """Title-case only alphabetic runs; keep punctuation intact."""
    return re.sub(r"[A-Za-z]+", lambda m: m.group(0)[0].upper() + m.group(0)[1:].lower(), text)


def _apply_case_style(canonical: str, matched: str) -> str:
    """Apply the matched case style to the canonical vocabulary term."""
    alpha = [ch for ch in (matched or "") if ch.isalpha()]
    if not alpha:
        return canonical

    if all(ch.isupper() for ch in alpha):
        return canonical.upper()
    if all(ch.islower() for ch in alpha):
        return canonical.lower()
    if _is_title_style(matched):
        return _to_title_style(canonical)
    return canonical


def _build_vocabulary_pattern(term: str):
    """
    Build a punctuation-safe, case-insensitive regex for a vocabulary term.

    Uses alnum lookarounds instead of \\b so terms like "C++" are matched.
    Also tolerates incidental spaces around punctuation (e.g., "c + +").
    """
    tokens = re.findall(r"[A-Za-z0-9]+|\s+|[^A-Za-z0-9\s]+", term or "")
    if not tokens:
        return None

    parts = []
    for i, token in enumerate(tokens):
        prev_token = tokens[i - 1] if i > 0 else ""
        next_token = tokens[i + 1] if i + 1 < len(tokens) else ""

        if token.isspace():
            parts.append(r"\s+")
            continue

        if token.isalnum():
            parts.append(re.escape(token))
            continue

        if prev_token and not prev_token.isspace():
            parts.append(r"\s*")
        parts.append(r"\s*".join(re.escape(ch) for ch in token))
        if next_token and not next_token.isspace():
            parts.append(r"\s*")

    core = "".join(parts)
    if not core:
        return None

    return re.compile(
        rf"(?<![{_VOCAB_BOUNDARY_ALNUM}])({core})(?![{_VOCAB_BOUNDARY_ALNUM}])",
        flags=re.IGNORECASE,
    )


def apply_vocabulary_corrections(text: str) -> str:
    """Apply deterministic replacements from user vocabulary.

    Two passes:
    1. Exact regex matching (case-insensitive, punctuation-safe).
    2. Fuzzy matching via sliding word windows to catch Whisper
       misrecognitions (e.g. "is higher" -> "Isaiah").
    """
    if not text:
        return text

    words = load_vocabulary(VOCABULARY_FILE)
    if not words:
        return text

    log_line(f"[vocab] loaded {len(words)} words from disk", "debug")

    corrected = text
    # Pass 1: exact regex matching (existing behaviour).
    for canonical in sorted(words, key=len, reverse=True):
        pattern = _build_vocabulary_pattern(canonical)
        if pattern is None:
            continue
        corrected = pattern.sub(
            lambda m, canonical_word=canonical: _apply_case_style(canonical_word, m.group(0)),
            corrected,
        )

    # Pass 2: fuzzy matching for words that Whisper misrecognised.
    corrected = _fuzzy_vocabulary_pass(corrected, words)

    return corrected


# Minimum similarity ratio for fuzzy vocabulary matching.  High enough
# to avoid false positives, low enough to catch common Whisper errors
# like word-splitting ("able ton" for "Ableton") or phonetic drift
# ("is higher" for "Isaiah").
_FUZZY_VOCAB_THRESHOLD = 0.78


def _fuzzy_vocabulary_pass(text: str, vocab_words: list[str]) -> str:
    """Replace near-miss transcriptions with the canonical vocabulary form.

    Two strategies are tried for each vocabulary term:

    1. **Same-size window** – a window of *n* words (where *n* = word count
       of the vocab term) is compared via ``SequenceMatcher``.
    2. **Expanded window** – windows of *n+1* and *n+2* words are
       concatenated (spaces removed) and compared against the concatenated
       canonical form.  This catches Whisper word-splitting errors like
       "able ton" → "Ableton" or "bid F T A" → "BidFTA".

    Only matches exceeding *_FUZZY_VOCAB_THRESHOLD* are accepted.
    """
    from difflib import SequenceMatcher

    text_words = text.split()
    if not text_words:
        return text

    # Sort longer terms first so multi-word terms get priority.
    sorted_vocab = sorted(vocab_words, key=lambda w: len(w.split()), reverse=True)

    # Track which word positions have already been replaced.
    replaced: set[int] = set()

    for canonical in sorted_vocab:
        canon_tokens = canonical.split()
        n = len(canon_tokens)
        if n == 0:
            continue
        canon_lower = canonical.lower()
        # Concatenated form for detecting word-splitting.
        canon_concat = canon_lower.replace(" ", "")

        # Try window sizes: same (n), expanded (n+1), expanded (n+2).
        # Expanded windows catch Whisper splitting single words into
        # multiple tokens (e.g. "Ableton" → "able ton").
        window_sizes = [n]
        if n + 1 <= len(text_words):
            window_sizes.append(n + 1)
        if n + 2 <= len(text_words):
            window_sizes.append(n + 2)

        best_match = None  # (start_idx, win_size, score, window_text)

        for ws in window_sizes:
            for i in range(len(text_words) - ws + 1):
                if any(j in replaced for j in range(i, i + ws)):
                    continue

                window = " ".join(text_words[i : i + ws])
                window_lower = window.lower()

                # Skip if already an exact match (handled by pass 1).
                if window_lower == canon_lower:
                    continue

                # Skip if the window already contains the canonical form
                # as a substring – avoids false positives when correct
                # instances bleed into adjacent windows.
                if canon_lower in window_lower:
                    continue

                # For same-size windows, compare as-is.
                # For expanded windows, compare concatenated forms.
                if ws == n:
                    ratio = SequenceMatcher(None, window_lower, canon_lower).ratio()
                else:
                    window_concat = window_lower.replace(" ", "")
                    ratio = SequenceMatcher(None, window_concat, canon_concat).ratio()

                if ratio >= _FUZZY_VOCAB_THRESHOLD:
                    if best_match is None or ratio > best_match[2]:
                        best_match = (i, ws, ratio, window)

        if best_match is not None:
            i, ws, ratio, window = best_match
            replacement = _apply_case_style(canonical, window)
            log_line(
                f"[vocab-fuzzy] '{window}' -> '{replacement}' "
                f"(score={ratio:.2f})",
                "info",
            )
            text_words[i] = replacement
            for j in range(i + 1, i + ws):
                text_words[j] = ""
            replaced.update(range(i, i + ws))

    return " ".join(w for w in text_words if w)

# ============================================================================
# DOMAIN POST-PROCESSING (Sections 3 & 4)
# ============================================================================

def fix_ip_addresses(text: str) -> str:
    """Rule 2: Collapse spaces in IPv4 addresses and normalize localhost."""
    # Collapse spaces around dots/colons in IPv4-like patterns: "127. 0. 0. 1 : 8080"
    text = re.sub(
        r'(\d{1,3})\s*\.\s*(\d{1,3})\s*\.\s*(\d{1,3})\s*\.\s*(\d{1,3})(\s*:\s*(\d+))?',
        lambda m: f"{m.group(1)}.{m.group(2)}.{m.group(3)}.{m.group(4)}"
                  + (f":{m.group(6)}" if m.group(6) else ""),
        text
    )
    # "local host" → "localhost"
    text = re.sub(r'\blocal\s+host\b', 'localhost', text, flags=re.IGNORECASE)
    return text

def fix_technical_terms(text: str) -> str:
    """Section 3: Normalize domain-specific technical terms."""
    replacements = [
        (r'\bTHD\s*(?:plus|\+)\s*N\b', 'THD+N'),
        (r'\bsignal[\s-]to[\s-]noise\s+ratio\b', 'Signal-to-Noise Ratio'),
        (r'\bhigh[\s-]pass\s+filter\b', 'High-pass filter'),
        (r'\blow[\s-]pass\s+filter\b', 'Low-pass filter'),
        (r'\bbit[\s-]depth\b', 'Bit-depth'),
        (r'\bphantom\s+power\b', 'Phantom Power'),
        (r'\bapt[\s-]get\b', 'apt-get'),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def fix_homophones(text: str) -> str:
    """Rule 3: Context-based homophone disambiguation using nearby keywords."""
    # write vs right
    text = re.sub(
        r'\bright\b(?=\s+(?:code|file|script|function|data|disk|program|log)\b)',
        'write', text, flags=re.IGNORECASE
    )
    text = re.sub(
        r'\bwrite\b(?=\s+(?:correct|direction|turn|go|answer|click)\b)',
        'right', text, flags=re.IGNORECASE
    )
    # there vs their vs they're
    text = re.sub(
        r'\b(?:there|they\'re)\b(?=\s+(?:team|group|project|code|data|names)\b)',
        'their', text, flags=re.IGNORECASE
    )
    text = re.sub(
        r'\b(?:their|they\'re)\b(?=\s+(?:house|place|location|over|go|put|sit)\b)',
        'there', text, flags=re.IGNORECASE
    )
    text = re.sub(
        r'\b(?:their|there)\b(?=\s+(?:going|running|coming|doing|saying)\b)',
        "they're", text, flags=re.IGNORECASE
    )
    return text

_AUTO_CODE_MODE = CodeModeCorrector(
    enabled=True,
    auto_detect=True,
    min_confidence=0.58,
    safe_confidence=0.35,
)


def detect_code_formatting(text: str) -> str:
    """Rule 4: Confidence-gated spoken code formatting."""
    if not text:
        return text

    lowered = text.lower()
    explicit_context = any(
        hint in lowered
        for hint in (
            "def ",
            "class ",
            "import ",
            "from ",
            "function ",
            "variable ",
            "method ",
            "code mode",
            "python",
            "javascript",
        )
    )
    return _AUTO_CODE_MODE.correct(text, force=explicit_context)

def fix_punctuation_safety(text: str) -> str:
    """Rule 1: Oxford comma and vocative comma safety."""
    # Oxford comma: "X, Y and Z" → "X, Y, and Z"
    text = re.sub(r',\s+(\w+)\s+and\s+', r', \1, and ', text)
    # Vocative comma before common names/terms of address
    text = re.sub(
        r'(?<!\w)(hey|hi|hello|thanks|okay|ok|please|yo|sorry|look|listen|well)\s+([A-Z]\w+)',
        r'\1, \2',
        text,
        flags=re.IGNORECASE
    )
    return text


def postprocess(text: str, context: 'AppContext' = None) -> str:
    """
    Apply comprehensive text post-processing with Wispr Flow-style features.

    Uses context awareness to adapt formatting based on the active application:
    - Code editors/terminals: Preserve casing, skip auto-punctuation
    - Messaging apps: More casual formatting
    - Email/documents: Formal formatting with proper punctuation

    Processing order:
    1. Apply user vocabulary replacements
    2. Apply voice commands (punctuation, formatting)
    3. Handle corrections ("actually", "no wait", etc.)
    4. Remove filler words
    5. Handle list formatting
    6. Clean up spacing
    7. Capitalize sentences (context-aware)

    Args:
        text: Raw transcription text
        context: Optional AppContext for smart formatting
    """
    if not text:
        return text

    # Use global context if not provided
    if context is None:
        context = active_app_context

    # Vocabulary correction pass first, before other correction stages.
    text = apply_vocabulary_corrections(text)

    # Domain-specific post-processing (Sections 3 & 4)
    text = fix_ip_addresses(text)
    text = fix_technical_terms(text)
    text = fix_homophones(text)
    text = detect_code_formatting(text)
    text = fix_punctuation_safety(text)

    # Step 1: Apply voice commands first (so "period" becomes ".")
    text = apply_commands(text)

    # Step 2: Handle corrections ("actually X" -> X)
    text = apply_corrections(text)

    # Step 3: Remove filler words
    text = scrub_fillers(text)

    # Step 4: Handle list formatting if requested
    text = to_numbered_list(text)
    text = to_bullets(text)

    # Step 5: Clean up spacing around punctuation
    text = clean_spacing(text)

    # Step 6: Context-aware capitalization and punctuation
    if context and context.should_preserve_casing():
        # Code editors and terminals: preserve original casing
        # Still clean up spacing but don't force capitalization
        debug_print(f"[Context] Preserving casing for {context.app_type}")
    elif context and context.is_casual_context():
        # Messaging apps: lighter touch - capitalize first word only
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        debug_print(f"[Context] Casual formatting for {context.app_type}")
    else:
        # Default/formal: full sentence capitalization
        text = autopunct_and_capitalize(text)

    return text


def apply_router_action(text: str):
    """Apply LLM routing when agent mode is enabled."""
    global voice_router

    if not MODE_ROUTER:
        return text, False, "disabled"

    if voice_router is None:
        voice_router = VoiceAgentRouter(model=ROUTER_MODEL, timeout_sec=ROUTER_TIMEOUT_SEC)

    result = voice_router.process(text)
    log_line(
        f"[router] action={result.action} handled={result.handled} details={result.details}",
        "info",
    )
    return result.output_text, result.handled, result.action


def set_transcript_action_handler(handler):
    """Register a custom transcript action handler from main wiring."""
    global transcript_action_handler
    transcript_action_handler = handler


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
    
    log_line(f"✓ Ready for dictation (Hold {_hotkey_display_text(HOTKEY_HOLD)} to speak)")
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
    last_hud_push_ts = 0.0

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
                now_ts = time.time()
                if now_ts - last_hud_push_ts >= 0.03:
                    try:
                        ui_queue.put((gui.set_audio_level, (rms,)))
                    except Exception:
                        pass
                    last_hud_push_ts = now_ts
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
    global rec_thread, target_window_on_record_start, pending_status_timer, active_app_context

    with STATE_LOCK:
        # Check if already recording or transcribing (must be first check inside lock)
        if recording_flag.is_set() or transcribing_flag.is_set():
            return False

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

        # Capture app context for smart formatting (Wispr Flow-style)
        capture_context_on_record()

        # Clean up previous temp file
        try:
            if os.path.exists(WAV_TMP):
                os.remove(WAV_TMP)
        except OSError:
            pass  # File in use or already deleted

        # Set flag to indicate recording has started
        recording_flag.set()

    # UI update and thread start outside lock (safe since flag is already set)
    log_line("[rec] hotkey hold detected - starting recording")
    duck_applied = audio_ducking_manager.activate(reason="recording_start")
    log_line(f"DUCK_APPLY requested_by=recording_start applied={duck_applied}")
    # Show the ambient pill now that recording is active
    try:
        if gui is not None:
            ui_queue.put((gui.show_for_active, ()))
    except Exception:
        pass
    set_status_safe("recording", Theme.PINK_DARK, Theme.TEXT_PRIMARY, Theme.PINK_PRIMARY)
    try:
        rec_thread = threading.Thread(target=record_loop, daemon=True)
        rec_thread.start()
        return True
    except Exception as e:
        with STATE_LOCK:
            recording_flag.clear()
        log_line(f"[rec] failed to start recording thread: {e}", "error")
        audio_ducking_manager.force_restore(reason="recording_start_error")
        set_status_safe("❌ Error", Theme.ERROR, Theme.TEXT_PRIMARY, Theme.ERROR)
        return False

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


def _build_dynamic_initial_prompt() -> str:
    """Compose the base Whisper prompt plus user vocabulary words and continual context."""
    from whisper_local.continual_context import get_continual_context_string
    words = load_vocabulary(VOCABULARY_FILE)
    base = get_continual_context_string()
    return compose_prompt(base, words)


def _verify_binary_hash(exe_path: str) -> None:
    """Verify the SHA256 hash of the whisper binary to prevent malicious replacement."""
    # In a commercial release, EXPECTED_HASH is stamped into the pyc during the build process.
    expected_hash = os.environ.get("WHISPER_EXPECTED_HASH")
    if not expected_hash:
        # Development mode fallback
        return
        
    try:
        sha256_hash = hashlib.sha256()
        with open(exe_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        actual_hash = sha256_hash.hexdigest()
        
        if actual_hash.lower() != expected_hash.lower():
            log_line(f"[security] CRITICAL: Binary hash mismatch for {exe_path}. Expected {expected_hash}, got {actual_hash}", "error")
            raise RuntimeError(f"Security Error: The speech engine binary ({os.path.basename(exe_path)}) is modified or corrupted.")
            
    except OSError as e:
        log_line(f"[security] Failed to read binary for hash verification: {e}", "error")
        raise RuntimeError("Security Error: Could not verify speech engine binary.")


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
    _verify_binary_hash(exe)
    
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
    initial_prompt = _build_dynamic_initial_prompt()
    
    # GPU mode: Use fewer threads (GPU does the heavy lifting)
    # More CPU threads can actually slow down GPU inference due to scheduling overhead
    num_threads = "2"  # Optimal for GPU mode
    
    is_whisper_cli = os.path.basename(exe).lower() == "whisper-cli.exe"
    whisper_args = [
        "-l", "en",
        "-nt",
        "-mc", "0",
        "-bs", str(batch_size),
        "-t", num_threads,
    ]
    if not is_whisper_cli:
        # Legacy main.exe builds support explicit GPU-layer control.
        whisper_args.extend(["-ngl", "999"])
    whisper_args.extend([
        "-fa",  # Enable Flash Attention for faster GPU inference
        "-otxt", "-of", out_txt[:-4],
        "--prompt", initial_prompt,
    ])

    cmd = build_whisper_cmd(
        exe,
        model_path,
        filename,
        base_args=whisper_args,
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
            "--no-gpu",
            "--prompt", initial_prompt,
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
            base_args=["-l", "en", "-nt", "-bs", "5", "-otxt", "-of", out_txt[:-4],
                       "--prompt", initial_prompt],
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


def _current_vram_total_mb() -> float:
    try:
        info = gpu_monitor.get_gpu_info()
        if info is None:
            return 0.0
        return float(getattr(info, "memory_total_mb", 0.0) or 0.0)
    except Exception:
        return 0.0


def _load_effective_model_selection():
    state = load_model_selection_state(MODEL_SELECTION_STATE_FILE)
    refreshed, _ = refresh_auto_state(state, _current_vram_total_mb())
    if refreshed != state:
        save_model_selection_state(MODEL_SELECTION_STATE_FILE, refreshed)
    return refreshed


def _resolve_model_path(model_name: str):
    model_key = str(model_name or "").strip().lower()
    if model_key == "base":
        return MODEL_PATH_BASE, "base"
    if model_key == "small":
        if os.path.exists(MODEL_PATH_SMALL):
            return MODEL_PATH_SMALL, "small"
        # Small model is optional in this repo. Fall back to medium for accuracy.
        return MODEL_PATH_MEDIUM, "medium"
    if model_key == "medium":
        return MODEL_PATH_MEDIUM, "medium"
    if model_key == "large":
        if os.path.exists(MODEL_PATH_LARGE):
            return MODEL_PATH_LARGE, "large-v3"
        return MODEL_PATH_BASE, "base"
    return MODEL_PATH_BASE, "base"


def _run_fixed_model_transcription(filename: str, bin_path: str):
    selection = _load_effective_model_selection()
    mode = str(selection.get("mode", "auto")).lower()
    active_model = str(selection.get("active_model", "base")).lower()

    if mode == "auto":
        selected_model = active_model
    else:
        selected_model = mode
        # Keep active model synchronized for dashboard polling/toasts.
        if selection.get("active_model") != selected_model:
            updated, _ = apply_model_mode(selection, selected_model, _current_vram_total_mb())
            save_model_selection_state(MODEL_SELECTION_STATE_FILE, updated)

    model_path, model_used = _resolve_model_path(selected_model)
    rc, text, err = run_whisper(filename, bin_path, model_path=model_path)
    return rc, text, err, model_used


def run_whisper_smart(filename, bin_path):
    """Run transcription with user-selected model mode.

    Modes come from ``state/model_selection.json``:
    - ``base``, ``small``, ``medium``: manual single-pass model selection
    - ``auto``: choose ``large`` when VRAM > 8 GB, else ``base``

    Legacy two-pass load-aware logic remains as a fallback for unknown modes.
    """
    start_time = time.time()

    selection = _load_effective_model_selection()
    configured_mode = str(selection.get("mode", "auto")).lower()
    if configured_mode in {"auto", "base", "small", "medium"}:
        if configured_mode == "auto":
            vram_total_mb = float(selection.get("vram_total_mb", 0.0) or 0.0)
            safe_print(
                f"[whisper-smart] Auto mode enabled: VRAM={vram_total_mb / 1024.0:.2f}GB -> "
                f"{str(selection.get('active_model', 'base')).lower()}"
            )
        else:
            safe_print(f"[whisper-smart] Manual model override: {configured_mode}")

        rc, text, err, model_used = _run_fixed_model_transcription(filename, bin_path)
        total_time = time.time() - start_time
        return rc, text, err, model_used, total_time
    
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
            return rc, text, err, "large-v3 (fallback)", total_time
        else:
            # CPU mode - fall back to medium.en instead
            safe_print(f"[whisper-smart] Base model failed (rc={rc_base}), using medium.en fallback (CPU mode)")
            rc, text, err = run_whisper(filename, bin_path, model_path=MODEL_PATH_MEDIUM)
            total_time = time.time() - start_time
            safe_print(f"[whisper-smart] Fallback complete: {total_time:.2f}s")
            return rc, text, err, "medium.en (fallback)", total_time
    
    # Sanitize and count words
    clean_text = sanitize_transcript(text_base)
    if not clean_text:
        # Empty transcript - return base result
        safe_print("[whisper-smart] Empty transcript from base.en")
        total_time = time.time() - start_time
        return rc_base, text_base, err_base, "base.en", total_time
    
    word_count = len(clean_text.split())
    safe_print(f"[whisper-smart] Phase 1 complete: {word_count} words in {phase1_time:.2f}s")
    
    # Phase 2: Decide if we need a better model based on hardware and word count
    if word_count < threshold_base:
        # Short utterance - base.en is perfect!
        safe_print(f"[whisper-smart] Using base.en result ({word_count} < {threshold_base} words)")
        total_time = time.time() - start_time
        safe_print(f"[whisper-smart] ✓ Total time: {total_time:.2f}s (base.en only)")
        return rc_base, text_base, err_base, "base.en", total_time
    
    elif word_count < threshold_medium:
        # Medium length - re-transcribe with medium.en
        safe_print(f"[whisper-smart] Phase 2: Re-transcribing with medium.en ({word_count} words)")
        rc_med, text_med, err_med = run_whisper(filename, bin_path, model_path=MODEL_PATH_MEDIUM)
        total_time = time.time() - start_time
        
        if rc_med == 0:
            safe_print(f"[whisper-smart] ✓ Total time: {total_time:.2f}s (base.en + medium.en)")
            return rc_med, text_med, err_med, "medium.en", total_time
        else:
            # Medium failed - fall back to base result
            safe_print(f"[whisper-smart] Medium.en failed, using base.en result")
            return rc_base, text_base, err_base, "base.en (medium failed)", total_time
    
    elif use_large_model:
        # GPU mode only - long utterance gets large-v3 for best quality
        safe_print(f"[whisper-smart] Phase 2: Re-transcribing with large-v3 ({word_count} words)")
        rc_large, text_large, err_large = run_whisper(filename, bin_path, model_path=MODEL_PATH_LARGE)
        total_time = time.time() - start_time
        
        if rc_large == 0:
            safe_print(f"[whisper-smart] ✓ Total time: {total_time:.2f}s (base.en + large-v3)")
            return rc_large, text_large, err_large, "large-v3", total_time
        else:
            # Large failed - fall back to base result
            safe_print(f"[whisper-smart] Large-v3 failed, using base.en result")
            return rc_base, text_base, err_base, "base.en (large failed)", total_time
    
    else:
        # CPU mode - cap at medium.en for acceptable speed
        safe_print(f"[whisper-smart] CPU mode: Using medium.en ({word_count} words, large-v3 skipped)")
        rc_med, text_med, err_med = run_whisper(filename, bin_path, model_path=MODEL_PATH_MEDIUM)
        total_time = time.time() - start_time
        
        if rc_med == 0:
            safe_print(f"[whisper-smart] ✓ Total time: {total_time:.2f}s (base.en + medium.en, CPU-optimized)")
            return rc_med, text_med, err_med, "medium.en (CPU-optimized)", total_time
        else:
            safe_print(f"[whisper-smart] Medium.en failed, using base.en result")
            return rc_base, text_base, err_base, "base.en (medium failed)", total_time


def _get_audio_duration_sec(wav_path: str):
    """Return WAV duration in seconds, or None if unavailable."""
    try:
        info = sf.info(wav_path)
        if getattr(info, "samplerate", 0) and getattr(info, "frames", 0):
            return info.frames / float(info.samplerate)
    except Exception as e:
        log_line(f"[audio] duration probe failed for '{wav_path}': {e}", "warning")
    return None


def _transcribe_and_paste(wav_path):
    global last_transcription, target_window_on_record_start, pending_status_timer
    
    safe_print("[whisper] running...")
    set_status_safe("⚙️ Transcribing...", Theme.BG_ELEVATED, Theme.INFO, Theme.INFO)
    bin_path = (resolved_whisper_bin or WHISPER_BIN)
    
    try:
        rc, out, err, model_used, processing_duration_sec = run_whisper_smart(wav_path, bin_path)
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
    audio_duration_sec = _get_audio_duration_sec(wav_path)
    if audio_duration_sec is not None:
        log_line(
            f"[audio] duration_sec={audio_duration_sec:.3f} (processing_sec={processing_duration_sec:.3f})",
            "info",
        )
    else:
        log_line(
            f"[audio] duration unavailable; skipping WPM calculation (processing_sec={processing_duration_sec:.3f})",
            "warning",
        )

    raw = (out or "").strip()
    text = sanitize_transcript(raw)
    text = collapse_repetition_artifacts(text)

    banned = {"[ Silence ]", "[silence]", ""}
    if text in banned or len(text.replace("\n","" ).strip()) == 0:
        # Skip slow toast notification
        set_status_safe("🔇 Empty transcript", Theme.WARNING, Theme.BG_DARK, Theme.WARNING)
        return

    try:
        router_action = "disabled"
        router_handled = False
        if transcript_action_handler is not None:
            try:
                text, router_handled, router_action = transcript_action_handler(text, active_app_context)
            except Exception as handler_exc:
                log_line(f"[router] custom handler failed: {handler_exc}", "warning")
                router_handled = False
                router_action = "handler_error"
        elif MODE_ROUTER:
            text, router_handled, router_action = apply_router_action(text)

        if not router_handled:
            text = postprocess(text)
            text = collapse_repetition_artifacts(text)
        elif router_action != "file_command":
            # Keep anti-dup cleanup for dictation/grammar outputs only.
            text = collapse_repetition_artifacts(text)

        should_apply_final_sanitizer = (
            (not router_handled)
            or router_action in {"transcribe", "correction", "grammar_fix"}
        )
        if should_apply_final_sanitizer:
            before_final = text
            context_hint = active_app_context.app_type if active_app_context else ""
            text = sanitize_final_glitches(text, context=context_hint)
            if text != before_final:
                log_line("[sanitize] final glitch cleanup applied", "info")
        
        # Apply snippet trigger→replacement substitutions.
        # Runs after all post-processing so triggers match the cleaned text.
        before_snippets = text
        text = apply_snippets(text, SNIPPETS_FILE)
        if text != before_snippets:
            log_line("[snippets] applied trigger replacement", "info")

        # Optional LLM-powered stylization (runs on full text).
        _style_profile = _get_stylization_profile()
        if _style_profile not in ("off", "clean"):
            from whisper_local.processing.text_stylizer import TextStylizer
            if not hasattr(_transcribe_and_paste, '_stylizer'):
                _transcribe_and_paste._stylizer = TextStylizer(
                    model=OLLAMA_MODEL, endpoint=OLLAMA_ENDPOINT,
                )
            before_style = text
            text = _transcribe_and_paste._stylizer.stylize(text, _style_profile)
            if text != before_style:
                log_line(f"[STYLE] {_style_profile} profile applied", "info")

        # Store last transcription for manual copy access
        last_transcription = text

        # Background auto-learning — extract new vocab without blocking the paste.
        _text_for_learning = text
        def _run_context_learning():
            try:
                from whisper_local.continual_context import extract_and_learn
                added = extract_and_learn(_text_for_learning, OLLAMA_MODEL, OLLAMA_ENDPOINT)
                if added:
                    log_line(f"[CONTEXT] Learned: {', '.join(added)}", "info")
            except Exception:
                pass
        threading.Thread(target=_run_context_learning, daemon=True).start()

        # Check if our pill had focus when recording STARTED
        # Using captured focus state to avoid issues with UI updates changing focus
        # NOTE: Dashboard focus check removed - new pywebview dashboard is separate window
        our_window_focused = False

        try:
            if target_window_on_record_start:
                # OLD: Dashboard window focus check (commented out - using pywebview now)
                # if dashboard_window and dashboard_window.winfo_exists():
                #     dashboard_hwnd = int(dashboard_window.winfo_id())
                #     if target_window_on_record_start == dashboard_hwnd:
                #         our_window_focused = True

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
            word_count = len(text.split())
            threading.Thread(
                target=stats_tracker.record_transcription,
                args=(text, model_used, audio_duration_sec),
                daemon=True,
            ).start()

            # Log session progress
            current_session_words = stats_tracker.data.get('total_words', 0) + word_count - app_session_start_words
            debug_print(f"[SESSION] Added {word_count} words, session total will be: {current_session_words}")

            # Check achievements (async with delay to allow stats to save)
            wpm = round(word_count / (audio_duration_sec / 60.0)) if audio_duration_sec and audio_duration_sec > 0 else 0
            def check_achievements_delayed():
                time.sleep(0.5)  # Wait for stats to be saved
                try:
                    stats_summary = stats_tracker.get_summary()
                    check_achievements(text, word_count, wpm, stats_summary)
                except Exception as e:
                    debug_print(f"[ACHIEVEMENT] Error in delayed check: {e}")
            threading.Thread(target=check_achievements_delayed, daemon=True).start()

            set_status_safe("📋 Copied!", Theme.SUCCESS, Theme.TEXT_PRIMARY, Theme.SUCCESS)
            pending_status_timer = threading.Timer(1.5, lambda: set_status_safe("🎤 Ready", Theme.BG_ELEVATED, Theme.TEXT_PRIMARY, Theme.PINK_PRIMARY))
            pending_status_timer.start()
            safe_print("Copied to clipboard (dashboard focused)")
        else:
            # --- CONTEXT SANDWICH LOGIC ---
            from whisper_local.settings_manager import SettingsManager
            sandwich_active = False
            try:
                if SettingsManager().get_setting("context_sandwich"):
                    original_clipboard = pyperclip.paste()
                    if original_clipboard and original_clipboard.strip() and original_clipboard != text:
                        # Append the dictated text above the clipboard
                        text = f"{text}\n\n{original_clipboard}"
                        sandwich_active = True
            except Exception as e:
                debug_print(f"Context Sandwich error: {e}")

            # Use pyautogui for reliable paste (Win32 SendInput blocked by Windows security)
            if instant_paste(text):
                if sandwich_active:
                    try:
                        time.sleep(0.1) # Small delay to ensure host app processes paste before Enter
                        pyautogui.press('enter')
                    except Exception as e:
                        debug_print(f"Failed to press enter for sandwich: {e}")

                # Record stats async (don't block the paste experience)
                word_count = len(text.split())
                threading.Thread(
                    target=stats_tracker.record_transcription,
                    args=(text, model_used, audio_duration_sec),
                    daemon=True,
                ).start()

                # Log session progress
                current_session_words = stats_tracker.data.get('total_words', 0) + word_count - app_session_start_words
                debug_print(f"[SESSION] Added {word_count} words, session total will be: {current_session_words}")

                # Check achievements (async with delay to allow stats to save)
                wpm = round(word_count / (audio_duration_sec / 60.0)) if audio_duration_sec and audio_duration_sec > 0 else 0
                def check_achievements_delayed():
                    time.sleep(0.5)  # Wait for stats to be saved
                    try:
                        stats_summary = stats_tracker.get_summary()
                        check_achievements(text, word_count, wpm, stats_summary)
                    except Exception as e:
                        debug_print(f"[ACHIEVEMENT] Error in delayed check: {e}")
                threading.Thread(target=check_achievements_delayed, daemon=True).start()

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
            word_count = len(text.split())
            threading.Thread(
                target=stats_tracker.record_transcription,
                args=(text, model_used, audio_duration_sec),
                daemon=True,
            ).start()

            # Log session progress
            current_session_words = stats_tracker.data.get('total_words', 0) + word_count - app_session_start_words
            debug_print(f"[SESSION] Added {word_count} words (fallback), session total will be: {current_session_words}")

            # Check achievements (async with delay to allow stats to save)
            wpm = round(word_count / (audio_duration_sec / 60.0)) if audio_duration_sec and audio_duration_sec > 0 else 0
            def check_achievements_delayed():
                time.sleep(0.5)  # Wait for stats to be saved
                try:
                    stats_summary = stats_tracker.get_summary()
                    check_achievements(text, word_count, wpm, stats_summary)
                except Exception as e:
                    debug_print(f"[ACHIEVEMENT] Error in delayed check: {e}")
            threading.Thread(target=check_achievements_delayed, daemon=True).start()

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

    log_line("[rec] hotkey released - stopping recording")
    restore_requested = audio_ducking_manager.release(reason="recording_stop")
    log_line(f"DUCK_RESTORE requested_by=recording_stop pending_or_done={restore_requested}")

    try:
        # Play sound effect to give immediate audio feedback that recording stopped
        play_recording_stop_sound()

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
            return

        _transcribe_and_paste(WAV_TMP)
    except Exception as e:
        log_line(f"[rec] stop/transcribe error: {e}", "error")
        set_status_safe("❌ Error", Theme.ERROR, Theme.TEXT_PRIMARY, Theme.ERROR)
    finally:
        forced_restore = audio_ducking_manager.force_restore(reason="stop_finally")
        log_line(f"DUCK_RESTORE requested_by=stop_finally forced={forced_restore}")
        with STATE_LOCK:
            transcribing_flag.clear()

def on_hotkey_press(e):
    if not recording_flag.is_set():
        start_recording()

def on_hotkey_release(e):
    if recording_flag.is_set():
        stop_recording_and_transcribe()
    else:
        release = audio_ducking_manager.release(reason="release_without_recording")
        log_line(f"DUCK_RESTORE requested_by=release_without_recording pending_or_done={release}")


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
    debug_dir = os.path.join(get_user_data_dir(), "debug")
    os.makedirs(debug_dir, exist_ok=True)
    for bin_path in candidates:
        name = os.path.basename(bin_path)
        exe = os.path.abspath(_resolve_whisper_exe(bin_path))
        cmd = build_whisper_cmd(exe, MODEL_PATH, sample, base_args=["-nt"]) 
        log_line(f"[debug] running: {' '.join(cmd)}")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=WHISPER_TIMEOUT_SEC, creationflags=CREATE_NO_WINDOW)
            raw = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
            san = sanitize_transcript(raw)
            with open(os.path.join(debug_dir, f"flow_debug_{name}_raw.txt"), "w", encoding="utf-8") as f:
                f.write(raw)
            with open(os.path.join(debug_dir, f"flow_debug_{name}_sanitized.txt"), "w", encoding="utf-8") as f:
                f.write(san)
            banner_present = ("deprecated" in raw.lower()) or ("please use" in raw.lower())
            log_line(
                f"[debug] {name}: rc={res.returncode} banner={'yes' if banner_present else 'no'}; "
                f"files in {debug_dir}"
            )
        except Exception as e:
            log_line(f"[debug] error running {name}: {e}")
    notify(f"Debug probe complete (see {debug_dir} and log)")

tray_icon = None
listening_enabled = True
# When True the recording is kept alive without holding the hotkey (toggle mode).
latch_recording = False

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
    try:
        if gui and gui.root and gui.root.winfo_exists():
            ui_queue.put((gui.set_status, (("armed" if listening_enabled else "idle"),)))
    except Exception:
        pass


def _tray_toggle_router(_=None):
    global MODE_ROUTER, voice_router
    MODE_ROUTER = not MODE_ROUTER
    if not MODE_ROUTER:
        voice_router = None
    state = "enabled" if MODE_ROUTER else "disabled"
    notify(f"Voice agent router {state}")


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
    """Open dashboard from tray via the shared launcher."""
    _launch_dashboard_from_ui_trigger()

def _tray_quit(_=None):
    log_line("[TRAY] User selected Quit from tray menu")
    try:
        if recording_flag.is_set():
            stop_recording_and_transcribe()
        restored = audio_ducking_manager.force_restore(reason="tray_quit")
        log_line(f"DUCK_RESTORE requested_by=tray_quit forced={restored}")
        # Stop GPU monitoring
        gpu_monitor.stop_monitoring()
    finally:
        os._exit(0)

def _tray_restart_gui(_=None):
    """Restart the GUI window without killing the whole application."""
    log_line("[TRAY] User selected Restart GUI from tray menu")
    notify("Restarting GUI...")

    def restore_or_create_gui():
        global gui
        try:
            if gui and gui.root and gui.root.winfo_exists():
                gui.set_status("ready")
                gui.show()
                try:
                    gui.root.lift()
                    gui.root.focus_force()
                except Exception:
                    pass
                log_line(
                    f"HUD_BACKEND={gui.__class__.__name__} "
                    f"HUD_BACKEND_MODULE={gui.__class__.__module__} path=restart_restore"
                )
                log_line("[GUI_RESTART] Existing GUI restored")
                notify(f"✅ GUI restored! Hold {_hotkey_display_text(HOTKEY_HOLD)} to speak.")
                return
        except Exception:
            pass

        try:
            gui = _create_status_hud()
            gui.set_status("armed" if listening_enabled else "idle")
            gui.show()
            log_line(
                f"HUD_BACKEND={gui.__class__.__name__} "
                f"HUD_BACKEND_MODULE={gui.__class__.__module__} path=restart_new"
            )
            log_line("[GUI_RESTART] New GUI created successfully")
            notify(f"✅ GUI restarted! Hold {_hotkey_display_text(HOTKEY_HOLD)} to speak.")
        except Exception as e:
            log_line(f"[GUI_RESTART_ERROR] Failed to create GUI: {e}\n{traceback.format_exc()}", "error")
            notify(f"❌ Failed to restart GUI: {e}")

    ui_queue.put((restore_or_create_gui, ()))

def start_tray():
    global tray_icon
    icon_path = res_path(os.path.join("ui", "assets", "mic_logo.png"))
    try:
        img = Image.open(icon_path)
    except Exception as e:
        log_line(f"Failed to load new mic logo for tray: {e}", "warning")
        # Fallback to the generated waveform icon
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        try:
            theme_id = SettingsManager().get_setting("theme")
        except Exception:
            theme_id = "hot_pink"
            
        if theme_id == "neon_dark":
            c = (187, 134, 252, 255) # bb86fc
        elif theme_id == "midnight_green":
            c = (0, 230, 118, 255) # 00e676
        else:
            c = (255, 20, 147, 255) # FF1493
        
        # Draw 4 vertical bars forming a waveform
        draw.rounded_rectangle([4, 12, 8, 20], radius=2, fill=c)
        draw.rounded_rectangle([10, 8, 14, 24], radius=2, fill=c)
        draw.rounded_rectangle([16, 4, 20, 28], radius=2, fill=c)
        draw.rounded_rectangle([22, 10, 26, 22], radius=2, fill=c)
    
    tray_icon = pystray.Icon(
        "Impulse",
        img,
        "Impulse",
        menu=pystray.Menu(
            pystray.MenuItem("Open Dashboard", _tray_open_dashboard, default=True),
            pystray.MenuItem("Toggle Listening", _tray_toggle),
            pystray.MenuItem("Toggle Agent Router", _tray_toggle_router),
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

def run_whisper_main_loop():
    """Run the whisper/hotkey/recording loop in a background thread.

    This function contains all the logic for listening to hotkeys,
    recording audio, and transcribing. It runs independently of the
    main GUI thread.
    """
    safe_print("=" * 60)
    safe_print(f"◉ {APP_NAME} v{APP_VERSION}")
    safe_print("=" * 60)

    # Show debug mode indicator
    if DEBUG_MODE:
        debug_print('')
        debug_print('=' * 60)
        debug_print('🐛 DEBUG MODE ACTIVE')
        debug_print('   Console output enabled for troubleshooting')
        debug_print('   All [DEBUG] messages will be shown')
        debug_print('=' * 60)
        debug_print('')

    safe_print("📌 Controls:")
    safe_print(f"  • Hold {_hotkey_display_text(HOTKEY_HOLD)} to record")
    safe_print("  • Release to transcribe & paste")
    safe_print("  • Dashboard shows status and stats")
    safe_print(f"  • Agent router: {'ON' if MODE_ROUTER else 'OFF'} ({ROUTER_MODEL})")
    safe_print("  • ESC to exit")
    safe_print("=" * 60)

    # Check for first run (skip wizard for now in background thread mode)
    if is_first_run():
        safe_print("First run detected - marking as complete...")
        mark_first_run_complete()

    # Initialize FloatingPill GUI (required for event loop and hotkey polling)
    global gui
    restored_stale_duck = audio_ducking_manager.restore_stale_state()
    log_line(f"DUCK_STARTUP_RESTORE restored={restored_stale_duck}")
    log_line(
        f"DUCK_BACKEND_AVAILABLE available={audio_ducking_manager.is_available} "
        f"backend={audio_ducking_manager.backend_name}"
    )
    gui = _create_status_hud()
    log_line(
        f"HUD_BACKEND={gui.__class__.__name__} "
        f"HUD_BACKEND_MODULE={gui.__class__.__module__} path=startup"
    )
    gui.set_hotkey_hint(HOTKEY_HOLD)
    gui.set_status("armed" if listening_enabled else "idle")

    startup_diagnostics()
    
    # Start GPU monitoring in background
    safe_print("🔍 Starting GPU monitoring...")
    gpu_monitor.start_monitoring()
    
    # Start CUDA warmup in background (pre-load GPU model for instant first transcription)
    threading.Thread(target=cuda_warmup, daemon=True).start()
    
    try:
        device_lines = devices_summary_text()
        notify(f"✅ Ready! Hold {_hotkey_display_text(HOTKEY_HOLD)} to speak.")
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

    active_hotkey_keys = HOTKEY_KEYS if HOTKEY_KEYS else ["ctrl", "windows"]
    active_hotkey_combo = [HOTKEY_HOLD]
    hotkey_settings_mtime = [_settings_mtime(SETTINGS_FILE)]
    last_hotkey_reload_ts = [0.0]
    settings_shortcut_keys = ["ctrl", "windows", "s"]

    def refresh_runtime_hotkey_binding(force: bool = False):
        now = time.time()
        if not force and (now - last_hotkey_reload_ts[0]) < 1.0:
            return
        last_hotkey_reload_ts[0] = now

        mtime = _settings_mtime(SETTINGS_FILE)
        if not force and mtime == hotkey_settings_mtime[0]:
            return

        loaded_combo = load_hotkey(SETTINGS_FILE)
        loaded_keys = hotkey_tokens(loaded_combo) or ["ctrl", "windows"]

        changed = loaded_keys != active_hotkey_keys
        active_hotkey_keys[:] = loaded_keys
        active_hotkey_combo[0] = loaded_combo
        hotkey_settings_mtime[0] = mtime

        if changed:
            log_line(f"[HOTKEY] Active hold shortcut updated to: {active_hotkey_combo[0]}")
            try:
                if gui and gui.root and gui.root.winfo_exists():
                    ui_queue.put((gui.set_hotkey_hint, (active_hotkey_combo[0],)))
                    if not recording_flag.is_set() and not transcribing_flag.is_set():
                        ui_queue.put((gui.set_status, (("armed" if listening_enabled else "idle"),)))
            except Exception:
                pass

    # Track ESC key state for debouncing
    esc_pressed_start = [None]  # Use list for nonlocal mutation
    last_keyboard_check_error = [0]  # Track keyboard library errors
    keyboard_error_count = [0]  # Count consecutive errors

    def poll_hotkey():
        nonlocal was_down
        global last_edge_ts, latch_recording

        try:
            refresh_runtime_hotkey_binding()
        except Exception as e:
            now = time.time()
            if now - last_keyboard_check_error[0] > 30:
                log_line(f"[HOTKEY_WARNING] Hotkey refresh failed: {e}", "warning")
                last_keyboard_check_error[0] = now
        
        # Check for keyboard library issues
        try:
            down = listening_enabled and _are_all_keys_pressed(active_hotkey_keys)
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
            if _are_all_keys_pressed(settings_shortcut_keys):
                _launch_dashboard_from_ui_trigger()
        except Exception:
            pass

        # ------------------------------------------------------------------
        # Ctrl+Win+Alt  → latch toggle (hold-free recording)
        # ------------------------------------------------------------------
        latch_keys = ["ctrl", "windows", "alt"]
        try:
            latch_chord_down = _are_all_keys_pressed(latch_keys)
        except Exception:
            latch_chord_down = False

        if latch_chord_down and not getattr(poll_hotkey, "_latch_chord_was_down", False):
            # Rising edge of latch chord – toggle latch mode
            now = time.time()
            if (now - last_edge_ts) * 1000 > EDGE_COOLDOWN_MS:
                last_edge_ts = now
                if not latch_recording:
                    # Turn latch ON: start recording hands-free
                    log_line("[LATCH] Ctrl+Win+Alt pressed – enabling latch recording")
                    latch_recording = True
                    on_hotkey_press(None)
                else:
                    # Turn latch OFF: stop recording and transcribe
                    log_line("[LATCH] Ctrl+Win+Alt pressed – disabling latch recording")
                    latch_recording = False
                    threading.Thread(target=stop_recording_and_transcribe, daemon=True).start()
        poll_hotkey._latch_chord_was_down = latch_chord_down

        # ------------------------------------------------------------------
        # Ctrl+Win+Shift  → cycle stylization profile
        # ------------------------------------------------------------------
        style_keys = ["ctrl", "windows", "shift"]
        try:
            style_chord_down = _are_all_keys_pressed(style_keys)
        except Exception:
            style_chord_down = False

        if style_chord_down and not getattr(poll_hotkey, "_style_chord_was_down", False):
            now_style = time.time()
            if (now_style - last_edge_ts) * 1000 > EDGE_COOLDOWN_MS:
                last_edge_ts = now_style
                from whisper_local.processing.text_stylizer import next_profile, PROFILES
                global _flow_settings_mgr
                cur = _get_stylization_profile()
                nxt = next_profile(cur)
                # Persist so dashboard and next transcription pick it up
                try:
                    if _flow_settings_mgr is None:
                        from whisper_local.settings_manager import SettingsManager
                        _flow_settings_mgr = SettingsManager()
                    _flow_settings_mgr.update_setting("stylization_profile", nxt)
                except Exception:
                    pass
                label = PROFILES.get(nxt, {}).get("label", nxt)
                log_line(f"[STYLE] Cycled to: {label}")
        poll_hotkey._style_chord_was_down = style_chord_down

        # ------------------------------------------------------------------
        # Normal hold-to-record (only when not in latch mode)
        # ------------------------------------------------------------------
        now = time.time()
        if not latch_recording:
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
        
        gui.root.after(HOTKEY_POLL_MS, poll_hotkey)

    refresh_runtime_hotkey_binding(force=True)
    gui.pump_queue()
    gui.root.after(HOTKEY_POLL_MS, poll_hotkey)
    
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
    restored = audio_ducking_manager.force_restore(reason="mainloop_exit")
    log_line(f"DUCK_RESTORE requested_by=mainloop_exit forced={restored}")
    safe_print("Bye.")

if __name__ == "__main__":
    _acquire_single_instance()  # Acquire singleton lock only when running directly
    start_tray()
    run_whisper_main_loop()
