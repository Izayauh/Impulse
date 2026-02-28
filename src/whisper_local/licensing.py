"""
Licensing system for WhisperLocal.

Provides activation, cached offline validation, and beta gating controls.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import uuid
from typing import Any, Dict, Optional, Tuple
import urllib.error
import urllib.request

from .config import get_user_data_dir

# Configuration for the licensing API
LICENSING_API_URL = os.environ.get(
    "WHISPER_LICENSE_API_URL",
    "https://api.lemonsqueezy.com/v1/licenses/validate",
)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat()


def _parse_dt(value: Any) -> Optional[_dt.datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=_dt.timezone.utc)
        return parsed.astimezone(_dt.timezone.utc)
    except Exception:
        return None


def _parse_date(value: Optional[str]) -> Optional[_dt.date]:
    if not value:
        return None
    try:
        return _dt.date.fromisoformat(value.strip())
    except Exception:
        return None


class LicensingManager:
    """Manages software licensing, activation, and offline validation."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or get_user_data_dir()
        self.license_file = os.path.join(self.data_dir, "state", "license.json")
        os.makedirs(os.path.dirname(self.license_file), exist_ok=True)
        self._machine_id = self._get_machine_id()

        # Runtime policy knobs (env-configurable for beta operations)
        self._license_required = _env_bool("WHISPER_REQUIRE_LICENSE", True)
        self._dev_bypass = _env_bool("WHISPER_DEV_BYPASS_LICENSE", False)
        self._force_disable = _env_bool("WHISPER_FORCE_DISABLE", False)
        self._offline_grace_days = _env_int("WHISPER_LICENSE_OFFLINE_GRACE_DAYS", 3)
        self._revalidate_interval_hours = _env_int("WHISPER_LICENSE_REVALIDATE_HOURS", 24)
        self._beta_expires_on = _parse_date(os.environ.get("WHISPER_BETA_EXPIRES_ON"))

    def _default_state(self) -> Dict[str, Any]:
        return {
            "active": False,
            "key": None,
            "last_check": None,
            "last_online_check": None,
            "revoked": False,
            "meta": {},
            "last_error": None,
        }

    def _get_machine_id(self) -> str:
        """Get a stable, anonymous identifier for this device."""
        machine_file = os.path.join(self.data_dir, "state", "machine_id.txt")
        if os.path.exists(machine_file):
            try:
                with open(machine_file, "r", encoding="utf-8") as f:
                    existing = f.read().strip()
                if existing:
                    return existing
            except Exception:
                pass

        new_id = str(uuid.uuid4())
        try:
            with open(machine_file, "w", encoding="utf-8") as f:
                f.write(new_id)
        except Exception:
            pass
        return new_id

    def load_license_state(self) -> Dict[str, Any]:
        """Load the cached license state from disk."""
        state = self._default_state()
        if not os.path.exists(self.license_file):
            return state

        try:
            with open(self.license_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                state.update(raw)
            return state
        except Exception:
            return state

    def _save_license_state(self, state: Dict[str, Any]) -> None:
        """Save the license state to disk."""
        try:
            with open(self.license_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Failed to save license state: {e}")

    def _extract_meta(self, result: Dict[str, Any]) -> Dict[str, Any]:
        meta = result.get("meta")
        if isinstance(meta, dict):
            return meta

        data = result.get("data")
        if isinstance(data, dict):
            attrs = data.get("attributes")
            if isinstance(attrs, dict):
                return attrs

        return {}

    def _extract_expiry_from_meta(self, meta: Dict[str, Any]) -> Optional[_dt.datetime]:
        candidates = (
            meta.get("expires_at"),
            meta.get("renews_at"),
            meta.get("expiry"),
            meta.get("expiration"),
        )
        for candidate in candidates:
            parsed = _parse_dt(candidate)
            if parsed is not None:
                return parsed
        return None

    def _is_build_expired(self, now: Optional[_dt.datetime] = None) -> bool:
        if self._beta_expires_on is None:
            return False
        check_now = now or _utc_now()
        return check_now.date() > self._beta_expires_on

    def _online_validate(self, license_key: str) -> Tuple[Optional[bool], str, Dict[str, Any]]:
        """Validate license online.

        Returns:
            (True|False|None, message, payload)
            - None means network/transport failure (unknown validity)
        """
        payload = json.dumps(
            {
                "license_key": license_key,
                "instance_name": f"WhisperLocal App - {self._machine_id}",
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            LICENSING_API_URL,
            data=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                valid = bool(result.get("valid"))
                if valid:
                    return True, "License valid", result
                return False, str(result.get("error", "Invalid or inactive license key.")), result

        except urllib.error.HTTPError as e:
            try:
                err_data = json.loads(e.read().decode("utf-8"))
                return False, str(err_data.get("error", "API validation error.")), err_data
            except Exception:
                return False, f"HTTP Error: {e.code}", {}
        except urllib.error.URLError:
            return None, "Network error. Please check internet connectivity.", {}
        except Exception as e:
            return None, f"Unexpected validation error: {str(e)}", {}

    def activate_license(self, license_key: str) -> Tuple[bool, str]:
        """Attempt to activate a license key online."""
        if not license_key or not license_key.strip():
            return False, "License key is required."

        license_key = license_key.strip()
        valid, message, payload = self._online_validate(license_key)

        if valid is True:
            state = self.load_license_state()
            state.update(
                {
                    "active": True,
                    "key": license_key,
                    "revoked": False,
                    "last_check": _iso_now(),
                    "last_online_check": _iso_now(),
                    "last_error": None,
                    "meta": self._extract_meta(payload),
                }
            )
            self._save_license_state(state)
            return True, "License activated successfully!"

        if valid is False:
            state = self.load_license_state()
            state.update(
                {
                    "active": False,
                    "revoked": True,
                    "last_check": _iso_now(),
                    "last_online_check": _iso_now(),
                    "last_error": message,
                    "meta": self._extract_meta(payload),
                }
            )
            self._save_license_state(state)
            return False, message

        # Network/unknown error: preserve existing state
        return False, message

    def deactivate_license(self) -> Tuple[bool, str]:
        """Remove the active license."""
        self._save_license_state(self._default_state())
        return True, "License deactivated."

    def get_license_status(
        self,
        offline_fallback: bool = True,
        allow_online_check: bool = True,
    ) -> Dict[str, Any]:
        """Return a rich status object for enforcement and UI."""
        now = _utc_now()

        if self._dev_bypass:
            return {
                "active": True,
                "is_valid": True,
                "reason": "dev_bypass",
                "message": "License bypass enabled via WHISPER_DEV_BYPASS_LICENSE.",
                "key": None,
                "last_check": None,
                "expires_at": None,
            }

        if self._force_disable:
            return {
                "active": False,
                "is_valid": False,
                "reason": "force_disabled",
                "message": "Application access has been disabled by operator.",
                "key": None,
                "last_check": None,
                "expires_at": None,
            }

        if self._is_build_expired(now):
            return {
                "active": False,
                "is_valid": False,
                "reason": "beta_expired",
                "message": "This beta build has expired.",
                "key": None,
                "last_check": None,
                "expires_at": self._beta_expires_on.isoformat() if self._beta_expires_on else None,
            }

        if not self._license_required:
            return {
                "active": True,
                "is_valid": True,
                "reason": "license_not_required",
                "message": "License enforcement disabled.",
                "key": None,
                "last_check": None,
                "expires_at": None,
            }

        state = self.load_license_state()
        active = bool(state.get("active"))
        key = state.get("key")
        last_check = _parse_dt(state.get("last_check"))
        last_online_check = _parse_dt(state.get("last_online_check"))
        revoked = bool(state.get("revoked"))
        meta = state.get("meta") if isinstance(state.get("meta"), dict) else {}
        expires_at = self._extract_expiry_from_meta(meta)

        if not active or not key:
            return {
                "active": False,
                "is_valid": False,
                "reason": "not_activated",
                "message": "No active license.",
                "key": None,
                "last_check": state.get("last_check"),
                "expires_at": expires_at.isoformat() if expires_at else None,
            }

        if revoked:
            return {
                "active": active,
                "is_valid": False,
                "reason": "revoked",
                "message": state.get("last_error") or "License has been revoked.",
                "key": key,
                "last_check": state.get("last_check"),
                "expires_at": expires_at.isoformat() if expires_at else None,
            }

        if expires_at and now > expires_at:
            return {
                "active": active,
                "is_valid": False,
                "reason": "license_expired",
                "message": "License has expired.",
                "key": key,
                "last_check": state.get("last_check"),
                "expires_at": expires_at.isoformat(),
            }

        # Decide if we should do online revalidation now.
        should_revalidate = False
        if allow_online_check:
            if last_online_check is None:
                should_revalidate = True
            else:
                age_hours = (now - last_online_check).total_seconds() / 3600.0
                should_revalidate = age_hours >= max(1, self._revalidate_interval_hours)

        if should_revalidate:
            valid, message, payload = self._online_validate(str(key))
            if valid is True:
                state.update(
                    {
                        "active": True,
                        "revoked": False,
                        "last_check": _iso_now(),
                        "last_online_check": _iso_now(),
                        "last_error": None,
                        "meta": self._extract_meta(payload),
                    }
                )
                self._save_license_state(state)
                refreshed_expiry = self._extract_expiry_from_meta(state.get("meta", {}))
                return {
                    "active": True,
                    "is_valid": True,
                    "reason": "validated_online",
                    "message": "License valid.",
                    "key": key,
                    "last_check": state.get("last_check"),
                    "expires_at": refreshed_expiry.isoformat() if refreshed_expiry else None,
                }

            if valid is False:
                state.update(
                    {
                        "active": False,
                        "revoked": True,
                        "last_check": _iso_now(),
                        "last_online_check": _iso_now(),
                        "last_error": message,
                        "meta": self._extract_meta(payload),
                    }
                )
                self._save_license_state(state)
                return {
                    "active": False,
                    "is_valid": False,
                    "reason": "revoked",
                    "message": message,
                    "key": key,
                    "last_check": state.get("last_check"),
                    "expires_at": None,
                }

            # Network issue: fall through to offline cache handling.
            state["last_error"] = message
            self._save_license_state(state)

        # Offline fallback policy using last successful check timestamp.
        if last_check is None:
            return {
                "active": active,
                "is_valid": False,
                "reason": "never_validated",
                "message": "License has never been validated on this device.",
                "key": key,
                "last_check": state.get("last_check"),
                "expires_at": expires_at.isoformat() if expires_at else None,
            }

        days_since_check = (now - last_check).total_seconds() / 86400.0
        in_grace = days_since_check <= max(0, self._offline_grace_days)

        if offline_fallback and in_grace:
            return {
                "active": active,
                "is_valid": True,
                "reason": "offline_grace",
                "message": "Using cached license within offline grace period.",
                "key": key,
                "last_check": state.get("last_check"),
                "expires_at": expires_at.isoformat() if expires_at else None,
            }

        return {
            "active": active,
            "is_valid": False,
            "reason": "offline_grace_expired",
            "message": "License revalidation required (offline grace expired).",
            "key": key,
            "last_check": state.get("last_check"),
            "expires_at": expires_at.isoformat() if expires_at else None,
        }

    def is_licensed(self, offline_fallback: bool = True, allow_online_check: bool = True) -> bool:
        """Compatibility wrapper returning only validity."""
        status = self.get_license_status(
            offline_fallback=offline_fallback,
            allow_online_check=allow_online_check,
        )
        return bool(status.get("is_valid"))
