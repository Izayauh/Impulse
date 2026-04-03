# Impulse (WhisperLocal) - Agent Guidelines

> Canonical guidelines live in AGENTS.md at the project root. Read it before making any changes.

## CRITICAL: This is a Live Public Product

Impulse is a publicly distributed application with paying users. All changes must be made with this in mind. Do not make breaking changes, remove features, or alter user-facing behavior without explicit approval.

## Licensing System - DO NOT MODIFY OR REMOVE

The licensing system is a core part of the product and must not be altered, bypassed, weakened, or removed in any commit or code change. This includes:

- `src/whisper_local/licensing.py` - Core licensing logic
- `src/whisper_local/controllers/licensing_controller.py` - Licensing API controller
- Any license validation checks throughout the codebase
- The `WHISPER_DEV_BYPASS_LICENSE` environment variable is a developer-only mechanism for local testing. It must never be set, documented, or exposed in any user-facing code, scripts, documentation, or builds.

### Rules

1. Never remove or weaken license checks - Every code path that validates a license must remain intact.
2. Never expose the dev bypass - The `WHISPER_DEV_BYPASS_LICENSE` env var exists only for the developer's local convenience. Do not reference it in README, user guides, release scripts, or distributed bat files.
3. Never skip licensing in builds/releases - All distributed builds must require valid license activation.
4. Test licensing paths - If modifying startup flow or any code that touches licensing, verify that both licensed and unlicensed states work correctly.

## Project Structure

- `src/whisper_local/` - Core application code
- `src/whisper_local/ui/` - UI components (Python GUI + React dashboard)
- `src/whisper_local/controllers/` - API controllers
- `src/whisper_local/processing/` - Text processing pipeline
- `scripts/windows/` - Developer utility scripts (NOT for distribution)
- `web/` - Web components
- `api/` - API layer
