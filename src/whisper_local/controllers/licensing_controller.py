"""Licensing controller for the dashboard UI."""

from typing import Dict, Any
from whisper_local.licensing import LicensingManager

class LicensingController:
    """Provides JavaScript API for license management."""

    def __init__(self, manager: LicensingManager):
        self._manager = manager

    def get_status(self) -> Dict[str, Any]:
        """Return the current licensing status."""
        state = self._manager.load_license_state()
        is_valid = self._manager.is_licensed(offline_fallback=True)
        key = state.get("key")
        
        # Mask key for privacy in UI
        masked_key = f"****-****-****-{key[-4:]}" if key and len(key) >= 4 else None

        return {
            "active": state.get("active", False),
            "is_valid": is_valid,
            "key": masked_key,
            "last_check": state.get("last_check")
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
