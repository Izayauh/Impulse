import os, subprocess, time, threading, queue, datetime, shlex
import sys, shutil, tempfile, uuid
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
    """Direct Win32 clipboard copy - faster than pyperclip."""
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
    except Exception:
        return False

def fast_send_paste() -> bool:
    """Direct SendInput for Ctrl+V - faster than pyautogui."""
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
    except Exception:
        return False

def instant_paste(text: str) -> bool:
    """Reliable paste using pyperclip + pyautogui (Win32 blocked by Windows security)."""
    # Win32 SendInput gets blocked by Windows UIPI after first use - use pyautogui instead
    try:
        pyperclip.copy(text)
        time.sleep(0.05)  # Small delay to ensure clipboard is ready
        pyautogui.hotkey("ctrl", "v")
        return True
    except Exception:
        return False

# ============================================================================
# THEME CONSTANTS - Pink/Black Dark Mode
# ============================================================================
class Theme:
    # Background colors
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
    
    # Sizes
    PILL_WIDTH = 180
    PILL_HEIGHT = 36
    PILL_RADIUS = 18
    
    DASHBOARD_WIDTH = 420
    DASHBOARD_HEIGHT = 580

# ============================================================================
# STATS TRACKING SYSTEM
# ============================================================================
STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whisper_stats.json")

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
        except Exception:
            pass
        return default
    
    def _save(self):
        """Save stats to JSON file."""
        try:
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Stats save error: {e}")
    
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

# Auto-detect whisper binary in current directory (no hardcoded paths)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_default_bin = os.path.join(_script_dir, "whisper-cli.exe")
if not os.path.isfile(_default_bin):
    _default_bin = os.path.join(_script_dir, "main.exe")

os.environ.setdefault("FLOW_WHISPER_BIN", _default_bin)
os.environ.setdefault("WHISPER_BIN", os.environ["FLOW_WHISPER_BIN"])
os.environ.setdefault("FLOW_WHISPER_ARGS", "-ngl 99")

_bin = os.environ.get("FLOW_WHISPER_BIN")
if _bin and not os.path.isfile(_bin):
    print(f"Warning: FLOW_WHISPER_BIN not found: {_bin}, will try to auto-detect...")

# Prefer winotify for reliable Windows 10/11 notifications; fall back gracefully if unavailable
try:
    from winotify import Notification, audio
except Exception:
    Notification = None
    audio = None

# --- Single-instance guard (Windows) ---
import tempfile, uuid, msvcrt

