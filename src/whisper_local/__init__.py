"""
WhisperLocal - Privacy-focused speech-to-text dictation.

This package contains the core components of the WhisperLocal application.
"""

__version__ = "1.0.0"
__author__ = "WhisperLocal"

# Import main components
from .config import (
    Config,
    config,
    APP_NAME,
    APP_VERSION,
    SAMPLE_RATE_HZ,
    AUDIO_CHANNELS,
    get_bundle_dir,
    get_app_dir,
    get_user_data_dir,
)

from .stats import StatsTracker

from .logging_config import (
    setup_logging,
    get_logger,
    StructuredLogger,
)

from .performance import (
    PerformanceMonitor,
    perf_monitor,
)

from .updater import (
    UpdateChecker,
    check_for_updates_async,
    show_update_notification,
)

from .crash_reporter import (
    CrashReporter,
    install_crash_handler,
    uninstall_crash_handler,
    get_crash_reporter,
    CrashContext,
)

from .health import (
    HealthCheck,
    HealthStatus,
    get_health_check,
)

from .gpu_monitor import (
    GPUMonitor,
    GPUInfo,
    gpu_monitor,
)

__all__ = [
    # Version info
    '__version__',
    '__author__',
    
    # Config
    'Config',
    'config',
    'APP_NAME',
    'APP_VERSION',
    'SAMPLE_RATE_HZ',
    'AUDIO_CHANNELS',
    'get_bundle_dir',
    'get_app_dir',
    'get_user_data_dir',
    
    # Stats
    'StatsTracker',
    
    # Logging
    'setup_logging',
    'get_logger',
    'StructuredLogger',
    
    # Performance
    'PerformanceMonitor',
    'perf_monitor',
    
    # GPU Monitoring
    'GPUMonitor',
    'GPUInfo',
    'gpu_monitor',
    
    # Updater
    'UpdateChecker',
    'check_for_updates_async',
    'show_update_notification',
    
    # Crash Reporter
    'CrashReporter',
    'install_crash_handler',
    'uninstall_crash_handler',
    'get_crash_reporter',
    'CrashContext',
    
    # Health Check
    'HealthCheck',
    'HealthStatus',
    'get_health_check',
]

