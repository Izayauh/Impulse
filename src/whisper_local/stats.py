"""
Statistics tracking for WhisperLocal.

This module handles tracking usage statistics, word counts, streaks,
milestones, and recent transcriptions.
"""

import json
import os
import datetime
import logging
from typing import Dict, List, Optional, Tuple
from .config import STATS_FILE

logger = logging.getLogger(__name__)


def debug_print(*args, **kwargs):
    """Module-local debug print compatible with prior behavior."""
    try:
        logger.debug(" ".join(str(a) for a in args))
    except Exception:
        pass


class StatsTracker:
    """Track usage statistics and achievements."""

    MAX_REASONABLE_WPM = 350
    
    def __init__(self, stats_file: Optional[str] = None):
        """Initialize stats tracker.
        
        Args:
            stats_file: Path to stats JSON file. If None, uses default from config.
        """
        self.stats_file = stats_file or STATS_FILE
        self.data = self._load_stats()
    
    def _load_stats(self) -> Dict:
        """Load statistics from file."""
        debug_print(f"[DEBUG] Loading stats from: {self.stats_file}")
        default_stats = {
            "total_words": 0,
            "total_sessions": 0,
            "daily_words": {},
            "model_usage": {},
            "recent_transcripts": [],
            "milestones": [],
            "streak": 0,
            "last_use_date": None,
            "wpm_history": [],
            "best_wpm": 0
        }

        if not os.path.exists(self.stats_file):
            debug_print(f"[DEBUG] Stats file does not exist, using defaults")
            return default_stats

        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                loaded = {**default_stats, **json.load(f)}
                loaded = self._sanitize_wpm_data(loaded)
                debug_print(f"[DEBUG] Stats loaded: {loaded.get('total_words', 0)} total words, {loaded.get('total_sessions', 0)} sessions")
                return loaded
        except (json.JSONDecodeError, IOError, OSError) as e:
            debug_print(f"[DEBUG] Failed to load stats: {e}")
            return default_stats

    def _sanitize_wpm_data(self, data: Dict) -> Dict:
        """Drop implausible WPM outliers from historical data."""
        history = data.get("wpm_history", [])
        if not isinstance(history, list):
            history = []
        valid_wpm = [
            int(w) for w in history
            if isinstance(w, (int, float)) and 0 < w <= self.MAX_REASONABLE_WPM
        ]
        data["wpm_history"] = valid_wpm[-100:]
        data["best_wpm"] = max(data["wpm_history"], default=0)
        return data
    
    def _save_stats(self):
        """Save statistics to file."""
        try:
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
            today_words = self.get_today_words()
            debug_print(f"[DEBUG] Saving stats to: {self.stats_file}")
            debug_print(f"[DEBUG] Stats saved: {today_words} words today, {self.data.get('total_words', 0)} total words")
        except (IOError, OSError) as e:
            debug_print(f"[DEBUG] Warning: Could not save stats to {self.stats_file}: {e}")
    
    def record_transcription(self, text: str, model: str, duration_sec: Optional[float] = None):
        """Record a transcription event.

        Args:
            text: The transcribed text
            model: The model used (base.en, medium.en, large-v3)
            duration_sec: Spoken audio duration in seconds from the recorded WAV (optional)
        """
        debug_print(f"[DEBUG] record_transcription called with {len(text.split())} words")
        if not text or not text.strip():
            debug_print(f"[DEBUG] Skipping empty text")
            return

        word_count = len(text.split())
        today = datetime.date.today().isoformat()
        debug_print(f"[DEBUG] Recording: {word_count} words on {today}")

        # Calculate WPM if duration provided
        wpm = None
        if duration_sec and duration_sec > 0:
            # Convert duration to minutes and calculate WPM
            duration_min = duration_sec / 60.0
            wpm = round(word_count / duration_min) if duration_min > 0 else 0
            if wpm > self.MAX_REASONABLE_WPM:
                # Guard against corrupted duration inputs.
                debug_print(f"[DEBUG] Ignoring implausible WPM={wpm} (duration_sec={duration_sec})")
                wpm = None

        # Update totals
        self.data["total_words"] += word_count
        self.data["total_sessions"] += 1

        # Update WPM statistics
        if wpm is not None:
            # Track all WPM values for calculating averages
            if "wpm_history" not in self.data:
                self.data["wpm_history"] = []
            self.data["wpm_history"].append(wpm)
            # Keep last 100 WPM measurements
            self.data["wpm_history"] = self.data["wpm_history"][-100:]

            # Update best WPM
            current_best = self.data.get("best_wpm", 0)
            if wpm > current_best:
                self.data["best_wpm"] = wpm

        # Update daily counts
        if today not in self.data["daily_words"]:
            self.data["daily_words"][today] = 0
        self.data["daily_words"][today] += word_count

        # Update model usage
        if model not in self.data["model_usage"]:
            self.data["model_usage"][model] = 0
        self.data["model_usage"][model] += 1

        # Update recent transcripts (keep last 5)
        transcript_data = {
            "text": text[:200],  # Store first 200 chars for display
            "full_text": text,   # Store complete text for copying
            "word_count": word_count,
            "model": model,
            "timestamp": datetime.datetime.now().isoformat()
        }
        if wpm is not None:
            transcript_data["wpm"] = wpm
        self.data["recent_transcripts"].insert(0, transcript_data)
        self.data["recent_transcripts"] = self.data["recent_transcripts"][:5]

        # Update streak
        self._update_streak(today)

        # Check milestones
        self._check_milestones()

        # Save changes
        self.data["last_use_date"] = today
        self._save_stats()
    
    def _update_streak(self, today: str):
        """Update the usage streak.
        
        Args:
            today: Today's date in ISO format
        """
        last_use = self.data.get("last_use_date")
        
        if last_use is None:
            # First use
            self.data["streak"] = 1
        else:
            last_date = datetime.date.fromisoformat(last_use)
            current_date = datetime.date.fromisoformat(today)
            days_diff = (current_date - last_date).days
            
            if days_diff == 0:
                # Same day, no change
                pass
            elif days_diff == 1:
                # Consecutive day, increment streak
                self.data["streak"] += 1
            else:
                # Streak broken, reset to 1
                self.data["streak"] = 1
    
    def _check_milestones(self):
        """Check and award milestones."""
        total_words = self.data["total_words"]
        milestones = self.data["milestones"]
        best_wpm = self.data.get("best_wpm", 0)

        # Word count milestones (classic)
        word_thresholds = [1000, 5000, 10000, 25000, 50000, 100000]
        for threshold in word_thresholds:
            milestone_name = f"{threshold // 1000}K Words"
            if total_words >= threshold and milestone_name not in milestones:
                milestones.append(milestone_name)
                print(f"Milestone achieved: {milestone_name}!")

        # Gamified WPM milestones (more exciting!)
        wpm_milestones = [
            (50, "First Steps"),
            (100, "Speedster"),
            (150, "Quick Draw"),
            (200, "Fast Lane"),
            (250, "Race Car"),
            (300, "Helicopter"),
            (350, "Jet Plane"),
            (400, "Supersonic"),
            (450, "Lightning"),
            (500, "Quantum")
        ]

        for wpm_threshold, milestone_name in wpm_milestones:
            if best_wpm >= wpm_threshold and milestone_name not in milestones:
                milestones.append(milestone_name)
                print(f"WPM Milestone achieved: {milestone_name} ({wpm_threshold} WPM)!")

        # Special combo milestones
        if total_words >= 10000 and best_wpm >= 200 and "🎯 Transcription Master" not in milestones:
            milestones.append("🎯 Transcription Master")
            print("🏆 Special Milestone: Transcription Master (10K words + 200 WPM)!")

        if self.data["streak"] >= 30 and best_wpm >= 150 and "🔥 Consistency King" not in milestones:
            milestones.append("🔥 Consistency King")
            print("🏆 Special Milestone: Consistency King (30 day streak + 150 WPM)!")
    
    def get_today_words(self) -> int:
        """Get word count for today."""
        today = datetime.date.today().isoformat()
        return self.data["daily_words"].get(today, 0)
    
    def get_week_words(self) -> int:
        """Get word count for the last 7 days."""
        total = 0
        today = datetime.date.today()
        for i in range(7):
            day = (today - datetime.timedelta(days=i)).isoformat()
            total += self.data["daily_words"].get(day, 0)
        return total
    
    def get_week_data(self) -> List[Tuple[str, int]]:
        """Get last 7 days of word counts for graph.
        
        Returns:
            List of (day_name, word_count) tuples
        """
        data = []
        today = datetime.date.today()
        for i in range(6, -1, -1):
            day = today - datetime.timedelta(days=i)
            day_name = day.strftime("%a")
            words = self.data["daily_words"].get(day.isoformat(), 0)
            data.append((day_name, words))
        return data
    
    def get_week_comparison(self) -> Optional[float]:
        """Get percentage change vs last week.
        
        Returns:
            Percentage change, or None if no data for last week
        """
        this_week = self.get_week_words()
        today = datetime.date.today()
        
        last_week_total = 0
        for i in range(7, 14):
            day = (today - datetime.timedelta(days=i)).isoformat()
            last_week_total += self.data["daily_words"].get(day, 0)
        
        if last_week_total == 0:
            return None
        
        change = ((this_week - last_week_total) / last_week_total) * 100
        return change
    
    def get_summary(self) -> Dict:
        """Get a summary of all statistics.

        Returns:
            Dictionary with all stats
        """
        # Calculate average WPM
        wpm_history = self.data.get("wpm_history", [])
        avg_wpm = round(sum(wpm_history) / len(wpm_history)) if wpm_history else 0

        return {
            "total_words": self.data["total_words"],
            "total_sessions": self.data["total_sessions"],
            "today_words": self.get_today_words(),
            "week_words": self.get_week_words(),
            "streak": self.data["streak"],
            "milestones": self.data["milestones"],
            "model_usage": self.data["model_usage"],
            "recent_transcripts": self.data["recent_transcripts"],
            "avg_wpm": avg_wpm,
            "best_wpm": self.data.get("best_wpm", 0)
        }

