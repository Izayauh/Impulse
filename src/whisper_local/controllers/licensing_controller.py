"""Licensing controller for the dashboard UI."""

from typing import Dict, Any
from whisper_local.licensing import LicensingManager

class LicensingController:
    """Provides JavaScript API for license management."""

    def __init__(self, manager: LicensingManager):
        self._manager = manager

    def get_status(self) -> Dict[str, Any]:
        """Return the current licensing status."""
        status = self._manager.get_license_status(
            offline_fallback=True,
            allow_online_check=True,
        )
        key = status.get("key")

        # Mask key for privacy in UI
        masked_key = f"****-****-****-{str(key)[-4:]}" if key and len(str(key)) >= 4 else None

        return {
            "active": bool(status.get("active", False)),
            "is_valid": bool(status.get("is_valid", False)),
            "key": masked_key,
            "last_check": status.get("last_check"),
            "reason": status.get("reason"),
            "message": status.get("message"),
            "expires_at": status.get("expires_at"),
        }

    def activate(self, license_key: str) -> Dict[str, Any]:
        """Attempt to activate the software with a key."""
        success, message = self._manager.activate_license(license_key)
        return {
            "success": success,
            "message": message,
            "status": self.get_status()
        }

    def deactivate(self) -> Dict[str, Any]:
        """Deactivate the current license."""
        success, message = self._manager.deactivate_license()
        return {
            "success": success,
            "message": message,
            "status": self.get_status()
        }
