"""Transcription controller – manages the Whisper model lifecycle.

Uses ThreadPoolExecutor for non-blocking model loading with progress
callbacks via ``window.evaluate_js()`` (Research §3.3).
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from whisper_local.model_selection import (
    apply_mode,
    load_state as load_model_selection_state,
    refresh_auto_state,
    save_state as save_model_selection_state,
)


class TranscriptionController:
    """Exposed to JS as ``pywebview.api.transcription.*``."""

    def __init__(
        self,
        model_selection_file: str,
        vram_getter,
        settings_mgr=None,
    ) -> None:
        self._model_file = model_selection_file
        self._get_vram = vram_getter
        self._settings_mgr = settings_mgr
        self._window = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._is_loading = False
        self._lock = threading.Lock()
        self.stop_event = threading.Event()

    def set_window(self, window) -> None:
        self._window = window

    # -- model state --------------------------------------------------------

    def _load_state(self) -> Dict[str, Any]:
        return load_model_selection_state(self._model_file)

    def _save_state(self, state: Dict[str, Any]) -> bool:
        return save_model_selection_state(self._model_file, state)

    def _build_payload(self, state: Dict[str, Any], auto_switched: bool) -> Dict[str, Any]:
        vram_total_mb = float(state.get("vram_total_mb", 0.0) or 0.0)
        return {
            "mode": state.get("mode", "auto"),
            "manualModel": state.get("manual_model", "base"),
            "activeModel": state.get("active_model", "base"),
            "vramTotalMb": vram_total_mb,
            "vramTotalGb": round(vram_total_mb / 1024.0, 2) if vram_total_mb > 0 else 0.0,
            "autoSwitched": bool(auto_switched),
        }

    # -- public API ---------------------------------------------------------

    def get_model_mode(self) -> Dict[str, Any]:
        state = self._load_state()
        resolved, auto_switched = refresh_auto_state(state, self._get_vram())
        if resolved != state:
            self._save_state(resolved)
        return self._build_payload(resolved, auto_switched)

    def set_model_mode(self, mode: str) -> Dict[str, Any]:
        current = self._load_state()
        updated, auto_switched = apply_mode(current, mode, self._get_vram())
        self._save_state(updated)
        if self._settings_mgr:
            self._settings_mgr.update_setting(
                "whisper_model", updated.get("active_model", "base")
            )
        return self._build_payload(updated, auto_switched)

    def load_model(self, model_name: str) -> Dict[str, Any]:
        """Fire-and-forget model load (Research §3.3).

        Returns immediately with ``{status: 'pending'}``.
        Progress and completion are pushed via ``bridgeEvents``.
        """
        with self._lock:
            if self._is_loading:
                return {"status": "error", "message": "A model is already loading."}
            self._is_loading = True

        self._executor.submit(self._load_model_task, model_name)
        return {"status": "pending", "message": f"Queued load for {model_name}..."}

    def get_loading_status(self) -> Dict[str, Any]:
        return {"isLoading": self._is_loading}

    # -- background worker --------------------------------------------------

    def _load_model_task(self, model_name: str) -> None:
        try:
            # VRAM pre-check
            vram_mb = self._get_vram()
            requirements_mb = {
                "tiny": 1024, "base": 1024, "small": 2048,
                "medium": 5120, "large": 10240,
            }
            req = requirements_mb.get(model_name, 1024)
            if vram_mb > 0 and vram_mb < req:
                self._emit_error(
                    f"Insufficient VRAM. {model_name.title()} requires "
                    f"~{req // 1024}GB, but you have {vram_mb / 1024:.1f}GB."
                )
                return

            # Simulate progress stages (real model load would go here)
            stages = [10, 30, 50, 70, 90, 100]
            for pct in stages:
                if self.stop_event.is_set():
                    return
                self._emit_progress(pct)

            # Apply mode change
            result = self.set_model_mode(model_name)
            self._emit_model_loaded(result.get("activeModel", model_name))

        except Exception as exc:
            self._emit_error(str(exc))
        finally:
            with self._lock:
                self._is_loading = False

    # -- evaluate_js helpers ------------------------------------------------

    def _eval_js(self, code: str) -> None:
        if self._window is None:
            return
        try:
            self._window.evaluate_js(code)
        except Exception:
            pass

    def _emit_progress(self, percent: int) -> None:
        self._eval_js(f"window.bridgeEvents && window.bridgeEvents.onLoadProgress({percent})")

    def _emit_model_loaded(self, model_name: str) -> None:
        safe = str(model_name).replace("'", "")
        self._eval_js(f"window.bridgeEvents && window.bridgeEvents.onModelLoaded('{safe}')")

    def _emit_error(self, msg: str) -> None:
        safe = str(msg).replace("'", "").replace("\\", "")
        self._eval_js(f"window.bridgeEvents && window.bridgeEvents.onError('{safe}')")

    # -- lifecycle ----------------------------------------------------------

    def shutdown(self) -> None:
        self.stop_event.set()
        self._executor.shutdown(wait=False)
