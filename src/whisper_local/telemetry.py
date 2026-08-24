"""
Telemetry system for WhisperLocal beta.

Collects crash reports, errors, and performance metrics and submits them
to a GitHub Issues endpoint so the dev team can improve the software
without requiring manual log sharing from beta testers.

Privacy guarantees:
  - No audio data is ever transmitted.
  - Transcribed text is stripped from payloads.
  - A random install-ID (not tied to identity) is used for deduplication.
  - Users can opt out at any time via the settings toggle.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from queue import Queue, Empty
from typing import Any, Dict, List, Optional
from urllib import request, error

from whisper_local.config import get_user_data_dir

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Install ID – random UUID persisted locally, NOT tied to user identity
# ---------------------------------------------------------------------------

def get_install_id() -> str:
    """Return a stable, anonymous install ID (creates one on first call)."""
    id_file = os.path.join(get_user_data_dir(), "state", "install_id.txt")

    if os.path.exists(id_file):
        try:
            with open(id_file, "r", encoding="utf-8") as f:
                existing = f.read().strip()
            if existing:
                return existing
        except (IOError, OSError):
            pass

    install_id = str(uuid.uuid4())
    try:
        os.makedirs(os.path.dirname(id_file), exist_ok=True)
        with open(id_file, "w", encoding="utf-8") as f:
            f.write(install_id)
    except (IOError, OSError) as exc:
        logger.warning("Could not persist install ID: %s", exc)

    return install_id


# ---------------------------------------------------------------------------
# Payload sanitizer – strip sensitive data before transmission
# ---------------------------------------------------------------------------

# Matches Windows-style user profile paths  (C:\Users\SomeUser\...)
_USER_PATH_RE = re.compile(
    # Match both normal paths (C:\\Users\\Name) and JSON-escaped paths
    # (C:\\\\Users\\\\Name) because sanitization runs on json.dumps output.
    r"[A-Za-z]:(?:\\)+Users(?:\\)+[^\\\"]+",
    re.IGNORECASE,
)


def sanitize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-copy *payload* and redact sensitive information.

    * File paths containing usernames are replaced with ``<USER_DIR>``.
    * Any key named ``transcribed_text`` or ``transcript`` is replaced
      with ``<redacted>``.
    """
    raw = json.dumps(payload)

    # Redact user paths
    raw = _USER_PATH_RE.sub("<USER_DIR>", raw)

    sanitized: Dict[str, Any] = json.loads(raw)

    # Walk and strip transcript keys
    _strip_keys(sanitized, {"transcribed_text", "transcript", "text"})

    return sanitized


def _strip_keys(obj: Any, keys: set) -> None:
    """Recursively redact *keys* inside nested dicts/lists."""
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            if k in keys:
                obj[k] = "<redacted>"
            else:
                _strip_keys(obj[k], keys)
    elif isinstance(obj, list):
        for item in obj:
            _strip_keys(item, keys)


# ---------------------------------------------------------------------------
# Telemetry Collector – in-process event queue
# ---------------------------------------------------------------------------

class TelemetryCollector:
    """Thread-safe queue of telemetry events."""

    def __init__(self, max_queue_size: int = 500):
        self._queue: Queue[Dict[str, Any]] = Queue(maxsize=max_queue_size)

    def record_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        *,
        severity: str = "info",
    ) -> None:
        """Enqueue a telemetry event.

        Args:
            event_type: e.g. ``crash``, ``error``, ``perf``
            data: Arbitrary event payload
            severity: ``info`` | ``warning`` | ``error`` | ``critical``
        """
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": severity,
            **data,
        }
        try:
            self._queue.put_nowait(event)
        except Exception:
            # Queue full – silently drop oldest-ish event
            pass

    def drain(self) -> List[Dict[str, Any]]:
        """Return and remove all queued events."""
        events: List[Dict[str, Any]] = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except Empty:
                break
        return events

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()


# ---------------------------------------------------------------------------
# Telemetry Submitter – background thread that batches & POSTs events
# ---------------------------------------------------------------------------

