# Project Impulse – Implementation Plan (2/22)

## Recently Completed
### Hotkeys & Interactions
- [x] **Speech Bubble Pop-Up On Demand**: Modified `AmbientPill` and `FloatingPill` to hide completely when idle, only showing the visual pill when `Ctrl+Win` is pressed to record.
- [x] **Latch / Toggle Mode**: Added `Ctrl+Win+Alt` toggle to latch recording on without holding buttons. Speaking continues to record until the hotkey is pressed again to stop and transcribe.

## Next Steps / Backlog

### Core Dictation & LLM Features (Next Priorities)
- [x] **Refine Stylization profiles & Ollama integration strategy**: Simplified from 5 profiles to 3 (off/clean/polished). Clean = no Ollama, fillers removed, human-sounding. Polished = light grammar/punctuation fix via constrained Ollama prompt (temp 0.15). Added Ollama setup step to first-run wizard with auto-detection, download link, and model pull. Old profile names auto-migrate. 339 tests pass.
- [x] **Implement Continual Context memorization**: After each transcription a daemon thread calls `extract_and_learn()` (Ollama `/api/generate`, non-blocking) to extract proper nouns/technical terms and add genuinely new ones to `continual_context.json`. Ollama offline → silent no-op. Capped at 10 words per transcription. Fixed `load_context()` mutable-default-list bug. Added `tests/test_continual_context.py` (8 tests, 336 total pass).

### Bug Fixes
- [x] **Fix voice dictation not working (keyboard library failure)**: The `keyboard` library's low-level hooks silently fail on Windows 11, causing `is_pressed()` to always return False. Replaced with Win32 `GetAsyncKeyState` API via ctypes for reliable key detection. Also fixed: `poll_hotkey` could die silently from unhandled exceptions (added top-level try/except + heartbeat logging), `debug_print` crashed on emoji characters due to cp1252 encoding, and StreamHandler logging failed on Unicode. 339 tests pass.

### Quality of Life
- [ ] Improve dictionary feature
- [ ] Refactor hardcoded dictionary words

### System Improvements
- [ ] Optimize application speed
- [ ] Improve microphone selection system
- [ ] Preemptively fix installation issues
- [ ] Evaluate health check interval

## Notes for Outside Agents (Claude Code, Codex, etc.)
- The primary UI/pill logic is located in `src/whisper_local/ui/AmbientPill.py` and `flow_local_dictation.py`.
- Hotkey detection uses Win32 `GetAsyncKeyState` API (ctypes) instead of the `keyboard` library's hook-based `is_pressed()` which silently fails on Windows 11. See `_win32_is_pressed()` and `_are_all_keys_pressed()` in `flow_local_dictation.py`.
- `poll_hotkey()` has a top-level try/except and 60-second heartbeat log (`[POLL_HEARTBEAT]`) to detect silent failures.
- The `.venv` environment might need missing dependencies (e.g. `pytest`) if you want to run tests manually (`python -m pytest tests/`).
