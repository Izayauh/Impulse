# GPU Load Detection - Visual Guide

## How It Works: Before vs After

### ❌ BEFORE (Without Load Detection)

```
You're gaming:
┌─────────────────────────────────────┐
│  Your Game                          │
│  GPU: ████████████████████ 80%      │
│  VRAM: 6GB / 8GB                    │
└─────────────────────────────────────┘

You press WIN+CTRL to dictate...

WhisperLocal:
"I'll use the large-v3 model for best quality!"

Result:
┌─────────────────────────────────────┐
│  Your Game                          │
│  GPU: ███████████████████████ 95%   │ ⚠️ OVERLOADED!
│  VRAM: 7.8GB / 8GB                  │ ⚠️ ALMOST FULL!
│  FPS: 45 → 25                       │ ⚠️ STUTTERING!
└─────────────────────────────────────┘

😡 Bad experience - game stutters!
```

### ✅ AFTER (With Load Detection)

```
You're gaming:
┌─────────────────────────────────────┐
│  Your Game                          │
│  GPU: ████████████████████ 80%      │
│  VRAM: 6GB / 8GB                    │
└─────────────────────────────────────┘

You press WIN+CTRL to dictate...

WhisperLocal:
"⚠️ GPU is busy at 80%!"
"I'll use the base.en model instead!"

Result:
┌─────────────────────────────────────┐
│  Your Game                          │
│  GPU: █████████████████████ 82%     │ ✅ Barely increased
│  VRAM: 6.1GB / 8GB                  │ ✅ Plenty of room
│  FPS: 45 → 44                       │ ✅ Smooth!
└─────────────────────────────────────┘

😊 Good experience - game stays smooth!
```

## Model Selection Chart

```
GPU Load:  0%      25%     50%     70%     85%     100%
           |-------|-------|-------|-------|-------|
           └──────IDLE──────┘       │       │
                           └──BUSY──┤       │
                                    └─CRITICAL─┘

Models Available:

IDLE       [base.en] [medium.en] [large-v3]  ← All available
(0-69%)    ⚡ Fast    ⚡⚡ Medium   🎯 Best

BUSY       [base.en] [medium.en]  ✗          ← Skip large-v3
(70-84%)   ⚡ Fast    ⚡⚡ Medium

CRITICAL   [base.en]  ✗            ✗          ← Base only
(85-100%)  ⚡ Fast
```

## Real-World Examples

### Example 1: Desktop Work → Gaming

```
Timeline:

10:00 AM - Working on document
┌─────────────────────────────┐
│ GPU: ██ 5% (IDLE)            │
│ Model: large-v3 (best)       │
│ Quality: ★★★★★               │
└─────────────────────────────┘

3:00 PM - Launch game
┌─────────────────────────────┐
│ GPU: ████████████████ 75%    │ ← AUTO-DETECTED
│ Model: medium.en (faster)    │ ← AUTO-SWITCHED
│ Quality: ★★★★                │
└─────────────────────────────┘

4:30 PM - Intense boss fight
┌─────────────────────────────┐
│ GPU: ██████████████████ 92%  │ ← CRITICAL LOAD
│ Model: base.en (fastest!)    │ ← SAFETY MODE
│ Quality: ★★★                 │
└─────────────────────────────┘

5:00 PM - Close game
┌─────────────────────────────┐
│ GPU: ██ 5% (IDLE)            │ ← BACK TO NORMAL
│ Model: large-v3 (best)       │ ← FULL QUALITY
│ Quality: ★★★★★               │
└─────────────────────────────┘
```

### Example 2: AMD GPU User

```
Your Setup:
┌─────────────────────────────────┐
│ GPU: AMD Radeon RX 6800 XT      │
│ Type: Non-NVIDIA                │
└─────────────────────────────────┘

System behavior:
┌─────────────────────────────────┐
│ Status: AMD GPU Detected        │
│ Decision: Use compatible models │
│ Available:                      │
│   ✅ base.en                    │
│   ✅ medium.en                  │
│   ❌ large-v3 (CUDA-only)       │
└─────────────────────────────────┘

No load monitoring needed!
AMD GPUs always use safe models.
```

## Quick Reference Table

