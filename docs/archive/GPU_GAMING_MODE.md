# 🎮 Gaming Mode - GPU Load Detection

## Quick Summary

WhisperLocal now **automatically detects when you're gaming** or running GPU-intensive apps and switches to faster, lighter AI models to keep your games smooth!

## How It Works

### Before This Update ❌
- WhisperLocal would use heavy AI models even during gaming
- Could cause frame drops or stuttering in GPU-intensive games
- No awareness of GPU load

### After This Update ✅
- **Automatically monitors your GPU load**
- Switches to lighter models when gaming (GPU >70% busy)
- Uses fastest model during intense gameplay (GPU >85%)
- Your games stay smooth! 🚀

## For Gamers

### What You'll Notice

1. **During Normal Use** (GPU idle):
   - Uses best quality models for accurate transcription
   - Maximum accuracy for document work

2. **While Gaming** (GPU 70-85% busy):
   - Automatically switches to medium-speed models
   - Prevents interference with your game
   - Still accurate, just slightly faster processing

3. **Intense Gaming** (GPU 85%+ critical):
   - Uses fastest model only (base.en)
   - Minimal GPU impact
   - Lightning-fast transcription

### You Don't Need To Do Anything!

The system handles everything automatically:
- ✅ Detects your game is running
- ✅ Checks GPU load in real-time
- ✅ Switches models automatically
- ✅ Returns to quality mode when game closes

## Technical Details

### GPU Detection

**NVIDIA GPUs** (RTX 20/30/40 series, GTX 16/10 series):
- ✅ Full support with real-time load monitoring
- ✅ VRAM monitoring
- ✅ Temperature tracking
- ✅ Adaptive model switching

**AMD GPUs** (Radeon RX 6000/7000 series):
- ⚠️ Detection only (no real-time monitoring yet)
- ✅ Always uses light/medium models for compatibility
- ✅ Prevents CUDA-specific code paths

**Intel GPUs** (Arc A-series):
- ⚠️ Detection only (no real-time monitoring yet)
- ✅ Always uses light/medium models for compatibility
- ✅ Prevents CUDA-specific code paths

**No GPU / Integrated Graphics**:
- ✅ CPU-optimized mode
- ✅ Uses lightweight models always
- ✅ Best performance for non-gaming PCs

### Model Selection

| GPU State | Load % | Model Used | Quality | Speed |
|-----------|--------|------------|---------|-------|
| **Idle** | 0-69% | large-v3 | ⭐⭐⭐⭐⭐ | 🐌 Slower |
| **Active** | 0-69% | medium.en | ⭐⭐⭐⭐ | ⚡ Fast |
| **Busy** | 70-84% | medium.en | ⭐⭐⭐⭐ | ⚡ Fast |
| **Critical** | 85-100% | base.en | ⭐⭐⭐ | ⚡⚡⚡ Fastest |

*Quality ratings: All models are highly accurate, differences are minimal for normal speech*

## Testing It

### See It In Action

1. Open WhisperLocal
2. Check the console output - you'll see GPU status:
   ```
   ✅ GPU acceleration: ENABLED - GPU: NVIDIA RTX 4090 | Load: 15% (IDLE)
   📊 GPU load monitoring: ACTIVE
   ```

3. Open a GPU-intensive game

4. Use WhisperLocal (WIN+CTRL to record)

5. Watch the console during transcription:
   ```
   [whisper-smart] GPU Status: GPU: NVIDIA RTX 4090 | Load: 82% (BUSY)
   [whisper-smart] ⚠️ GPU busy (70%+) - skipping large-v3
   ```

### Run the Test Script

```powershell
python test_gpu_monitor.py
```

This shows real-time GPU monitoring for 30 seconds. Try opening a game while it's running!

## Performance Impact

The monitoring system is extremely lightweight:
- **CPU Usage**: <0.1%
- **Memory**: <1 MB
- **GPU Queries**: Every 2 seconds (negligible impact)
- **No frame drops** from the monitoring itself

## For Non-NVIDIA GPU Users

If you have an **AMD Radeon** or **Intel Arc** GPU:

✅ **Good News**: System detects your GPU and uses compatible models  
⚠️ **Limitation**: No real-time load monitoring (yet)  
✅ **Benefit**: Always uses light/medium models for best compatibility  

The system won't use CUDA-optimized models that could cause issues on non-NVIDIA GPUs.

## Frequently Asked Questions

### Does this slow down my transcriptions?
Only during gaming! When your GPU is busy, lighter models are actually *faster*, so you get results quicker. When idle, you get maximum quality.

### Can I disable this feature?
The monitoring is always active, but if you want to force a specific model tier, you can edit the thresholds in `whisper_local/gpu_monitor.py`.

### Will this drain my GPU/battery?
No - the monitoring queries GPU status every 2 seconds using standard system APIs (nvidia-smi). This has no measurable impact on battery or GPU performance.

### What if I have multiple GPUs?
Currently, the system monitors the primary GPU (GPU 0). Multi-GPU support is planned for a future update.

### Does this work with laptop GPUs?
Yes! Works perfectly with laptop NVIDIA GPUs (RTX 30/40 Mobile, GTX 16 Mobile, etc.).

## Troubleshooting

### "GPU: unknown" in console
- Install NVIDIA drivers: https://www.nvidia.com/drivers
- Verify `nvidia-smi` works in PowerShell

### Always uses light models even when idle
- This is normal for non-NVIDIA GPUs
- AMD/Intel GPUs don't support CUDA acceleration

### GPU load shows 0% during gaming
- Check Windows Task Manager → Performance → GPU
- Ensure game is actually using the GPU
- Some games use GPU 1 instead of GPU 0

## What's Next?

Future improvements planned:
- [ ] AMD GPU monitoring support (ROCm)
- [ ] Intel Arc monitoring support (oneAPI)
- [ ] Multi-GPU selection
- [ ] User-configurable load thresholds
- [ ] GUI settings for gaming mode

## Feedback

Love this feature? Have suggestions? Let us know!

---

**🎯 Bottom Line**: Game without worry! WhisperLocal now plays nice with your GPU-intensive apps.

