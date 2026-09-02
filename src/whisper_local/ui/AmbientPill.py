"""Ambient, non-verbal HUD pill for WhisperLocal."""

from __future__ import annotations

import math
import os
import queue
import time
from enum import Enum
from typing import Any, Callable, Optional
from whisper_local.settings_manager import SettingsManager

# ============================================================================
# CONFIGURATION
# ============================================================================
IDLE_DIMENSIONS = (10, 10)
ACTIVE_DIMENSIONS = (166, 48)
ANIMATION_SPEED_MS = 250
SENSITIVITY = 14.0
SMOOTHING_FACTOR = 0.20
IDLE_OPACITY = 0.0

_AUDIO_WIDTH_DELTA = 12
_AUDIO_HEIGHT_DELTA = 4
_GLOW_BASE = 6
_GLOW_DELTA = 12
_DOCK_MARGIN_BOTTOM = 16
_AUDIO_FPS = 30          # FPS while recording/processing (visible)
# Beta safety knob: set WHISPER_IDLE_AUDIO_FPS env var to override idle tick rate.
# Lower = less GPU compositor overhead when app is idle (default 2 FPS).
_AUDIO_FPS_IDLE = int(os.environ.get("WHISPER_IDLE_AUDIO_FPS", "2"))
_AUDIO_RESPONSE_ALPHA = 0.35
_AUDIO_MAX_STEP = 0.22
_PROCESSING_TIMEOUT_MS = 1200
_WAVE_BARS = 12
_LANDED_MS = 1000            # the landed moment: "+N" and today's total, then gone
_SWEEP_MS = 900              # one left-to-right pass of the working sweep
_SWEEP_SEGMENT = 0.4         # pink segment as a fraction of the line
_PILL_PAD = 16               # inner padding for the working and landed layouts
_SMALL_ICON = 16
_ICON_GAP = 10
_TEXT_COLOR = "#EDEDEF"
_MUTED_COLOR = "#9A9AA3"
# SENSITIVITY above is a fixed multiplier tuned for consumer mics with automatic
# gain, where speech lands near RMS 0.07. A gain-staged input (studio interface,
# XLR chain) speaks at RMS 0.002-0.02, which that multiplier renders as a 3-15%
# twitch — indistinguishable from a frozen pill. So normalise against the loudest
# level of the current take instead of an absolute constant.
_PEAK_DECAY = 0.995          # per level push (~33/s), so the reference follows the voice down
_LEVEL_FLOOR = 0.004         # just above RMS_THRESHOLD_VOICED; below this we render silence
_LEVEL_CURVE = 0.6           # <1 lifts quiet speech so the bars read on camera


def normalize_level(ema: float, peak: float) -> float:
    """Map a smoothed RMS to 0..1 relative to the take's own peak.

    Device-independent by construction: what matters is how loud this moment is
    against the loudest moment so far, not how hot the interface runs.
    """
    if ema <= _LEVEL_FLOOR:
        return 0.0
    ceiling = max(peak, _LEVEL_FLOOR)
    ratio = max(0.0, min(1.0, ema / ceiling))
    return ratio ** _LEVEL_CURVE


class PillState(str, Enum):
    IDLE = "IDLE"
    ARMED = "ARMED"
    RECORDING = "RECORDING"
    PROCESSING = "PROCESSING"
    LANDED = "LANDED"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    HINT = "HINT"


QtCore = None
QtGui = None
QtWidgets = None
QT_BINDING = None
QT_IMPORT_ERROR = None

try:
    from PySide6 import QtCore as _QtCore  # type: ignore
    from PySide6 import QtGui as _QtGui  # type: ignore
    from PySide6 import QtWidgets as _QtWidgets  # type: ignore

    QtCore = _QtCore
    QtGui = _QtGui
    QtWidgets = _QtWidgets
    QT_BINDING = "PySide6"