_SINGLETON_LOCK = None
def _acquire_single_instance():
    global _SINGLETON_LOCK
    lock_path = os.path.join(tempfile.gettempdir(), "flow_local_dictation.lock")
    _SINGLETON_LOCK = open(lock_path, "w")
    try:
        msvcrt.locking(_SINGLETON_LOCK.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        print("Already running. Exiting.")
        sys.exit(0)

_acquire_single_instance()

# --- Config ---
# Model paths for dynamic selection based on word count
MODEL_BASE = os.path.join("models", "ggml-base.en.bin")
MODEL_MEDIUM = os.path.join("models", "ggml-medium.en.bin")
MODEL_LARGE = os.path.join("models", "ggml-large-v3.bin")

# Word count thresholds for model selection
WORD_THRESHOLD_BASE = 25    # Use base.en for <25 words (fastest)
WORD_THRESHOLD_MEDIUM = 75  # Use medium.en for 25-75 words (balanced)
                            # Use large-v3 for 75+ words (highest quality)

# Legacy default (will be dynamically selected)
MODEL_PATH_REL = MODEL_LARGE  # fallback if dynamic selection fails
WHISPER_BIN = os.environ.get("WHISPER_BIN") or os.path.join(".", "main.exe")
SAMPLE_RATE = 16000
CHANNELS = 1
WAV_TMP = "flow_input.wav"
TEXT_TMP_BASE = "flow_out"  # base name for whisper-cli text output
HOTKEY_HOLD = "windows+ctrl"    # hold to talk; release to transcribe
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

# Timeout for whisper subprocess (seconds)
WHISPER_TIMEOUT_SEC = 120

# Silence detection during recording (on normalized float32 audio)
SILENCE_RMS_THRESHOLD = 0.008
MIN_SPOKEN_BLOCKS = 3

# Log file for diagnostics
LOG_FILE = "flow.log"

# Whisper binary detection candidates (prefer whisper-cli.exe in script directory)
_script_dir = os.path.dirname(os.path.abspath(__file__)) or "."
WHISPER_CANDIDATES = [
    os.path.join(_script_dir, "whisper-cli.exe"),
    os.path.join(_script_dir, "main.exe"),
    os.path.join(".", "whisper-cli.exe"),
    os.path.join(".", "main.exe"),
    os.path.join("whisper.cpp", "build", "bin", "Release", "whisper-cli.exe"),
    os.path.join("whisper.cpp", "build", "bin", "Debug", "whisper-cli.exe"),
]

# Resolved at startup
resolved_whisper_bin = None

# Concurrency & debounce
STATE_LOCK = threading.Lock()
transcribing_flag = threading.Event()
last_edge_ts = 0.0
EDGE_COOLDOWN_MS = 150

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
        
        # Glow effect for listening state
        if state == "listening":
            glow_size = 3 + int(pulse * 2)
            glow_alpha = 0.3 + pulse * 0.2
            # Draw glow layers
            for i in range(glow_size, 0, -1):
                alpha = int((glow_alpha / glow_size) * i * 255)
                glow_color = self._blend_color(Theme.PINK_PRIMARY, Theme.BG_DARKEST, i / glow_size)
                self._draw_rounded_rect(
                    2 - i, 2 - i, w - 2 + i, h - 2 + i, r + i,
                    fill=glow_color, outline=""
                )
        
        # Main pill background
        self._draw_rounded_rect(2, 2, w - 2, h - 2, r, fill=bg_color, outline=accent_color)
        
        # Accent dot/icon
        dot_x = 18
        dot_y = h // 2
        if state == "listening":
            # Pulsing dot
            dot_r = 4 + int(pulse * 2)
            self.canvas.create_oval(
                dot_x - dot_r, dot_y - dot_r,
                dot_x + dot_r, dot_y + dot_r,
                fill=accent_color, outline=""
            )
        else:
            # Static indicator
            self.canvas.create_oval(
                dot_x - 4, dot_y - 4,
                dot_x + 4, dot_y + 4,
                fill=accent_color, outline=""
            )
        
        # Status text
        self.canvas.create_text(
            w // 2 + 8, h // 2,
            text=text.split("  ")[1] if "  " in text else text,
            fill=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, 10, "bold"),
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

        x = (sw - self.width) // 2
        y = sh - self.height - 12
        if res:
            edge = abd.uEdge
            rc = abd.rc
            if edge == ABE_BOTTOM:
                y = rc.top - self.height - 12
                x = (sw - self.width) // 2
            elif edge == ABE_TOP:
                y = rc.bottom + 12
                x = (sw - self.width) // 2
            elif edge == ABE_LEFT:
                x = rc.right + 12
                y = sh - self.height - 12
            elif edge == ABE_RIGHT:
                x = rc.left - self.width - 12
                y = sh - self.height - 12

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
        self.title_bar = tk.Frame(self, bg=Theme.BG_ELEVATED, height=40)
        self.title_bar.pack(fill="x")
        self.title_bar.pack_propagate(False)
        
        # App icon/logo
        logo_label = tk.Label(
            self.title_bar, 
            text="◉", 
            font=(Theme.FONT_FAMILY, 16),
            fg=Theme.PINK_PRIMARY,
            bg=Theme.BG_ELEVATED
        )
        logo_label.pack(side="left", padx=(12, 6))
        
        # Title
        title_label = tk.Label(
            self.title_bar,
            text="Whisper Local",
            font=(Theme.FONT_FAMILY, 11, "bold"),
            fg=Theme.TEXT_PRIMARY,
            bg=Theme.BG_ELEVATED
        )
        title_label.pack(side="left")
        
        # Close button
        close_btn = tk.Label(
            self.title_bar,
            text="✕",
            font=(Theme.FONT_FAMILY, 12),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_ELEVATED,
            cursor="hand2"
        )
        close_btn.pack(side="right", padx=12)
        close_btn.bind("<Button-1>", lambda e: self.destroy())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg=Theme.ERROR))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg=Theme.TEXT_SECONDARY))
        
        # Minimize button
        min_btn = tk.Label(
            self.title_bar,
            text="─",
            font=(Theme.FONT_FAMILY, 12),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_ELEVATED,
            cursor="hand2"
        )
        min_btn.pack(side="right", padx=4)
        min_btn.bind("<Button-1>", lambda e: self.iconify())
        min_btn.bind("<Enter>", lambda e: min_btn.config(fg=Theme.TEXT_PRIMARY))
        min_btn.bind("<Leave>", lambda e: min_btn.config(fg=Theme.TEXT_SECONDARY))
    
    def _create_content(self):
        """Create main content area."""
        content = tk.Frame(self, bg=Theme.BG_DARK)
        content.pack(fill="both", expand=True, padx=16, pady=16)
        
        # Stats cards row
        cards_frame = tk.Frame(content, bg=Theme.BG_DARK)
        cards_frame.pack(fill="x", pady=(0, 16))
        
        self.today_card = self._create_stat_card(cards_frame, "Today", "0", "words")
        self.today_card.pack(side="left", expand=True, fill="x", padx=(0, 8))
        
        self.week_card = self._create_stat_card(cards_frame, "This Week", "0", "words")
        self.week_card.pack(side="left", expand=True, fill="x", padx=(0, 8))
        
        self.total_card = self._create_stat_card(cards_frame, "Total", "0", "words")
        self.total_card.pack(side="left", expand=True, fill="x")
        
        # Streak and milestone row
        gamify_frame = tk.Frame(content, bg=Theme.BG_DARK)
        gamify_frame.pack(fill="x", pady=(0, 16))
        
        self.streak_card = self._create_streak_card(gamify_frame)
        self.streak_card.pack(side="left", expand=True, fill="x", padx=(0, 8))
        
        self.milestone_card = self._create_milestone_card(gamify_frame)
        self.milestone_card.pack(side="left", expand=True, fill="x")
        
        # Activity graph
        graph_label = tk.Label(
            content,
            text="Last 7 Days",
            font=(Theme.FONT_FAMILY, 10),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_DARK,
            anchor="w"
        )
        graph_label.pack(fill="x", pady=(0, 8))
        
        self.graph_canvas = Canvas(
            content,
            height=110,
            bg=Theme.BG_CARD,
            highlightthickness=1,
            highlightbackground=Theme.BORDER_SUBTLE
        )
        self.graph_canvas.pack(fill="x", pady=(0, 16))
        
        # Bind configure event to redraw graph when canvas is ready
        self.graph_canvas.bind("<Configure>", lambda e: self._draw_graph(stats_tracker.get_week_data()))
        
        # Recent transcripts
        recent_label = tk.Label(
            content,
            text="Recent",
            font=(Theme.FONT_FAMILY, 10),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_DARK,
            anchor="w"
        )
        recent_label.pack(fill="x", pady=(0, 8))
        
        self.recent_frame = tk.Frame(content, bg=Theme.BG_CARD, highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE)
        self.recent_frame.pack(fill="both", expand=True, pady=(0, 12))
        
        # Status label for feedback
        self.status_label = tk.Label(
            content,
            text="",
            font=(Theme.FONT_FAMILY, 9),
            fg=Theme.SUCCESS,
            bg=Theme.BG_DARK,
            anchor="center"
        )
        self.status_label.pack(fill="x", pady=(0, 8))
        
        # Quick actions
        actions_frame = tk.Frame(content, bg=Theme.BG_DARK)
        actions_frame.pack(fill="x")
        
        self.copy_last_btn = self._create_action_button(actions_frame, "📋 Copy Last", self._copy_last_message)
        self.copy_last_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))
        self._create_action_button(actions_frame, "⚙ Settings", lambda: open_settings_window(self)).pack(side="left", expand=True, fill="x", padx=(0, 8))
        self._create_action_button(actions_frame, "↻ Refresh", self._refresh_stats).pack(side="left", expand=True, fill="x")
    
    def _create_stat_card(self, parent, label, value, unit):
        """Create a stat card widget."""
        card = tk.Frame(parent, bg=Theme.BG_CARD, highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE)
        card.pack_propagate(False)
        card.configure(height=90)
        
        inner = tk.Frame(card, bg=Theme.BG_CARD)
        inner.pack(expand=True, fill="both", padx=12, pady=12)
        
        label_widget = tk.Label(
            inner,
            text=label,
            font=(Theme.FONT_FAMILY, 9),
            fg=Theme.TEXT_MUTED,
            bg=Theme.BG_CARD,
            anchor="w"
        )
        label_widget.pack(anchor="w", pady=(0, 2))
        
        value_widget = tk.Label(
            inner,
            text=value,
            font=(Theme.FONT_FAMILY, 22, "bold"),
            fg=Theme.PINK_PRIMARY,
            bg=Theme.BG_CARD,
            anchor="w"
        )
        value_widget.pack(anchor="w", pady=(0, 1))
        
        unit_widget = tk.Label(
            inner,
            text=unit,
            font=(Theme.FONT_FAMILY, 9),
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
        card.configure(height=80)
        card.pack_propagate(False)
        
        inner = tk.Frame(card, bg=Theme.BG_CARD)
        inner.pack(expand=True, fill="both", padx=12, pady=12)
        
        # Flame emoji + streak count
        streak_row = tk.Frame(inner, bg=Theme.BG_CARD)
        streak_row.pack(anchor="w", pady=(0, 2))
        
        flame = tk.Label(
            streak_row,
            text="🔥",
            font=(Theme.FONT_FAMILY, 18),
            bg=Theme.BG_CARD
        )
        flame.pack(side="left")
        
        self.streak_value = tk.Label(
            streak_row,
            text="0",
            font=(Theme.FONT_FAMILY, 20, "bold"),
            fg=Theme.WARNING,
            bg=Theme.BG_CARD,
            anchor="w"
        )
        self.streak_value.pack(side="left", padx=(4, 0))
        
        streak_label = tk.Label(
            inner,
            text="day streak",
            font=(Theme.FONT_FAMILY, 9),
            fg=Theme.TEXT_SECONDARY,
            bg=Theme.BG_CARD,
            anchor="w"
        )
        streak_label.pack(anchor="w")
        
        return card
    
    def _create_milestone_card(self, parent):
        """Create milestone badges card."""
        card = tk.Frame(parent, bg=Theme.BG_CARD, highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE)
        card.configure(height=80)
        card.pack_propagate(False)
        
        inner = tk.Frame(card, bg=Theme.BG_CARD)
        inner.pack(expand=True, fill="both", padx=12, pady=12)
        
        milestone_label = tk.Label(
            inner,
            text="Milestones",
            font=(Theme.FONT_FAMILY, 9),
            fg=Theme.TEXT_MUTED,
            bg=Theme.BG_CARD,
            anchor="w"
        )
        milestone_label.pack(anchor="w", pady=(0, 4))
        
        self.badges_frame = tk.Frame(inner, bg=Theme.BG_CARD)
        self.badges_frame.pack(anchor="w", fill="both", expand=True)
        
        return card
    
    def _create_action_button(self, parent, text, command):
        """Create an action button."""
        btn = tk.Label(
            parent,
            text=text,
            font=(Theme.FONT_FAMILY, 10),
            fg=Theme.TEXT_PRIMARY,
            bg=Theme.BG_ELEVATED,
            cursor="hand2",
            pady=10
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
        
        padding = 25
        usable_width = w - 2 * padding
        bar_spacing = usable_width / len(data)
        bar_width = bar_spacing * 0.6  # 60% of space for bar, 40% for gap
        max_val = max(d[1] for d in data) if any(d[1] for d in data) else 1
        
        for i, (day, value) in enumerate(data):
            x = padding + i * bar_spacing + (bar_spacing - bar_width) / 2
            bar_height = (value / max_val) * (h - 45) if max_val > 0 else 0
            
            # Bar
            self.graph_canvas.create_rectangle(
                x, h - 25 - bar_height,
                x + bar_width, h - 25,
                fill=Theme.PINK_PRIMARY if value > 0 else Theme.BG_ELEVATED,
                outline="",
                width=0
            )
            
            # Day label
            self.graph_canvas.create_text(
                x + bar_width / 2, h - 10,
                text=day,
                font=(Theme.FONT_FAMILY, 9),
                fill=Theme.TEXT_MUTED
            )
            
            # Value label (if non-zero)
            if value > 0:
                self.graph_canvas.create_text(
                    x + bar_width / 2, h - 32 - bar_height,
                    text=str(value),
                    font=(Theme.FONT_FAMILY, 9),
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
                font=(Theme.FONT_FAMILY, 10),
                fg=Theme.TEXT_MUTED,
                bg=Theme.BG_CARD,
                pady=25
            )
            empty_label.pack()
            return
        
        for i, t in enumerate(transcripts[:5]):
            item = tk.Frame(self.recent_frame, bg=Theme.BG_CARD)
            item.pack(fill="x", padx=12, pady=7)
            
            # Time
            time_label = tk.Label(
                item,
                text=t.get("time", ""),
                font=(Theme.FONT_FAMILY, 9),
                fg=Theme.TEXT_MUTED,
                bg=Theme.BG_CARD,
                width=7,
                anchor="w"
            )
            time_label.pack(side="left", padx=(0, 8))
            
            # Text preview
            text_preview = t.get("text", "")
            if len(text_preview) > 40:
                text_preview = text_preview[:40] + "..."
            
            text_label = tk.Label(
                item,
                text=text_preview,
                font=(Theme.FONT_FAMILY, 9),
                fg=Theme.TEXT_SECONDARY,
                bg=Theme.BG_CARD,
                anchor="w"
            )
            text_label.pack(side="left", fill="x", expand=True, padx=(0, 8))
            
            # Word count
            words_label = tk.Label(
                item,
                text=f"{t.get('words', 0)}w",
                font=(Theme.FONT_FAMILY, 9),
                fg=Theme.PINK_SOFT,
                bg=Theme.BG_CARD,
                anchor="e",
                width=5
            )
            words_label.pack(side="left", padx=(0, 4))
            
            # Copy button
            full_text = t.get("full_text", t.get("text", ""))
            copy_btn = tk.Label(
                item,
                text="⎘",
                font=(Theme.FONT_FAMILY, 11),
                fg=Theme.TEXT_MUTED,
                bg=Theme.BG_CARD,
                cursor="hand2",
                padx=4
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
                font=(Theme.FONT_FAMILY, 10),
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
                font=(Theme.FONT_FAMILY, 10, "bold"),
                fg=Theme.BG_DARK,
                bg=Theme.PINK_PRIMARY,
                padx=6,
                pady=2
            )
            badge.pack(side="left", padx=(0, 6) if i < len(milestones[-4:]) - 1 else (0, 0))
    
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
    win.geometry("480x420")
    win.configure(bg=Theme.BG_DARK)
    win.resizable(False, False)
    win.attributes("-topmost", True)
    
    # Remove decorations for custom title bar
    win.overrideredirect(True)
    
    # Center window
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - 480) // 2
    y = (sh - 420) // 2
    win.geometry(f"480x420+{x}+{y}")
    
    # Custom title bar
    title_bar = tk.Frame(win, bg=Theme.BG_ELEVATED, height=40)
    title_bar.pack(fill="x")
    title_bar.pack_propagate(False)
    
    title_label = tk.Label(
        title_bar,
        text="⚙  Settings",
        font=(Theme.FONT_FAMILY, 11, "bold"),
        fg=Theme.TEXT_PRIMARY,
        bg=Theme.BG_ELEVATED
    )
    title_label.pack(side="left", padx=12)
    
    close_btn = tk.Label(
        title_bar,
        text="✕",
        font=(Theme.FONT_FAMILY, 12),
        fg=Theme.TEXT_SECONDARY,
        bg=Theme.BG_ELEVATED,
        cursor="hand2"
    )
    close_btn.pack(side="right", padx=12)
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
    content.pack(fill="both", expand=True, padx=16, pady=16)
    
    # Microphone section header
    mic_header = tk.Label(
        content,
        text="MICROPHONE",
        font=(Theme.FONT_FAMILY, 9, "bold"),
        fg=Theme.PINK_PRIMARY,
        bg=Theme.BG_DARK
    )
    mic_header.pack(anchor="w", pady=(0, 8))
    
    # Device listbox with scrollbar
    list_frame = tk.Frame(content, bg=Theme.BG_CARD, highlightthickness=1, highlightbackground=Theme.BORDER_SUBTLE)
    list_frame.pack(fill="both", expand=True, pady=(0, 12))
    
    idxs, labels = device_index_and_names()
    
    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side="right", fill="y")
    
    listbox = tk.Listbox(
        list_frame,
        bg=Theme.BG_CARD,
        fg=Theme.TEXT_PRIMARY,
        selectbackground=Theme.PINK_PRIMARY,
        selectforeground=Theme.TEXT_PRIMARY,
        font=(Theme.FONT_FAMILY, 10),
        borderwidth=0,
        highlightthickness=0,
        yscrollcommand=scrollbar.set
    )
    listbox.pack(fill="both", expand=True, padx=8, pady=8)
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
        font=(Theme.FONT_FAMILY, 9),
        fg=Theme.TEXT_SECONDARY,
        bg=Theme.BG_DARK
    )
    status_label.pack(anchor="w", pady=(0, 12))
    
    # Audio level indicator
    level_frame = tk.Frame(content, bg=Theme.BG_DARK)
    level_frame.pack(fill="x", pady=(0, 12))
    
    level_label = tk.Label(
        level_frame,
        text="Audio Level:",
        font=(Theme.FONT_FAMILY, 9),
        fg=Theme.TEXT_SECONDARY,
        bg=Theme.BG_DARK
    )
    level_label.pack(side="left")
    
    level_bar = tk.Canvas(level_frame, width=200, height=12, bg=Theme.BG_ELEVATED, highlightthickness=0)
    level_bar.pack(side="left", padx=(8, 0))
    level_fill = level_bar.create_rectangle(0, 0, 0, 12, fill=Theme.PINK_PRIMARY, outline="")
    
    # Button row
    btn_frame = tk.Frame(content, bg=Theme.BG_DARK)
    btn_frame.pack(fill="x")
    
    def create_button(parent, text, command, accent=False):
        btn = tk.Label(
            parent,
            text=text,
            font=(Theme.FONT_FAMILY, 10),
            fg=Theme.TEXT_PRIMARY if not accent else Theme.BG_DARK,
            bg=Theme.BG_ELEVATED if not accent else Theme.PINK_PRIMARY,
            cursor="hand2",
            padx=16,
            pady=8
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
                        level_pct = min(rms * 500, 200)  # Scale for visibility
                        level_bar.coords(level_fill, 0, 0, level_pct, 12)
                        level_bar.update()
                        time.sleep(0.1)
                status_var.set(f"Test complete")
            except Exception as e:
                status_var.set(f"Error: {str(e)[:30]}")
            finally:
                test_running[0] = False
                level_bar.coords(level_fill, 0, 0, 0, 12)
        
        threading.Thread(target=test_audio, daemon=True).start()
    
    create_button(btn_frame, "Refresh", do_refresh).pack(side="left", padx=(0, 8))
    create_button(btn_frame, "Test Mic", do_test).pack(side="left", padx=(0, 8))
    create_button(btn_frame, "Apply", do_apply, accent=True).pack(side="right")


# --- Helpers & Diagnostics ---
def res_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel)

