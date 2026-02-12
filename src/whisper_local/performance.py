"""
Performance monitoring for WhisperLocal.

This module provides tools to measure and track application performance.
"""

import time
import statistics
from contextlib import contextmanager
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class PerformanceMetric:
    """Performance metric data."""
    operation: str
    count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    times: List[float] = field(default_factory=list)
    
    def add_measurement(self, duration: float):
        """Add a measurement.
        
        Args:
            duration: Duration in seconds
        """
        self.count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.times.append(duration)
        
        # Keep only last 100 measurements to limit memory
        if len(self.times) > 100:
            self.times = self.times[-100:]
    
    def get_stats(self) -> Dict:
        """Get statistics for this metric.
        
        Returns:
            Dictionary with mean, median, min, max, std_dev
        """
        if self.count == 0:
            return {}
        
        return {
            'count': self.count,
            'mean': self.total_time / self.count,
            'median': statistics.median(self.times) if self.times else 0,
            'min': self.min_time,
            'max': self.max_time,
            'std_dev': statistics.stdev(self.times) if len(self.times) > 1 else 0,
            'total': self.total_time
        }


class PerformanceMonitor:
    """Monitor application performance metrics."""
    
    def __init__(self):
        """Initialize performance monitor."""
        self.metrics: Dict[str, PerformanceMetric] = {}
        self.enabled = True
    
    def enable(self):
        """Enable performance monitoring."""
        self.enabled = True
    
    def disable(self):
        """Disable performance monitoring."""
        self.enabled = False
    
    @contextmanager
    def measure(self, operation: str):
        """Context manager to measure operation duration.
        
        Args:
            operation: Name of the operation being measured
        
        Yields:
            None
        
        Example:
            with perf_monitor.measure('transcription'):
                # Code to measure
                pass
        """
        if not self.enabled:
            yield
            return
        
        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self.record(operation, duration)
    
    def record(self, operation: str, duration: float):
        """Record a performance measurement.
        
        Args:
            operation: Name of the operation
            duration: Duration in seconds
        """
        if not self.enabled:
            return
        
        if operation not in self.metrics:
            self.metrics[operation] = PerformanceMetric(operation=operation)
        
        self.metrics[operation].add_measurement(duration)
    
    def get_stats(self, operation: str) -> Optional[Dict]:
        """Get statistics for an operation.
        
        Args:
            operation: Name of the operation
        
        Returns:
            Statistics dictionary, or None if operation not found
        """
        if operation not in self.metrics:
            return None
        
        return self.metrics[operation].get_stats()
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all operations.
        
        Returns:
            Dictionary mapping operation names to their statistics
        """
        return {
            operation: metric.get_stats()
            for operation, metric in self.metrics.items()
        }
    
    def reset(self, operation: Optional[str] = None):
        """Reset metrics.
        
        Args:
            operation: Specific operation to reset, or None to reset all
        """
        if operation:
            if operation in self.metrics:
                del self.metrics[operation]
        else:
            self.metrics.clear()
    
    def get_summary(self) -> str:
        """Get a human-readable summary of performance metrics.
        
        Returns:
            Formatted string with performance summary
        """
        if not self.metrics:
            return "No performance data collected"
        
        lines = ["Performance Summary:", "=" * 60]
        
        for operation, metric in sorted(self.metrics.items()):
            stats = metric.get_stats()
            lines.append(f"\n{operation}:")
            lines.append(f"  Count: {stats['count']}")
            lines.append(f"  Mean:  {stats['mean']:.3f}s")
            lines.append(f"  Min:   {stats['min']:.3f}s")
            lines.append(f"  Max:   {stats['max']:.3f}s")
            if stats['count'] > 1:
                lines.append(f"  StdDev: {stats['std_dev']:.3f}s")
        
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


# Global performance monitor instance
perf_monitor = PerformanceMonitor()

