# UI_CONTEXT.md — WhisperLocal Visual Spec

> **Purpose**: This file is the single source of truth for the WhisperLocal dashboard UI.
> Any AI model reading this document can reconstruct the full visual layout, data bindings,
> and update lifecycle without needing a screenshot.
>
> **Last updated**: 2026-02-10

---

## 1. Architecture Overview

```
+--------------------------------------------------+
|  Python Backend (SSOT)                           |
|  gui_host.py → AppApi                            |
|    ├── .settings      (SettingsController)       |
|    ├── .transcription  (TranscriptionController)  |
|    ├── .stats          (StatsController / SQLite)  |
|    └── .system         (SystemController)         |
+------------|-------------------------------------+
             | pywebview bridge
             v
+--------------------------------------------------+
|  JS Bridge abstraction (dashboard.html)          |
|  Bridge.settings.*  Bridge.transcription.*       |
|  Bridge.stats.*     Bridge.system.*              |
+------------|-------------------------------------+
             | async calls + digest-based polling
             v
+--------------------------------------------------+
|  JS Render Functions                             |
|  renderHome() → renderWelcomeHeader()            |
|                → renderActivityGraph()            |
|                → renderRecentTimeline()           |
|  renderSnippets(), renderDictionary()            |
|  renderAchievements(), renderChallenges()        |
+--------------------------------------------------+
```

**Data flow rule**: Python owns all state. JS polls via Bridge, receives data,
updates the global `stats` object, and calls `scheduleRender()`.

---

## 2. Window Layout

```
+--Sidebar (250px fixed)--------+--Main Panel (fluid, min 380px)--------+
|                               |                                        |
|  [brand-dot] Whisper Local    |  Main Toolbar                          |
|  Lvl {stats.level}            |  [Copy Last]              [- ] [x]    |
|  #sidebar-level               |                                        |
|                               |  #tab-content                          |
|  Sidebar Nav                  |  (innerHTML swapped per view)          |
|  [Home]         "Feed"        |                                        |
|  [Snippets]     {count}       |  Currently 5 views:                    |
|  [Dictionary]   {count}       |    home | snippets | dictionary        |
|  [Achievements] {u}/{total}   |    achievements | challenges           |
|  [Challenges]   "Daily"       |                                        |
|                               |                                        |
|  (spacer — margin-top:auto)   |                                        |
|                               |                                        |
|  Profile Card                 |                                        |
|  [WL] Rank: {stats.rank}     |                                        |
|       {totalWords} XP         |                                        |
|                    [gear]     |                                        |
+-------------------------------+----------------------------------------+
```

### CSS Grid
- `#app-shell`: `grid-template-columns: 250px 1fr`
- Sidebar: fixed position, full height, `background: linear-gradient(...)`
- Main panel: `margin-left: 250px`, `padding: 18px 24px`
- Breakpoint `<=980px`: sidebar becomes horizontal, single-column layout

---

## 3. Home View (default)

```
+--home-left (360-440px)--------+--home-right (fluid)-------------------+
|                               |                                        |
|  WelcomeHeader (.home-header) |  RecentTimeline (.activity-section)    |
|  ┌────────────────────────┐   |  ┌────────────────────────────────┐    |
|  │ Welcome back, {userName}│  |  │ Recent Activity    {DATE}     │    |
|  │ Voice performance...    │  |  │                                │    |
|  │                         │  |  │ ┌─TimelineCard──────────────┐ │    |
|  │ [Lvl] [XP] [Streak]    │  |  │ │ {time}  {text}    [Copy]  │ │    |
|  │       [Weekly Words]    │  |  │ │         {words} words     │ │    |
|  │                         │  |  │ └──────────────────────────-┘ │    |
|  │ XP Progress             │  |  │ ┌─TimelineCard──────────────┐ │    |
|  │ ███████░░░░ 2300/3500   │  |  │ │ ...                       │ │    |
|  └────────────────────────┘   |  │ └──────────────────────────-┘ │    |
|                               |  │ (up to 5 cards, scrollable)   │    |
|  HeroCard                     |  └────────────────────────────────┘    |
|  ┌────────────────────────┐   |                                        |
|  │ Voice dictation in any  │  |                                        |
|  │ app...     [Copy latest]│  |                                        |
|  └────────────────────────┘   |                                        |
|                               |                                        |
|  ActivityGraph (.mini-activity)|                                       |
|  ┌────────────────────────┐   |                                        |
|  │ Weekly activity  {N}w   │  |                                        |
|  │                         │  |                                        |
|  │  ▓  ▓     ▓        █   │  |                                        |
|  │  ▓  ▓  ▓  ▓  ▓  ▓  █   │  |                                        |
|  │ Mon Tue Wed Thu Fri Sat Sun|                                        |
|  │                    ^^^     |                                        |
|  │              today=green   |                                        |
|  └────────────────────────┘   |                                        |
+-------------------------------+----------------------------------------+
```

