"""
Health check system for WhisperLocal.

This module provides health checks and diagnostics for all system components.
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class HealthStatus:
    """Health status constants."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck:
    """Application health check system."""
    
    def __init__(self):
        """Initialize health check system."""
        self.checks = {}
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks."""
        self.register_check("whisper_binary", self.check_whisper_binary)
        self.register_check("ai_models", self.check_models)
        self.register_check("audio_devices", self.check_audio_devices)
        self.register_check("file_permissions", self.check_file_permissions)
        self.register_check("disk_space", self.check_disk_space)
        self.register_check("dependencies", self.check_dependencies)
    
    def register_check(self, name: str, check_func: callable):
        """Register a health check.
        
        Args:
            name: Name of the check
            check_func: Function that performs the check
        """
        self.checks[name] = check_func
    
    def check_whisper_binary(self) -> Dict[str, Any]:
        """Check if Whisper binary exists and is executable.
        
        Returns:
            Health check result dictionary
        """
        from .config import config
        
        binary_path = config.whisper_binary
        
        if not binary_path:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': 'Whisper binary not found',
                'details': {'searched_paths': 'auto-detection failed'}
            }
        
        if not os.path.isfile(binary_path):
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'Whisper binary not found at {binary_path}',
                'details': {'path': binary_path}
            }
        
        if not os.access(binary_path, os.X_OK):
            return {
                'status': HealthStatus.DEGRADED,
                'message': 'Whisper binary exists but may not be executable',
                'details': {'path': binary_path}
            }
        
        return {
            'status': HealthStatus.HEALTHY,
            'message': 'Whisper binary found and accessible',
            'details': {'path': binary_path}
        }
    
    def check_models(self) -> Dict[str, Any]:
        """Check if AI models are available.
        
        Returns:
            Health check result dictionary
        """
        from .config import config, get_app_dir
        
        models = {
            'base': config.model_base,
            'medium': config.model_medium,
            'large': config.model_large
        }
        
        app_dir = get_app_dir()
        found_models = {}
        missing_models = []
        
        for name, rel_path in models.items():
            full_path = os.path.join(app_dir, rel_path)
            if os.path.isfile(full_path):
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
                found_models[name] = {
                    'path': full_path,
                    'size_mb': round(size_mb, 1)
                }
            else:
                missing_models.append(name)
        
        if not found_models:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': 'No AI models found',
                'details': {
                    'missing': missing_models,
                    'search_dir': app_dir
                }
            }
        
        if missing_models:
            return {
                'status': HealthStatus.DEGRADED,
                'message': f'Some models missing: {", ".join(missing_models)}',
                'details': {
                    'found': list(found_models.keys()),
                    'missing': missing_models
                }
            }
        
        return {
            'status': HealthStatus.HEALTHY,
            'message': f'All {len(found_models)} models available',
            'details': {'models': found_models}
        }
    
    def check_audio_devices(self) -> Dict[str, Any]:
        """Check if audio input devices are available.
        
        Returns:
            Health check result dictionary
        """
        try:
            import sounddevice as sd
            
            devices = sd.query_devices()
            input_devices = [
                d for d in devices 
                if isinstance(d, dict) and d.get('max_input_channels', 0) > 0
            ]
            
            if not input_devices:
                return {
                    'status': HealthStatus.UNHEALTHY,
                    'message': 'No audio input devices found',
                    'details': {'device_count': 0}
                }
            
            default_input = sd.query_devices(kind='input')
            
            return {
                'status': HealthStatus.HEALTHY,
                'message': f'{len(input_devices)} audio input device(s) available',
                'details': {
                    'device_count': len(input_devices),
                    'default_device': default_input.get('name') if isinstance(default_input, dict) else None
                }
            }
        
        except Exception as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'Audio device check failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def check_file_permissions(self) -> Dict[str, Any]:
        """Check file system permissions for critical directories.
        
        Returns:
            Health check result dictionary
        """
        from .config import get_user_data_dir
        
        user_dir = get_user_data_dir()
        
        # Check if we can create/write files
        test_file = os.path.join(user_dir, '.health_check_test')
        
        try:
            # Try to write
            with open(test_file, 'w') as f:
                f.write('test')
            
            # Try to read
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Cleanup
            os.remove(test_file)
            
            if content != 'test':
                return {
                    'status': HealthStatus.DEGRADED,
                    'message': 'File write/read may be corrupted',
                    'details': {'user_dir': user_dir}
                }
            
            return {
                'status': HealthStatus.HEALTHY,
                'message': 'File permissions OK',
                'details': {'user_dir': user_dir, 'writable': True}
            }
        
        except (IOError, OSError) as e:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'Cannot write to user directory: {str(e)}',
                'details': {'user_dir': user_dir, 'error': str(e)}
            }
    
    def check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space.
        
        Returns:
            Health check result dictionary
        """
        from .config import get_user_data_dir
        
        try:
            import shutil
            
            user_dir = get_user_data_dir()
            total, used, free = shutil.disk_usage(user_dir)
            
            free_gb = free / (1024 ** 3)
            total_gb = total / (1024 ** 3)
            percent_free = (free / total) * 100
            
            if free_gb < 0.5:  # Less than 500 MB
                status = HealthStatus.UNHEALTHY
                message = f'Low disk space: {free_gb:.1f} GB free'
            elif free_gb < 2.0:  # Less than 2 GB
                status = HealthStatus.DEGRADED
                message = f'Disk space getting low: {free_gb:.1f} GB free'
            else:
                status = HealthStatus.HEALTHY
                message = f'Sufficient disk space: {free_gb:.1f} GB free'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'free_gb': round(free_gb, 2),
                    'total_gb': round(total_gb, 2),
                    'percent_free': round(percent_free, 1)
                }
            }
        
        except Exception as e:
            return {
                'status': HealthStatus.UNKNOWN,
                'message': f'Could not check disk space: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def check_dependencies(self) -> Dict[str, Any]:
        """Check if required dependencies are installed.
        
        Returns:
            Health check result dictionary
        """
        required = [
            'sounddevice',
            'soundfile',
            'keyboard',
            'pyperclip',
            'pyautogui',
            'PIL',
            'pystray',
            'numpy'
        ]
        
        installed = []
        missing = []
        
        for module_name in required:
            try:
                __import__(module_name)
                installed.append(module_name)
            except ImportError:
                missing.append(module_name)
        
        if missing:
            return {
                'status': HealthStatus.UNHEALTHY,
                'message': f'{len(missing)} required dependencies missing',
                'details': {
                    'installed': installed,
                    'missing': missing
                }
            }
        
        return {
            'status': HealthStatus.HEALTHY,
            'message': f'All {len(installed)} dependencies installed',
            'details': {'installed': installed}
        }
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all registered health checks.
        
        Returns:
            Dictionary with all check results and overall status
        """
        results = {}
        statuses = []
        
        for name, check_func in self.checks.items():
            try:
                results[name] = check_func()
                statuses.append(results[name]['status'])
            except Exception as e:
                results[name] = {
                    'status': HealthStatus.UNKNOWN,
                    'message': f'Check failed: {str(e)}',
                    'details': {'error': str(e)}
                }
                statuses.append(HealthStatus.UNKNOWN)
        
        # Determine overall status
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall_status = HealthStatus.DEGRADED
        elif any(s == HealthStatus.UNKNOWN for s in statuses):
            overall_status = HealthStatus.UNKNOWN
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': overall_status,
            'checks': results
        }
    
    def get_health_summary(self) -> str:
        """Get human-readable health summary.
        
        Returns:
            Formatted string with health status
        """
        health = self.run_all_checks()
        
        lines = [
            "System Health Check",
            "=" * 60,
            f"Overall Status: {health['overall_status'].upper()}",
            f"Timestamp: {health['timestamp']}",
            "",
            "Component Status:",
        ]
        
        for name, result in health['checks'].items():
            status_icon = {
                HealthStatus.HEALTHY: "✅",
                HealthStatus.DEGRADED: "⚠️",
                HealthStatus.UNHEALTHY: "❌",
                HealthStatus.UNKNOWN: "❓"
            }.get(result['status'], "❓")
            
            lines.append(f"  {status_icon} {name}: {result['message']}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)
    
    def save_health_report(self, output_file: Optional[str] = None) -> str:
        """Save health report to file.
        
        Args:
            output_file: Path to output file (default: user_dir/health_report.json)
        
        Returns:
            Path to saved report
        """
        if output_file is None:
            from .config import get_user_data_dir
            output_file = os.path.join(get_user_data_dir(), 'health_report.json')
        
        health = self.run_all_checks()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(health, f, indent=2)
        
        return output_file


# Global health check instance
_health_check: Optional[HealthCheck] = None


def get_health_check() -> HealthCheck:
    """Get global health check instance.
    
    Returns:
        HealthCheck instance
    """
    global _health_check
    
    if _health_check is None:
        _health_check = HealthCheck()
    
    return _health_check