| Your Situation | GPU Load | Model Used | Why? |
|----------------|----------|------------|------|
| Writing email | 5% | large-v3 | Quality matters, GPU idle |
| Web browsing | 15% | large-v3 | Plenty of resources |
| Video editing | 45% | large-v3 or medium.en | Moderate load, still room |
| Gaming | 75% | medium.en | Busy GPU, skip heavy model |
| Intense gaming | 90% | base.en | Critical load, speed only |
| 3D rendering | 99% | base.en | Maximum GPU usage |

## Console Messages You'll See

### Normal Operation (Idle)
```
[whisper-smart] GPU Status: GPU: RTX 2070 | Load: 12% (IDLE)
[whisper-smart] ✅ GPU available with low load - full quality mode
[whisper-smart] GPU mode: threshold_base=25, use_large=True
```

### Gaming (Busy)
```
[whisper-smart] GPU Status: GPU: RTX 2070 | Load: 76% (BUSY)
[whisper-smart] ⚠️ GPU busy (70%+) - skipping large-v3
[whisper-smart] GPU-BUSY mode: threshold_base=50, use_large=False
```

### Intense Gaming (Critical)
```
[whisper-smart] GPU Status: GPU: RTX 2070 | Load: 92% (CRITICAL)
[whisper-smart] ⚠️ GPU under critical load (85%+) - using base.en only
[whisper-smart] GPU-CRITICAL mode: threshold_base=999999, use_large=False
```

## What This Means For You

### ✅ Benefits

1. **Seamless Gaming**
   - No frame drops from AI processing
   - Automatic adaptation to game load
   - No manual configuration needed

2. **Better Performance**
   - Lighter models = faster results when busy
   - No GPU memory conflicts
   - Stable frame rates

3. **Smart Quality**
   - Best quality when you have resources
   - Speed prioritized when you need it
   - Always appropriate for the situation

### 🎮 Gaming Tips

- **Don't worry about hotkeys** - Use WhisperLocal normally even while gaming
- **No configuration needed** - System auto-detects everything
- **Works with any game** - As long as it uses the GPU, it's detected
- **VR compatible** - Even works with VR gaming (high GPU load)

### 💡 Pro Tips

1. **Streaming**: System detects OBS/streaming GPU load too
2. **Video Editing**: Lighter models during rendering
3. **Machine Learning**: Respects your training workloads
4. **Multi-tasking**: Adapts to combined GPU usage

## Technical Thresholds

```python
# You can customize these in whisper_local/gpu_monitor.py

HIGH_LOAD_THRESHOLD = 70      # Start using lighter models
CRITICAL_LOAD_THRESHOLD = 85  # Use fastest model only

# Model selection in flow_local_dictation.py

WORD_THRESHOLD_BASE = 25      # Switch from base to medium
WORD_THRESHOLD_MEDIUM = 75    # Switch from medium to large
```

## Supported GPUs

### ✅ Full Support (Real-time Monitoring)
- NVIDIA GeForce RTX 40 series (4090, 4080, 4070...)
- NVIDIA GeForce RTX 30 series (3090, 3080, 3070...)
- NVIDIA GeForce RTX 20 series (2080 Ti, 2070...)
- NVIDIA GeForce GTX 16 series (1660 Ti, 1650...)
- NVIDIA Quadro / Tesla / A-series
- **Any GPU with nvidia-smi support**

### ⚠️ Detection Only (No Monitoring Yet)
- AMD Radeon RX 7000 series
- AMD Radeon RX 6000 series
- Intel Arc A-series
- *Will use safe light/medium models always*

### ❌ Not Supported
- Integrated graphics (Intel UHD, AMD Vega)
- *Will use CPU mode*

## Questions?

**Q: Will this slow down my transcriptions?**  
A: Actually no! When GPU is busy, lighter models are FASTER. You get results quicker during gaming.

**Q: Can I disable this?**  
A: It's always active, but you can adjust thresholds in the code if needed.

**Q: What if I have multiple GPUs?**  
A: Currently monitors primary GPU (GPU 0). Multi-GPU support planned.

**Q: Does this work on laptops?**  
A: Yes! Fully supports laptop NVIDIA GPUs.

**Q: How much overhead does monitoring add?**  
A: < 0.1% CPU, negligible impact.

---

**Visual Summary**: 🎮 Game smoothly + 🎤 Dictate freely = 😊 Happy user!

