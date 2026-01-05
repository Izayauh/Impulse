"""
Statistics tracking for WhisperLocal.

This module handles tracking usage statistics, word counts, streaks,
milestones, and recent transcriptions.
"""

import json
import os
import datetime
from typing import Dict, List, Optional, Tuple
from .config import STATS_FILE


class StatsTracker:
    """Track usage statistics and achievements."""
    
    def __init__(self, stats_file: Optional[str] = None):
        """Initialize stats tracker.
        
        Args:
            stats_file: Path to stats JSON file. If None, uses default from config.
        """
        self.stats_file = stats_file or STATS_FILE
        self.data = self._load_stats()
    
    def _load_stats(self) -> Dict:
        """Load statistics from file."""
        default_stats = {
            "total_words": 0,
            "total_sessions": 0,
            "daily_words": {},
            "model_usage": {},
            "recent_transcripts": [],
            "milestones": [],
            "streak": 0,
            "last_use_date": None
        }
        
        if not os.path.exists(self.stats_file):
            return default_stats
        
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return {**default_stats, **json.load(f)}
        except (json.JSONDecodeError, IOError, OSError):
            return default_stats
    
    def _save_stats(self):
        """Save statistics to file."""
        try:
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
        except (IOError, OSError) as e:
            print(f"Warning: Could not save stats: {e}")
    
    def record_transcription(self, text: str, model: str):
        """Record a transcription event.
        
        Args:
            text: The transcribed text
            model: The model used (base.en, medium.en, large-v3)
        """
        if not text or not text.strip():
            return
        
        word_count = len(text.split())
        today = datetime.date.today().isoformat()
        
        # Update totals
        self.data["total_words"] += word_count
        self.data["total_sessions"] += 1
        
        # Update daily counts
        if today not in self.data["daily_words"]:
            self.data["daily_words"][today] = 0
        self.data["daily_words"][today] += word_count
        
        # Update model usage
        if model not in self.data["model_usage"]:
            self.data["model_usage"][model] = 0
        self.data["model_usage"][model] += 1
        
        # Update recent transcripts (keep last 5)
        self.data["recent_transcripts"].insert(0, {
            "text": text[:200],  # Store first 200 chars
            "word_count": word_count,
            "model": model,
            "timestamp": datetime.datetime.now().isoformat()
        })
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
        
        # Define milestone thresholds
        thresholds = [1000, 5000, 10000, 25000, 50000, 100000]
        
        for threshold in thresholds:
            milestone_name = f"{threshold // 1000}K"
            if total_words >= threshold and milestone_name not in milestones:
                milestones.append(milestone_name)
                print(f"🏆 Milestone achieved: {milestone_name} words!")
    
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
        return {
            "total_words": self.data["total_words"],
            "total_sessions": self.data["total_sessions"],
            "today_words": self.get_today_words(),
            "week_words": self.get_week_words(),
            "streak": self.data["streak"],
            "milestones": self.data["milestones"],
            "model_usage": self.data["model_usage"],
            "recent_transcripts": self.data["recent_transcripts"]
        }

