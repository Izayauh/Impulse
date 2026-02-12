# GPU Load Monitoring and Adaptive Model Selection

## Overview

WhisperLocal now includes intelligent GPU load monitoring that automatically adapts model selection based on your GPU's current workload. This ensures smooth operation even when running GPU-intensive applications like games.

## Features

### 🎮 Game-Aware Operation

When you're playing a GPU-intensive game, WhisperLocal automatically detects the high GPU load and switches to lighter models to avoid:
- Stuttering or frame drops in your game
- GPU memory conflicts
- Transcription timeouts
- System instability

### 🔍 Real-Time Load Detection

The system continuously monitors GPU utilization every 2 seconds and categorizes load into three tiers:

| Load Level | Utilization | Behavior |
|------------|-------------|----------|
| **IDLE** | 0-69% | Full quality mode - all models available |
| **BUSY** | 70-84% | Skip large-v3, use base.en or medium.en |
| **CRITICAL** | 85-100% | Base.en only for maximum speed |

### 🎯 Hardware-Specific Optimization

#### NVIDIA GPUs
- **Low Load Mode**: Uses intelligent model selection
  - <25 words → base.en (fastest)
  - 25-75 words → medium.en (balanced)
  - 75+ words → large-v3 (best quality)

- **Busy Mode (70%+ GPU)**: Quality-performance balance
  - <50 words → base.en
  - 50+ words → medium.en
  - large-v3 disabled to preserve GPU resources

- **Critical Mode (85%+ GPU)**: Maximum speed
  - All utterances → base.en only
  - Minimal GPU impact

#### Non-NVIDIA GPUs (AMD, Intel)
Always uses light/medium models due to limited CUDA support:
- <50 words → base.en
- 50+ words → medium.en
- large-v3 permanently disabled (poor compatibility)

#### CPU-Only Mode
Optimized for speed when no GPU is detected:
- <50 words → base.en
- 50+ words → medium.en
- large-v3 disabled (too slow)

## How It Works

### 1. GPU Detection
At startup, the system detects:
- GPU vendor (NVIDIA, AMD, Intel, or unknown)
- GPU availability and functional status
- CUDA capability (NVIDIA only)

### 2. Background Monitoring
A lightweight background thread:
- Queries GPU utilization every 2 seconds (NVIDIA only)
- Updates load status cache
- Minimal performance impact (<0.1% CPU)

### 3. Dynamic Model Selection
When you start recording:
1. System checks current GPU load
2. Adjusts model selection thresholds accordingly
3. Logs the decision for transparency
4. Proceeds with optimal model

## Example Scenarios

### Scenario 1: Gaming
```
You're playing a game at 80% GPU load
→ WhisperLocal detects "BUSY" state
→ Uses base.en for short speech
→ Uses medium.en for longer speech
→ Skips large-v3 to avoid frame drops
→ Your game stays smooth! 🎮
```

### Scenario 2: Idle Desktop
```
Desktop idle, GPU at 10% load
→ WhisperLocal detects "IDLE" state
→ Uses full quality model selection
→ Transcribes with large-v3 for best accuracy
→ Maximum quality! 🎯
```

### Scenario 3: Non-NVIDIA GPU
```
You have an AMD Radeon GPU
→ WhisperLocal detects non-NVIDIA
→ Forces light/medium models always
→ Avoids CUDA-specific optimizations
→ Reliable compatibility! ✅
```

## Console Output

The system provides clear feedback about GPU status:

```
🔍 Starting GPU monitoring...
✅ GPU acceleration: ENABLED - GPU: NVIDIA RTX 4090 | Load: 15% (IDLE) | VRAM: 2048/24576MB (8%)
✅ Dynamic model selection (load-aware):
   • GPU idle/low load:
     - <25 words → base.en (fastest)
     - 25-75 words → medium.en
     - 75+ words → large-v3 (best quality)
   • GPU busy (70%+ load): Skip large-v3, use base/medium only
   • GPU critical (85%+ load): Base.en only for speed
🔥 CUDA warmup running in background...
📊 GPU load monitoring: ACTIVE
```

