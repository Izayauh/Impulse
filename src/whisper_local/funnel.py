"""Anonymous setup-funnel events for the beta.

Answers the one question crash telemetry cannot: where do fresh installs
silently stall (launch -> activation -> first dictation)? Each event
carries the random install ID telemetry already uses, the app version,
and the OS build - never audio, transcripts, file paths, or identity.

Consent: gated on the same ``telemetry_enabled`` opt-in the first-run
wizard asks for; nothing is ever sent while it is off.

Delivery is fire-and-forget on a daemon thread with a short timeout, so
a dead network or endpoint can never slow the app down. Once-only events
are marked locally before the send, so a lost packet is dropped rather
than retried - funnel data is best-effort by design.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib import request

from whisper_local.config import APP_VERSION, get_user_data_dir
from whisper_local.telemetry import get_install_id

logger = logging.getLogger(__name__)

FUNNEL_API_URL = os.environ.get(
    "WHISPER_FUNNEL_API_URL",
    # Same origin released clients already use for license validation.
    "https://impulse-eight-lake.vercel.app/api/events",
)

VALID_EVENTS = {"first_launch", "license_blocked", "activated", "first_dictation"}
# license_blocked repeats per launch on purpose: repeated stalls are the signal.
ONCE_EVENTS = {"first_launch", "activated", "first_dictation"}


def _consent_given() -> bool:
    try:
        from whisper_local.settings_manager import SettingsManager

        return bool(SettingsManager().get_setting("telemetry_enabled"))
    except Exception:
        return False


def _marker_file() -> str:
    return os.path.join(get_user_data_dir(), "state", "funnel_sent.json")


def _load_sent() -> Dict[str, str]:
    try:
        with open(_marker_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _mark_sent(event: str) -> None:
    sent = _load_sent()
    sent[event] = datetime.now(timezone.utc).isoformat()
    try:
        path = _marker_file()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sent, f, indent=2)
    except Exception:
        pass


def _post(payload: Dict[str, Any]) -> None:
    try:
        req = request.Request(
            FUNNEL_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        request.urlopen(req, timeout=5).close()
    except Exception as exc:  # a funnel event must never hurt the app
        logger.debug("funnel event not delivered: %s", exc)


def record_funnel_event(event: str, props: Optional[Dict[str, Any]] = None) -> bool:
    """Fire one funnel event in the background. Returns True if queued."""
    if event not in VALID_EVENTS:
        return False
    if not _consent_given():
        return False
    if event in ONCE_EVENTS and event in _load_sent():
        return False

    payload = {
        "install_id": get_install_id(),
        "event": event,
        "ts": datetime.now(timezone.utc).isoformat(),
        "app_version": APP_VERSION,
        "os": platform.platform(),
        "props": dict(props or {}),
    }
    if event in ONCE_EVENTS:
        _mark_sent(event)
    threading.Thread(target=_post, args=(payload,), daemon=True).start()
    return True
