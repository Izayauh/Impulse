"""
Auto-update system for WhisperLocal.

This module handles checking for updates, downloading installers,
and notifying users about new versions - all while preserving privacy.
"""

import os
import sys
import json
import hashlib
import re
import socket
import ssl
from typing import Optional, Dict, Tuple
from pathlib import Path
from urllib.parse import urlparse
from packaging import version as version_lib

from .config import APP_VERSION, APP_NAME


# GitHub API endpoint for releases (no authentication needed for public repos)
GITHUB_API = "https://api.github.com/repos/Izayauh/Impulse/releases/latest"
UPDATE_CHECK_FILE = "last_update_check.json"
UPDATE_CA_BUNDLE_ENV = "WHISPER_UPDATE_CA_BUNDLE"
UPDATE_CERT_PIN_ENV = "WHISPER_UPDATE_CERT_SHA256"


class UpdateChecker:
    """Check for and manage application updates."""
    
    def __init__(self, current_version: str = APP_VERSION, cache_dir: Optional[str] = None):
        """Initialize update checker.
        
        Args:
            current_version: Current application version
            cache_dir: Directory for cache files (default: user data dir)
        """
        self.current_version = current_version
        self.cache_dir = cache_dir or self._get_cache_dir()
        self.update_check_file = os.path.join(self.cache_dir, UPDATE_CHECK_FILE)

    @staticmethod
    def _normalize_hash(value: str) -> Optional[str]:
        """Normalize SHA256 digests from metadata fields like 'sha256:<hex>'."""
        if not value:
            return None
        cleaned = str(value).strip().lower()
        if cleaned.startswith("sha256:"):
            cleaned = cleaned.split(":", 1)[1].strip()
        if re.fullmatch(r"[a-f0-9]{64}", cleaned):
            return cleaned
        return None

    @staticmethod
    def _extract_release_hashes(release_notes: str) -> Dict[str, str]:
        """Extract SHA256 hashes from release notes keyed by installer filename."""
        hashes: Dict[str, str] = {}
        if not release_notes:
            return hashes

        expecting_default_hash = False
        for line in release_notes.splitlines():
            row = line.strip()
            if not row:
                continue

            # sha256sum format: "<hash> *Installer.exe"
            m = re.search(r"(?i)\b([a-f0-9]{64})\b\s+\*?([^\s]+\.exe)\b", row)
            if m:
                hashes[m.group(2).lower()] = m.group(1).lower()
                continue

            # release-note format: "Installer.exe: <hash>"
            m = re.search(r"(?i)\b([^\s]+\.exe)\b[^a-f0-9]*([a-f0-9]{64})\b", row)
            if m:
                hashes[m.group(1).lower()] = m.group(2).lower()
                continue

            # Multi-line label format:
            #   SHA256:
            #   <hash>
            if re.fullmatch(r"(?i)sha(?:-?256)?\s*:?", row):
                expecting_default_hash = True
                continue
            if expecting_default_hash:
                m = re.fullmatch(r"(?i)([a-f0-9]{64})", row)
                if m:
                    hashes.setdefault("__default__", m.group(1).lower())
                expecting_default_hash = False
                continue

            # fallback format: "SHA256: <hash>"
            m = re.search(r"(?i)\bsha(?:-?256)?\b[^a-f0-9]*([a-f0-9]{64})\b", row)
            if m:
                hashes.setdefault("__default__", m.group(1).lower())

        return hashes

    @staticmethod
    def _requests_verify_setting():
        """Use a custom CA bundle if configured, else default requests trust-store."""
        ca_bundle = os.environ.get(UPDATE_CA_BUNDLE_ENV, "").strip()
        return ca_bundle if ca_bundle else True

    @staticmethod
    def _enforce_optional_cert_pin(url: str, timeout: int = 5) -> None:
        """
        Optional certificate pinning controlled by env var:
        WHISPER_UPDATE_CERT_SHA256=<leaf_cert_sha256>[,<rotated_sha256>...]
        """
        pin_env = os.environ.get(UPDATE_CERT_PIN_ENV, "").strip()
        if not pin_env:
            return

        pins = {
            p.strip().lower()
            for p in pin_env.split(",")
            if re.fullmatch(r"[a-fA-F0-9]{64}", p.strip())
        }
        if not pins:
            raise RuntimeError(f"{UPDATE_CERT_PIN_ENV} is set but has no valid SHA256 pins")

        parsed = urlparse(url)
        if parsed.scheme.lower() != "https" or not parsed.hostname:
            raise RuntimeError("Certificate pinning requires an HTTPS URL")

        port = parsed.port or 443
        context = ssl.create_default_context()
        ca_bundle = os.environ.get(UPDATE_CA_BUNDLE_ENV, "").strip()
        if ca_bundle:
            context.load_verify_locations(cafile=ca_bundle)

        with socket.create_connection((parsed.hostname, port), timeout=timeout) as raw_sock:
            with context.wrap_socket(raw_sock, server_hostname=parsed.hostname) as tls_sock:
                cert_der = tls_sock.getpeercert(binary_form=True)
        fingerprint = hashlib.sha256(cert_der).hexdigest().lower()
        if fingerprint not in pins:
            raise RuntimeError(
                "TLS certificate pin mismatch for update endpoint "
                f"(got {fingerprint[:16]}..., expected one of {len(pins)} pin(s))"
            )
    
    def _get_cache_dir(self) -> str:
        """Get cache directory for update checks."""
        from .config import get_user_data_dir
        cache = os.path.join(get_user_data_dir(), 'cache')
        os.makedirs(cache, exist_ok=True)
        return cache
    
    def check_for_updates(self, timeout: int = 5) -> Dict:
        """Check if a new version is available.
        
        This method does NOT automatically download or install updates.
        It only checks and returns information.
        
        Args:
            timeout: Request timeout in seconds
        
        Returns:
            Dictionary with update information:
            {
                'update_available': bool,
                'current_version': str,
                'latest_version': str,
                'download_url': str,
                'release_notes': str,
                'release_date': str,
                'error': str (if error occurred)
            }
        """
        result = {
            'update_available': False,
            'current_version': self.current_version,
            'latest_version': None,
            'download_url': None,
            'expected_hash': None,
            'release_notes': None,
            'release_date': None,
            'error': None
        }
        
        try:
            # Try to import requests (optional dependency)
            try:
                import requests
            except ImportError:
                result['error'] = "requests library not installed (optional feature)"
                return result
            
            # Optional certificate pinning + request with optional custom CA bundle.
            self._enforce_optional_cert_pin(GITHUB_API, timeout=timeout)
            response = requests.get(
                GITHUB_API,
                timeout=timeout,
                verify=self._requests_verify_setting(),
            )
            response.raise_for_status()
            release = response.json()
            
            # Extract version from tag (remove 'v' prefix if present)
            latest_version = release['tag_name'].lstrip('v')
            
            # Compare versions
            update_available = version_lib.parse(latest_version) > version_lib.parse(self.current_version)
            
            # Find Windows installer asset
            download_url = None
            installer_name = None
            expected_hash = None
            release_hashes = self._extract_release_hashes(release.get('body', ''))
            for asset in release.get('assets', []):
                if asset['name'].endswith('.exe') and 'Setup' in asset['name']:
                    download_url = asset['browser_download_url']
                    installer_name = asset['name']
                    expected_hash = self._normalize_hash(
                        str(asset.get('digest', '') or asset.get('sha256', ''))
                    )
                    if not expected_hash:
                        expected_hash = release_hashes.get(installer_name.lower())
                    if not expected_hash:
                        expected_hash = release_hashes.get("__default__")
                    break
            
            result.update({
                'update_available': update_available,
                'latest_version': latest_version,
                'download_url': download_url,
                'expected_hash': expected_hash,
                'release_notes': release.get('body', ''),
                'release_date': release.get('published_at', ''),
            })

            if update_available and download_url and not expected_hash:
                result['error'] = (
                    "Update found but no SHA256 hash metadata was discovered for installer "
                    f"{installer_name or 'asset'}."
                )
            
            # Cache result
            self._save_check_result(result)
            
        except ImportError as e:
            result['error'] = f"Missing dependency: {e}"
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _save_check_result(self, result: Dict):
        """Save update check result to cache.
        
        Args:
            result: Update check result dictionary
        """
        try:
            import datetime
            cache_data = {
                'last_check': datetime.datetime.now().isoformat(),
                'result': result
            }
            with open(self.update_check_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
        except (IOError, OSError):
            pass  # Cache failure is not critical
    
    def get_cached_check(self) -> Optional[Dict]:
        """Get last cached update check result.
        
        Returns:
            Last check result, or None if no cache
        """
        try:
            if not os.path.exists(self.update_check_file):
                return None
            
            with open(self.update_check_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            return cache_data.get('result')
        except (IOError, OSError, json.JSONDecodeError):
            return None
    
    def should_check_for_updates(self, check_interval_hours: int = 24) -> bool:
        """Determine if it's time to check for updates.
        
        Args:
            check_interval_hours: Hours between update checks
        
        Returns:
            True if should check, False otherwise
        """
        try:
            if not os.path.exists(self.update_check_file):
                return True
            
            with open(self.update_check_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            import datetime
            last_check = datetime.datetime.fromisoformat(cache_data['last_check'])
            now = datetime.datetime.now()
            hours_since_check = (now - last_check).total_seconds() / 3600
            
            return hours_since_check >= check_interval_hours
            
        except (IOError, OSError, json.JSONDecodeError, KeyError, ValueError):
            return True
    
    def _lookup_expected_hash_for_url(self, download_url: str, timeout: int = 5) -> Optional[str]:
        """Resolve expected SHA256 for a download URL from latest release metadata."""
        check = self.check_for_updates(timeout=timeout)
        if check.get('download_url') == download_url:
            return check.get('expected_hash')
        return None

    def download_update(self, download_url: str, output_path: str,
                       progress_callback: Optional[callable] = None,
                       expected_hash: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Download update installer.
        
        NOTE: This requires the 'requests' library to be installed.
        
        Args:
            download_url: URL to download from
            output_path: Where to save the installer
            progress_callback: Optional callback(bytes_downloaded, total_bytes)
            expected_hash: Expected installer SHA256 hash. If omitted, attempts lookup.
        
        Returns:
            (success: bool, error_message: Optional[str])
        """
        expected_hash = self._normalize_hash(expected_hash or "")
        if not expected_hash:
            expected_hash = self._lookup_expected_hash_for_url(download_url, timeout=5)
        if not expected_hash:
            return False, (
                "Refusing to download update without SHA256 metadata. "
                "Publish hash in release notes or pass expected_hash."
            )

        try:
            import requests
        except ImportError:
            return False, "requests library not installed"

        try:
            self._enforce_optional_cert_pin(download_url, timeout=5)
            response = requests.get(
                download_url,
                stream=True,
                timeout=30,
                verify=self._requests_verify_setting(),
            )
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded, total_size)

            if not self.verify_installer(output_path, expected_hash=expected_hash):
                try:
                    os.remove(output_path)
                except (IOError, OSError):
                    pass
                return False, "Downloaded installer failed SHA256 verification"

            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def verify_installer(self, installer_path: str, expected_hash: Optional[str] = None) -> bool:
        """Verify installer integrity using SHA256 hash.
        
        Args:
            installer_path: Path to installer file
            expected_hash: Expected SHA256 hash
        
        Returns:
            True if valid, False otherwise
        """
        normalized_hash = self._normalize_hash(expected_hash or "")
        if not normalized_hash:
            return False

        if not os.path.exists(installer_path):
            return False
        size = os.path.getsize(installer_path)
        if size <= 1024 * 1024:
            return False

        try:
            sha256 = hashlib.sha256()
            with open(installer_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)

            return sha256.hexdigest().lower() == normalized_hash
            
        except (IOError, OSError):
            return False
    
    def get_update_summary(self) -> str:
        """Get human-readable update status summary.
        
        Returns:
            Formatted string with update status
        """
        result = self.check_for_updates()
        
        if result.get('error'):
            return f"Update check failed: {result['error']}"
        
        if result['update_available']:
            summary = [
                f"🎉 New version available: {result['latest_version']}",
                f"Current version: {result['current_version']}",
                "",
                "What's new:",
                result.get('release_notes', 'No release notes available')[:200],
                "",
                f"Download: {result.get('download_url', 'Not available')}"
            ]
            return "\n".join(summary)
        else:
            return f"✅ You're up to date! (v{result['current_version']})"


def check_for_updates_async(callback: callable):
    """Check for updates in background thread.
    
    Args:
        callback: Function to call with result dict
    """
    import threading
    
    def _check():
        checker = UpdateChecker()
        result = checker.check_for_updates()
        callback(result)
    
    thread = threading.Thread(target=_check, daemon=True)
    thread.start()


def show_update_notification(update_info: Dict):
    """Show update notification to user (if update available).
    
    Args:
        update_info: Update information dictionary from check_for_updates()
    """
    if not update_info.get('update_available'):
        return
    
    try:
        # Try to use Windows toast notification
        from winotify import Notification
        
        notification = Notification(
            app_id=APP_NAME,
            title=f"{APP_NAME} Update Available",
            msg=f"Version {update_info['latest_version']} is now available!",
            duration="long"
        )
        notification.show()
        
    except ImportError:
        # Fallback: just print to console
        print(f"\n🎉 Update available: v{update_info['latest_version']}")
        print(f"Download: {update_info.get('download_url', 'Check GitHub')}\n")

