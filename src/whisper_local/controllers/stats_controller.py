"""Stats controller – manages usage analytics via SQLite.

Provides pre-aggregated data for Chart.js rendering and maintains
backward compatibility with the existing JSON stats file.
(Research §5)
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List


class StatsController:
    """Exposed to JS as ``pywebview.api.stats.*``."""

    def __init__(self, user_data_dir: str, stats_json_path: str) -> None:
        self._user_dir = user_data_dir
        self._stats_json = stats_json_path
        self._db_path = os.path.join(user_data_dir, "state", "usage_stats.db")
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._init_db()
        self._migrate_json_to_sqlite()

    # -- SQLite setup -------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transcription_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT DEFAULT (datetime('now','localtime')),
                date TEXT,
                duration_seconds REAL DEFAULT 0,
                model_name TEXT DEFAULT '',
                word_count INTEGER DEFAULT 0,
                wpm REAL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_date ON transcription_logs(date)
        """)
        conn.commit()
        conn.close()

    def _migrate_json_to_sqlite(self) -> None:
        """One-time import of existing daily_words from whisper_stats.json."""
        conn = self._connect()
        existing = conn.execute(
            "SELECT COUNT(*) FROM transcription_logs"
        ).fetchone()[0]
        if existing > 0:
            conn.close()
            return

        data = self._load_json_stats()
        daily_words = data.get("daily_words", {})
        if not isinstance(daily_words, dict) or not daily_words:
            conn.close()
            return

        rows = []
        for date_key, word_count in sorted(daily_words.items()):
            wc = int(word_count or 0)
            if wc > 0:
                rows.append((date_key + "T12:00:00", date_key, 0.0, "", wc, 0.0))

        if rows:
            conn.executemany(
                "INSERT INTO transcription_logs "
                "(timestamp, date, duration_seconds, model_name, word_count, wpm) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                rows,
            )
            conn.commit()
            print(f"[StatsController] Migrated {len(rows)} days from JSON to SQLite")

        conn.close()

    def _load_json_stats(self) -> Dict[str, Any]:
        if not os.path.exists(self._stats_json):
            return {}
        try:
            with open(self._stats_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    # -- write API (called by dictation engine) -----------------------------

    def record_transcription(
        self,
        word_count: int,
        model_name: str = "",
        duration_seconds: float = 0.0,
        wpm: float = 0.0,
    ) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        conn = self._connect()
        conn.execute(
            "INSERT INTO transcription_logs "
            "(date, duration_seconds, model_name, word_count, wpm) "
            "VALUES (?, ?, ?, ?, ?)",
            (today, duration_seconds, model_name, word_count, wpm),
        )
        conn.commit()
        conn.close()

    # -- read API (exposed to JS) -------------------------------------------

    def get_chart_data(self, days: int = 7) -> Dict[str, Any]:
        """Return pre-aggregated data for Chart.js (Research §5.3)."""
        conn = self._connect()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT date, SUM(word_count) as total_words "
            "FROM transcription_logs "
            "WHERE date >= ? "
            "GROUP BY date "
            "ORDER BY date ASC",
            (cutoff,),
        ).fetchall()
        conn.close()

        lookup = {r[0]: r[1] for r in rows}
        labels = []
        data = []
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i in range(days - 1, -1, -1):
            day_obj = datetime.now() - timedelta(days=i)
            key = day_obj.strftime("%Y-%m-%d")
            labels.append(day_names[day_obj.weekday()])
            data.append(lookup.get(key, 0))

        return {
            "labels": labels,
            "datasets": [{"label": "Words", "data": data}],
        }

    def get_daily_usage(self, days: int = 30) -> List[List[Any]]:
        """Return [date, word_count] pairs for the last N days."""
        conn = self._connect()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT date, SUM(word_count) "
            "FROM transcription_logs "
            "WHERE date >= ? "
            "GROUP BY date "
            "ORDER BY date ASC",
            (cutoff,),
        ).fetchall()
        conn.close()
        return [[r[0], r[1]] for r in rows]

    def get_totals(self) -> Dict[str, Any]:
        conn = self._connect()
        row = conn.execute(
            "SELECT COALESCE(SUM(word_count),0), COUNT(*), "
            "COALESCE(AVG(wpm),0), COALESCE(MAX(wpm),0) "
            "FROM transcription_logs"
        ).fetchone()
        conn.close()
        return {
            "totalWords": row[0],
            "totalSessions": row[1],
            "avgWpm": round(row[2]),
            "bestWpm": round(row[3]),
        }

    # -- lifecycle ----------------------------------------------------------

    def close(self) -> None:
        pass  # connections are opened/closed per-call
