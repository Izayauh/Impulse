"""
Logging configuration for WhisperLocal.

This module provides both traditional and structured logging capabilities.
"""

import logging
import logging.handlers
import json
import sys
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path


class StructuredLogger:
    """Logger that outputs structured JSON for easy parsing."""
    
    def __init__(self, name: str, log_file: Optional[str] = None):
        """Initialize structured logger.
        
        Args:
            name: Logger name
            log_file: Path to log file (optional)
        """
        self.name = name
        self.log_file = log_file
        self.logger = logging.getLogger(f"{name}.structured")
        
        # Set up file handler for structured logs if specified
        if log_file:
            structured_log_file = log_file.replace('.log', '_structured.json')
            handler = logging.FileHandler(structured_log_file, encoding='utf-8')
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Log a structured event.
        
        Args:
            event_type: Type of event (e.g., 'transcription', 'error')
            data: Event data dictionary
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'data': data
        }
        self.logger.info(json.dumps(log_entry))
    
    def log_transcription(self, model: str, duration: float, words: int, success: bool = True):
        """Log transcription event.
        
        Args:
            model: Model used
            duration: Duration in seconds
            words: Word count
            success: Whether transcription succeeded
        """
        self.log_event('transcription', {
            'model': model,
            'duration_sec': round(duration, 3),
            'word_count': words,
            'success': success
        })
    
    def log_error(self, error_type: str, message: str, details: Optional[Dict] = None):
        """Log error event.
        
        Args:
            error_type: Type of error
            message: Error message
            details: Additional details (optional)
        """
        self.log_event('error', {
            'error_type': error_type,
            'message': message,
            'details': details or {}
        })
    
    def log_performance(self, operation: str, duration: float):
        """Log performance metric.
        
        Args:
            operation: Operation name
            duration: Duration in seconds
        """
        self.log_event('performance', {
            'operation': operation,
            'duration_sec': round(duration, 3)
        })


def setup_logging(app_name: str, log_file: str, level: int = logging.DEBUG) -> logging.Logger:
    """Configure application-wide logging.
    
    Creates a logger with:
    - File handler: Writes to log file in user data directory
    - Console handler: Prints INFO+ to stdout
    - Rotating file handler: 5 MB max, 3 backups
    
    Args:
        app_name: Application name for logger
        log_file: Path to log file
        level: Logging level (default: DEBUG)
    
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(level)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Ensure log directory exists
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # File handler - DEBUG level, rotating
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB max
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except (IOError, OSError) as e:
        print(f"Warning: Could not create log file: {e}")
    
    # Console handler - INFO level
    # Use UTF-8 encoding for console to handle Unicode characters properly
    try:
        import io
        console_handler = logging.StreamHandler(io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace'))
    except AttributeError:
        # Fallback for older Python versions
        console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

