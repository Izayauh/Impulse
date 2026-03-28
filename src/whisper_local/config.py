"""
Configuration management for WhisperLocal.

This module contains all configuration constants, path resolution,
and environment variable handling.
"""

import os
import sys
import json
import datetime
from pathlib import Path
import logging

from typing import Optional

from whisper_local.gpu_monitor import gpu_monitor

logger = logging.getLogger(__name__)


def debug_print(*args, **kwargs):
    """Module-local debug print compatible with previous callsites."""
    try:
        logger.debug(" ".join(str(a) for a in args))
    except Exception:
        pass


# ============================================================================
# APPLICATION METADATA
# ============================================================================
APP_NAME = "WhisperLocal"
APP_VERSION = "1.0.5"
APP_AUTHOR = "WhisperLocal"


# ============================================================================
# AUDIO RECORDING CONSTANTS
# ============================================================================
SAMPLE_RATE_HZ = 16000  # 16kHz sample rate for Whisper compatibility
AUDIO_CHANNELS = 1  # Mono recording for speech

# Voice Activity Detection (VAD) thresholds
RMS_THRESHOLD_VOICED = 0.002  # Minimum RMS to consider audio as "voiced"
SILENCE_RMS_THRESHOLD_CONFIG = 0.008  # Threshold for silence detection

# Timing constants for recording
MIN_SPEECH_DURATION_SEC = 0.2  # Minimum duration of speech to process
AUDIO_BLOCK_DURATION_SEC = 0.05  # Audio block size for RMS calculation
PREROLL_DURATION_SEC = 2.0  # Audio buffer before speech detection
POSTROLL_DURATION_SEC = 0.15  # Continue recording after key release


# ============================================================================
# TRANSCRIPTION CONSTANTS
# ============================================================================
WHISPER_PROCESS_TIMEOUT_SEC = 120  # 2 minutes max per transcription

# Word count thresholds for dynamic model selection
WORD_THRESHOLD_FAST = 25  # <25 words: use base.en
WORD_THRESHOLD_BALANCED = 75  # 25-75 words: use medium.en


# ============================================================================
# UI INTERACTION CONSTANTS
# ============================================================================
HOTKEY_DEBOUNCE_MS = 150  # Minimum ms between hotkey state changes
UI_ANIMATION_FPS = 15  # Frame rate for pulse animations
UI_QUEUE_POLL_MS = 50  # How often to check UI update queue
HOTKEY_POLL_MS = 50  # How often to check hotkey state (20 Hz, responsive)
STATUS_SUCCESS_DISPLAY_SEC = 1.5  # How long to show success messages
CLIPBOARD_SETTLE_DELAY_SEC = 0.05  # Delay after clipboard copy before paste


# ============================================================================
# INPUT VALIDATION CONSTANTS
# ============================================================================
MAX_TRANSCRIPT_SIZE_BYTES = 1024 * 1024  # 1 MB max transcript size
MAX_TRANSCRIPT_LINE_COUNT = 10000  # Maximum lines to process
MAX_LINE_LENGTH_CHARS = 10000  # Maximum characters per line


# ============================================================================
# TELEMETRY CONSTANTS
# ============================================================================
TELEMETRY_VERSION = 1
TELEMETRY_SUBMIT_INTERVAL_SEC = 300  # Batch submissions every 5 minutes
TELEMETRY_GITHUB_OWNER = "Izayauh"
TELEMETRY_GITHUB_REPO = "whisper"


# ============================================================================
# PATH RESOLUTION
# ============================================================================
def is_frozen() -> bool:
    """Check if running as a PyInstaller bundle."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_bundle_dir() -> str:
    """Get the directory where bundled resources are located."""
    if is_frozen():
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_app_dir() -> str:
    """Get the application directory (where the exe is located, or script dir in dev)."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    # In development, go up to project root from src/whisper_local
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_user_data_dir() -> str:
    """Get the user data directory for config, logs, and temp files."""
    if is_frozen():
        appdata = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        data_dir = os.path.join(appdata, APP_NAME)
        os.makedirs(data_dir, exist_ok=True)
        debug_print(f"[DEBUG] get_user_data_dir (whisper_local/config.py): {data_dir}")
        return data_dir
    # In development, keep runtime outputs isolated from source tree.
    result = os.path.join(get_app_dir(), "output")
    for rel in ("logs", "audio", "transcripts", "state"):
        os.makedirs(os.path.join(result, rel), exist_ok=True)
    debug_print(f"[DEBUG] get_user_data_dir (whisper_local/config.py): {result}")
    return result


def get_config_file() -> str:
    """Get the path to the config file."""
    return os.path.join(get_user_data_dir(), "state", "config.json")