# Resolve model paths after res_path is defined
MODEL_PATH_BASE = res_path(MODEL_BASE)
MODEL_PATH_MEDIUM = res_path(MODEL_MEDIUM)
MODEL_PATH_LARGE = res_path(MODEL_LARGE)
MODEL_PATH = MODEL_PATH_LARGE  # Legacy fallback
model_info_logged = False

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except Exception:
        msg = " ".join(str(a) for a in args)
        try:
            enc = sys.stdout.encoding or "utf-8"
        except Exception:
            enc = "utf-8"
        sys.stdout.write((msg + "\n").encode(enc, errors="replace").decode(errors="replace"))

def log_line(message):
    """Append a timestamped line to LOG_FILE and print it."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {message}"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    safe_print(line)


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
                n = Notification(app_id="Whisper Local", title="Whisper Local", msg=msg)
                if audio is not None:
                    n.set_audio(audio.SMS, loop=False)
                n.show()
        except Exception:
            pass
    log_line(msg)


def sanitize_transcript(text: str) -> str:
    """Remove banners, deprecation notices, and placeholder tokens from transcript."""
    if not text:
        return ""
    text = text.replace("[BLANK_AUDIO]", "").replace("BLANK_AUDIO", "").strip()
    lines = []
    for ln in text.splitlines():
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
    """Run preflight checks and print a concise summary."""
    issues = []
    
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
        issues.append("No model files found")
    else:
        log_line(f"Models available: {', '.join(models_found)}")
        if models_missing:
            log_line(f"Models missing: {', '.join(models_missing)} (will fall back if needed)")
    global resolved_whisper_bin
    resolved_whisper_bin = None
    for candidate in WHISPER_CANDIDATES:
        if os.path.exists(candidate):
            resolved_whisper_bin = candidate
            break
    if resolved_whisper_bin is None:
        issues.append("Missing whisper binary (checked multiple locations)")
    else:
        log_line(f"Whisper bin: {resolved_whisper_bin}")

    try:
        pa_ver = sd.get_portaudio_version()
        log_line(f"PortAudio: {pa_ver}")
    except Exception as e:
        issues.append(f"PortAudio error: {e}")

    resolve_input_device()
    if selected_input_device_idx is None:
        issues.append("No working input device")
    else:
        try:
            sd.check_input_settings(device=selected_input_device_idx, samplerate=SAMPLE_RATE, channels=CHANNELS)
        except Exception as e:
            issues.append(f"Device unsupported @ {SAMPLE_RATE} Hz / {CHANNELS}ch: {e}")

    if issues:
        set_status_safe("⚠️ Issues detected", Theme.WARNING, Theme.BG_DARK, Theme.WARNING)
        for it in issues:
            log_line(f"DIAG: {it}")
            notify(it)
        log_line("Available input devices:\n" + devices_summary_text())
    else:
        set_status_safe("🎤 Ready", Theme.BG_ELEVATED, Theme.TEXT_PRIMARY, Theme.PINK_PRIMARY)
        log_line("Diagnostics OK")
        log_line(f"Selected mic: {selected_input_device_name}")
        log_line("Available input devices:\n" + devices_summary_text())


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
        
        # Run silently
        subprocess.run(cmd, cwd=workdir, env=env, capture_output=True, timeout=30)
        
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
    """Resolve path to whisper binary."""
    for key in ("FLOW_WHISPER_BIN", "WHISPER_BIN"):
        p = os.getenv(key)
        if p and os.path.isfile(p):
            return p
    if bin_path and os.path.isfile(bin_path):
        return bin_path
    w = shutil.which("whisper-cli.exe") or shutil.which("main.exe")
    if w:
        return w
    _script_dir = os.path.dirname(os.path.abspath(__file__)) or "."
    for exe_name in ("whisper-cli.exe", "main.exe"):
        candidate = os.path.join(_script_dir, exe_name)
        if os.path.isfile(candidate):
            return candidate
    for exe_name in ("whisper-cli.exe", "main.exe"):
        if os.path.isfile(exe_name):
            return os.path.abspath(exe_name)
    raise FileNotFoundError("Whisper binary not found (env, PATH, or known locations).")

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

MIN_SEC = 0.2  # Reduced for faster speech detection
RMS_THRESH = 0.002
PREROLL_SEC = 2.0
POSTROLL_SEC = 0.15  # Reduced from 0.4 for snappier response

def record_loop():
    """Record while recording_flag is set; write to WAV on stop with RMS gate."""
    log_line("[rec] start")
    # Skip slow toast notification - UI pill already shows listening state
    data = []
    voiced_samples = 0
    block_dur = 0.05  # Reduced from 0.1 for faster RMS detection

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
    global rec_thread, target_window_on_record_start, pending_status_timer
    
    # Cancel any pending status timer from previous transcription
    if pending_status_timer is not None:
        try:
            pending_status_timer.cancel()
        except Exception:
            pass
        pending_status_timer = None
    
    with STATE_LOCK:
        if recording_flag.is_set() or transcribing_flag.is_set():
            return
        # Capture focus BEFORE we start (before our UI updates)
        # This ensures we know where to paste when transcription completes
        try:
            user32 = ctypes.windll.user32
            target_window_on_record_start = user32.GetForegroundWindow()
        except Exception:
            target_window_on_record_start = None
        try:
            if os.path.exists(WAV_TMP):
                os.remove(WAV_TMP)
        except Exception:
            pass
        recording_flag.set()
    set_status_safe("🎙️ Listening...", Theme.PINK_DARK, Theme.TEXT_PRIMARY, Theme.PINK_PRIMARY)
    rec_thread = threading.Thread(target=record_loop, daemon=True)
    rec_thread.start()

def _select_whisper_params(duration_sec):
    """Aggressive GPU-optimized parameters for maximum speed with large model."""
    # Use consistent high batch size - GPU can handle it
    if duration_sec is None or duration_sec < 15:
        return 8, None, "fast-gpu"  # No best-of for short audio = faster
    elif duration_sec < 30:
        return 8, 2, "balanced-gpu"
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
    
    num_threads = str(os.cpu_count() or 4)
    
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

    res = subprocess.run(
        cmd,
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

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
        
        cpu_args = [
            "-l", "en",
            "-nt",
            "-mc", "0",
            "-bs", str(cpu_batch_size),
            "-t", num_threads,
            "-otxt", "-of", out_txt[:-4],
            "--no-gpu"
        ]
        
        if cpu_best_of:
            cpu_args.extend(["-bo", str(cpu_best_of)])
        
        cmd_cpu = build_whisper_cmd(exe, model_path, filename, base_args=cpu_args)
        
        safe_print(f"[whisper] CPU fallback: bs={cpu_batch_size}" + (f", bo={cpu_best_of}" if cpu_best_of else "") + f", threads={num_threads}")
        
        res = subprocess.run(
            cmd_cpu,
            cwd=workdir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
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
        res = subprocess.run(
            cmd_fallback,
            cwd=workdir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
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
    """Two-pass smart model selection based on word count.
    
    Strategy:
    1. Always transcribe with base.en first (fast, <1s)
    2. Count words in result
    3. If word count < WORD_THRESHOLD_BASE: use base.en result (done!)
    4. If word count < WORD_THRESHOLD_MEDIUM: re-transcribe with medium.en
    5. If word count >= WORD_THRESHOLD_MEDIUM: re-transcribe with large-v3
    
    Args:
        filename: Path to audio file
        bin_path: Path to whisper binary
    
    Returns:
        Tuple of (return_code, transcription_text, stderr, model_used)
    """
    start_time = time.time()
    
    # Phase 1: Fast pass with base.en to count words
    safe_print("[whisper-smart] Phase 1: Quick transcription with base.en...")
    rc_base, text_base, err_base = run_whisper(filename, bin_path, model_path=MODEL_PATH_BASE)
    
    phase1_time = time.time() - start_time
    
    if rc_base != 0:
        # Base model failed - fall back to large model directly
        safe_print(f"[whisper-smart] Base model failed (rc={rc_base}), using large-v3 fallback")
        rc, text, err = run_whisper(filename, bin_path, model_path=MODEL_PATH_LARGE)
        total_time = time.time() - start_time
        safe_print(f"[whisper-smart] Fallback complete: {total_time:.2f}s")
        return rc, text, err, "large-v3 (fallback)"
    
    # Sanitize and count words
    clean_text = sanitize_transcript(text_base)
    if not clean_text:
        # Empty transcript - return base result
        safe_print("[whisper-smart] Empty transcript from base.en")
        return rc_base, text_base, err_base, "base.en"
    
    word_count = len(clean_text.split())
    safe_print(f"[whisper-smart] Phase 1 complete: {word_count} words in {phase1_time:.2f}s")
    
    # Phase 2: Decide if we need a better model
    if word_count < WORD_THRESHOLD_BASE:
        # Short utterance - base.en is perfect!
        safe_print(f"[whisper-smart] Using base.en result ({word_count} < {WORD_THRESHOLD_BASE} words)")
        total_time = time.time() - start_time
        safe_print(f"[whisper-smart] ✓ Total time: {total_time:.2f}s (base.en only)")
        return rc_base, text_base, err_base, "base.en"
    
    elif word_count < WORD_THRESHOLD_MEDIUM:
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
    
    else:
        # Long utterance - re-transcribe with large-v3 for best quality
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


def _transcribe_and_paste(wav_path):
    global last_transcription, target_window_on_record_start, pending_status_timer
    
    safe_print("[whisper] running...")
    set_status_safe("⚙️ Transcribing...", Theme.BG_ELEVATED, Theme.INFO, Theme.INFO)
    bin_path = (resolved_whisper_bin or WHISPER_BIN)
    rc, out, err, model_used = run_whisper_smart(wav_path, bin_path)

    if rc != 0:
        # Skip slow toast notification - just update UI status
        set_status_safe("❌ Failed", Theme.ERROR, Theme.TEXT_PRIMARY, Theme.ERROR)
        safe_print(f"[whisper] exit={rc} stderr={err[:400]}")
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
    sample = os.path.join("whisper.cpp", "samples", "jfk.wav")
    if not os.path.exists(sample):
        notify("Self-test sample not found: whisper.cpp/samples/jfk.wav")
        return
    if resolved_whisper_bin is None and not os.path.exists(WHISPER_BIN):
        notify("No whisper binary available for self-test")
        return
    exe = os.path.abspath(_resolve_whisper_exe(resolved_whisper_bin or WHISPER_BIN))
    cmd = build_whisper_cmd(exe, MODEL_PATH, sample, base_args=["-nt"]) 
    log_line("[self-test] running: " + " ".join(cmd))
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=WHISPER_TIMEOUT_SEC)
        out = (res.stdout or "").strip() or (res.stderr or "").strip()
        if out:
            notify("Self-test OK (see log)")
            log_line("[self-test-output]\n" + out)
        else:
            notify("Self-test produced no output")
    except Exception as e:
        notify(f"Self-test error: {e}")


def run_debug_probe():
    sample = os.path.join("whisper.cpp", "samples", "jfk.wav")
    if not os.path.exists(sample):
        notify("Debug: sample not found whisper.cpp/samples/jfk.wav")
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
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=WHISPER_TIMEOUT_SEC)
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
    """Open dashboard from tray."""
    global dashboard_window
    try:
        if gui and gui.root:
            if dashboard_window is None or not dashboard_window.winfo_exists():
                dashboard_window = DashboardWindow(gui.root)
            else:
                dashboard_window.lift()
                dashboard_window.focus_force()
    except Exception as e:
        safe_print(f"Dashboard error: {e}")

def _tray_quit(_=None):
    try:
        if recording_flag.is_set():
            stop_recording_and_transcribe()
    finally:
        os._exit(0)

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
    safe_print("◉ Whisper Local Dictation System")
    safe_print("=" * 60)
    safe_print("📌 Controls:")
    safe_print("  • Hold WIN + CTRL to record")
    safe_print("  • Release to transcribe & paste")
    safe_print("  • Click floating pill to open dashboard")
    safe_print("  • WIN + CTRL + S for settings")
    safe_print("  • ESC to exit")
    safe_print("=" * 60)
    
    global gui
    gui = FloatingPill()
    gui.set_status("ready")
    
    startup_diagnostics()
    
    # Start CUDA warmup in background (pre-load GPU model for instant first transcription)
    threading.Thread(target=cuda_warmup, daemon=True).start()
    
    try:
        device_lines = devices_summary_text()
        notify("✅ Ready! Hold WIN + CTRL to speak.")
        log_line("Startup devices:\n" + device_lines)
        safe_print(f"✅ Microphone: {selected_input_device_name}")
        safe_print(f"✅ Smart model selection enabled:")
        safe_print(f"   • <{WORD_THRESHOLD_BASE} words → base.en (fastest)")
        safe_print(f"   • {WORD_THRESHOLD_BASE}-{WORD_THRESHOLD_MEDIUM} words → medium.en")
        safe_print(f"   • {WORD_THRESHOLD_MEDIUM}+ words → large-v3 (best quality)")
        safe_print(f"✅ Whisper binary: {resolved_whisper_bin}")
        safe_print("🔥 CUDA warmup running in background...")
        safe_print("=" * 60)
    except Exception:
        pass

    was_down = False

    keyboard.on_press_key("f8", lambda e: threading.Thread(target=self_test_jfk, daemon=True).start())
    keyboard.on_press_key("f9", lambda e: threading.Thread(target=run_debug_probe, daemon=True).start())
    keyboard.add_hotkey("ctrl+alt+j", lambda: threading.Thread(target=self_test_jfk, daemon=True).start())
    keyboard.add_hotkey("ctrl+alt+d", lambda: threading.Thread(target=run_debug_probe, daemon=True).start())
    keyboard.add_hotkey("ctrl+alt+b", lambda: set_bullet_next())

    def poll_hotkey():
        nonlocal was_down
        global last_edge_ts
        try:
            down = listening_enabled and keyboard.is_pressed("windows") and keyboard.is_pressed("ctrl")
        except Exception:
            down = False
        try:
            if (keyboard.is_pressed("windows") and keyboard.is_pressed("ctrl") and keyboard.is_pressed("s")):
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
        try:
            if keyboard.is_pressed("esc"):
                gui.root.destroy()
                return
        except Exception:
            pass
        gui.root.after(10, poll_hotkey)

    gui.pump_queue()
    gui.root.after(10, poll_hotkey)
    gui.root.mainloop()
    if recording_flag.is_set():
        stop_recording_and_transcribe()
    safe_print("Bye.")

if __name__ == "__main__":
    start_tray()
    main()
