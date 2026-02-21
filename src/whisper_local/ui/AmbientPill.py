"""Ambient, non-verbal HUD pill for WhisperLocal."""

from __future__ import annotations

import math
import queue
from enum import Enum
from typing import Any, Callable, Optional
from whisper_local.settings_manager import SettingsManager

# ============================================================================
# CONFIGURATION
# ============================================================================
IDLE_DIMENSIONS = (44, 10)
ACTIVE_DIMENSIONS = (96, 24)
ANIMATION_SPEED_MS = 135
SENSITIVITY = 14.0
SMOOTHING_FACTOR = 0.20
IDLE_OPACITY = 0.40

_AUDIO_WIDTH_DELTA = 22
_AUDIO_HEIGHT_DELTA = 4
_GLOW_BASE = 6
_GLOW_DELTA = 12
_DOCK_MARGIN_BOTTOM = 12
_AUDIO_FPS = 30
_AUDIO_RESPONSE_ALPHA = 0.35
_AUDIO_MAX_STEP = 0.22
_PROCESSING_TIMEOUT_MS = 1200
_WAVE_BARS = 11


class PillState(str, Enum):
    IDLE = "IDLE"
    ARMED = "ARMED"
    RECORDING = "RECORDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


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
            self._wave_phase = 0.0
            self._wave_levels = [0.10 for _ in range(_WAVE_BARS)]

            self._size_anim: Optional[QtCore.QVariantAnimation] = None
            self._color_anim: Optional[QtCore.QVariantAnimation] = None
            self._opacity_anim_group: Optional[QtCore.QSequentialAnimationGroup] = None
            self._flash_timer = QtCore.QTimer(self)
            self._flash_timer.setSingleShot(True)
            self._flash_timer.timeout.connect(self._transition_to_base_state)

            self._audio_timer = QtCore.QTimer(self)
            self._audio_timer.timeout.connect(self._on_audio_tick)
            self._audio_timer.start(int(1000 / max(10, _AUDIO_FPS)))

            self.resize(self._base_size)
            self._position_docked()
            self.setWindowOpacity(IDLE_OPACITY)
            self.show()
            self.raise_()

        # ------------------------------------------------------------------
        # External integration API
        # ------------------------------------------------------------------
        def set_hotkey_hint(self, hotkey_value: str) -> None:
            # Non-verbal UI intentionally ignores textual hotkey labels.
            _ = hotkey_value

        def set_audio_level(self, rms: float) -> None:
            if self._state != PillState.RECORDING:
                return
            level = max(0.0, float(rms))
            self._audio_ema = (1.0 - SMOOTHING_FACTOR) * self._audio_ema + SMOOTHING_FACTOR * level
            self._audio_level_target = max(0.0, min(1.0, self._audio_ema * SENSITIVITY))

        def set_status(self, state, text=None, bg=None, fg=None, border=None):
            _ = (text, bg, fg, border)
            target = self._coerce_state(state)
            self._set_state(target)

        def show(self):
            super().show()

        def hide(self):
            super().hide()

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

        def _set_state(self, target: PillState) -> None:
            if self._state == target and target not in (PillState.SUCCESS, PillState.ERROR):
                return

            self._state = target
            self._stop_processing_breathing()
            self._flash_timer.stop()
            self._processing_timer.stop()

            if target in (PillState.IDLE, PillState.ARMED):
                self._audio_ema = 0.0
                self._audio_level_target = 0.0
                self._audio_level_display = 0.0
                self._glow = 0.0
                self._animate_size(*IDLE_DIMENSIONS, duration_ms=ANIMATION_SPEED_MS)
                self._animate_opacity(IDLE_OPACITY)
                if target == PillState.ARMED:
                    self._animate_color(QtGui.QColor("#8FB2C7"))
                else:
                    self._animate_color(QtGui.QColor("#7D93A8"))
                return

            if target == PillState.RECORDING:
                self._audio_ema = 0.0
                self._audio_level_target = 0.0
                self._audio_level_display = 0.0
                self._animate_size(*ACTIVE_DIMENSIONS, duration_ms=ANIMATION_SPEED_MS)
                self._animate_opacity(1.0)
                self._animate_color(QtGui.QColor(self._base_accent))
                return

            if target == PillState.PROCESSING:
                self._glow = 0.2
                self._animate_size(*ACTIVE_DIMENSIONS, duration_ms=ANIMATION_SPEED_MS)
                self._animate_color(QtGui.QColor(self._base_hover))
                self._start_processing_breathing()
                self._processing_timer.start(_PROCESSING_TIMEOUT_MS)
                return

            if target == PillState.SUCCESS:
                self._glow = 1.0
                self._animate_color(QtGui.QColor("#86FFCC"), duration_ms=90)
                self._animate_opacity(1.0, duration_ms=90)
                self._flash_timer.start(200)
                return

            if target == PillState.ERROR:
                self._glow = 1.0
                self._animate_color(QtGui.QColor("#FF5A66"), duration_ms=90)
                self._animate_opacity(1.0, duration_ms=90)
                self._flash_timer.start(240)
                return

        def _transition_to_base_state(self):
            base = PillState.ARMED if self._is_armed_fn() else PillState.IDLE
            self._set_state(base)

        def _on_audio_tick(self):
            if self._state != PillState.RECORDING:
                self._audio_level_display *= 0.85
                self._glow *= 0.9
                self._wave_levels = [max(0.08, w * 0.86) for w in self._wave_levels]
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
                self._size_anim.stop()

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
                self._color_anim.stop()
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
            if self._opacity_anim_group is not None:
                self._opacity_anim_group.stop()
                self._opacity_anim_group = None

            current = float(self.windowOpacity())
            anim = QtCore.QVariantAnimation(self)
            anim.setDuration(max(60, int(duration_ms)))
            anim.setStartValue(current)
            anim.setEndValue(max(0.05, min(1.0, float(target))))
            anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
            anim.valueChanged.connect(lambda value: self.setWindowOpacity(float(value)))
            anim.finished.connect(anim.deleteLater)
            anim.start()

        def _start_processing_breathing(self):
            down = QtCore.QVariantAnimation(self)
            down.setDuration(420)
            down.setStartValue(1.0)
            down.setEndValue(0.6)
            down.setEasingCurve(QtCore.QEasingCurve.Type.InOutSine)
            down.valueChanged.connect(lambda value: self.setWindowOpacity(float(value)))

            up = QtCore.QVariantAnimation(self)
            up.setDuration(420)
            up.setStartValue(0.6)
            up.setEndValue(1.0)
            up.setEasingCurve(QtCore.QEasingCurve.Type.InOutSine)
            up.valueChanged.connect(lambda value: self.setWindowOpacity(float(value)))

            group = QtCore.QSequentialAnimationGroup(self)
            group.addAnimation(down)
            group.addAnimation(up)
            group.setLoopCount(-1)
            self._opacity_anim_group = group
            group.start()

        def _stop_processing_breathing(self):
            if self._opacity_anim_group is not None:
                self._opacity_anim_group.stop()
                self._opacity_anim_group.deleteLater()
                self._opacity_anim_group = None

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
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)

            bounds = self.rect().adjusted(1, 1, -1, -1)
            radius = max(4.0, bounds.height() / 2.0)

            if self._glow > 0.01:
                glow_rect = bounds.adjusted(
                    -int(_GLOW_BASE + self._glow * _GLOW_DELTA),
                    -int(_GLOW_BASE + self._glow * (_GLOW_DELTA * 0.55)),
                    int(_GLOW_BASE + self._glow * _GLOW_DELTA),
                    int(_GLOW_BASE + self._glow * (_GLOW_DELTA * 0.55)),
                )
                glow_color = QtGui.QColor(self._pill_color)
                glow_color.setAlpha(int(28 + (self._glow * 65)))
                painter.setBrush(glow_color)
                painter.drawRoundedRect(glow_rect, glow_rect.height() / 2.0, glow_rect.height() / 2.0)

            base = QtGui.QColor("#0D1220")
            base.setAlpha(235)
            painter.setBrush(base)
            painter.drawRoundedRect(bounds, radius, radius)

            border = QtGui.QColor(self._pill_color)
            border.setAlpha(140)
            pen = QtGui.QPen(border)
            pen.setWidthF(1.0)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(bounds, radius, radius)

            # Recording: tiny waveform bars.
            if self._state == PillState.RECORDING:
                center_y = bounds.center().y()
                bars = _WAVE_BARS
                spacing = max(2.2, bounds.width() / (bars + 3))
                start_x = bounds.center().x() - ((bars - 1) * spacing) / 2.0
                bar_color = QtGui.QColor("#DDF8FF")
                bar_pen = QtGui.QPen(bar_color)
                bar_pen.setWidthF(2.0)
                bar_pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
                painter.setPen(bar_pen)
                max_h = max(3.0, bounds.height() * 0.62)
                for i in range(bars):
                    level = self._wave_levels[i] if i < len(self._wave_levels) else 0.15
                    h = max(2.0, max_h * level)
                    x = start_x + i * spacing
                    painter.drawLine(QtCore.QPointF(x, center_y - h / 2.0), QtCore.QPointF(x, center_y + h / 2.0))

            # Processing: dotted line pulse.
            elif self._state == PillState.PROCESSING:
                dots = 12
                spacing = max(2.0, bounds.width() / (dots + 3))
                start_x = bounds.center().x() - ((dots - 1) * spacing) / 2.0
                pulse = 0.4 + 0.6 * abs(self.windowOpacity() - 0.8)
                dot_color = QtGui.QColor("#CFE8FF")
                dot_color.setAlpha(int(130 + (pulse * 110)))
                painter.setBrush(dot_color)
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                r = 1.4
                y = bounds.center().y()
                for i in range(dots):
                    painter.drawEllipse(QtCore.QPointF(start_x + i * spacing, y), r, r)

            # Idle/armed: subtle center dot.
            else:
                dot = QtGui.QColor(self._pill_color)
                dot.setAlpha(170)
                painter.setBrush(dot)
                painter.drawEllipse(QtCore.QPointF(bounds.center().x(), bounds.center().y()), 1.8, 1.8)

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
            self._stop_processing_breathing()
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
