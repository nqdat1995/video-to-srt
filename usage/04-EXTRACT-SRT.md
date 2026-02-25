# Extract SRT Subtitles (Trích xuất SRT)

## Basic Health Check

```bash
curl http://localhost:8000/health

# Response: {"status": "ok"}
```

## 1. Synchronous Extraction (Blocking)

### cURL Example

```bash
curl -X POST "http://localhost:8000/extract-srt" \
  -H "Content-Type: application/json" \
  -d '{
    "video": "uploads/sample.mp4",
    "lang": "vi",
    "device": "cpu",
    "target_fps": 4.0,
    "conf_min": 0.5
  }'

# Response:
# {
#   "srt": "1\n00:00:01,000 --> 00:00:05,000\nSubtitle text\n\n...",
#   "srt_detail": [
#     {
#       "srt": "Subtitle text",
#       "srt_time": "00:00:01,000 --> 00:00:05,000",
#       "x1": 100, "y1": 950, "x2": 1820, "y2": 1050
#     }
#   ],
#   "stats": {
#     "mode": "ocr",
#     "frames_seen": 7200,
#     "frames_sampled": 1200,
#     "frames_hashed_skipped": 800,
#     "frames_ocr": 400,
#     "cues": 150,
#     "timing_ms": {...}
#   }
# }
```

### Python Client

```python
import requests

response = requests.post(
    "http://localhost:8000/extract-srt",
    json={
        "video": "uploads/sample.mp4",
        "lang": "vi",
        "device": "cpu",
        "target_fps": 4.0,
        "conf_min": 0.5
    }
)

data = response.json()
srt_content = data["srt"]
srt_detail = data["srt_detail"]  # Include coordinates
stats = data["stats"]

print(f"Extracted {len(srt_detail)} subtitle blocks")
print(f"Time taken: {stats['timing_ms']['total']/1000:.2f}s")

# Save to file
with open("output.srt", "w", encoding="utf-8") as f:
    f.write(srt_content)
```

## 2. Full-FPS Extraction

Process OCR on every sampled frame and merge consecutive identical text:

```bash
curl -X POST "http://localhost:8000/extract-srt-frames" \
  -H "Content-Type: application/json" \
  -d '{
    "video": "uploads/sample.mp4",
    "lang": "vi",
    "device": "cpu",
    "target_fps": 4.0,
    "conf_min": 0.5
  }'

# Response structure identical to /extract-srt
```

## 3. Asynchronous Extraction (Non-blocking)

### Start Task

```bash
curl -X POST "http://localhost:8000/extract-srt-async" \
  -H "Content-Type: application/json" \
  -d '{
    "video": "uploads/long_video.mp4",
    "lang": "vi",
    "device": "cpu"
  }'

# Response: {"task_id": "abc123...", "status": "processing", "message": "Task started..."}
```

### Check Status

```bash
curl "http://localhost:8000/task/abc123..."

# Response:
# {
#   "task_id": "abc123...",
#   "status": "processing",  # or "completed", "failed"
#   "progress": 0.45,
#   "result": {...},  # When completed
#   "error": null
# }
```

### Cancel Task

```bash
curl -X DELETE "http://localhost:8000/task/abc123..."

# Response: {"message": "Task deleted"}
```

### Python Client - With Progress

```python
import requests
import time

# Start task
response = requests.post(
    "http://localhost:8000/extract-srt-async",
    json={
        "video": "uploads/long_video.mp4",
        "lang": "vi",
        "device": "cpu"
    }
)

task_id = response.json()["task_id"]
print(f"Task started: {task_id}")

# Poll for progress
while True:
    status_response = requests.get(f"http://localhost:8000/task/{task_id}")
    task_data = status_response.json()
    
    if task_data["status"] == "processing":
        progress = task_data.get("progress", 0) * 100
        print(f"Progress: {progress:.1f}%", end="\r")
        time.sleep(1)
    
    elif task_data["status"] == "completed":
        print(f"\nCompleted!")
        srt_content = task_data["result"]["srt"]
        with open("output.srt", "w", encoding="utf-8") as f:
            f.write(srt_content)
        break
    
    elif task_data["status"] == "failed":
        print(f"\nFailed: {task_data['error']}")
        break

# Cleanup
requests.delete(f"http://localhost:8000/task/{task_id}")
```

