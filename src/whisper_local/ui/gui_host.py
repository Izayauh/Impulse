"""HTML-first dashboard host for WhisperLocal.

This module hosts the dashboard window via pywebview and exposes
a hierarchical JavaScript bridge API following the Modular
Hierarchical Bridge pattern (Research §2).

Domain controllers (exposed as namespaced JS objects):
  - settings      – configuration, hotkeys, vocabulary, snippets
  - transcription  – Whisper model lifecycle and loading
  - stats          – usage analytics (SQLite-backed)
  - system         – OS-level interactions (window, clipboard, export)
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List

import webview

from whisper_local.config import STATS_FILE, get_app_dir, get_user_data_dir
from whisper_local.settings_manager import SettingsManager
from whisper_local.controllers import (
    SettingsController,
    TranscriptionController,
    StatsController,
    SystemController,
    LicensingController,
)
from whisper_local.licensing import LicensingManager
from whisper_local.snippets import snippets_file
from whisper_local.hotkey_settings import (
    default_settings as default_hotkey_settings,
    settings_file,
    save_settings as save_hotkey_settings,
)
from whisper_local.model_selection import (
    load_state as load_model_selection_state,
    model_selection_file,
    save_state as save_model_selection_state,
)
from whisper_local.vocabulary import (
    save_vocabulary,
    vocabulary_file,
)

try:
    from whisper_local.gpu_monitor import gpu_monitor
except ImportError:
    gpu_monitor = None


DASHBOARD_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")

_dashboard_open = False
_dashboard_lock = threading.Lock()
_dashboard_mutex = None
_migration_lock = threading.Lock()
_migration_completed = False
_api_instance = None  # Module-level ref for graceful shutdown


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on", "debug", "info", "trace", "verbose"}


def _pywebview_debug_enabled() -> bool:
    return _is_truthy(os.environ.get("PYWEBVIEW_LOG")) or _is_truthy(os.environ.get("WHISPERLOCAL_DEBUG"))


def _configure_hardware_acceleration_env(env: Dict[str, str] | None = None) -> Dict[str, str]:
    """Ensure GPU acceleration flags are present for WebView2/EdgeChromium."""
    target_env = env if env is not None else os.environ
    existing = target_env.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "").strip()
    flags = (
        "--enable-gpu --enable-gpu-rasterization --enable-zero-copy "
        "--ignore-gpu-blocklist --use-angle=d3d11 "
        "--enable-features=CanvasOopRasterization --disable-frame-rate-limit"
    )
    if existing:
        if flags not in existing:
            target_env["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = f"{existing} {flags}".strip()
    else:
        target_env["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = flags
    return target_env


# =========================================================================
# AppApi – Hierarchical bridge root (Research §2.2)
# =========================================================================

class AppApi:
    """Hierarchical JavaScript bridge API for the dashboard.

    Domain controllers are exposed as public attributes and
    auto-mapped by pywebview to namespaced JS calls::

        pywebview.api.settings.get_all()
        pywebview.api.transcription.load_model('medium')
        pywebview.api.stats.get_chart_data(7)
        pywebview.api.system.minimize()

    Root-level backward-compatible methods are preserved so that
    existing dashboard.html JS continues to work during the
    transition to the namespaced Bridge abstraction (Task #11).
    """

    def __init__(self) -> None:
        self.user_dir = get_user_data_dir()
        self.stats_file = STATS_FILE
        self.achievements_file = os.path.join(self.user_dir, "state", "whisper_achievements.json")

        # Shared settings manager (Pydantic-backed, Research §6)
        settings_mgr = SettingsManager(self.user_dir)

        # Resolve file paths for sub-controllers
        model_file = model_selection_file(self.user_dir)
        vocab_file = vocabulary_file(self.user_dir)
        hotkey_file = settings_file(self.user_dir)
        snippets_path = snippets_file(self.user_dir)

        # -- Domain controllers (§2.2 Modular Hierarchical Bridge) --------
        self.settings = SettingsController(
            settings_mgr, hotkey_file, vocab_file, snippets_path,
        )
        self.transcription = TranscriptionController(
            model_file, self._get_vram_total_mb, settings_mgr,
        )
        self.stats = StatsController(self.user_dir, self.stats_file)
        self.system = SystemController(self.user_dir, self.stats_file)
        self.licensing = LicensingController(LicensingManager(self.user_dir))

        # Private refs (not exposed by pywebview)
        self._window = None
        self._settings_manager = settings_mgr

        # Legacy one-time migrations
        self._migrate_legacy_state_once()

        # Ensure state files exist on first run
        if not os.path.exists(self.achievements_file):
            self._save_achievements([])
        if not os.path.exists(model_file):
            save_model_selection_state(model_file, load_model_selection_state(model_file))
        if not os.path.exists(vocab_file):
            save_vocabulary(vocab_file, [])
        if not os.path.exists(hotkey_file):
            save_hotkey_settings(hotkey_file, default_hotkey_settings())

    # -- window wiring (called after webview.create_window) ----------------

    def wire_window(self, window) -> None:
        """Pass the webview window reference to controllers that need it."""
        self._window = window
        self.system.set_window(window)
        self.transcription.set_window(window)

    # -- graceful shutdown (Research §8.2) ---------------------------------

    def shutdown(self) -> None:
        """Clean up resources before the dashboard window closes."""
        try:
            self.transcription.shutdown()
        except Exception:
            pass
        try:
            self.stats.close()
        except Exception:
            pass

    # -- VRAM helper -------------------------------------------------------

    def _get_vram_total_mb(self) -> float:
        if gpu_monitor is None:
            return 0.0
        try:
            info = gpu_monitor.get_gpu_info()
            if info is None:
                return 0.0
            return float(getattr(info, "memory_total_mb", 0.0) or 0.0)
        except Exception:
            return 0.0

    # ======================================================================
    # Legacy migration (runs once per process)
    # ======================================================================

    def _default_stats_payload(self) -> Dict[str, Any]:
        return {
            "total_words": 0,
            "total_sessions": 0,
            "daily_words": {},
            "model_usage": {},
            "recent_transcripts": [],
            "milestones": [],
            "streak": 0,
            "last_use_date": None,
            "wpm_history": [],
            "best_wpm": 0,
        }

    def _stats_candidate_paths(self) -> List[str]:
        app_dir = get_app_dir()
        candidates = [
            self.stats_file,
            os.path.join(self.user_dir, "whisper_stats.json"),
            os.path.join(self.user_dir, "state", "whisper_stats.json"),
            os.path.join(app_dir, "output", "state", "whisper_stats.json"),
            os.path.join(app_dir, "output", "whisper_stats.json"),
            os.path.join(app_dir, "whisper_stats.json"),
        ]
        seen = set()
        ordered = []
        for path in candidates:
            norm = os.path.normcase(os.path.abspath(path))
            if norm not in seen:
                seen.add(norm)
                ordered.append(path)
        return ordered

    def _achievements_candidate_paths(self) -> List[str]:
        app_dir = get_app_dir()
        candidates = [
            self.achievements_file,
            os.path.join(self.user_dir, "whisper_achievements.json"),
            os.path.join(self.user_dir, "state", "whisper_achievements.json"),
            os.path.join(app_dir, "output", "state", "whisper_achievements.json"),
            os.path.join(app_dir, "output", "whisper_achievements.json"),
            os.path.join(app_dir, "whisper_achievements.json"),
        ]
        seen = set()
        ordered = []
        for path in candidates:
            norm = os.path.normcase(os.path.abspath(path))
            if norm not in seen:
                seen.add(norm)
                ordered.append(path)
        return ordered

    def _normalize_stats_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = {**self._default_stats_payload(), **(data or {})}
        if not isinstance(payload.get("daily_words"), dict):
            payload["daily_words"] = {}
        if not isinstance(payload.get("model_usage"), dict):
            payload["model_usage"] = {}
        if not isinstance(payload.get("recent_transcripts"), list):
            payload["recent_transcripts"] = []
        if not isinstance(payload.get("milestones"), list):
            payload["milestones"] = []
        if not isinstance(payload.get("wpm_history"), list):
            payload["wpm_history"] = []
        return payload

    def _stats_has_history(self, data: Dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False
        total_words = int(data.get("total_words", 0) or 0)
        daily_words = data.get("daily_words", {})
        return total_words > 0 or (isinstance(daily_words, dict) and len(daily_words) > 0)

    def _select_best_stats_source(self, paths: List[str]) -> tuple[str | None, Dict[str, Any] | None]:
        best_path = None
        best_payload = None
        best_score = (-1, -1, -1.0)
        for path in paths:
            payload = self._load_json_file(path, default=None)
            if not isinstance(payload, dict):
                continue
            total_words = int(payload.get("total_words", 0) or 0)
            daily_words = payload.get("daily_words", {})
            day_count = len(daily_words) if isinstance(daily_words, dict) else 0
            if total_words <= 0 and day_count <= 0:
                continue
            mtime = os.path.getmtime(path) if os.path.exists(path) else 0.0
            score = (total_words, day_count, mtime)
            if score > best_score:
                best_score = score
                best_path = path
                best_payload = payload
        return best_path, best_payload

    def _select_best_achievements_source(self, paths: List[str]) -> tuple[str | None, List[str] | None]:
        best_path = None
        best_unlocked = None
        best_score = (-1, -1.0)
        for path in paths:
            payload = self._load_json_file(path, default=None)
            if not isinstance(payload, dict):
                continue
            unlocked = payload.get("unlocked", [])
            if not isinstance(unlocked, list):
                continue
            score = (len(unlocked), os.path.getmtime(path) if os.path.exists(path) else 0.0)
            if score > best_score:
                best_score = score
                best_path = path
                best_unlocked = [str(x) for x in unlocked]
        return best_path, best_unlocked

    def _migrate_legacy_state_once(self) -> None:
        global _migration_completed
        with _migration_lock:
            if _migration_completed:
                return

            # Stats migration: if canonical file is empty, import richest legacy source.
            canonical_stats = self._load_json_file(self.stats_file, self._default_stats_payload())
            if not self._stats_has_history(canonical_stats):
                source_path, source_payload = self._select_best_stats_source(self._stats_candidate_paths())
                if source_path and source_payload:
                    normalized = self._normalize_stats_payload(source_payload)
                    self._save_json_file(self.stats_file, normalized)
                    print(f"[AppApi] Migrated stats from {source_path} -> {self.stats_file}")

            # Achievements migration: if canonical file is empty, import richest legacy source.
            canonical_ach = self._load_json_file(self.achievements_file, {"unlocked": []})
            canonical_unlocked = canonical_ach.get("unlocked", []) if isinstance(canonical_ach, dict) else []
            if not isinstance(canonical_unlocked, list):
                canonical_unlocked = []
            if len(canonical_unlocked) == 0:
                source_path, source_unlocked = self._select_best_achievements_source(self._achievements_candidate_paths())
                if source_path and source_unlocked:
                    self._save_json_file(self.achievements_file, {"unlocked": source_unlocked})
                    print(f"[AppApi] Migrated achievements from {source_path} -> {self.achievements_file}")

            _migration_completed = True

    # -- JSON helpers (used by migration & stats) --------------------------

    def _load_json_file(self, filepath: str, default: Any = None) -> Any:
        if not os.path.exists(filepath):
            return default if default is not None else {}
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, IOError) as e:
            print(f"[AppApi] Error loading {filepath}: {e}")
            return default if default is not None else {}

    def _save_json_file(self, filepath: str, data: Any) -> bool:
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except (OSError, IOError) as e:
            print(f"[AppApi] Error saving {filepath}: {e}")
            return False

    def _save_achievements(self, achievements: List[str]) -> bool:
        return self._save_json_file(self.achievements_file, {"unlocked": achievements})

    # ======================================================================
    # Backward-compatible root-level API
    # These delegate to domain controllers so existing dashboard.html JS
    # keeps working during the transition to namespaced calls (Task #11).
    # ======================================================================

    # -- window management (-> system) -------------------------------------

    def minimize(self) -> None:
        self.system.minimize()

    def close(self) -> None:
        self.system.close()

    def copy_text(self, text: str) -> bool:
        return self.system.copy_text(text)

    def bridge_ping(self) -> Dict[str, Any]:
        result = self.system.bridge_ping()
        result["statsFile"] = self.stats_file
        result["statsFileExists"] = os.path.exists(self.stats_file)
        return result

    def export_data_csv(self) -> Dict[str, Any]:
        return self.system.export_data_csv()

    def open_settings(self) -> None:
        return None

    # -- model management (-> transcription) -------------------------------

    def get_model_mode(self) -> Dict[str, Any]:
        return self.transcription.get_model_mode()

    def set_model_mode(self, mode: str) -> Dict[str, Any]:
        return self.transcription.set_model_mode(mode)

    # -- settings (-> settings) --------------------------------------------

    def get_user_settings(self) -> Dict[str, Any]:
        return self.settings.get_all()

    def update_user_setting(self, key: str, value: Any) -> Dict[str, Any]:
        return self.settings.update(key, value)

    def get_vocabulary(self) -> List[str]:
        return self.settings.get_vocabulary()

    def add_vocabulary_word(self, word: str) -> Dict[str, Any]:
        return self.settings.add_vocabulary_word(word)

    def get_hotkey(self) -> Dict[str, Any]:
        return self.settings.get_hotkey()

    def set_hotkey(self, hotkey: str) -> Dict[str, Any]:
        return self.settings.set_hotkey(hotkey)

    def get_snippets(self) -> List[Dict[str, Any]]:
        return self.settings.get_snippets()

    def add_snippet(self, trigger: str, replacement: str) -> Dict[str, Any]:
        return self.settings.add_snippet(trigger, replacement)

    def delete_snippet(self, snippet_id: int) -> Dict[str, Any]:
        return self.settings.delete_snippet(snippet_id)

    # ======================================================================
    # Complex root-level methods (XP/level/rank computation, achievements)
    # These stay at root until a dedicated controller absorbs them.
    # ======================================================================

    def _format_recent_transcripts(self, raw_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        recent = raw_stats.get("recent_transcripts", [])
        formatted: List[Dict[str, Any]] = []
        for item in recent[-5:]:
            if isinstance(item, dict):
                full_text = item.get("full_text", item.get("text", "")) or ""
                preview = full_text[:50] + "..." if len(full_text) > 50 else full_text
                timestamp = item.get("timestamp", "")
                formatted.append(
                    {
                        "text": preview,
                        "fullText": full_text,
                        "words": item.get("word_count", len(full_text.split())),
                        "time": timestamp[-5:] if timestamp else "recent",
                    }
                )
            elif isinstance(item, str):
                preview = item[:50] + "..." if len(item) > 50 else item
                formatted.append(
                    {
                        "text": preview,
                        "fullText": item,
                        "words": len(item.split()),
                        "time": "recent",
                    }
                )
        return formatted

    def get_stats(self) -> Dict[str, Any]:
        raw_stats = self._normalize_stats_payload(
            self._load_json_file(self.stats_file, self._default_stats_payload())
        )

        total_words = int(raw_stats.get("total_words", 0) or 0)
        total_sessions = int(raw_stats.get("total_sessions", 0) or 0)
        daily_words = raw_stats.get("daily_words", {}) or {}
        wpm_history = raw_stats.get("wpm_history", []) or []

        today = datetime.now().strftime("%Y-%m-%d")
        today_words = int(daily_words.get(today, 0) or 0)

        week_words = 0
        last_7_days = []
        last_7_days_series = []
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i in range(6, -1, -1):
            day_obj = datetime.now() - timedelta(days=i)
            day_key = day_obj.strftime("%Y-%m-%d")
            day_count = int(daily_words.get(day_key, 0) or 0)
            week_words += day_count
            last_7_days.append({"day": day_names[day_obj.weekday()], "words": day_count})
            last_7_days_series.append([day_key, day_count])

        month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        month_words = sum(int(v or 0) for k, v in daily_words.items() if k >= month_start)

        valid_wpm = [float(v) for v in wpm_history if isinstance(v, (int, float)) and v > 0]
        avg_wpm = int(sum(valid_wpm) / len(valid_wpm)) if valid_wpm else 0
        best_wpm = int(max([raw_stats.get("best_wpm", 0)] + valid_wpm)) if valid_wpm else int(raw_stats.get("best_wpm", 0) or 0)

        xp = total_words
        level = 1
        xp_for_level = 1000
        remaining_xp = xp
        while remaining_xp >= xp_for_level:
            remaining_xp -= xp_for_level
            level += 1
            xp_for_level = int(xp_for_level * 1.5)

        ranks = [
            (1, "Beginner", "Word Warrior"),
            (5, "Word Warrior", "Voice Virtuoso"),
            (10, "Voice Virtuoso", "Speech Sage"),
            (20, "Speech Sage", "Dictation Master"),
            (35, "Dictation Master", "Transcription Titan"),
            (50, "Transcription Titan", "Legend"),
            (100, "Legend", "Mythical"),
        ]
        rank = "Beginner"
        next_rank = "Word Warrior"
        for min_level, r, nr in ranks:
            if level >= min_level:
                rank = r
                next_rank = nr

        streak = int(raw_stats.get("streak", 0) or 0)
        best_streak = max(streak, int(raw_stats.get("best_streak", streak) or streak))
        formatted_recent = self._format_recent_transcripts(raw_stats)

        total_minutes = total_sessions * 2
        hours = total_minutes // 60
        minutes = total_minutes % 60

        print(
            f"DEBUG: Loaded {len(daily_words)} days of history and {total_words} XP from {self.stats_file}"
        )

        return {
            "xp": remaining_xp,
            "totalXp": total_words,
            "total_xp": total_words,
            "xpToNextLevel": xp_for_level,
            "level": level,
            "rank": rank,
            "nextRank": next_rank,
            "today": today_words,
            "thisWeek": week_words,
            "thisMonth": month_words,
            "totalWords": total_words,
            "totalSessions": total_sessions,
            "totalTime": f"{hours}h {minutes}m",
            "avgWpm": avg_wpm,
            "bestWpm": best_wpm,
            "dayStreak": streak,
            "bestStreak": best_streak,
            "weekStreak": streak // 7,
            "sessionWords": 0,
            "sessionWpm": 0,
            "sessionTime": "0:00",
            "accuracy": 97.2,
            "dailyGoal": 500,
            "last7Days": last_7_days,
            "last7DaysSeries": last_7_days_series,
            "recentTranscripts": formatted_recent,
            "records": {
                "mostWordsDay": {
                    "value": max([int(v or 0) for v in daily_words.values()] or [0]),
                    "date": max(daily_words.keys(), key=lambda k: int(daily_words[k] or 0)) if daily_words else "N/A",
                },
                "fastestWpm": {"value": best_wpm, "date": "Recent"},
                "longestSession": {"value": "N/A", "date": "N/A"},
                "longestStreak": {"value": best_streak, "date": "Recent"},
            },
        }

    def get_transcription_history(self) -> List[Dict[str, Any]]:
        raw_stats = self._load_json_file(self.stats_file, {"recent_transcripts": []})
        return self._format_recent_transcripts(raw_stats)

    def get_achievements(self) -> List[str]:
        data = self._load_json_file(self.achievements_file, {"unlocked": []})
        unlocked = data.get("unlocked", []) if isinstance(data, dict) else []
        return unlocked if isinstance(unlocked, list) else []

    def unlock_achievement(self, achievement_id: str) -> bool:
        achievements = self.get_achievements()
        if achievement_id not in achievements:
            achievements.append(achievement_id)
            return self._save_achievements(achievements)
        return True

    def get_activity_data(self) -> List[List[Any]]:
        raw_stats = self._normalize_stats_payload(
            self._load_json_file(self.stats_file, self._default_stats_payload())
        )
        daily_words = raw_stats.get("daily_words", {}) or {}
        series = []
        for i in range(6, -1, -1):
            day_obj = datetime.now() - timedelta(days=i)
            day_key = day_obj.strftime("%Y-%m-%d")
            series.append([day_key, int(daily_words.get(day_key, 0) or 0)])
        return series


# Backward compatibility for modules/tests that still import DashboardAPI.
class DashboardAPI(AppApi):
    pass


# =========================================================================
# Window management helpers
# =========================================================================

def _bring_window_to_front() -> None:
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.FindWindowW(None, "Whisper Local Dashboard")
        if hwnd:
            user32.ShowWindow(hwnd, 5)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
    except Exception:
        pass


def _acquire_dashboard_mutex() -> bool:
    """Cross-process singleton guard for dashboard host."""
    global _dashboard_mutex
    if os.name != "nt":
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        mutex_name = "Local\\WhisperLocalDashboardHostSingleton"
        _dashboard_mutex = kernel32.CreateMutexW(None, False, mutex_name)
        if not _dashboard_mutex:
            return True
        already_exists = kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
        if already_exists:
            _bring_window_to_front()
            return False
        return True
    except Exception:
        return True


def _on_dashboard_closed() -> None:
    global _dashboard_open, _api_instance
    if _api_instance:
        try:
            _api_instance.shutdown()
        except Exception:
            pass
        _api_instance = None
    with _dashboard_lock:
        _dashboard_open = False


def _run_webview_dashboard() -> None:
    global _api_instance
    try:
        if not os.path.exists(DASHBOARD_HTML_PATH):
            raise FileNotFoundError(f"Missing HTML file: {DASHBOARD_HTML_PATH}")

        debug_mode = _pywebview_debug_enabled()
        _configure_hardware_acceleration_env()
        if debug_mode:
            print("[Dashboard] Starting pywebview host in debug mode")

        api = AppApi()
        _api_instance = api

        window = webview.create_window(
            title="Whisper Local Dashboard",
            url=DASHBOARD_HTML_PATH,
            width=420,
            height=700,
            min_size=(380, 500),
            resizable=True,
            js_api=api,
            focus=True,
        )
        api.wire_window(window)
        window.events.loaded += _bring_window_to_front
        window.events.closed += _on_dashboard_closed

        try:
            # Keep devtools disabled in production UI for smoother startup and UX.
            webview.start(debug=False, gui="edgechromium")
        except Exception:
            # Fallback renderer for older Windows machines without WebView2 runtime.
            webview.start(debug=False, gui="mshtml")
    except Exception as e:
        print(f"[Dashboard] Failed to open HTML host: {e}")
        _on_dashboard_closed()


def _dashboard_bootstrap_script() -> str:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    return os.path.join(project_root, "gui_host.py")


def _spawn_dashboard_process() -> bool:
    """Start dashboard host in a fresh process (main-thread safe)."""
    try:
        env = _configure_hardware_acceleration_env(os.environ.copy())
        debug_mode = _pywebview_debug_enabled()
        if debug_mode and "PYWEBVIEW_LOG" not in env:
            env["PYWEBVIEW_LOG"] = "debug"

        bootstrap_script = _dashboard_bootstrap_script()
        if os.path.isfile(bootstrap_script):
            cmd = [sys.executable, bootstrap_script]
        else:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            src_path = os.path.join(project_root, "src")
            pythonpath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = src_path if not pythonpath else f"{src_path}{os.pathsep}{pythonpath}"
            cmd = [sys.executable, "-m", "whisper_local.ui.gui_host"]

        kwargs = {"env": env}
        if os.name == "nt" and not debug_mode:
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        if debug_mode:
            print(f"[Dashboard] Spawning host: {' '.join(cmd)}")
        subprocess.Popen(cmd, **kwargs)
        return True
    except Exception as e:
        print(f"[Dashboard] Failed to spawn dashboard process: {e}")
        return False


def open_dashboard() -> bool:
    """Open the HTML dashboard in a dedicated native window."""
    # pywebview must run on the main thread. If called from worker/tray thread,
    # spawn a dedicated process and let its main thread host the window.
    if threading.current_thread() is not threading.main_thread():
        return _spawn_dashboard_process()

    if not _acquire_dashboard_mutex():
        return True

    global _dashboard_open
    with _dashboard_lock:
        if _dashboard_open:
            _bring_window_to_front()
            return True
        _dashboard_open = True

    _run_webview_dashboard()
    return True


def main() -> int:
    open_dashboard()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