def is_first_run() -> bool:
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
        except (json.JSONDecodeError, IOError, OSError) as e:
            print(f"Warning: Config file corrupted, using defaults: {e}")
    
    config['first_run_complete'] = True
    config['version'] = APP_VERSION
    config['install_date'] = datetime.datetime.now().isoformat()
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
    except (IOError, OSError) as e:
        print(f"Warning: Could not save config: {e}")


# ============================================================================
# MODEL PATHS
# ============================================================================
_bundle_dir = get_bundle_dir()
_app_dir = get_app_dir()
_user_dir = get_user_data_dir()

MODEL_BASE = os.path.join("runtime", "models", "ggml-base.en.bin")
MODEL_MEDIUM = os.path.join("runtime", "models", "ggml-medium.en.bin")
MODEL_LARGE = os.path.join("runtime", "models", "ggml-large-v3.bin")

# Word count thresholds
WORD_THRESHOLD_BASE = WORD_THRESHOLD_FAST
WORD_THRESHOLD_MEDIUM = WORD_THRESHOLD_BALANCED


# ============================================================================
# WHISPER BINARY RESOLUTION
# ============================================================================
def get_whisper_binary() -> Optional[str]:
    """Find the Whisper binary executable."""
    candidates = [
        os.path.join(_bundle_dir, "whisper-cli.exe"),
        os.path.join(_bundle_dir, "main.exe"),
        os.path.join(_app_dir, "whisper-cli.exe"),
        os.path.join(_app_dir, "main.exe"),
        os.path.join(".", "whisper-cli.exe"),
        os.path.join(".", "main.exe"),
    ]
    
    # Add legacy dev paths if whisper.cpp directory exists
    if os.path.exists("whisper.cpp"):
        candidates.extend([
            os.path.join("whisper.cpp", "build", "bin", "Release", "whisper-cli.exe"),
            os.path.join("whisper.cpp", "build", "bin", "Debug", "whisper-cli.exe"),
        ])
    
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    
    return None


# ============================================================================
# FILE PATHS
# ============================================================================
WAV_TMP = os.path.join(_user_dir, "audio", "flow_input.wav")
TEXT_TMP_BASE = os.path.join(_user_dir, "transcripts", "flow_out")
LOG_FILE = os.path.join(_user_dir, "logs", "flow.log")
STATS_FILE = os.path.join(_user_dir, "state", "whisper_stats.json")


# ============================================================================
# CONFIGURATION CLASS
# ============================================================================
class Config:
    """Application configuration singleton."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.app_name = APP_NAME
        self.app_version = APP_VERSION
        self.app_author = APP_AUTHOR
        
        # Paths
        self.bundle_dir = _bundle_dir
        self.app_dir = _app_dir
        self.user_dir = _user_dir
        self.config_file = get_config_file()
        self.log_file = LOG_FILE
        self.stats_file = STATS_FILE
        self.wav_tmp = WAV_TMP
        
        # Audio settings
        self.sample_rate = SAMPLE_RATE_HZ
        self.channels = AUDIO_CHANNELS
        self.rms_threshold = RMS_THRESHOLD_VOICED
        self.silence_threshold = SILENCE_RMS_THRESHOLD_CONFIG
        
        # Transcription settings
        self.whisper_timeout = WHISPER_PROCESS_TIMEOUT_SEC
        self.whisper_binary = get_whisper_binary()
        
        # Model paths
        self.model_base = MODEL_BASE
        self.model_medium = MODEL_MEDIUM
        self.model_large = MODEL_LARGE
        
        # Word thresholds
        self.word_threshold_base = WORD_THRESHOLD_BASE
        self.word_threshold_medium = WORD_THRESHOLD_MEDIUM
        
        # UI settings
        self.hotkey_debounce = HOTKEY_DEBOUNCE_MS
        self.ui_poll_rate = UI_QUEUE_POLL_MS
        
        # Input validation
        self.max_transcript_bytes = MAX_TRANSCRIPT_SIZE_BYTES
        self.max_transcript_lines = MAX_TRANSCRIPT_LINE_COUNT
        
        # Environment variable overrides
        self._apply_env_overrides()
        
        self._initialized = True
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        # Whisper binary override
        if os.environ.get("FLOW_WHISPER_BIN"):
            self.whisper_binary = os.environ["FLOW_WHISPER_BIN"]
        
        # Input device override
        if os.environ.get("FLOW_INPUT_DEVICE"):
            self.input_device = os.environ["FLOW_INPUT_DEVICE"]
        
        # CUDA enable/disable
        if gpu_monitor.is_nvidia_gpu():
            os.environ.setdefault("GGML_CUDA_ENABLE", "1")
        else:
            os.environ.setdefault("GGML_CUDA_ENABLE", "0")
    
    def get(self, key: str, default=None):
        """Get a configuration value."""
        return getattr(self, key, default)


# Create global config instance
config = Config()