## 4. Batch Processing

```python
import requests
from pathlib import Path

video_dir = Path("uploads")
videos = list(video_dir.glob("*.mp4"))

for video_file in videos:
    print(f"Processing {video_file.name}...")
    
    response = requests.post(
        "http://localhost:8000/extract-srt",
        json={
            "video": str(video_file),
            "lang": "vi",
            "device": "cpu"
        }
    )
    
    if response.status_code == 200:
        srt_content = response.json()["srt"]
        output_path = video_file.with_suffix(".srt")
        output_path.write_text(srt_content, encoding="utf-8")
        print(f"  -> {output_path}")
    else:
        print(f"  -> Error: {response.text}")
```

## 5. Using Embedded Subtitles (Fast-path)

```bash
curl -X POST "http://localhost:8000/extract-srt" \
  -H "Content-Type: application/json" \
  -d '{
    "video": "video_with_subtitles.mp4",
    "prefer_subtitle_stream": true
  }'
```

If the video has embedded subtitles, this uses ffmpeg (20x faster) instead of OCR.

## Configuration Parameters

### Quick Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `video` | string | - | Path to video file (required) |
| `lang` | string | "vi" | Language: vi, en, zh, ja |
| `device` | string | "cpu" | cpu or gpu:0 |
| `target_fps` | float | 4.0 | Sampling rate (0.1-30.0) |
| `conf_min` | float | 0.5 | Confidence threshold (0.0-1.0) |
| `enhance` | bool | true | Enable CLAHE enhancement |
| `bottom_start` | float | 0.55 | ROI start (0.0-1.0) |
| `max_width` | int | 1280 | Max frame width (320-3840) |
| `debounce_frames` | int | 2 | Stability frames (1-10) |
| `merge_gap_ms` | int | 250 | Merge gap threshold (0-3000) |
| `min_duration_ms` | int | 400 | Min subtitle duration (0-5000) |
| `prefer_subtitle_stream` | bool | false | Use embedded subtitles if available |

See [04-PARAMETER-TUNING.md](04-PARAMETER-TUNING.md) for detailed parameter guide.

## Common Configurations

### Fast Mode (Speed Priority)

```python
response = requests.post(
    "http://localhost:8000/extract-srt",
    json={
        "video": "video.mp4",
        "lang": "vi",
        "device": "gpu:0",  # GPU 3-4x faster
        "target_fps": 2.0,
        "max_width": 640,
        "hash_dist_thr": 10,
        "min_duration_ms": 1000,
        "merge_gap_ms": 500
    }
)
```

### Accurate Mode (Quality Priority)

```python
response = requests.post(
    "http://localhost:8000/extract-srt",
    json={
        "video": "video.mp4",
        "lang": "vi",
        "target_fps": 8.0,
        "max_width": 1920,
        "enhance": True,
        "conf_min": 0.7,
        "debounce_frames": 3,
        "min_duration_ms": 200
    }
)
```

### Balanced Mode (Recommended)

```python
response = requests.post(
    "http://localhost:8000/extract-srt",
    json={
        "video": "video.mp4",
        "lang": "vi",
        "device": "gpu:0" if <gpu_available> else "cpu",
        "target_fps": 4.0,
        "max_width": 1280,
        "enhance": True,
        "conf_min": 0.5,
        "debounce_frames": 2,
        "merge_gap_ms": 250,
        "min_duration_ms": 400
    }
)
```

## Performance Benchmarks

| Duration | Device | FPS | Time | Notes |
|----------|--------|-----|------|-------|
| 1 minute | CPU | 4.0 | 30-45s | Single-threaded |
| 1 minute | GPU | 4.0 | 10-15s | NVIDIA GTX 1060 |
| 10 minutes | CPU | 2.0 | 3-5 min | Reduced FPS |
| 10 minutes | GPU | 6.0 | 1-2 min | Higher FPS |

*Times vary based on video resolution and content complexity*
