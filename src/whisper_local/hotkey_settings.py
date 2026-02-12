"""Persistent user hotkey settings shared by dashboard and dictation."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Iterable, List


DEFAULT_HOTKEY = "ctrl+windows"
MODIFIER_ORDER = ("ctrl", "alt", "shift", "windows")
MODIFIER_KEYS = set(MODIFIER_ORDER)

KEY_ALIASES = {
    "control": "ctrl",
    "ctl": "ctrl",
    "option": "alt",
    "meta": "windows",
    "win": "windows",
    "command": "windows",
    "cmd": "windows",
    "escape": "esc",
    "return": "enter",
    "spacebar": "space",
    "arrowup": "up",
    "arrowdown": "down",
    "arrowleft": "left",
    "arrowright": "right",
    "page up": "pageup",
    "page down": "pagedown",
    "caps lock": "capslock",
}

SPECIAL_KEYS = {
    "space",
    "tab",
    "enter",
    "esc",
    "backspace",
    "delete",
    "insert",
    "home",
    "end",
    "pageup",
    "pagedown",
    "up",
    "down",
    "left",
    "right",
    "capslock",
}


def settings_file(user_data_dir: str) -> str:
    return os.path.join(user_data_dir, "state", "settings.json")


def default_settings() -> Dict[str, Any]:
    return {"hotkey": DEFAULT_HOTKEY}


def _normalize_key_token(token: Any) -> str:
    key = str(token or "").strip().lower()
    if not key:
        return ""

    key = KEY_ALIASES.get(key, key)
    key = key.replace(" ", "")
    key = KEY_ALIASES.get(key, key)

    if key in MODIFIER_KEYS or key in SPECIAL_KEYS:
        return key
    if re.fullmatch(r"[a-z0-9]", key):
        return key
    if re.fullmatch(r"f([1-9]|1[0-9]|2[0-4])", key):
        return key
    if re.fullmatch(r"numpad[0-9]", key):
        return key
    return ""


def _parse_hotkey_tokens(value: Any) -> List[str]:
    raw_tokens: Iterable[Any]
    if isinstance(value, str):
        raw_tokens = [part.strip() for part in value.split("+")]
    elif isinstance(value, (list, tuple)):
        raw_tokens = value
    else:
        raw_tokens = []

    tokens: List[str] = []
    seen = set()
    for token in raw_tokens:
        normalized = _normalize_key_token(token)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        tokens.append(normalized)
    return tokens


def _ordered_hotkey_tokens(tokens: List[str]) -> List[str]:
    mods = [k for k in MODIFIER_ORDER if k in tokens]
    others = [k for k in tokens if k not in MODIFIER_KEYS]
    return mods + others


def _is_valid_hotkey_tokens(tokens: List[str]) -> bool:
    return len(tokens) >= 2 and any(token in MODIFIER_KEYS for token in tokens)


def try_normalize_hotkey(value: Any) -> str | None:
    tokens = _ordered_hotkey_tokens(_parse_hotkey_tokens(value))
    if not _is_valid_hotkey_tokens(tokens):
        return None
    return "+".join(tokens)


def normalize_hotkey(value: Any) -> str:
    normalized = try_normalize_hotkey(value)
    return normalized if normalized is not None else DEFAULT_HOTKEY


def hotkey_tokens(value: Any) -> List[str]:
    return _parse_hotkey_tokens(normalize_hotkey(value))


def normalize_settings(data: Any) -> Dict[str, Any]:
    payload = data if isinstance(data, dict) else {}
    merged = {**default_settings(), **payload}
    merged["hotkey"] = normalize_hotkey(merged.get("hotkey"))
    return merged


def load_settings(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return default_settings()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return normalize_settings(json.load(f))
    except (json.JSONDecodeError, OSError, IOError):
        return default_settings()


def save_settings(path: str, settings: Dict[str, Any]) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(normalize_settings(settings), f, indent=2)
        return True
    except (OSError, IOError):
        return False


def load_hotkey(path: str) -> str:
    return normalize_hotkey(load_settings(path).get("hotkey"))


def set_hotkey(path: str, value: Any) -> tuple[str, bool]:
    normalized = try_normalize_hotkey(value)
    if normalized is None:
        raise ValueError("Invalid hotkey")

    settings = load_settings(path)
    previous = normalize_hotkey(settings.get("hotkey"))
    settings["hotkey"] = normalized
    if not save_settings(path, settings):
        raise OSError("Could not save settings")
    return normalized, normalized != previous
