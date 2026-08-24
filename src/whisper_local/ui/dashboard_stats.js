// Placeholder stats for the browser-based dashboard.
//
// This file ships inside the installer and is what the dashboard renders when
// the pywebview bridge has not supplied live stats yet. It must therefore stay
// synthetic: it was previously an export of a real machine's usage, which meant
// one person's dictated text was distributed to every user and shown in their
// app whenever the bridge was slow or unavailable.
//
// Never regenerate this from a real profile. Keep the shape in sync with
// gui_host.py's stats payload.
window.WHISPER_STATS = {
  "xp": 0,
  "xpToNextLevel": 1000,
  "level": 1,
  "rank": "Getting Started",
  "nextRank": "Word Warrior",
  "today": 0,
  "thisWeek": 0,
  "thisMonth": 0,
  "totalWords": 0,
  "totalSessions": 0,
  "totalTime": "0h 0m",
  "avgWpm": 0,
  "bestWpm": 0,
  "dayStreak": 0,
  "bestStreak": 0,
  "weekStreak": 0,
  "sessionWords": 0,
  "sessionWpm": 0,
  "sessionTime": "0:00",
  "accuracy": 0,
  "dailyGoal": 500,
  "last7Days": [
    { "day": "Mon", "words": 0 },
    { "day": "Tue", "words": 0 },
    { "day": "Wed", "words": 0 },
    { "day": "Thu", "words": 0 },
    { "day": "Fri", "words": 0 },
    { "day": "Sat", "words": 0 },
    { "day": "Sun", "words": 0 }
  ],
  "recentTranscripts": [],
  "records": {
    "mostWordsDay": { "value": 0, "date": "N/A" },
    "fastestWpm": { "value": 0, "date": "N/A" },
    "longestSession": { "value": "N/A", "date": "N/A" },
    "longestStreak": { "value": 0, "date": "N/A" }
  }
};
window.WHISPER_ACHIEVEMENTS = [];
