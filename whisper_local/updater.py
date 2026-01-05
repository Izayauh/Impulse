"""
Auto-update system for WhisperLocal.

This module handles checking for updates, downloading installers,
and notifying users about new versions - all while preserving privacy.
"""

import os
import sys
import json
import hashlib
from typing import Optional, Dict, Tuple
from pathlib import Path
from packaging import version as version_lib

from .config import APP_VERSION, APP_NAME


# GitHub API endpoint for releases (no authentication needed for public repos)
GITHUB_API = "https://api.github.com/repos/Izayauh/whisper/releases/latest"
UPDATE_CHECK_FILE = "last_update_check.json"


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
            
            # Make request to GitHub API
            response = requests.get(GITHUB_API, timeout=timeout)
            response.raise_for_status()
            release = response.json()
            
            # Extract version from tag (remove 'v' prefix if present)
            latest_version = release['tag_name'].lstrip('v')
            
            # Compare versions
            update_available = version_lib.parse(latest_version) > version_lib.parse(self.current_version)
            
            # Find Windows installer asset
            download_url = None
            for asset in release.get('assets', []):
                if asset['name'].endswith('.exe') and 'Setup' in asset['name']:
                    download_url = asset['browser_download_url']
                    break
            
            result.update({
                'update_available': update_available,
                'latest_version': latest_version,
                'download_url': download_url,
                'release_notes': release.get('body', ''),
                'release_date': release.get('published_at', ''),
            })
            
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
    
    def download_update(self, download_url: str, output_path: str, 
                       progress_callback: Optional[callable] = None) -> Tuple[bool, Optional[str]]:
        """Download update installer.
        
        NOTE: This requires the 'requests' library to be installed.
        
        Args:
            download_url: URL to download from
            output_path: Where to save the installer
            progress_callback: Optional callback(bytes_downloaded, total_bytes)
        
        Returns:
            (success: bool, error_message: Optional[str])
        """
        try:
            import requests
        except ImportError:
            return False, "requests library not installed"
        
        try:
            response = requests.get(download_url, stream=True, timeout=30)
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
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    def verify_installer(self, installer_path: str, expected_hash: Optional[str] = None) -> bool:
        """Verify installer integrity using SHA256 hash.
        
        Args:
            installer_path: Path to installer file
            expected_hash: Expected SHA256 hash (optional)
        
        Returns:
            True if valid (or no hash to check), False otherwise
        """
        if not expected_hash:
            # If no hash provided, just check file exists and has reasonable size
            if not os.path.exists(installer_path):
                return False
            size = os.path.getsize(installer_path)
            return size > 1024 * 1024  # At least 1 MB
        
        try:
            sha256 = hashlib.sha256()
            with open(installer_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            
            return sha256.hexdigest().lower() == expected_hash.lower()
            
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

