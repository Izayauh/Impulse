"""Unified settings manager for WhisperLocal.

Single source of truth for persistent user preferences.
Loads/saves to ``user_settings.json`` in the state directory.
Uses Pydantic for schema validation so corrupt or hand-edited
files are auto-corrected on startup.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, ValidationError

from whisper_local.config import get_user_data_dir


# ---------------------------------------------------------------------------
# Pydantic Schema  (Research §6.1)
# ---------------------------------------------------------------------------

class TranscriptionSettings(BaseModel):
    model_size: Literal["tiny", "base", "small", "medium", "large"] = "base"
    language: Optional[str] = Field(None, min_length=2, max_length=5)
    use_gpu: bool = True


class AppSettings(BaseModel):
    """Top-level settings schema with validation."""
    whisper_model: str = "base"
    input_device: str = "default"
    theme: Literal["hot_pink", "neon_dark", "midnight_green"] = "hot_pink"
    vad_enabled: bool = True
    hotkey: str = "ctrl+win"
    save_to_file: bool = False
    launch_behavior: Literal["start_minimized", "open_dashboard"] = "start_minimized"
    command_mode: bool = True
    auto_copy: bool = True
    stylization_profile: Literal["off", "clean", "polished"] = "clean"
    ollama_model: str = "llama3.2:3b"
    ollama_endpoint: str = "http://127.0.0.1:11434"
    vad_sensitivity: int = Field(65, ge=1, le=100)
    vad_silence_ms: int = Field(700, ge=250, le=2000)
    telemetry_enabled: bool = False
    transcription: TranscriptionSettings = Field(default_factory=TranscriptionSettings)


# ---------------------------------------------------------------------------
# Path helper
# ---------------------------------------------------------------------------

def _settings_path(user_data_dir: str | None = None) -> str:
    base = user_data_dir or get_user_data_dir()
    return os.path.join(base, "state", "user_settings.json")


# ---------------------------------------------------------------------------
# Manager class
# ---------------------------------------------------------------------------

class SettingsManager:
    """Load, read, and persist user settings from a single JSON file.

    Pydantic ensures that invalid or missing keys are auto-corrected to
    defaults, so the application can never boot with bad state.
    """

    def __init__(self, user_data_dir: str | None = None) -> None:
        self.path = _settings_path(user_data_dir)
        first_run = not os.path.exists(self.path)
        self._model: AppSettings = self._load()
        if first_run:
            self._save()

    # -- persistence --------------------------------------------------------

    def _load(self) -> AppSettings:
        if not os.path.exists(self.path):
            return AppSettings()
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                return AppSettings()
            known_keys = set(AppSettings.model_fields.keys())
            filtered = {k: v for k, v in raw.items() if k in known_keys}
            # Migrate old stylization profiles to simplified set
            _profile_migration = {"casual": "clean", "formal": "polished", "technical": "polished"}
            old_profile = filtered.get("stylization_profile")
            if old_profile in _profile_migration:
                filtered["stylization_profile"] = _profile_migration[old_profile]
            return AppSettings(**filtered)
        except (json.JSONDecodeError, OSError, IOError):
            return AppSettings()
        except ValidationError as exc:
            print(f"[SettingsManager] Validation error, reverting to defaults: {exc}")
            return AppSettings()

    def _save(self) -> bool:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(self._model.model_dump_json(indent=2))
            return True
        except (OSError, IOError):
            return False

    # -- public API (unchanged signatures for backward compat) --------------

    def get_setting(self, key: str) -> Any:
        return self._model.model_dump().get(key)

    def update_setting(self, key: str, value: Any) -> bool:
        data = self._model.model_dump()
        data[key] = value
        try:
            self._model = AppSettings(**data)
        except ValidationError:
            return False
        return self._save()

    def get_all(self) -> Dict[str, Any]:
        return self._model.model_dump()

    def update_many(self, updates: Dict[str, Any]) -> bool:
        data = self._model.model_dump()
        data.update(updates)
        try:
            self._model = AppSettings(**data)
        except ValidationError:
            return False
        return self._save()

    def reload(self) -> None:
        self._model = self._load()