During transcription:
```
[whisper-smart] GPU Status: GPU: NVIDIA RTX 4090 | Load: 82% (BUSY) | VRAM: 18432/24576MB (75%)
[whisper-smart] ⚠️ GPU busy (70%+) - skipping large-v3
[whisper-smart] GPU-BUSY mode: threshold_base=50, use_large=False
```

## Testing GPU Monitoring

Run the test script to see GPU monitoring in action:

```powershell
python test_gpu_monitor.py
```

This will:
1. Detect your GPU type
2. Monitor GPU load for 30 seconds
3. Show real-time load status
4. Display recommended model tiers
5. Demonstrate adaptive behavior

**Pro tip**: Open a game or GPU stress test while running this to see the system adapt!

## Configuration

### Customizing Load Thresholds

Edit `whisper_local/gpu_monitor.py`:

```python
class GPUMonitor:
    # GPU load thresholds
    HIGH_LOAD_THRESHOLD = 70  # "Busy" threshold (default: 70%)
    CRITICAL_LOAD_THRESHOLD = 85  # "Critical" threshold (default: 85%)
```

### Adjusting Update Interval

```python
def __init__(self):
    self._update_interval = 2.0  # Update every 2 seconds (default)
```

## Troubleshooting

### GPU Not Detected
**Symptoms**: System runs in CPU mode despite having a GPU

**Solutions**:
1. Install/update NVIDIA drivers
2. Ensure `nvidia-smi` command works: `nvidia-smi` in PowerShell
3. Check `ggml-cuda.dll` exists in application directory

### Load Not Updating
**Symptoms**: GPU load shows 0% when it shouldn't

**Solutions**:
1. Verify `nvidia-smi` works with query: 
   ```powershell
   nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits
   ```
2. Check Windows Task Manager → Performance → GPU for comparison
3. Ensure monitoring thread started (check logs)

### Non-NVIDIA GPU Not Recognized
**Expected behavior**: AMD/Intel GPUs are detected but monitoring is limited

The system requires vendor-specific tools:
- AMD: `rocm-smi` (ROCm toolkit)
- Intel: `xpu-smi` (oneAPI toolkit)

Currently, only NVIDIA monitoring is fully implemented. Non-NVIDIA GPUs will use conservative model selection.

## Performance Impact

The GPU monitoring feature has minimal overhead:

| Resource | Impact |
|----------|--------|
| CPU Usage | <0.1% |
| Memory | <1MB |
| GPU Query | Every 2 seconds |
| Startup Time | +50ms (GPU detection) |

## Privacy

All GPU monitoring is local:
- No data sent to external servers
- No telemetry or analytics
- GPU info stays on your machine
- See [PRIVACY.md](../PRIVACY.md) for full details

## Future Enhancements

Planned improvements:
- [ ] AMD GPU monitoring support (ROCm)
- [ ] Intel Arc monitoring support (oneAPI)
- [ ] User-configurable thresholds via GUI
- [ ] GPU memory monitoring for better model selection
- [ ] Temperature-based throttling
- [ ] Multi-GPU support

## Technical Details

### GPU Query Method

**NVIDIA** (implemented):
```
nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits
```

**AMD** (planned):
```
rocm-smi --showproductname --showuse --showmeminfo
```

**Intel** (planned):
```
xpu-smi dump -m 0,1,5
```

### Threading Model

- Main thread: UI and recording
- Background thread: GPU monitoring (daemon)
- Synchronization: Thread lock for GPU info cache
- Clean shutdown: `gpu_monitor.stop_monitoring()` on exit

### Error Handling

The system is fail-safe:
- GPU query timeout: 3 seconds
- Failed queries: Cached data used
- No GPU detected: Graceful fallback to CPU mode
- Import errors: Dummy monitor with safe defaults

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [PERFORMANCE.md](../IMPROVEMENTS.md) - Performance optimizations
- [USER_GUIDE.md](../USER_GUIDE.md) - User documentation

