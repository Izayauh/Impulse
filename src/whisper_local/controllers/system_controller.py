"""System controller – handles OS-level interactions.

Window management, clipboard, file export, and bridge health.
"""

from __future__ import annotations

import csv
import io
import json
import os
from datetime import datetime
from typing import Any, Dict, List

import pyperclip


class SystemController:
    """Exposed to JS as ``pywebview.api.system.*``."""

    def __init__(self, user_data_dir: str, stats_json_path: str) -> None:
        self._user_dir = user_data_dir
        self._stats_json = stats_json_path
        self._window = None

    def set_window(self, window) -> None:
        self._window = window

    # -- window management --------------------------------------------------

    def minimize(self) -> None:
        if self._window:
            self._window.minimize()

    def close(self) -> None:
        if self._window:
            self._window.destroy()

    # -- clipboard ----------------------------------------------------------

    def copy_text(self, text: str) -> bool:
        try:
            pyperclip.copy(text or "")
            return True
        except Exception:
            return False

    # -- bridge health ------------------------------------------------------

    def bridge_ping(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "bridge": "pywebview",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

    # -- export -------------------------------------------------------------

    def export_data_csv(self) -> Dict[str, Any]:
        try:
            export_dir = os.path.join(self._user_dir, "exports")
            os.makedirs(export_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            csv_path = os.path.join(export_dir, f"whisper_history_{timestamp}.csv")

            raw = self._load_stats()
            buf = io.StringIO()
            writer = csv.writer(buf)

            writer.writerow(["date", "word_count"])
            daily_words = raw.get("daily_words", {})
            for date_key in sorted(daily_words.keys()):
                writer.writerow([date_key, int(daily_words[date_key] or 0)])

            writer.writerow([])
            writer.writerow(["timestamp", "text", "word_count", "model", "wpm"])
            for t in raw.get("recent_transcripts", []):
                if isinstance(t, dict):
                    writer.writerow([
                        t.get("timestamp", ""),
                        t.get("full_text", t.get("text", "")),
                        t.get("word_count", 0),
                        t.get("model", ""),
                        t.get("wpm", ""),
                    ])

            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                f.write(buf.getvalue())

            if os.name == "nt":
                os.startfile(export_dir)
            return {"ok": True, "path": csv_path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _load_stats(self) -> Dict[str, Any]:
        if not os.path.exists(self._stats_json):
            return {}
        try:
            with open(self._stats_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