### CSS Grid
- `.home-view`: `grid-template-columns: minmax(360px, 440px) minmax(0, 1fr)`
- `.home-left`, `.home-right`: `display: grid; gap: 14px; align-content: start`

---

## 4. Component Registry

| Component | CSS Selector | BEM Alias | data-source | data-update-fn | data-bind |
|-----------|-------------|-----------|-------------|----------------|-----------|
| **Sidebar Level** | `#sidebar-level` | — | `Bridge.stats.get` | `updateSidebar` | `stats.level` |
| **Sidebar Rank** | `#rank` | — | `Bridge.stats.get` | `updateSidebar` | `stats.rank` |
| **Sidebar XP** | `#header-xp-display` | — | `Bridge.stats.get` | `updateSidebar` | `stats.totalWords` |
| **Snippet Count** | `#snippet-count` | — | `Bridge.settings.getSnippets` | `updateSidebar` | `snippets.length` |
| **Dictionary Count** | `#dictionary-count` | — | `Bridge.settings.getVocabulary` | `updateSidebar` | `vocabularyWords.length` |
| **Achievement Count** | `#achievement-count` | — | `Bridge.stats.getAchievements` | `updateSidebar` | `achievements.unlocked/total` |
| **Welcome Header** | `.home-header` | `.WelcomeHeader` | `Bridge.stats.get` | `renderWelcomeHeader` | multiple chips |
| ↳ Level Chip | `.metric-chip:nth(1)` | `.WelcomeHeader__chip` | — | — | `stats.level` |
| ↳ XP Chip | `.metric-chip-xp` | `.WelcomeHeader__chip` | — | — | `stats.xp` |
| ↳ Streak Chip | `.metric-chip-streak` | `.WelcomeHeader__chip` | — | — | `stats.dayStreak` |
| ↳ Weekly Chip | `.metric-chip-week` | `.WelcomeHeader__chip` | — | — | `stats.thisWeek` |
| ↳ XP Bar | `.xp-fill` | `.XpProgress__fill` | — | — | `stats.xp / stats.xpToNextLevel` |
| **Activity Graph** | `.mini-activity` | `.ActivityGraph` | `Bridge.stats.getChartData` | `renderActivityGraph` | `stats.last7Days` |
| ↳ Bar (per day) | `.mini-bar-col` | `.ActivityGraph__bar` | — | — | `stats.last7Days[i].words` |
| ↳ Today Bar | `.mini-bar-col.is-today` | `.ActivityGraph__bar--today` | — | — | last element |
| ↳ Value Label | `.mini-bar-value` | `.ActivityGraph__value` | — | — | word count |
| ↳ Day Label | `.mini-day` | `.ActivityGraph__label` | — | — | day name |
| **Recent Timeline** | `.activity-section` | `.RecentTimeline` | `Bridge.stats.getHistory` | `renderRecentTimeline` | `stats.recentTranscripts` |
| ↳ Card | `.timeline-card` | `.RecentTimeline__card` | — | — | transcript object |
| ↳ Time | `.timeline-time` | `.RecentTimeline__time` | — | — | `.time` |
| ↳ Body | `.timeline-body` | `.RecentTimeline__body` | — | — | `.fullText` |
| ↳ Meta | `.timeline-meta` | `.RecentTimeline__meta` | — | — | `.words` |
| **Hero Card** | `.hero-card` | — | none (static) | — | — |

---

## 5. Other Views

### 5.1 Snippets View
```
+--Left (360-460px)-------------+--Right (fluid)------------------------+
| View Header                   | Snippet List (scrollable)              |
|  "Snippets"    [Add new]      |  trigger -> replacement  [Copy] [Del] |
|                               |  trigger -> replacement  [Copy] [Del] |
| Snippet Banner                |  ...                                   |
|  "The stuff you should not    |                                        |
|   have to re-type."           |                                        |
|  [pill] [pill] [pill]         |                                        |
|                               |                                        |
| Scope Tabs + Search           |                                        |
|  [All] [Personal] [Shared]   |                                        |
|  [Search snippets...]        |                                        |
+-------------------------------+----------------------------------------+
```
- Render fn: `renderSnippets()`
- Data source: `Bridge.settings.getSnippets()` → `snippets[]`
- CSS: `.snippets-view` grid `minmax(360px, 460px) minmax(0, 1fr)`