class TelemetrySubmitter:
    """Posts batched telemetry to a GitHub Issues endpoint."""

    def __init__(
        self,
        collector: TelemetryCollector,
        github_token: Optional[str] = None,
        interval_sec: Optional[int] = None,
    ):
        from whisper_local.config import (
            APP_VERSION,
            TELEMETRY_SUBMIT_INTERVAL_SEC,
            TELEMETRY_GITHUB_OWNER,
            TELEMETRY_GITHUB_REPO,
            TELEMETRY_VERSION,
        )

        self._collector = collector
        self._interval = interval_sec or TELEMETRY_SUBMIT_INTERVAL_SEC
        self._app_version = APP_VERSION
        self._telemetry_version = TELEMETRY_VERSION
        self._github_owner = TELEMETRY_GITHUB_OWNER
        self._github_repo = TELEMETRY_GITHUB_REPO
        self._github_token = github_token or os.environ.get("WHISPER_TELEMETRY_TOKEN", "")
        self._install_id = get_install_id()

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # -- lifecycle -----------------------------------------------------------

    def start(self) -> None:
        """Start the background submission thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="telemetry-submitter"
        )
        self._thread.start()
        logger.info("Telemetry submitter started (interval=%ds)", self._interval)

    def stop(self, flush: bool = True) -> None:
        """Signal the background thread to stop.

        Args:
            flush: If True, submit remaining events before stopping.
        """
        self._stop_event.set()
        if flush:
            self.flush()
        if self._thread:
            self._thread.join(timeout=5)

    def flush(self) -> None:
        """Immediately submit any queued events."""
        events = self._collector.drain()
        if events:
            self._submit_batch(events)

    # -- internal ------------------------------------------------------------

    def _run_loop(self) -> None:
        """Background loop: sleep → drain → submit → repeat."""
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=self._interval)
            if self._stop_event.is_set():
                break
            events = self._collector.drain()
            if events:
                self._submit_batch(events)

    def _submit_batch(self, events: List[Dict[str, Any]]) -> bool:
        """Build a payload and POST it as a GitHub issue."""
        import platform

        payload = {
            "telemetry_version": self._telemetry_version,
            "install_id": self._install_id,
            "app_version": self._app_version,
            "os": f"{platform.system()} {platform.release()}",
            "events": events,
        }
        payload = sanitize_payload(payload)

        # Build GitHub Issues API body
        title = self._build_issue_title(events)
        body = (
            f"**Telemetry Report** — `{self._install_id[:8]}…`\n\n"
            f"- App version: `{self._app_version}`\n"
            f"- OS: `{payload['os']}`\n"
            f"- Events: {len(events)}\n\n"
            f"```json\n{json.dumps(payload, indent=2)}\n```"
        )
        issue_data = {
            "title": title,
            "body": body,
            "labels": ["telemetry", "beta"],
        }

        url = (
            f"https://api.github.com/repos/"
            f"{self._github_owner}/{self._github_repo}/issues"
        )

        try:
            req = request.Request(
                url,
                data=json.dumps(issue_data).encode("utf-8"),
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {self._github_token}",
                    "Content-Type": "application/json",
                    "User-Agent": f"Impulse/{self._app_version}",
                },
                method="POST",
            )
            with request.urlopen(req, timeout=15) as resp:
                if resp.status in (200, 201):
                    logger.info(
                        "Telemetry submitted (%d events, status=%d)",
                        len(events),
                        resp.status,
                    )
                    return True
                else:
                    logger.warning("Telemetry submit status %d", resp.status)
        except error.HTTPError as exc:
            logger.warning("Telemetry HTTP error %s: %s", exc.code, exc.reason)
        except Exception as exc:
            logger.warning("Telemetry submit failed: %s", exc)

        return False

    @staticmethod
    def _build_issue_title(events: List[Dict[str, Any]]) -> str:
        """Create a concise issue title from the batch of events."""
        crash_events = [e for e in events if e.get("type") == "crash"]
        error_events = [e for e in events if e.get("type") == "error"]

        parts = []
        if crash_events:
            first = crash_events[0]
            exc_type = first.get("exception_type", "Unknown")
            parts.append(f"Crash: {exc_type}")
        if error_events:
            parts.append(f"{len(error_events)} error(s)")
        if not parts:
            parts.append(f"{len(events)} telemetry event(s)")

        return f"[Telemetry] {' + '.join(parts)}"


# ---------------------------------------------------------------------------
# Module-level singleton & init
# ---------------------------------------------------------------------------

_collector: Optional[TelemetryCollector] = None
_submitter: Optional[TelemetrySubmitter] = None
_initialized = False


def init_telemetry(*, force: bool = False) -> bool:
    """Initialise telemetry if the user has opted in.

    Safe to call multiple times – subsequent calls are no-ops unless
    *force* is True.

    Returns:
        True if telemetry is active, False if disabled or failed.
    """
    global _collector, _submitter, _initialized

    if _initialized and not force:
        return _submitter is not None

    _initialized = True

    # Check user preference
    try:
        from whisper_local.settings_manager import SettingsManager
        settings = SettingsManager()
        if not settings.get_setting("telemetry_enabled"):
            logger.info("Telemetry disabled by user preference")
            return False
    except Exception as exc:
        logger.warning("Could not read telemetry setting: %s", exc)
        return False

    # Check for GitHub token — env var takes priority, then baked build constant
    token = os.environ.get("WHISPER_TELEMETRY_TOKEN", "")
    if not token:
        try:
            from whisper_local._build_config import TELEMETRY_TOKEN as _baked
            token = _baked or ""
        except ImportError:
            pass
    if not token:
        logger.info("Telemetry inactive — no WHISPER_TELEMETRY_TOKEN set")
        return False

    _collector = TelemetryCollector()
    _submitter = TelemetrySubmitter(_collector, github_token=token)
    _submitter.start()
    logger.info("Telemetry initialized (install_id=%s)", get_install_id()[:8])
    return True


def get_collector() -> Optional[TelemetryCollector]:
    """Return the global collector (or None if telemetry is disabled)."""
    return _collector


def get_submitter() -> Optional[TelemetrySubmitter]:
    """Return the global submitter (or None if telemetry is disabled)."""
    return _submitter


def record_crash(
    exception: Exception,
    *,
    crash_id: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Convenience: record a crash event if telemetry is active."""
    if _collector is None:
        return
    _collector.record_event(
        "crash",
        {
            "crash_id": crash_id,
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "traceback": traceback.format_exc(),
            "context": context or {},
        },
        severity="critical",
    )


def record_error(
    error_type: str,
    message: str,
    *,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Convenience: record a non-fatal error event."""
    if _collector is None:
        return
    _collector.record_event(
        "error",
        {
            "error_type": error_type,
            "message": message,
            "details": details or {},
        },
        severity="error",
    )


def shutdown_telemetry() -> None:
    """Flush remaining events and stop the submitter thread."""
    global _submitter
    if _submitter is not None:
        logger.info("Shutting down telemetry — flushing remaining events")
        _submitter.stop(flush=True)
        _submitter = None
