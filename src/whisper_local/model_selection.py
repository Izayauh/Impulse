"""Shared model-selection state and auto-resolution helpers."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Tuple


AUTO_VRAM_THRESHOLD_MB = 8 * 1024
VALID_MODES = {"auto", "base", "small", "medium"}
VALID_ACTIVE_MODELS = {"base", "small", "medium", "large"}


def model_selection_file(user_data_dir: str) -> str:
    return os.path.join(user_data_dir, "state", "model_selection.json")


def _normalize_mode(value: Any) -> str:
    mode = str(value or "").strip().lower()
    return mode if mode in VALID_MODES else "auto"


def _normalize_manual_model(value: Any) -> str:
    model = str(value or "").strip().lower()
    return model if model in {"base", "small", "medium"} else "base"


def _normalize_active_model(value: Any) -> str:
    model = str(value or "").strip().lower()
    return model if model in VALID_ACTIVE_MODELS else "base"


def default_state() -> Dict[str, Any]:
    return {
        "mode": "auto",
        "manual_model": "base",
        "active_model": "base",
        "vram_total_mb": 0.0,
    }


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def normalize_state(data: Any) -> Dict[str, Any]:
    base = default_state()
    payload = data if isinstance(data, dict) else {}
    state = {**base, **payload}
    state["mode"] = _normalize_mode(state.get("mode"))
    state["manual_model"] = _normalize_manual_model(state.get("manual_model"))
    state["active_model"] = _normalize_active_model(state.get("active_model"))
    state["vram_total_mb"] = _safe_float(state.get("vram_total_mb"))
    return state


def load_state(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return default_state()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return normalize_state(json.load(f))
    except (json.JSONDecodeError, OSError, IOError):
        return default_state()


def save_state(path: str, state: Dict[str, Any]) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(normalize_state(state), f, indent=2)
        return True
    except (OSError, IOError):
        return False


def auto_model_for_vram(vram_total_mb: Any) -> str:
    vram_mb = _safe_float(vram_total_mb)
    return "large" if vram_mb > AUTO_VRAM_THRESHOLD_MB else "base"


def apply_mode(state: Dict[str, Any], requested_mode: str, vram_total_mb: Any) -> Tuple[Dict[str, Any], bool]:
    current = normalize_state(state)
    previous_active = current["active_model"]

    mode = _normalize_mode(requested_mode)
    current["mode"] = mode
    if mode == "auto":
        current["vram_total_mb"] = _safe_float(vram_total_mb)
        current["active_model"] = auto_model_for_vram(vram_total_mb)
    else:
        current["manual_model"] = mode
        current["active_model"] = mode

    auto_switched = mode == "auto" and current["active_model"] != previous_active
    return current, auto_switched


def refresh_auto_state(state: Dict[str, Any], vram_total_mb: Any) -> Tuple[Dict[str, Any], bool]:
    current = normalize_state(state)
    if current["mode"] != "auto":
        return current, False

    previous_active = current["active_model"]
    current["vram_total_mb"] = _safe_float(vram_total_mb)
    current["active_model"] = auto_model_for_vram(vram_total_mb)
    return current, current["active_model"] != previous_active
