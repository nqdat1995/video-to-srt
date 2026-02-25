# Parameter Tuning Guide (Hướng dẫn tối ưu hóa)

## 26 Tunable Parameters

| # | Category | Parameter | Type | Default | Range | Description |
|---|----------|-----------|------|---------|-------|-------------|
| **INPUT** | | | | | | |
| 1 | Input | `video` | string | - | path | Đường dẫn video trên server (**required**) |
| **SAMPLING & ROI** | | | | | | |
| 2 | Sampling | `target_fps` | float | 4.0 | 0.1-30.0 | Tỷ lệ frame được lấy mẫu từ video |
| 3 | | `bottom_start` | float | 0.55 | 0.0-1.0 | Phần trăm chiều cao bắt đầu ROI |
| 4 | | `max_width` | int | 1280 | 320-3840 | Chiều rộng max sau scale |
| 5 | | `enhance` | bool | true | T/F | Bật CLAHE (Contrast enhancement) |
| **OCR CONFIG** | | | | | | |
| 6 | OCR | `lang` | string | "vi" | "vi","en","zh","ja" | Mã ngôn ngữ |
| 7 | | `device` | string | "cpu" | "cpu","gpu:0","gpu:1" | Device xử lý OCR |
| 8 | | `det_model` | string | "PP-OCRv5_mobile_det" | model | Text detection model |
| 9 | | `rec_model` | string | "PP-OCRv5_mobile_rec" | model | Text recognition model |
| 10 | | `use_textline_orientation` | bool | false | T/F | Detect & xử lý text xoay |
| 11 | | `conf_min` | float | 0.5 | 0.0-1.0 | Confidence threshold |
| **FRAME GATING** | | | | | | |
| 12 | Frame Gate | `hash_dist_thr` | int | 6 | 0-64 | Hamming distance threshold |
| 13 | | `content_change_thr` | float | 0.12 | 0.0-1.0 | Content change threshold |
| 14 | | `text_motion_thr` | float | 0.08 | 0.0-1.0 | Text motion threshold |
| 15 | | `text_presence_thr` | float | 0.30 | 0.0-1.0 | Text presence threshold |
| 16 | | `intensity_spike_thr` | float | 0.25 | 0.0-1.0 | Intensity spike threshold |
| **SEGMENTATION** | | | | | | |
| 17 | Debounce | `debounce_frames` | int | 2 | 1-10 | Confirm frames for text change |
| 18 | | `empty_debounce_frames` | int | 2 | 1-10 | Confirm frames for empty |
| 19 | | `sim_thr` | float | 0.90 | 0.5-1.0 | Similarity threshold |
| **SRT CLEANUP** | | | | | | |
| 20 | Cleanup | `min_duration_ms` | int | 400 | 0-5000 | Minimum subtitle duration |
| 21 | | `merge_gap_ms` | int | 250 | 0-3000 | Gap to merge cues |
| **OUTPUT** | | | | | | |
| 22 | Output | `output_path` | string | null | path | Save .srt file |
| 23 | | `prefer_subtitle_stream` | bool | false | T/F | Use embedded subtitles |
| **ADVANCED** | | | | | | |
| 24 | Model | `det_model_v3` | string | auto | - | (Future use) |
| 25 | | `rec_model_v3` | string | auto | - | (Future use) |
| 26 | | (reserved) | - | - | - | Reserved for future |

## Parameter Impact on Processing Pipeline

```
STEP 1: VIDEO INPUT → STEP 2: FRAME SAMPLING
├─ target_fps: Số frame được OCR (ảnh hưởng tổng thời gian)
├─ bottom_start: Vùng OCR (quyết định độ chính xác)
└─ max_width: Scale size (tốc độ vs chất lượng)

STEP 3: PREPROCESSING → STEP 4: FRAME GATING
├─ enhance: CLAHE tăng contrast
├─ hash_dist_thr: Skip frame giống (tiết kiệm 60-80% OCR)
├─ content_change_thr: Detect text changes
└─ text_motion_thr: Detect text moving

STEP 5: OCR EXECUTION → STEP 6: TEXT ASSEMBLY
├─ lang: Chọn model
├─ device: CPU/GPU (3-4x khác nhau)
├─ conf_min: Loại bỏ text thấp confidence
├─ debounce_frames: Ổn định output
└─ sim_thr: Fuzzy matching

STEP 7: SRT CLEANUP → STEP 8: OUTPUT
├─ min_duration_ms: Loại short subtitles
├─ merge_gap_ms: Merge liền kề
└─ output_path: Save file
```

## Speed vs Accuracy Trade-off

### Fast Mode (30-45s cho 5 phút video)

```python
{
    "target_fps": 2.0,          # Ít frame
    "max_width": 640,           # Nhỏ
    "hash_dist_thr": 10,        # Skip nhiều
    "debounce_frames": 1,       # Ít confirm
    "min_duration_ms": 800,     # Loại short
    "device": "gpu:0"           # GPU nếu có
}
```

### Balanced Mode (1-2 phút cho 5 phút video)

```python
{
    "target_fps": 4.0,          # Mặc định
    "max_width": 1280,          # Mặc định
    "hash_dist_thr": 6,         # Mặc định
    "debounce_frames": 2,       # Mặc định
    "min_duration_ms": 400,     # Mặc định
    "device": "gpu:0"           # GPU nếu có
}
```

### Slow/Accurate Mode (2-3 phút cho 5 phút video)