except ImportError as exc:
    QT_IMPORT_ERROR = f"PySide6 import failed: {exc}"
    try:
        from PyQt6 import QtCore as _QtCore  # type: ignore
        from PyQt6 import QtGui as _QtGui  # type: ignore
        from PyQt6 import QtWidgets as _QtWidgets  # type: ignore

        QtCore = _QtCore
        QtGui = _QtGui
        QtWidgets = _QtWidgets
        QT_BINDING = "PyQt6"
    except ImportError as exc:
        QT_BINDING = None
        QT_IMPORT_ERROR = f"PySide6 and PyQt6 imports failed: {exc}"


def is_qt_available() -> bool:
    return bool(QtCore and QtGui and QtWidgets and QT_BINDING)


def qt_backend_diagnostics() -> dict:
    return {
        "qt_available": bool(is_qt_available()),
        "qt_binding": QT_BINDING or "none",
        "qt_import_error": QT_IMPORT_ERROR or "",
    }


class QtUnavailableError(RuntimeError):
    pass


if is_qt_available():
    class _QtRootAdapter:
        """Tk-like adapter for the existing flow loop integration."""

        def __init__(self, pill: "AmbientPill"):
            self._pill = pill
            self._app = pill._app
            self._timers = set()

        def after(self, delay_ms: int, callback: Callable[[], Any]):
            timer = QtCore.QTimer()
            timer.setSingleShot(True)

            def _runner():
                self._timers.discard(timer)
                try:
                    callback()
                finally:
                    timer.deleteLater()

            timer.timeout.connect(_runner)
            timer.start(max(0, int(delay_ms)))
            self._timers.add(timer)
            return timer

        def after_cancel(self, timer):
            if timer in self._timers:
                self._timers.discard(timer)
                try:
                    timer.stop()
                except Exception:
                    pass
                try:
                    timer.deleteLater()
                except Exception:
                    pass

        def mainloop(self):
            return self._app.exec()

        def destroy(self):
            try:
                self._pill.close()
            finally:
                self._app.quit()

        def winfo_exists(self) -> bool:
            return not self._pill._closing

        def update_idletasks(self):
            self._app.processEvents()

        def winfo_id(self) -> int:
            return int(self._pill.winId())

        def lift(self):
            self._pill.raise_()

        def focus_force(self):
            self._pill.activateWindow()

    class AmbientPill(QtWidgets.QWidget):
        """Purely visual ambient capsule HUD with explicit state machine."""

        def __init__(
            self,
            ui_queue: "queue.Queue",
            on_open_dashboard: Optional[Callable[[], None]] = None,
            on_quit: Optional[Callable[[], None]] = None,
            is_armed_fn: Optional[Callable[[], bool]] = None,
            log_fn: Optional[Callable[..., None]] = None,
        ):
            app = QtWidgets.QApplication.instance()
            if app is None:
                app = QtWidgets.QApplication([])
            self._app = app

            super().__init__(None)
            self._queue = ui_queue
            self._on_open_dashboard = on_open_dashboard
            self._on_quit = on_quit
            self._is_armed_fn = is_armed_fn or (lambda: True)
            self._log_fn = log_fn

            flags = (
                QtCore.Qt.WindowType.WindowStaysOnTopHint
                | QtCore.Qt.WindowType.FramelessWindowHint
                | QtCore.Qt.WindowType.Tool
            )
            self.setWindowFlags(flags)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

            self._closing = False
            self.root = _QtRootAdapter(self)
            self._state = PillState.ARMED if self._is_armed_fn() else PillState.IDLE
            self._audio_ema = 0.0
            self._audio_peak = 0.0
            self._glow = 0.0
            self._audio_level_target = 0.0
            self._audio_level_display = 0.0
            
            try:
                theme_id = SettingsManager().get_setting("theme")
            except Exception:
                theme_id = "hot_pink"
                
            if theme_id == "neon_dark":
                self._base_accent = "#bb86fc"
                self._base_hover = "#d4b0ff"
            elif theme_id == "midnight_green":
                self._base_accent = "#00e676"
                self._base_hover = "#69f0ae"
            else:
                self._base_accent = "#FF1493"
                self._base_hover = "#FF69B4"
                
            self._pill_color = QtGui.QColor("#D6DCE4")
            self._base_size = QtCore.QSize(*IDLE_DIMENSIONS)
            self._last_target_size = QtCore.QSize(*IDLE_DIMENSIONS)
            self._anchor_center_x: Optional[int] = None
            self._anchor_bottom_y: Optional[int] = None
            self._processing_timer = QtCore.QTimer(self)
            self._processing_timer.setSingleShot(True)
            self._processing_timer.timeout.connect(self._transition_to_base_state)
            self._landed_timer = QtCore.QTimer(self)
            self._landed_timer.setSingleShot(True)
            self._landed_timer.timeout.connect(self._transition_to_base_state)
            self._landed_words = 0
            self._landed_total = 0
            self._phase_started = 0.0
            self._wave_phase = 0.0
            self._wave_levels = [0.10 for _ in range(_WAVE_BARS)]

            self._size_anim: Optional[QtCore.QVariantAnimation] = None
            self._color_anim: Optional[QtCore.QVariantAnimation] = None
            self._flash_timer = QtCore.QTimer(self)
            self._flash_timer.setSingleShot(True)
            self._flash_timer.timeout.connect(self._transition_to_base_state)

            self._audio_timer = QtCore.QTimer(self)
            self._audio_timer.timeout.connect(self._on_audio_tick)
            # Start at idle rate; _set_state will ramp up to _AUDIO_FPS when active
            self._audio_timer.start(int(1000 / max(1, _AUDIO_FPS_IDLE)))

            self.resize(self._base_size)
            self._position_docked()
            self.setWindowOpacity(IDLE_OPACITY)
            # Start hidden – the main loop calls show_for_active() on hotkey press
            self.hide()
            self.raise_()

        # ------------------------------------------------------------------
        # External integration API
        # ------------------------------------------------------------------
        def set_hotkey_hint(self, hotkey_value: str) -> None:
            self._hotkey_text = f"Hold {hotkey_value} to record"
            self._set_state(PillState.HINT)

        def set_audio_level(self, rms: float) -> None:
            if self._state != PillState.RECORDING:
                return
            level = max(0.0, float(rms))
            self._audio_ema = (1.0 - SMOOTHING_FACTOR) * self._audio_ema + SMOOTHING_FACTOR * level
            self._audio_peak = max(self._audio_ema, self._audio_peak * _PEAK_DECAY)
            self._audio_level_target = normalize_level(self._audio_ema, self._audio_peak)

        def set_status(self, state, text=None, bg=None, fg=None, border=None):
            _ = (text, bg, fg, border)
            target = self._coerce_state(state)
            self._set_state(target)

        def show_landed(self, word_count: int, today_total: int) -> None:
            """Show "+N" and today's total for one second, then hide."""
            words = int(word_count or 0)
            if words <= 0:
                self._transition_to_base_state()
                return
            self._landed_words = words
            self._landed_total = max(0, int(today_total or 0))
            self._set_state(PillState.LANDED)
            self._landed_timer.start(_LANDED_MS)
            self.update()

        def show(self):
            super().show()

        def hide(self):
            super().hide()

        def show_for_active(self) -> None:
            """Show the pill when the user presses the record hotkey."""
            self._set_audio_timer_rate(active=True)
            super().show()
            self.raise_()

        def hide_when_idle(self) -> None:
            """Hide the pill once it has returned to idle/armed state."""
            super().hide()
            self._set_audio_timer_rate(active=False)

        def pump_queue(self):
            self._drain_ui_queue()
            self.root.after(50, self.pump_queue)

        # ------------------------------------------------------------------
        # State machine
        # ------------------------------------------------------------------
        def _coerce_state(self, raw: Any) -> PillState:
            if isinstance(raw, PillState):
                return raw

            token = str(raw or "").strip()
            mapped = {
                "idle": PillState.IDLE,
                "armed": PillState.ARMED,
                "recording": PillState.RECORDING,
                "listening": PillState.RECORDING,
                "transcribing": PillState.PROCESSING,
                "processing": PillState.PROCESSING,
                "success": PillState.SUCCESS,
                "done": PillState.SUCCESS,
                "warning": PillState.ARMED if self._is_armed_fn() else PillState.IDLE,
                "error": PillState.ERROR,
                "ready": PillState.ARMED if self._is_armed_fn() else PillState.IDLE,
                "🎙️ Listening...": PillState.RECORDING,
                "⚙️ Transcribing...": PillState.PROCESSING,
                "✅ Pasted!": PillState.SUCCESS,
                "📋 Copied!": PillState.SUCCESS,
                "🔇 No speech": PillState.ARMED if self._is_armed_fn() else PillState.IDLE,
                "🔇 No speech detected": PillState.ARMED if self._is_armed_fn() else PillState.IDLE,
                "🔇 Empty transcript": PillState.ARMED if self._is_armed_fn() else PillState.IDLE,
                "🎤 Ready": PillState.ARMED if self._is_armed_fn() else PillState.IDLE,
                "❌ Error": PillState.ERROR,
                "❌ Try again": PillState.ERROR,
                "❌ Paste error": PillState.ERROR,
                "❌ Mic not ready": PillState.ERROR,
                "❌ Engine not found": PillState.ERROR,
            }
            return mapped.get(token, PillState.ARMED if self._is_armed_fn() else PillState.IDLE)

        def _set_audio_timer_rate(self, active: bool) -> None:
            """Switch the audio timer between active-rate and hidden-idle mode.

            When hidden, we fully stop the timer so Qt doesn't keep scheduling
            repaint-related ticks in the background. When visible/active, we
            run at full-rate for responsive animation.
            """
            if not active and not self.isVisible():
                if self._audio_timer.isActive():
                    self._audio_timer.stop()
                return

            interval_ms = int(1000 / max(1, _AUDIO_FPS if active else _AUDIO_FPS_IDLE))
            if not self._audio_timer.isActive() or self._audio_timer.interval() != interval_ms:
                self._audio_timer.start(interval_ms)

        def _set_state(self, target: PillState) -> None:
            if self._state == target:
                return

            self._state = target
            self._flash_timer.stop()
            self._processing_timer.stop()
            self._landed_timer.stop()

            # Completely hide the pill unless something is happening
            if target not in (PillState.RECORDING, PillState.PROCESSING, PillState.LANDED):
                self._audio_ema = 0.0
                self._audio_peak = 0.0
                self._audio_level_target = 0.0
                self._audio_level_display = 0.0
                self._glow = 0.0
                self.hide()
                # Drop to idle tick rate — no GPU compositor work needed while hidden
                self._set_audio_timer_rate(active=False)
                return

            # Prepare for active states — ramp up to full animation rate
            self._set_audio_timer_rate(active=True)
            if not self.isVisible():
                self.setWindowOpacity(0.0)
                self.show()

            if target == PillState.RECORDING:
                self._audio_ema = 0.0
                self._audio_peak = 0.0
                self._audio_level_target = 0.0
                self._audio_level_display = 0.0
                self._animate_size(*ACTIVE_DIMENSIONS, duration_ms=ANIMATION_SPEED_MS)
                self._animate_opacity(1.0)
                self._animate_color(QtGui.QColor(self._base_accent))
                return

            if target == PillState.PROCESSING:
                self._glow = 0.2
                self._phase_started = time.monotonic()
                self._animate_size(*ACTIVE_DIMENSIONS, duration_ms=ANIMATION_SPEED_MS)
                self._animate_color(QtGui.QColor(self._base_hover))
                self.setWindowOpacity(1.0)
                return

            if target == PillState.LANDED:
                self._glow = 0.0
                self._animate_size(*ACTIVE_DIMENSIONS, duration_ms=ANIMATION_SPEED_MS)
                self._animate_color(QtGui.QColor(self._base_accent))
                self.setWindowOpacity(1.0)
                return

        def _transition_to_base_state(self):
            base = PillState.ARMED if self._is_armed_fn() else PillState.IDLE
            self._set_state(base)

        def _on_audio_tick(self):
            if self._state != PillState.RECORDING:
                self._audio_level_display *= 0.85
                if self._state == PillState.PROCESSING:
                    self._wave_phase += 0.45
                    self._glow = 0.28 + (0.18 * (math.sin(self._wave_phase) * 0.5 + 0.5))
                else:
                    self._glow *= 0.9
                    self._wave_levels = [max(0.08, w * 0.86) for w in self._wave_levels]
                if self.isVisible():
                    self.update()
                return

            delta = self._audio_level_target - self._audio_level_display
            
            # Smooth audio tracking a bit more
            _AUDIO_MAX_STEP_SMOOTH = 0.15
            delta = max(-_AUDIO_MAX_STEP_SMOOTH, min(_AUDIO_MAX_STEP_SMOOTH, delta))
            self._audio_level_display += delta * 0.45
            normalized = max(0.0, min(1.0, self._audio_level_display))

            width = ACTIVE_DIMENSIONS[0] + int(normalized * _AUDIO_WIDTH_DELTA)
            height = ACTIVE_DIMENSIONS[1] + int(normalized * _AUDIO_HEIGHT_DELTA)
            self._glow = normalized
            self._wave_phase += 0.35

            for i in range(_WAVE_BARS):
                t = (i / max(1, _WAVE_BARS - 1)) * math.pi * 2.0
                shape = 0.45 + 0.55 * (math.sin(self._wave_phase + t) * 0.5 + 0.5)
                target = max(0.12, min(1.0, normalized * (0.45 + shape * 0.9)))
                self._wave_levels[i] = (self._wave_levels[i] * 0.58) + (target * 0.42)

            self._apply_size_direct(width, height)

        # ------------------------------------------------------------------
        # Animations
        # ------------------------------------------------------------------
        def _animate_size(self, width: int, height: int, duration_ms: int) -> None:
            clamped_w = max(IDLE_DIMENSIONS[0], min(width, ACTIVE_DIMENSIONS[0] + _AUDIO_WIDTH_DELTA))
            clamped_h = max(IDLE_DIMENSIONS[1], min(height, ACTIVE_DIMENSIONS[1] + _AUDIO_HEIGHT_DELTA))
            target = QtCore.QSize(clamped_w, clamped_h)
            if target == self._last_target_size:
                return
            self._last_target_size = target

            if self._size_anim is not None:
                try:
                    self._size_anim.stop()
                except RuntimeError:
                    pass  # finished animations delete themselves

            start = QtCore.QSize(self.width(), self.height())
            anim = QtCore.QVariantAnimation(self)
            anim.setDuration(max(50, int(duration_ms)))
            anim.setStartValue(start)
            anim.setEndValue(target)
            anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            anim.valueChanged.connect(self._apply_size_value)
            anim.finished.connect(anim.deleteLater)
            self._size_anim = anim
            anim.start()

        def _apply_size_value(self, value):
            if isinstance(value, QtCore.QSize):
                next_w = value.width()
                next_h = value.height()
            else:
                next_w = int(getattr(value, "width", lambda: self.width())())
                next_h = int(getattr(value, "height", lambda: self.height())())

            self._apply_size_direct(next_w, next_h)

        def _apply_size_direct(self, width: int, height: int):
            clamped_w = max(IDLE_DIMENSIONS[0], min(int(width), ACTIVE_DIMENSIONS[0] + _AUDIO_WIDTH_DELTA))
            clamped_h = max(IDLE_DIMENSIONS[1], min(int(height), ACTIVE_DIMENSIONS[1] + _AUDIO_HEIGHT_DELTA))

            center_x = self._anchor_center_x
            bottom_y = self._anchor_bottom_y
            if center_x is None or bottom_y is None:
                current = self.geometry()
                center_x = current.x() + (current.width() // 2)
                bottom_y = current.y() + current.height()

            self.resize(clamped_w, clamped_h)
            self.move(int(center_x - (clamped_w // 2)), int(bottom_y - clamped_h))
            self._last_target_size = QtCore.QSize(clamped_w, clamped_h)
            self.update()

        def _animate_color(self, target: "QtGui.QColor", duration_ms: int = ANIMATION_SPEED_MS) -> None:
            if self._color_anim is not None:
                try:
                    self._color_anim.stop()
                except RuntimeError:
                    pass  # finished animations delete themselves
            start_color = QtGui.QColor(self._pill_color)
            anim = QtCore.QVariantAnimation(self)
            anim.setDuration(max(60, int(duration_ms)))
            anim.setStartValue(start_color)
            anim.setEndValue(target)
            anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            anim.valueChanged.connect(self._on_color_step)
            anim.finished.connect(anim.deleteLater)
            self._color_anim = anim
            anim.start()

        def _on_color_step(self, color_value):
            if isinstance(color_value, QtGui.QColor):
                self._pill_color = color_value
            else:
                self._pill_color = QtGui.QColor(color_value)
            self.update()

        def _animate_opacity(self, target: float, duration_ms: int = ANIMATION_SPEED_MS) -> None:
            current = float(self.windowOpacity())
            anim = QtCore.QVariantAnimation(self)
            anim.setDuration(max(60, int(duration_ms)))
            anim.setStartValue(current)
            anim.setEndValue(max(0.05, min(1.0, float(target))))
            anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            anim.valueChanged.connect(lambda value: self.setWindowOpacity(float(value)))
            anim.finished.connect(anim.deleteLater)
            anim.start()

        # ------------------------------------------------------------------
        # Drawing and placement
        # ------------------------------------------------------------------
        def _position_docked(self):
            screen = self.screen() or QtGui.QGuiApplication.primaryScreen()
            if screen is None:
                return
            available = screen.availableGeometry()
            self._anchor_center_x = available.x() + (available.width() // 2)
            self._anchor_bottom_y = available.y() + available.height() - _DOCK_MARGIN_BOTTOM
            self.move(int(self._anchor_center_x - (self.width() // 2)), int(self._anchor_bottom_y - self.height()))

        def paintEvent(self, event):
            _ = event
            if self._state not in (PillState.RECORDING, PillState.PROCESSING, PillState.LANDED):
                return

            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)

            bounds = self.rect().adjusted(1, 1, -1, -1)
            radius = bounds.height() / 2.0

            if self._glow > 0.01:
                glow_rect = bounds.adjusted(
                    -int(_GLOW_BASE + self._glow * _GLOW_DELTA),
                    -int(_GLOW_BASE + self._glow * (_GLOW_DELTA * 0.55)),
                    int(_GLOW_BASE + self._glow * _GLOW_DELTA),
                    int(_GLOW_BASE + self._glow * (_GLOW_DELTA * 0.55)),
                )
                glow_color = QtGui.QColor(self._pill_color)
                glow_color.setAlpha(int(10 + (self._glow * 50)))
                painter.setBrush(glow_color)
                painter.drawRoundedRect(glow_rect, glow_rect.height() / 2.0, glow_rect.height() / 2.0)

            base = QtGui.QColor("#040608")
            base.setAlpha(220)
            painter.setBrush(base)
            painter.drawRoundedRect(bounds, radius, radius)

            border = QtGui.QColor(self._pill_color)
            border.setAlpha(80)
            if self._state == PillState.PROCESSING:
                border.setAlpha(120)
            elif self._state == PillState.LANDED:
                border = QtGui.QColor(self._base_accent)
                border.setAlpha(115)
            pen = QtGui.QPen(border)
            pen.setWidthF(1.0)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(bounds, radius, radius)

            center_y = bounds.center().y()
            accent_color = QtGui.QColor(self._base_accent)

            if self._state == PillState.PROCESSING:
                self._paint_working(painter, bounds, center_y, accent_color)
                return
            if self._state == PillState.LANDED:
                self._paint_landed(painter, bounds, center_y, accent_color)
                return

            # --- Listening: mic plus level bars ---
            start_x = bounds.left() + 24
            icon_size = 18
            icon_rect = QtCore.QRectF(start_x, center_y - icon_size / 2.0, icon_size, icon_size)

            painter.save()
            painter.setPen(QtGui.QPen(accent_color, 1.8, QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap, QtCore.Qt.PenJoinStyle.RoundJoin))
            cx, cy = icon_rect.center().x(), icon_rect.center().y()
            # Mic body
            painter.drawRoundedRect(QtCore.QRectF(cx - 3, cy - 6, 6, 10), 3, 3)
            # U-arc
            p = QtGui.QPainterPath()
            p.moveTo(cx - 5, cy - 2)
            p.arcTo(QtCore.QRectF(cx - 5, cy - 4, 10, 8), 180, 180)
            painter.drawPath(p)
            # Stem and Base
            painter.drawLine(QtCore.QPointF(cx, cy + 4), QtCore.QPointF(cx, cy + 7))
            painter.drawLine(QtCore.QPointF(cx - 3, cy + 7), QtCore.QPointF(cx + 3, cy + 7))

            # Pulse glow when recording
            pulse_color = QtGui.QColor(accent_color)
            pulse_color.setAlpha(int(15 + 15 * math.sin(self._wave_phase)))
            painter.setBrush(pulse_color)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.drawEllipse(icon_rect.center(), icon_size * 1.5, icon_size * 1.5)
            painter.restore()

            start_x += 24 + 14

            middle_width = 54
            bars = _WAVE_BARS
            spacing = middle_width / (bars + 1)
            bar_color = QtGui.QColor(accent_color)
            bar_color.setAlpha(160)
            bar_pen = QtGui.QPen(bar_color)
            bar_pen.setWidthF(3.0)
            bar_pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
            painter.setPen(bar_pen)
            max_h = bounds.height() * 0.45
            for i in range(bars):
                level = self._wave_levels[i] if i < len(self._wave_levels) else 0.15
                h = max(3.0, max_h * level)
                x = start_x + i * spacing
                painter.drawLine(QtCore.QPointF(x, center_y - h / 2.0), QtCore.QPointF(x, center_y + h / 2.0))

        def _paint_working(self, painter, bounds, center_y, accent):
            """Working: the bars fold into a 2 px line with a pink sweep, an arc spins where the mic was."""
            elapsed_ms = max(0.0, time.monotonic() - self._phase_started) * 1000.0
            fold = max(0.0, min(1.0, elapsed_ms / ANIMATION_SPEED_MS))
            icon_rect = QtCore.QRectF(bounds.left() + _PILL_PAD, center_y - _SMALL_ICON / 2.0, _SMALL_ICON, _SMALL_ICON)

            painter.save()
            painter.translate(icon_rect.center())
            painter.rotate((elapsed_ms / _SWEEP_MS * 360.0) % 360.0)
            painter.translate(-icon_rect.center())
            painter.setPen(QtGui.QPen(accent, 2.0, QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap))
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawArc(icon_rect.adjusted(1, 1, -1, -1), 0, 90 * 16)
            painter.restore()

            line_left = icon_rect.right() + _ICON_GAP
            line_width = max(1.0, (bounds.right() - _PILL_PAD) - line_left)

            if fold < 1.0:
                bar_color = QtGui.QColor(accent)
                bar_color.setAlpha(int(160 * (1.0 - fold)))
                bar_pen = QtGui.QPen(bar_color)
                bar_pen.setWidthF(3.0)
                bar_pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
                painter.setPen(bar_pen)
                spacing = line_width / (_WAVE_BARS + 1)
                max_h = bounds.height() * 0.45
                for i in range(_WAVE_BARS):
                    level = self._wave_levels[i] if i < len(self._wave_levels) else 0.15
                    h = max(3.0, max_h * level) * (1.0 - fold) + 2.0 * fold
                    x = line_left + (i + 1) * spacing
                    painter.drawLine(QtCore.QPointF(x, center_y - h / 2.0), QtCore.QPointF(x, center_y + h / 2.0))

            line_rect = QtCore.QRectF(line_left, center_y - 1.0, line_width, 2.0)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(255, 255, 255, int(31 * fold)))
            painter.drawRoundedRect(line_rect, 1.0, 1.0)

            t = (elapsed_ms % _SWEEP_MS) / _SWEEP_MS
            eased = 0.5 - 0.5 * math.cos(math.pi * t)
            seg_x = line_left + (eased * (1.0 + _SWEEP_SEGMENT) - _SWEEP_SEGMENT) * line_width
            sweep = QtGui.QColor(accent)
            sweep.setAlpha(int(255 * fold))
            painter.save()
            painter.setClipRect(line_rect)
            painter.setBrush(sweep)
            painter.drawRoundedRect(QtCore.QRectF(seg_x, center_y - 1.0, line_width * _SWEEP_SEGMENT, 2.0), 1.0, 1.0)
            painter.restore()

        def _paint_landed(self, painter, bounds, center_y, accent):
            """Landed: pink check, "+N" for this take, today's total right-aligned."""
            icon_rect = QtCore.QRectF(bounds.left() + _PILL_PAD, center_y - _SMALL_ICON / 2.0, _SMALL_ICON, _SMALL_ICON)
            k = _SMALL_ICON / 24.0
            check = QtGui.QPainterPath()
            check.moveTo(icon_rect.left() + 5 * k, icon_rect.top() + 12 * k)
            check.lineTo(icon_rect.left() + 10 * k, icon_rect.top() + 17 * k)
            check.lineTo(icon_rect.left() + 19 * k, icon_rect.top() + 7 * k)
            painter.setPen(QtGui.QPen(accent, 2.0, QtCore.Qt.PenStyle.SolidLine, QtCore.Qt.PenCapStyle.RoundCap, QtCore.Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawPath(check)

            text_left = icon_rect.right() + _ICON_GAP
            text_rect = QtCore.QRectF(text_left, center_y - 10.0, max(1.0, (bounds.right() - _PILL_PAD) - text_left), 20.0)
            align_v = QtCore.Qt.AlignmentFlag.AlignVCenter

            painter.setFont(self._mono_font(13))
            painter.setPen(QtGui.QColor(_TEXT_COLOR))
            gained = f"+{self._landed_words:,}"
            painter.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignLeft | align_v, gained)
            room = text_rect.width() - painter.fontMetrics().horizontalAdvance(gained) - _ICON_GAP

            painter.setFont(self._mono_font(12))
            painter.setPen(QtGui.QColor(_MUTED_COLOR))
            total = f"{self._landed_total:,} today"
            if self._landed_total >= 1000 and painter.fontMetrics().horizontalAdvance(total) > room:
                total = f"{self._landed_total / 1000.0:.1f}k today"
            painter.drawText(text_rect, QtCore.Qt.AlignmentFlag.AlignRight | align_v, total)

        @staticmethod
        def _mono_font(pixel_size: int):
            font = QtGui.QFont()
            font.setFamilies(["Geist Mono", "Cascadia Mono", "Consolas", "Courier New"])
            font.setStyleHint(QtGui.QFont.StyleHint.Monospace)
            font.setPixelSize(pixel_size)
            font.setWeight(QtGui.QFont.Weight.Medium)
            return font

        # ------------------------------------------------------------------
        # Input and queue handling
        # ------------------------------------------------------------------
        def mousePressEvent(self, event):
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                if callable(self._on_open_dashboard):
                    try:
                        self._on_open_dashboard()
                    except Exception:
                        pass
            elif event.button() == QtCore.Qt.MouseButton.RightButton:
                self._show_context_menu(event.globalPosition().toPoint())
            super().mousePressEvent(event)

        def _show_context_menu(self, pos):
            menu = QtWidgets.QMenu(self)
            open_action = menu.addAction("Open Dashboard")
            quit_action = menu.addAction("Quit")
            action = menu.exec(pos)
            if action == open_action and callable(self._on_open_dashboard):
                self._on_open_dashboard()
            elif action == quit_action:
                if callable(self._on_quit):
                    self._on_quit()
                else:
                    self.root.destroy()

        def _drain_ui_queue(self):
            try:
                while True:
                    fn, args = self._queue.get_nowait()
                    try:
                        fn(*args)
                    except Exception:
                        pass
            except queue.Empty:
                pass

        def closeEvent(self, event):
            self._closing = True
            try:
                self._audio_timer.stop()
            except Exception:
                pass
            super().closeEvent(event)
else:
    class AmbientPill:  # pragma: no cover - used only when Qt is unavailable
        def __init__(self, *args, **kwargs):
            _ = (args, kwargs)
            raise QtUnavailableError("Install PySide6 or PyQt6 to use AmbientPill.")