### 5.2 Dictionary View
```
+--Single column (max 760px)----+
| View Header                   |
|  "Dictionary"                 |
|                               |
| Dictionary Editor             |
|  [Add word or phrase...] [Add]|
|                               |
| Dictionary List               |
|  (pill) (pill) (pill) (pill)  |
+-------------------------------+
```
- Render fn: `renderDictionary()`
- Data source: `Bridge.settings.getVocabulary()` → `vocabularyWords[]`
- CSS: `.dictionary-view` single column, `max-width: 760px`

### 5.3 Achievements View
```
+--Full width-------------------+
| View Header                   |
|  "Achievements" N of M unlkd  |
|                               |
| Rarity Grid (4-col)           |
|  [Common N/M] [Rare N/M]     |
|  [Epic N/M]   [Legendary N/M]|
|                               |
| Category Filters              |
|  [All] [Milestones] [Speed]  |
|  [Streaks] [Accuracy] ...    |
|                               |
| Achievement Grid (auto-fill)  |
|  ┌─Card──┐ ┌─Card──┐ ┌─Card─┐|
|  │ icon  │ │ icon  │ │ LOCK │|
|  │ name  │ │ name  │ │ name │|
|  │ desc  │ │ desc  │ │ desc │|
|  │ +XP   │ │ +XP   │ │ bar  │|
|  └───────┘ └───────┘ └──────┘|
+-------------------------------+
```
- Render fn: `renderAchievements()`
- Data source: `Bridge.stats.getAchievements()` → `achievements[]`
- CSS: `.achievement-grid` `repeat(auto-fill, minmax(210px, 1fr))`

### 5.4 Challenges View
```
+--Left col---------------------+--Right col------------------------+
| View Header (spans both)      |                                    |
|  "Challenges"                 |                                    |
|                               |                                    |
| Daily Challenges              | Weekly Challenges                  |
|  ┌─ChallengeCard───────────┐  |  ┌─ChallengeCard───────────┐      |
|  │ Word Count      +50 XP  │  |  │ Weekly Words    +200 XP  │      |
|  │ ████████░░░░░░          │  |  │ ██████░░░░░░░░           │      |
|  │ 420 / 500 words         │  |  │ 3200 / 5000 words        │      |
|  └─────────────────────────┘  |  └─────────────────────────-┘      |
|                               |                                    |
| Records Grid (spans both, 2x2)|                                   |
|  [Most Words Day] [Fastest WPM]                                    |
|  [Longest Session] [Best Streak]                                   |
+-------------------------------+------------------------------------+
```
- Render fn: `renderChallenges()`
- Data source: `Bridge.stats.get()` → `stats.today`, `stats.avgWpm`, `weekWords()`
- CSS: `.challenges-view` `repeat(2, minmax(0, 1fr))`

---

## 6. Settings Modal

Opened by gear icon. Overlay with 4-tab navigation.

```
+--Settings Dialog (max 980px)---------------------------------+
| Settings                                              [x]    |
+--Settings Nav (230px)--+--Settings Panel (fluid)-------------+
|                        |                                      |
| [General]              |  (content changes per tab)           |
| [Audio]                |                                      |
| [Models]               |                                      |
| [Data]                 |                                      |
+------------------------+--------------------------------------+
```

### 6.1 General Tab
| Setting | Control | data key |
|---------|---------|----------|
| Launch Behavior | `<select>` | `settingsState.launchBehavior` |
| Theme | `<select>` | `settingsState.theme` |
| Record Shortcut | hotkey input + record button | `settingsState.hotkey` |
| Command Mode | toggle switch | `settingsState.commandMode` |
| Auto-copy | toggle switch | `settingsState.autoCopy` |

### 6.2 Audio Tab
| Setting | Control | data key |
|---------|---------|----------|
| Microphone Input | `<select>` | `settingsState.microphone` |
| VAD Sensitivity | `<input type=range>` 1-100 | `settingsState.vadSensitivity` |
| Silence Timeout | `<input type=range>` 250-2000ms | `settingsState.vadSilenceMs` |

### 6.3 Models Tab
4-column card grid: `[Auto] [Base] [Small] [Medium]`
- Active card has purple border
- Auto card shows current model + VRAM info
- Data source: `Bridge.transcription.getModelMode()`
- Action: `Bridge.transcription.setModelMode(m)`

