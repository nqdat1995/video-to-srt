# Video Processing APIs (Xử lý Video)

## Blur Original Subtitles

Làm mờ phụ đề gốc trong video (trước khi thêm phụ đề mới)

### cURL Example

```bash
curl -X POST "http://localhost:8000/blur" \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "uploads/video.mp4",
    "srt_detail": [
      {"x1": 100, "y1": 950, "x2": 1820, "y2": 1050},
      {"x1": 150, "y1": 900, "x2": 1800, "y2": 950}
    ],
    "blur_strength": 25,
    "output_suffix": "blurred",
    "use_gpu": true
  }'

# Response: {"status": "success", "data": {...}}
```

### Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `video_path` | string | - | path | Đường dẫn video |
| `srt_detail` | array | - | coords | Danh sách region blur: `[{x1, y1, x2, y2}, ...]` |
| `blur_strength` | int | 25 | 1-100 | Độ mạnh blur (1=nhẹ, 100=rất mạnh) |
| `output_suffix` | string | "blurred" | string | Hậu tố filename output |
| `use_gpu` | bool | true | true/false | GPU acceleration (nhanh 2-3x) |

## Add Subtitles to Video

Thêm phụ đề SRT vào video

### cURL Example

```bash
curl -X POST "http://localhost:8000/subtitle" \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "uploads/video.mp4",
    "srt_path": "uploads/output.srt",
    "output_suffix": "subtitled",
    "use_gpu": true
  }'

# Response: {"status": "success", "data": {...}}
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `video_path` | string | - | Đường dẫn video |
| `srt_path` | string | - | Đường dẫn file SRT |
| `output_suffix` | string | "subtitled" | Hậu tố filename output |
| `use_gpu` | bool | true | GPU acceleration |

## Blur and Add Subtitles (Combined)

Kết hợp blur + subtitle (tối ưu: 1 lần encode video thay vì 2 lần)

### cURL Example

```bash
curl -X POST "http://localhost:8000/blur-and-subtitle" \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "uploads/video.mp4",
    "srt_path": "uploads/output.srt",
    "srt_detail": [
      {"x1": 100, "y1": 950, "x2": 1820, "y2": 1050}
    ],
    "blur_strength": 25,
    "output_suffix": "vnsrt",
    "use_gpu": true
  }'

# Response: {"status": "success", "data": {...}}
```

### Parameters

Combine all blur + subtitle parameters above.

### Performance Advantage

- Separate blur + subtitle: 2x video encoding = slow
- Combined: 1x video encoding = 2x faster

## Complete Blur + Subtitle Workflow

```python
import requests
from pathlib import Path

# Step 1: Extract subtitles from video
print("Step 1: Extracting subtitles...")
extract_resp = requests.post(
    "http://localhost:8000/extract-srt",
    json={"video": "video.mp4", "lang": "vi"}
)
srt_content = extract_resp.json()["srt"]
srt_detail = extract_resp.json()["srt_detail"]

# Save SRT
Path("extracted.srt").write_text(srt_content, encoding="utf-8")

# Step 2: Blur original subtitles + add new subtitles
print("Step 2: Blurring original + adding new subtitles...")
process_resp = requests.post(
    "http://localhost:8000/blur-and-subtitle",
    json={
        "video_path": "video.mp4",
        "srt_path": "extracted.srt",
        "srt_detail": [
            {"x1": s["x1"], "y1": s["y1"], "x2": s["x2"], "y2": s["y2"]}
            for s in srt_detail
        ],
        "blur_strength": 30,
        "output_suffix": "vnsrt"
    }
)

print(f"✓ Done! Output: {process_resp.json()['data']['output_path']}")
```

## Python Client Examples

### Extract and Blur Workflow

```python
import requests

# Extract subtitles (with coordinates)
extract_resp = requests.post(
    "http://localhost:8000/extract-srt",
    json={"video": "original_video.mp4", "lang": "vi"}
)

srt_detail = extract_resp.json()["srt_detail"]
srt_content = extract_resp.json()["srt"]

# Blur original subtitles
blur_resp = requests.post(
    "http://localhost:8000/blur",
    json={
        "video_path": "original_video.mp4",
        "srt_detail": [
            {"x1": s["x1"], "y1": s["y1"], "x2": s["x2"], "y2": s["y2"]}
            for s in srt_detail
        ],
        "blur_strength": 25,
        "output_suffix": "blurred"
    }
)

blurred_video = blur_resp.json()["data"]["output_path"]

# Add new subtitles
subtitle_resp = requests.post(
    "http://localhost:8000/subtitle",
    json={
        "video_path": blurred_video,
        "srt_path": "extracted.srt",
        "output_suffix": "final"
    }
)

output_video = subtitle_resp.json()["data"]["output_path"]
print(f"Final output: {output_video}")
```

## API Response Format

### Blur Response

```json
{
  "status": "success",
  "data": {
    "input_path": "original.mp4",
    "output_path": "original_blurred.mp4",
    "blur_strength": 25,
    "regions_blurred": 5,
    "processing_time_ms": 45000
  }
}
```

### Subtitle Response

```json
{
  "status": "success",
  "data": {
    "input_path": "video.mp4",
    "srt_path": "subtitles.srt",
    "output_path": "video_subtitled.mp4",
    "cues_added": 150,
    "processing_time_ms": 60000
  }
}
```

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Video not found | Invalid video_path | Check file exists |
| SRT not found | Invalid srt_path | Check file exists |
| Invalid coordinates | x1,y1,x2,y2 out of bounds | Use coordinates from extract-srt |
| GPU out of memory | Video too large | Use CPU or reduce video resolution |
| Encoding error | Unsupported video codec | Re-encode video to H.264 MP4 |

See [TROUBLESHOOTING.md](09-TROUBLESHOOTING.md) for detailed solutions.
