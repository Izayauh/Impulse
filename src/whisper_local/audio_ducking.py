"""System playback ducking utilities for push-to-talk recording."""

from __future__ import annotations

import ctypes
import json
import os
import sys
import threading
import time
from ctypes import wintypes
from typing import Callable, Optional


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def ratio_to_waveout_raw(level: float) -> int:
    """Convert 0.0-1.0 ratio to WinMM packed stereo DWORD."""
    sample = int(round(_clamp01(level) * 65535.0))
    return (sample & 0xFFFF) | ((sample & 0xFFFF) << 16)


def waveout_raw_to_percent(raw_value: int) -> float:
    """Return average L/R channel volume as a percent."""
    raw = int(raw_value) & 0xFFFFFFFF
    left = raw & 0xFFFF
    right = (raw >> 16) & 0xFFFF
    return ((left + right) / 2.0) * 100.0 / 65535.0


class WaveOutVolumeBackend:
    """Windows volume backend based on winmm waveOut* APIs."""

    _WAVE_MAPPER = 0xFFFFFFFF

    def __init__(self) -> None:
        self._available = bool(sys.platform == "win32" and hasattr(ctypes, "windll") and hasattr(ctypes.windll, "winmm"))
        self._wave_out_get = None
        self._wave_out_set = None

        if not self._available:
            return

        winmm = ctypes.windll.winmm
        self._wave_out_get = winmm.waveOutGetVolume
        self._wave_out_set = winmm.waveOutSetVolume
        self._wave_out_get.argtypes = [wintypes.UINT, ctypes.POINTER(wintypes.DWORD)]
        self._wave_out_get.restype = wintypes.UINT
        self._wave_out_set.argtypes = [wintypes.UINT, wintypes.DWORD]
        self._wave_out_set.restype = wintypes.UINT

    @property
    def is_available(self) -> bool:
        return self._available

    def get_volume_raw(self) -> int:
        if not self._available:
            raise RuntimeError("Windows waveOut backend unavailable")
        value = wintypes.DWORD(0)
        result = self._wave_out_get(self._WAVE_MAPPER, ctypes.byref(value))
        if result != 0:
            raise OSError(f"waveOutGetVolume failed (MMRESULT={result})")
        return int(value.value)

    def set_volume_raw(self, raw_value: int) -> None:
        if not self._available:
            raise RuntimeError("Windows waveOut backend unavailable")
        result = self._wave_out_set(self._WAVE_MAPPER, wintypes.DWORD(int(raw_value) & 0xFFFFFFFF))
        if result != 0:
            raise OSError(f"waveOutSetVolume failed (MMRESULT={result})")


class EndpointVolumeBackend:
    """Windows CoreAudio endpoint volume backend (preferred on Win10/11)."""

    def __init__(self) -> None:
        self._available = False
        self._endpoint = None
        if not sys.platform.startswith("win"):
            return
        try:
            from comtypes import CLSCTX_ALL  # type: ignore
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore

            device = AudioUtilities.GetSpeakers()
            interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self._endpoint = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
            self._available = self._endpoint is not None
        except Exception:
            self._available = False
            self._endpoint = None

    @property
    def is_available(self) -> bool:
        return self._available and self._endpoint is not None

    def get_volume_raw(self) -> int:
        if not self.is_available:
            raise RuntimeError("CoreAudio endpoint backend unavailable")
        scalar = float(self._endpoint.GetMasterVolumeLevelScalar())
        return ratio_to_waveout_raw(scalar)

    def set_volume_raw(self, raw_value: int) -> None:
        if not self.is_available:
            raise RuntimeError("CoreAudio endpoint backend unavailable")
        scalar = _clamp01((int(raw_value) & 0xFFFF) / 65535.0)
        self._endpoint.SetMasterVolumeLevelScalar(float(scalar), None)


