"""
Licensing system for WhisperLocal.

Handles validation of commercial license keys (e.g. via LemonSqueezy)
and local cached state with an offline grace period.
"""

import os
import json
import uuid
import datetime
from typing import Dict, Any, Tuple, Optional
import urllib.request
import urllib.parse
import urllib.error

from .config import get_user_data_dir

# Configuration for the licensing API
# Switch to actual production endpoint for LemonSqueezy or Keygen
LICENSING_API_URL = os.environ.get("WHISPER_LICENSE_API_URL", "https://api.lemonsqueezy.com/v1/licenses/validate")
OFFLINE_GRACE_PERIOD_DAYS = 7


class LicensingManager:
    """Manages software licensing, activation, and offline validation."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or get_user_data_dir()
        self.license_file = os.path.join(self.data_dir, "state", "license.json")
        os.makedirs(os.path.dirname(self.license_file), exist_ok=True)
        self._machine_id = self._get_machine_id()

    def _get_machine_id(self) -> str:
        """Get a stable, anonymous identifier for this device."""
        # A simple fallback for machine ID. 
        # In a real app, you might use hardware UUID via WMI or similar.
        machine_file = os.path.join(self.data_dir, "state", "machine_id.txt")
        if os.path.exists(machine_file):
            with open(machine_file, "r") as f:
                return f.read().strip()
        
        new_id = str(uuid.uuid4())
        with open(machine_file, "w") as f:
            f.write(new_id)
        return new_id

    def load_license_state(self) -> Dict[str, Any]:
        """Load the cached license state from disk."""
        if not os.path.exists(self.license_file):
            return {"active": False, "key": None, "last_check": None}
        
        try:
            with open(self.license_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"active": False, "key": None, "last_check": None}

    def _save_license_state(self, state: Dict[str, Any]) -> None:
        """Save the license state to disk."""
        try:
            with open(self.license_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Failed to save license state: {e}")

    def activate_license(self, license_key: str) -> Tuple[bool, str]:
        """
        Attempt to activate a license key online.
        Logs the machine ID with the provider.
        """
        if not license_key or not license_key.strip():
            return False, "License key is required."

        license_key = license_key.strip()
        
        # Example using LemonSqueezy's validation endpoint:
        # POST to https://api.lemonsqueezy.com/v1/licenses/validate
        payload = json.dumps({
            "license_key": license_key,
            "instance_name": f"WhisperLocal App - {self._machine_id}"
        }).encode("utf-8")

        req = urllib.request.Request(LICENSING_API_URL, data=payload, headers={
            "Accept": "application/json",
            "Content-Type": "application/json"
        }, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
                
                # Verify LemonSqueezy validation response
                if result.get("valid"):
                    state = {
                        "active": True,
                        "key": license_key,
                        "last_check": datetime.datetime.now().isoformat(),
                        "meta": result.get("meta", {})
                    }
                    self._save_license_state(state)
                    return True, "License activated successfully!"
                else:
                    error_msg = result.get("error", "Invalid or inactive license key.")
                    return False, error_msg
        
        except urllib.error.HTTPError as e:
            # Handle HTTP errors (4xx, 5xx)
            try:
                err_data = json.loads(e.read().decode("utf-8"))
                error_msg = err_data.get("error", "API validation error.")
            except Exception:
                error_msg = f"HTTP Error: {e.code}"
            return False, error_msg
            
        except urllib.error.URLError:
            return False, "Network error. Please ensure you are connected to the internet to activate."
        except Exception as e:
            return False, f"Unexpected error during activation: {str(e)}"

    def deactivate_license(self) -> Tuple[bool, str]:
        """Remove the active license."""
        state = self.load_license_state()
        if not state.get("active"):
            return True, "No active license to deactivate."
        
        # In a complete implementation, this would make an API call to free up the machine activation lock.
        # For now, just clear local state.
        self._save_license_state({"active": False, "key": None, "last_check": None})
        return True, "License deactivated."

    def is_licensed(self, offline_fallback: bool = True) -> bool:
        """
        Check if the application is currently licensed.
        Uses offline cache if online check fails or offline_fallback is True.
        """
        state = self.load_license_state()
        if not state.get("active") or not state.get("key"):
            return False

        last_check_str = state.get("last_check")
        if not last_check_str:
            return False

        try:
            last_check = datetime.datetime.fromisoformat(last_check_str)
            days_since_check = (datetime.datetime.now() - last_check).days
            
            # If within grace period, return True immediately
            if offline_fallback and days_since_check < OFFLINE_GRACE_PERIOD_DAYS:
                return True
                
            # If past grace period, attempt silent re-validation
            # (In a real background task, you might do this asynchronously)
            if days_since_check >= OFFLINE_GRACE_PERIOD_DAYS:
                valid, _ = self.activate_license(state["key"])
                if valid:
                    return True
                # Decide policy: do we revoke access immediately on failed network check?
                # A friendlier approach is to allow if network is down, but revoke if API specifically says "invalid".
                # For simplicity here, we enforce strict online check if beyond grace period.
                return False
                
        except Exception:
            # Date parse error or similar
            return False
            
        return True