### 6.4 Data Tab
| Setting | Control |
|---------|---------|
| Export History | `[Export History]` button → `Bridge.system.exportCsv()` |
| Snapshot | Read-only summary: total words, recent count, achievements |

---

## 7. Data Flow: Polling Lifecycle

```
DOMContentLoaded
  └─► startPyPoll() [once, when Bridge.ready()]
       ├─► loadStatsFromPython()         → Bridge.stats.get()
       ├─► loadChartDataFromSqlite()     → Bridge.stats.getChartData(7)
       ├─► loadTotalsFromSqlite()        → Bridge.stats.getTotals()
       ├─► loadAchievementsFromPython()  → Bridge.stats.getAchievements()
       ├─► loadRecentTranscriptionsFromPython() → Bridge.stats.getHistory()
       ├─► loadModelSettingsFromPython() → Bridge.transcription.getModelMode()
       ├─► loadVocabularyFromPython()    → Bridge.settings.getVocabulary()
       ├─► loadHotkeyFromPython()        → Bridge.settings.getHotkey()
       ├─► loadSnippetsFromPython()      → Bridge.settings.getSnippets()
       ├─► loadUserSettingsFromPython()  → Bridge.settings.getAll()
       └─► setInterval(pollPythonData, 1000ms)

pollPythonData() [every 1s]
  ├─► Stats-heavy views (home/challenges): every tick
  │    ├─► loadStatsFromPython()
  │    ├─► loadChartDataFromSqlite()
  │    └─► loadTotalsFromSqlite()
  ├─► Achievements view: every tick (else every 15th)
  ├─► Home view: loadRecentTranscriptionsFromPython()
  ├─► Models settings visible: every tick (else every 30th)
  ├─► Dictionary view: every tick (else every 30th)
  ├─► General settings open: every tick (else every 30th)
  ├─► Snippets view: every tick (else every 30th)
  └─► User settings: every 60th tick
```

### Digest-based change detection
Every loader function computes `JSON.stringify(data)` and compares to a stored
digest string. If unchanged, no re-render occurs. This prevents DOM thrashing
during the 1s polling cycle.

---

## 8. Async Events (Python → JS)

The `TranscriptionController` pushes events via `window.evaluate_js()`:

```
window.bridgeEvents = {
  onLoadProgress(pct)    → console.log (model loading %)
  onModelLoaded(name)    → showToast + loadModelSettingsFromPython()
  onError(msg)           → console.error + showToast
}
```

---

## 9. Toast / Notification System

| Container | Position | Purpose |
|-----------|----------|---------|
| `#toast-container` | fixed top-right | General notifications |
| `#achievement-toast-container` | fixed bottom-right | Achievement unlocks |
| `#achievement-popup` | fixed top-center | Large achievement card |
| `#confetti-container` | fixed fullscreen | Particle effects |

All use `mountAnimatedNode()` with CSS opacity/transform transitions.

---

## 10. Color Palette

| Variable | Value | Usage |
|----------|-------|-------|
| `--bg` | `#111116` | Page background |
| `--sidebar` | `#1a1a20` | Sidebar background |
| `--card` | `#25252e` | Card backgrounds |
| `--text` | `#f5f6ff` | Primary text |
| `--muted` | `#a6a7bf` | Secondary text, labels |
| `--border` | `#333447` | All borders |
| `--purple` | `#bb86fc` | Primary accent, XP bar start, active states |
| `--green` | `#03dac6` | Secondary accent, XP bar end, today bar |
| `--red` | `#cf6679` | Streak chips, error toasts |

---

## 11. Key Files

| File | Purpose |
|------|---------|
| `src/whisper_local/ui/dashboard.html` | Full frontend: HTML + JS (Bridge, renderers, polling) |
| `src/whisper_local/ui/styles.css` | All CSS with BEM aliases |
| `src/whisper_local/ui/gui_host.py` | AppApi bridge host + pywebview lifecycle |
| `src/whisper_local/controllers/settings_controller.py` | Settings, hotkey, vocabulary, snippets |
| `src/whisper_local/controllers/transcription_controller.py` | Model loading, VRAM check, bridgeEvents |
| `src/whisper_local/controllers/stats_controller.py` | SQLite analytics (WAL mode) |
| `src/whisper_local/controllers/system_controller.py` | Window, clipboard, CSV export |
| `src/whisper_local/settings_manager.py` | Pydantic-backed settings validation |