class CompositeVolumeBackend:
    """Try CoreAudio first, then WinMM waveOut fallback."""

    def __init__(self) -> None:
        self._backends = [EndpointVolumeBackend(), WaveOutVolumeBackend()]
        self._backend = next((b for b in self._backends if b.is_available), None)

    @property
    def is_available(self) -> bool:
        return self._backend is not None and self._backend.is_available

    def get_volume_raw(self) -> int:
        if not self.is_available:
            raise RuntimeError("No audio volume backend available")
        return self._backend.get_volume_raw()

    def set_volume_raw(self, raw_value: int) -> None:
        if not self.is_available:
            raise RuntimeError("No audio volume backend available")
        self._backend.set_volume_raw(raw_value)


class AudioDuckingSessionManager:
    """Reference-counted duck/restore manager for hold-to-record workflows."""

    def __init__(
        self,
        state_file: Optional[str] = None,
        duck_level: float = 0.0,
        restore_delay_ms: int = 90,
        backend: Optional[WaveOutVolumeBackend] = None,
        log_fn: Optional[Callable[..., None]] = None,
        time_fn: Optional[Callable[[], float]] = None,
    ) -> None:
        self._backend = backend or CompositeVolumeBackend()
        self._state_file = state_file
        self._duck_raw_volume = ratio_to_waveout_raw(duck_level)
        self._restore_delay_sec = max(0.0, float(restore_delay_ms) / 1000.0)
        self._log_fn = log_fn
        self._time_fn = time_fn or time.time

        self._lock = threading.RLock()
        self._active_holds = 0
        self._duck_applied = False
        self._saved_raw_volume: Optional[int] = None
        self._pending_restore_timer: Optional[threading.Timer] = None

    @property
    def is_available(self) -> bool:
        return bool(self._backend and self._backend.is_available)

    @property
    def backend_name(self) -> str:
        if not self._backend:
            return "none"
        inner = getattr(self._backend, "_backend", None)
        if inner is not None:
            return inner.__class__.__name__
        return self._backend.__class__.__name__

    def _emit_log(self, message: str, level: str = "info") -> None:
        if not self._log_fn:
            return
        try:
            self._log_fn(message, level=level)
        except TypeError:
            try:
                self._log_fn(message, level)
            except TypeError:
                self._log_fn(message)
        except Exception:
            pass

    def _write_state(self, active: bool, saved_raw: Optional[int]) -> None:
        if not self._state_file:
            return
        payload = {
            "version": 1,
            "active": bool(active),
            "saved_raw_volume": int(saved_raw) if saved_raw is not None else None,
            "duck_raw_volume": int(self._duck_raw_volume),
            "pid": os.getpid(),
            "timestamp_unix": self._time_fn(),
        }
        try:
            os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
            with open(self._state_file, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
        except OSError as exc:
            self._emit_log(f"[duck] failed to persist state file: {exc}", level="warning")

    def _clear_state(self) -> None:
        if not self._state_file:
            return
        try:
            if os.path.exists(self._state_file):
                os.remove(self._state_file)
        except OSError as exc:
            self._emit_log(f"[duck] failed to clear state file: {exc}", level="warning")

    def _cancel_pending_restore_locked(self) -> None:
        timer = self._pending_restore_timer
        self._pending_restore_timer = None
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass

    def _restore_locked(self, reason: str = "") -> bool:
        self._cancel_pending_restore_locked()

        if not self._duck_applied:
            self._saved_raw_volume = None
            self._clear_state()
            return False

        restored = False
        saved_raw = self._saved_raw_volume
        try:
            if saved_raw is not None and self._backend.is_available:
                self._backend.set_volume_raw(saved_raw)
                restored = True
                self._emit_log(
                    "DUCK_RESTORE "
                    + f"restored_raw={saved_raw} "
                    + f"restored_pct={waveout_raw_to_percent(saved_raw):.1f} "
                    + f"reason={reason or '-'}"
                )
        except Exception as exc:
            self._emit_log(f"DUCK_RESTORE_FAILED reason={reason or '-'} error={exc}", level="error")
        finally:
            self._duck_applied = False
            self._saved_raw_volume = None
            self._clear_state()
        return restored

    def _restore_from_timer(self) -> None:
        with self._lock:
            self._pending_restore_timer = None
            if self._active_holds > 0:
                return
            self._restore_locked(reason="debounced_release")

    def activate(self, reason: str = "hotkey_hold") -> bool:
        """Apply ducking for an active hold; idempotent across nested calls."""
        with self._lock:
            if not self._backend.is_available:
                self._emit_log(
                    f"DUCK_APPLY_SKIPPED reason={reason} backend_unavailable=1",
                    level="warning",
                )
                return False

            self._cancel_pending_restore_locked()
            self._active_holds += 1
            if self._duck_applied:
                return True

            try:
                current_raw = self._backend.get_volume_raw()
            except Exception as exc:
                self._active_holds = max(0, self._active_holds - 1)
                self._emit_log(f"DUCK_APPLY_FAILED reason={reason} capture_error={exc}", level="warning")
                return False

            self._saved_raw_volume = current_raw
            self._write_state(active=True, saved_raw=current_raw)

            try:
                if current_raw != self._duck_raw_volume:
                    self._backend.set_volume_raw(self._duck_raw_volume)
                self._duck_applied = True
                self._emit_log(
                    "DUCK_APPLY "
                    + f"saved_raw={current_raw} "
                    + f"saved_pct={waveout_raw_to_percent(current_raw):.1f} "
                    + f"target_raw={self._duck_raw_volume} "
                    + f"target_pct={waveout_raw_to_percent(self._duck_raw_volume):.1f} "
                    + f"reason={reason or '-'}"
                )
                return True
            except Exception as exc:
                self._active_holds = max(0, self._active_holds - 1)
                self._duck_applied = False
                self._saved_raw_volume = None
                self._clear_state()
                self._emit_log(f"DUCK_APPLY_FAILED reason={reason} apply_error={exc}", level="error")
                return False

    def release(self, force: bool = False, reason: str = "hotkey_release") -> bool:
        """Release one hold and restore when no holds remain."""
        with self._lock:
            if force:
                self._active_holds = 0
                return self._restore_locked(reason=reason)

            if self._active_holds <= 0:
                return False

            self._active_holds -= 1
            if self._active_holds > 0:
                return False

            if not self._duck_applied:
                self._clear_state()
                return False

            if self._restore_delay_sec <= 0:
                return self._restore_locked(reason=reason)

            self._cancel_pending_restore_locked()
            timer = threading.Timer(self._restore_delay_sec, self._restore_from_timer)
            timer.daemon = True
            self._pending_restore_timer = timer
            timer.start()
            return True

    def force_restore(self, reason: str = "force_restore") -> bool:
        """Immediately restore original volume regardless of hold count."""
        return self.release(force=True, reason=reason)

    def restore_stale_state(self) -> bool:
        """Restore volume if previous run crashed while ducking was active."""
        if not self._state_file or not self._backend.is_available:
            return False
        if not os.path.exists(self._state_file):
            return False

        try:
            with open(self._state_file, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, json.JSONDecodeError):
            self._clear_state()
            return False

        if not bool(payload.get("active")):
            self._clear_state()
            return False

        saved_raw = payload.get("saved_raw_volume")
        if not isinstance(saved_raw, int):
            self._clear_state()
            return False

        try:
            self._backend.set_volume_raw(saved_raw)
            self._emit_log(
                "DUCK_RESTORE_STALE "
                + f"restored_raw={saved_raw} "
                + f"restored_pct={waveout_raw_to_percent(saved_raw):.1f}"
            )
            return True
        except Exception as exc:
            self._emit_log(f"DUCK_RESTORE_STALE_FAILED error={exc}", level="error")
            return False
        finally:
            self._clear_state()
