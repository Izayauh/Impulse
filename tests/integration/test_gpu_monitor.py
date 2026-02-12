"""
Test script for GPU monitoring functionality.

This script demonstrates the GPU monitoring capabilities and shows
how the system adapts to GPU load.
"""

import time
import sys
import os

# Add whisper_local to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from whisper_local.gpu_monitor import gpu_monitor


def main():
    # Set console encoding to UTF-8 for emoji support
    import sys
    if sys.platform == 'win32':
        try:
            # Try to set UTF-8 encoding for Windows console
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        except Exception:
            # Fallback: will use ASCII-safe output
            pass
    
    print("=" * 70)
    print("GPU Monitoring Test")
    print("=" * 70)
    
    # Detect GPU
    vendor = gpu_monitor.get_gpu_vendor()
    is_nvidia = gpu_monitor.is_nvidia_gpu()
    is_available = gpu_monitor.is_gpu_available()
    
    print(f"\nGPU Detection:")
    print(f"  Vendor: {vendor.upper()}")
    print(f"  NVIDIA: {'Yes' if is_nvidia else 'No'}")
    print(f"  Available: {'Yes' if is_available else 'No'}")
    
    if not is_nvidia:
        print(f"\nNon-NVIDIA GPU detected!")
        print(f"   System will use light/medium models only for compatibility.")
        if vendor == "unknown":
            print(f"   No GPU detected - will run in CPU mode.")
        return
    
    # Start monitoring
    print(f"\nStarting GPU monitoring...")
    gpu_monitor.start_monitoring()
    
    print(f"\nMonitoring GPU for 30 seconds...")
    print(f"   (Run a game or GPU-intensive task to see load adaptation)")
    print(f"\n{'Time':<8} {'GPU Load':<12} {'VRAM':<20} {'Recommended Model':<20}")
    print("-" * 70)
    
    try:
        for i in range(30):
            gpu_info = gpu_monitor.get_gpu_info()
            
            if gpu_info:
                recommended = gpu_monitor.get_recommended_model_tier()
                load_percent = gpu_info.utilization_percent
                vram = f"{gpu_info.memory_used_mb:.0f}/{gpu_info.memory_total_mb:.0f}MB"
                
                # Color coding for load
                if load_percent >= 85:
                    load_str = f"{load_percent:>5.1f}% CRITICAL"
                elif load_percent >= 70:
                    load_str = f"{load_percent:>5.1f}% BUSY"
                else:
                    load_str = f"{load_percent:>5.1f}% IDLE"
                
                # Model recommendation
                if recommended == "light":
                    model_str = "base.en (light)"
                elif recommended == "medium":
                    model_str = "medium.en"
                else:
                    model_str = "large-v3 (heavy)"
                
                print(f"{i+1:>3}s     {load_str:<12} {vram:<20} {model_str:<20}")
            else:
                print(f"{i+1:>3}s     [No GPU data available]")
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\nMonitoring interrupted by user")
    
    finally:
        gpu_monitor.stop_monitoring()
        print("\n" + "=" * 70)
        print("GPU monitoring stopped")
        
        # Summary
        gpu_info = gpu_monitor.get_gpu_info()
        if gpu_info:
            print(f"\nFinal GPU Status:")
            print(f"  Name: {gpu_info.name}")
            print(f"  Load: {gpu_info.utilization_percent:.1f}%")
            print(f"  VRAM: {gpu_info.memory_used_mb:.0f}/{gpu_info.memory_total_mb:.0f}MB")
            print(f"  Temperature: {gpu_info.temperature_c:.0f}°C" if gpu_info.temperature_c else "")
            
            print(f"\nModel Selection Logic:")
            if gpu_info.utilization_percent >= 85:
                print(f"  GPU at {gpu_info.utilization_percent:.0f}% (CRITICAL) -> base.en only")
            elif gpu_info.utilization_percent >= 70:
                print(f"  GPU at {gpu_info.utilization_percent:.0f}% (BUSY) -> base.en or medium.en")
            else:
                print(f"  GPU at {gpu_info.utilization_percent:.0f}% (IDLE) -> All models available")
        
        print("=" * 70)


if __name__ == "__main__":
    main()

