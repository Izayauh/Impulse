# Project Impulse – Implementation Plan (2/22)

## Recently Completed
### Hotkeys & Interactions
- [x] **Speech Bubble Pop-Up On Demand**: Modified `AmbientPill` and `FloatingPill` to hide completely when idle, only showing the visual pill when `Ctrl+Win` is pressed to record.
- [x] **Latch / Toggle Mode**: Added `Ctrl+Win+Alt` toggle to latch recording on without holding buttons. Speaking continues to record until the hotkey is pressed again to stop and transcribe.

## Next Steps / Backlog

### Core Dictation & LLM Features (Next Priorities)
- [ ] Refine Stylization profiles & Ollama integration strategy
- [ ] Implement Continual Context memorization

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
- Hotkey capture and routing uses the `keyboard` library on Windows, managed inside `poll_hotkey()` in `flow_local_dictation.py`.
- The `.venv` environment might need missing dependencies (e.g. `pytest`) if you want to run tests manually (`python -m pytest tests/`).
