"""Settings controller – manages configuration state and persistence.

Wraps the SettingsManager and exposes methods to the JS bridge.
Handles hotkey, vocabulary, and snippets as sub-domains.
"""

from __future__ import annotations

from typing import Any, Dict, List

from whisper_local.settings_manager import SettingsManager
from whisper_local.hotkey_settings import (
    load_hotkey,
    set_hotkey as save_hotkey_value,
    normalize_hotkey,
)
from whisper_local.vocabulary import (
    add_vocabulary_word as add_vocabulary_word_to_file,
    load_vocabulary,
    save_vocabulary,
)
from whisper_local.snippets import (
    add_snippet as add_snippet_to_file,
    delete_snippet as delete_snippet_from_file,
    load_snippets,
)


class SettingsController:
    """Exposed to JS as ``pywebview.api.settings.*``."""

    def __init__(
        self,
        settings_mgr: SettingsManager,
        hotkey_file: str,
        vocabulary_file: str,
        snippets_file: str,
    ) -> None:
        self._mgr = settings_mgr
        self._hotkey_file = hotkey_file
        self._vocabulary_file = vocabulary_file
        self._snippets_file = snippets_file

    # -- unified settings ---------------------------------------------------

    def get_all(self) -> Dict[str, Any]:
        self._mgr.reload()
        return {"ok": True, "settings": self._mgr.get_all()}

    def update(self, key: str, value: Any) -> Dict[str, Any]:
        ok = self._mgr.update_setting(key, value)
        return {"ok": ok, "key": key, "value": value}

    def save(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ok = self._mgr.update_many(data)
        return {"ok": ok, "settings": self._mgr.get_all()}

    # -- hotkey -------------------------------------------------------------

    def get_hotkey(self) -> Dict[str, Any]:
        hotkey = load_hotkey(self._hotkey_file)
        return {"ok": True, "hotkey": hotkey}

    def set_hotkey(self, hotkey: str) -> Dict[str, Any]:
        try:
            value, changed = save_hotkey_value(self._hotkey_file, hotkey)
            self._mgr.update_setting("hotkey", value)
            return {"ok": True, "hotkey": value, "changed": bool(changed)}
        except ValueError:
            return {"ok": False, "error": "Invalid hotkey"}
        except OSError:
            return {"ok": False, "error": "Failed to save hotkey"}

    # -- vocabulary ---------------------------------------------------------

    def get_vocabulary(self) -> List[str]:
        return load_vocabulary(self._vocabulary_file)

    def add_vocabulary_word(self, word: str) -> Dict[str, Any]:
        words, added = add_vocabulary_word_to_file(self._vocabulary_file, word)
        return {"ok": True, "added": bool(added), "words": words}

    # -- snippets -----------------------------------------------------------

    def get_snippets(self) -> List[Dict[str, Any]]:
        return load_snippets(self._snippets_file)

    def add_snippet(self, trigger: str, replacement: str) -> Dict[str, Any]:
        return add_snippet_to_file(self._snippets_file, trigger, replacement)

    def delete_snippet(self, snippet_id: int) -> Dict[str, Any]:
        return delete_snippet_from_file(self._snippets_file, snippet_id)
