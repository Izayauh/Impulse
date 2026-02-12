"""Domain-oriented controllers for the WhisperLocal pywebview API.

Architecture follows the Modular Hierarchical Bridge pattern
described in the UI research document (§2.2).
"""

from whisper_local.controllers.settings_controller import SettingsController
from whisper_local.controllers.transcription_controller import TranscriptionController
from whisper_local.controllers.stats_controller import StatsController
from whisper_local.controllers.system_controller import SystemController

__all__ = [
    "SettingsController",
    "TranscriptionController",
    "StatsController",
    "SystemController",
]