```python
{
    "target_fps": 8.0,          # Nhiều frame
    "max_width": 1920,          # Full res
    "hash_dist_thr": 2,         # Skip ít
    "debounce_frames": 3,       # Nhiều confirm
    "min_duration_ms": 200,     # Keep short subs
    "device": "gpu:0",          # GPU strongly recommended
    "enhance": True
}
```

## Stability vs Detection

### Stable Mode (ít false positive)

```python
{
    "debounce_frames": 3,           # Delay xác nhận
    "empty_debounce_frames": 3,     # Delay kết thúc
    "sim_thr": 0.95,                # Exact match
    "content_change_thr": 0.20,     # Bỏ small changes
    "merge_gap_ms": 500             # Merge aggressive
}
```

### Sensitive Mode (detect mọi thay đổi)

```python
{
    "debounce_frames": 1,           # Nhanh xác nhận
    "empty_debounce_frames": 1,     # Nhanh kết thúc
    "sim_thr": 0.80,                # Fuzzy match
    "content_change_thr": 0.05,     # Detect mọi changes
    "merge_gap_ms": 100             # Merge ít
}
```

## Real-World Scenarios

| Scenario | Configuration | Tại sao |
|----------|---|---------|
| **Fast subtitle extraction** | `target_fps=1.5, max_width=640, hash_dist_thr=10, prefer_subtitle_stream=true` | Minimize frame processing |
| **High accuracy extraction** | `target_fps=8, max_width=1920, enhance=true, conf_min=0.7` | Maximize OCR coverage |
| **Noisy video (anime/cartoon)** | `debounce_frames=3, sim_thr=0.85, content_change_thr=0.15` | Smooth flickering text |
| **Clean video (news/subtitles)** | `debounce_frames=1, sim_thr=0.95, conf_min=0.6` | Detect every change quickly |
| **Limited resources (CPU only)** | `target_fps=2, max_width=640, hash_dist_thr=8, device=cpu` | Balance speed/accuracy |
| **High-end GPU available** | `target_fps=6, max_width=1920, debounce_frames=2, device=gpu:0` | Leverage GPU power |
| **With embedded subtitles** | `prefer_subtitle_stream=true` | Use ffmpeg fast-path (20x faster) |
| **Multiple languages** | `lang=en/zh/ja, use_textline_orientation=true` | Auto-select appropriate model |

## Performance Calculation Examples

### Example 1: Processing Time Estimation

```
Input: 10 minute video, 30fps
Parameters:
  - target_fps = 4.0
  - device = gpu:0

Calculation:
1. Total frames = 10 * 60 * 30 = 18,000 frames
2. Sampled frames = 18,000 / (30 / 4) = 2,400 frames
3. Hash gating skip (~70%) = 720 frames to OCR
4. GPU speed: ~1 frame/50ms = 36 frames/sec

Estimated time:
  - Frame decoding: 24 seconds
  - OCR processing: 20 seconds
  - Total: ~45-60 seconds
```

### Example 2: ROI Calculation

```
Input: 1080p video (1920x1080)
Parameters:
  - bottom_start = 0.55
  - max_width = 1280

Calculation:
1. Active region height = 1080 * 0.45 = 486 pixels
2. After scale: 1280 x 320 pixels
3. OCR area = 1280 * 320 = 409,600 pixels (~21% of original)

Speed benefit: ~79% faster image processing
```

### Example 3: Hash Gating Effect

```
Video: 30fps, 10 minutes = 18,000 frames
target_fps=4 → sample 2,400 frames

Without hash gating:
- OCR all 2,400 frames
- Time: 120 seconds (GPU)

With hash_dist_thr=6:
- OCR ~700 frames (static scenes skipped)
- Time: 35 seconds (GPU)
- Speedup: 3.4x on GPU!
```

## Parameter Dependencies

**FPS + Hash Gating**
- Low FPS + High Hash Thr = Very fast but may miss subtitles
- High FPS + Low Hash Thr = Slower but more accurate

**ROI + Accuracy**
- Small ROI (bottom_start=0.55) + Small width (640) = Fast but lower quality
- Full ROI (bottom_start=0.0) + Full width (1920) = Slow but more accurate

**Confidence + Debouncing**
- Low conf_min (0.5) + Low debounce (1) = Many false positives
- High conf_min (0.8) + High debounce (3) = Clean output but may miss text

**Merge + Similarity**
- Short merge_gap + High sim_thr = Few merges, fragmented
- Long merge_gap + Low sim_thr = Many merges, clean output

## Tips for Optimization

1. **Start with defaults** - Most videos work well with default settings
2. **Test with small segment** - Use short video section to tune parameters
3. **Prioritize your use case** - Speed or accuracy?
4. **Use GPU if available** - 3-4x faster than CPU
5. **Monitor frame statistics** - Check `stats` output to understand what's happening
6. **Iterate gradually** - Change one parameter at a time
7. **Document your settings** - Save configs for specific video types

## Testing Your Configuration

```python
import requests
from pathlib import Path

# Test with a short video snippet
response = requests.post(
    "http://localhost:8000/extract-srt",
    json={
        "video": "test_clip.mp4",  # 30 second test video
        "lang": "vi",
        "target_fps": 4.0,
        # ... your other parameters ...
    }
)

result = response.json()
stats = result["stats"]

print(f"Total time: {stats['timing_ms']['total']}ms")
print(f"Frames OCR'd: {stats['frames_ocr']}")
print(f"Subtitle cues: {stats['cues']}")
print(f"Quality: {len(result['srt_detail'])} details")
```

Use this to fine-tune before processing full videos.
