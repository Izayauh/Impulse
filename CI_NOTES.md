# Whisper Local - Development Notes

This file tracks development notes for CI and testing.

## CI / GitHub Actions

- Integration tests under `tests/integration/` are excluded from CI runs.
  These are manual hardware/diagnostic scripts that require a physical keyboard and GPU.
- HuggingFace model tests in `TestRestorePunctuation` are skipped in GitHub Actions
  to prevent long download timeouts.
