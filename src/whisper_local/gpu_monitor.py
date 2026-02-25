"""
GPU monitoring and utilization tracking for WhisperLocal.

This module provides tools to monitor GPU utilization and memory usage,
allowing the application to adapt model selection based on GPU load.
"""

import subprocess
import time
import threading
from typing import Optional, Dict, Tuple
from dataclasses import dataclass


@dataclass
class GPUInfo:
    """GPU information and utilization metrics."""
    vendor: str  # "nvidia", "amd", "intel", "unknown"
    name: str
    utilization_percent: float  # 0-100
    memory_used_mb: float
    memory_total_mb: float
    memory_percent: float  # 0-100
    temperature_c: Optional[float] = None


class GPUMonitor:
    """Monitor GPU utilization and provide load-aware recommendations."""
    
    # GPU load thresholds
    HIGH_LOAD_THRESHOLD = 70  # Consider GPU "busy" above this %
    CRITICAL_LOAD_THRESHOLD = 85  # GPU under heavy load
    
    def __init__(self):
        """Initialize GPU monitor."""
        self._gpu_info: Optional[GPUInfo] = None
        self._last_update = 0
        self._update_interval = 10.0  # Update every 10 seconds (reduces fan noise)
        self._monitoring_enabled = False
        self._monitor_thread = None
        self._lock = threading.Lock()
        
        # Detect GPU vendor and capabilities
        self._gpu_vendor = self._detect_gpu_vendor()
        self._gpu_available = self._gpu_vendor == "nvidia"
    
    def _detect_gpu_vendor(self) -> str:
        """Detect GPU vendor.
        
        Returns:
            "nvidia", "amd", "intel", or "unknown"
        """
        try:
            # Try NVIDIA first
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True,
                timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            )
            if result.returncode == 0:
                return "nvidia"
        except Exception:
            pass
        
        try:
            # Try AMD (ROCm)
            result = subprocess.run(
                ["rocm-smi", "--showproductname"],
                capture_output=True,
                timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            )
            if result.returncode == 0:
                return "amd"
        except Exception:
            pass
        
        try:
            # Try Intel (Arc)
            result = subprocess.run(
                ["xpu-smi", "discovery"],
                capture_output=True,
                timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            )
            if result.returncode == 0 and b"Intel" in result.stdout:
                return "intel"
        except Exception:
            pass
        
        return "unknown"
    
    def _query_nvidia_gpu(self) -> Optional[GPUInfo]:
        """Query NVIDIA GPU using nvidia-smi.
        
        Returns:
            GPUInfo object or None if query fails
        """
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                    "--format=csv,noheader,nounits"
                ],
                capture_output=True,
                timeout=3,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            )
            
            if result.returncode != 0:
                return None
            
            # Parse CSV output (first GPU only)
            lines = result.stdout.strip().split('\n')
            if not lines:
                return None
            
            parts = [p.strip() for p in lines[0].split(',')]
            if len(parts) < 4:
                return None
            
            name = parts[0]
            utilization = float(parts[1])
            memory_used = float(parts[2])
            memory_total = float(parts[3])
            temperature = float(parts[4]) if len(parts) > 4 else None
            
            memory_percent = (memory_used / memory_total * 100) if memory_total > 0 else 0
            
            return GPUInfo(
                vendor="nvidia",
                name=name,
                utilization_percent=utilization,
                memory_used_mb=memory_used,
                memory_total_mb=memory_total,
                memory_percent=memory_percent,
                temperature_c=temperature
            )
        except Exception:
            return None
    
    def _update_gpu_info(self):
        """Update GPU information cache."""
        now = time.time()
        
        # Rate limit updates
        if now - self._last_update < self._update_interval:
            return
        
        if self._gpu_vendor == "nvidia":
            info = self._query_nvidia_gpu()
            if info:
                with self._lock:
                    self._gpu_info = info
                    self._last_update = now
    
    def start_monitoring(self):
        """Start background GPU monitoring thread."""
        if self._monitoring_enabled:
            return
        
        self._monitoring_enabled = True
        
        def monitor_loop():
            while self._monitoring_enabled:
                try:
                    self._update_gpu_info()
                except Exception:
                    pass
                time.sleep(self._update_interval)
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop background GPU monitoring."""
        self._monitoring_enabled = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
    
    def get_gpu_info(self) -> Optional[GPUInfo]:
        """Get current GPU information.
        
        Returns:
            GPUInfo object or None if not available
        """
        # Update on-demand if not monitoring in background
        if not self._monitoring_enabled:
            self._update_gpu_info()
        
        with self._lock:
            return self._gpu_info
    
    def is_gpu_available(self) -> bool:
        """Check if GPU acceleration is available.
        
        Returns:
            True if GPU is available for compute
        """
        return self._gpu_available
    
    def is_nvidia_gpu(self) -> bool:
        """Check if GPU is NVIDIA.
        
        Returns:
            True if GPU is NVIDIA
        """
        return self._gpu_vendor == "nvidia"
    
    def get_gpu_vendor(self) -> str:
        """Get GPU vendor name.
        
        Returns:
            "nvidia", "amd", "intel", or "unknown"
        """
        return self._gpu_vendor
    
    def is_gpu_busy(self) -> bool:
        """Check if GPU is currently busy (high utilization).
        
        Returns:
            True if GPU utilization is above HIGH_LOAD_THRESHOLD
        """
        info = self.get_gpu_info()
        if not info:
            return False
        
        return info.utilization_percent >= self.HIGH_LOAD_THRESHOLD
    
    def is_gpu_critical_load(self) -> bool:
        """Check if GPU is under critical load.
        
        Returns:
            True if GPU utilization is above CRITICAL_LOAD_THRESHOLD
        """
        info = self.get_gpu_info()
        if not info:
            return False
        
        return info.utilization_percent >= self.CRITICAL_LOAD_THRESHOLD
    
    def get_recommended_model_tier(self) -> str:
        """Get recommended model tier based on GPU load.
        
        Returns:
            "light" (base), "medium", or "heavy" (large)
        """
        # Non-NVIDIA GPUs: always use light/medium models
        if not self.is_nvidia_gpu():
            return "light"
        
        # NVIDIA GPU: consider load
        if not self._gpu_available:
            return "medium"  # CPU fallback
        
        info = self.get_gpu_info()
        if not info:
            return "medium"  # Unknown state, be conservative
        
        # Critical load (85%+): Use lightest model
        if info.utilization_percent >= self.CRITICAL_LOAD_THRESHOLD:
            return "light"
        
        # High load (70%+): Use medium model
        if info.utilization_percent >= self.HIGH_LOAD_THRESHOLD:
            return "medium"
        
        # Low load: Can use heavy model
        return "heavy"
    
    def get_load_status_text(self) -> str:
        """Get human-readable GPU load status.
        
        Returns:
            Status string describing GPU state
        """
        if not self._gpu_available:
            return f"GPU: None ({self._gpu_vendor})"
        
        info = self.get_gpu_info()
        if not info:
            return f"GPU: {self._gpu_vendor.upper()} (unavailable)"
        
        load_desc = "IDLE"
        if info.utilization_percent >= self.CRITICAL_LOAD_THRESHOLD:
            load_desc = "CRITICAL"
        elif info.utilization_percent >= self.HIGH_LOAD_THRESHOLD:
            load_desc = "BUSY"
        elif info.utilization_percent >= 30:
            load_desc = "ACTIVE"
        
        return (
            f"GPU: {info.name} | "
            f"Load: {info.utilization_percent:.0f}% ({load_desc}) | "
            f"VRAM: {info.memory_used_mb:.0f}/{info.memory_total_mb:.0f}MB "
            f"({info.memory_percent:.0f}%)"
        )
    
    def should_use_light_model(self, word_count: int = 0) -> bool:
        """Determine if light model should be used based on GPU state.
        
        Args:
            word_count: Estimated word count (used for additional context)
        
        Returns:
            True if light model should be forced
        """
        # Non-NVIDIA: always use light/medium
        if not self.is_nvidia_gpu():
            return True
        
        # No GPU available
        if not self._gpu_available:
            return word_count < 50  # CPU mode decisions
        
        # GPU is critically loaded
        if self.is_gpu_critical_load():
            return True
        
        return False


# Global GPU monitor instance
gpu_monitor = GPUMonitor()

