# Usage Guide (Hướng dẫn sử dụng)

## Table of Contents
1. [Installation (Cài đặt)](#installation)
2. [Running the Server (Chạy Server)](#running-server)
3. [Docker Deployment (Triển khai Docker)](#docker-deployment)
4. [API Examples (Ví dụ API)](#api-examples)
5. [Configuration (Cấu hình)](#configuration)
6. [Troubleshooting (Xử lý Sự cố)](#troubleshooting)

## Installation

### Prerequisites
- Python 3.10+
- FFmpeg installed and in system PATH
- (Optional) NVIDIA GPU with CUDA 12.x for GPU acceleration

### 1. Clone or Download Repository

```bash
cd d:\LEARN\video-to-srt
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

**Option A: Using uv (Recommended - Much Faster)**
```bash
pip install uv
uv pip install -r requirements.txt
```

**Option B: Using pip (Traditional)**
```bash
pip install -r requirements.txt
```

### 4. Install FFmpeg

- **Windows**: Download from https://ffmpeg.org/download.html and add to PATH
- **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
- **macOS**: `brew install ffmpeg`

### 5. Verify Installation

```bash
# Check Python packages
python -c "import paddleocr; import fastapi; print('OK')"

# Check FFmpeg
ffmpeg -version
```

## Running Server

### Development Mode (Auto-reload with uv - Recommended)

```bash
# Fastest option
uv run python run.py
```

### Development Mode (Python direct)

```bash
python run.py
```

### Production Mode (Multiple Workers)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### With Custom Environment Variables

**Windows**:
```bash
set OCR_CACHE_MAX=8
set BATCH_OCR_SIZE=16
set DEFAULT_DEVICE=cpu
python run.py
```

**Linux/macOS**:
```bash
export OCR_CACHE_MAX=8
export BATCH_OCR_SIZE=16
export DEFAULT_DEVICE=cpu
python run.py
```

### Using .env File

```bash
# Create .env file
cp .env.example .env

# Edit .env with your settings
# Then just run
python run.py
```

### Access API

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)
- **Health Check**: http://localhost:8000/health

## Docker Deployment

### Quick Start

**CPU Version** (Default):
```bash
docker-compose up -d video-to-srt

# View logs
docker-compose logs -f video-to-srt

# Access: http://localhost:8000
```

**GPU Version** (Requires NVIDIA GPU):
```bash
docker-compose --profile gpu up -d video-to-srt-gpu

# View logs
docker-compose logs -f video-to-srt-gpu

# Access: http://localhost:8001
```

**Development** (Hot-reload):
```bash
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Access: http://localhost:8000
```

### Stop Services

```bash
docker-compose down
```

### Full Documentation

See [DOCKER.md](DOCKER.md) for complete Docker deployment guide.

## API Examples

### 1. Health Check

```bash
curl http://localhost:8000/health

# Response: {"status": "ok"}
```

### 2. Synchronous Extraction (Blocking)

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

### Synchronous Full-FPS Extraction (Blocking)

This endpoint is like `/extract-srt` but performs OCR on every sampled frame at `target_fps` and merges consecutive frames with identical (or similar above `sim_thr`) OCR text into single SRT cues. It is blocking and returns the same `ExtractResponse` schema. Use when you want exhaustive per-sampled-frame OCR but still rely on textual equivalence to merge cues.

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

# Response structure is identical to `/extract-srt` (SRT text, `srt_detail`, `stats`).
```

Note: This mode does not rely on `hash_dist_thr` to skip OCR calls (OCR runs on every sampled frame). Cue merging is driven by textual similarity (`sim_thr`) across sampled frames.

**Parameters** (26 tunable parameters):

| # | Category | Parameter | Type | Default | Range | Tác động | Description |
|---|----------|-----------|------|---------|-------|---------|-------------|
| **INPUT** | | | | | | | |
| 1 | Input | `video` | string | - | path | - | Đường dẫn video trên server (**required**) |
| **SAMPLING & ROI** | | | | | | | |
| 2 | Sampling | `target_fps` | float | 4.0 | 0.1-30.0 | Speed/Accuracy | Tỷ lệ frame được lấy mẫu từ video. Cao hơn = OCR nhiều frame hơn, chính xác hơn nhưng chậm hơn. VD: 30fps video ÷ target_fps=4.0 = lấy 1 frame mỗi 7.5 frame |
| 3 | | `bottom_start` | float | 0.55 | 0.0-1.0 | Accuracy/Speed | Phần trăm chiều cao bắt đầu ROI (Region Of Interest). 0.55 = bỏ top 55% video, chỉ OCR bottom 45%. Giảm vùng OCR, tăng speed. 0.0 = full frame |
| 4 | | `max_width` | int | 1280 | 320-3840 | Speed/Accuracy | Chiều rộng max sau scale. Frame sẽ scale proportional đến max_width này. Giảm = nhanh hơn nhưng độ chính xác OCR giảm |
| 5 | | `enhance` | bool | true | T/F | Accuracy | Bật CLAHE (Contrast Limited Adaptive Histogram Equalization) trước OCR. Tăng contrast subtitle, giúp OCR chính xác hơn ~5-10% |
| **OCR CONFIG** | | | | | | | |
| 6 | OCR | `lang` | string | "vi" | "vi","en","zh","ja" | Model Selection | Mã ngôn ngữ (auto-select PP-OCRv5 model tối ưu cho ngôn ngữ). Không ảnh hưởng performance, chỉ model được load |
| 7 | | `device` | string | "cpu" | "cpu","gpu:0","gpu:1" | Speed ↑ | Device xử lý OCR. GPU ~3-4x nhanh hơn CPU nhưng cần CUDA. Có thể chỉ định gpu:0, gpu:1, ... |
| 8 | | `det_model` | string | "PP-OCRv5_mobile_det" | model | (Legacy) | Text detection model. V3.x tự động chọn dựa vào `lang`, tham số này giữ cho compatibility |
| 9 | | `rec_model` | string | "PP-OCRv5_mobile_rec" | model | (Legacy) | Text recognition model. V3.x tự động chọn dựa vào `lang`, tham số này giữ cho compatibility |
| 10 | | `use_textline_orientation` | bool | false | T/F | Speed ↓ | Detect & xử lý text xoay (rotated text). Chậm hơn ~10-15%, dùng khi video có text xoay |
| 11 | | `conf_min` | float | 0.5 | 0.0-1.0 | Accuracy | Confidence threshold cho OCR results. Cao hơn = loại bỏ text không confident, giảm false positive nhưng có thể mất một số text |
| **FRAME GATING (Optimization)** | | | | | | | |
| 12 | Frame Gate | `hash_dist_thr` | int | 6 | 0-64 | Speed ↑↑ | Hamming distance threshold. Nếu 2 frame giống nhau (distance < 6), skip OCR frame sau. **Tiết kiệm 60-80% OCR calls**. Tăng = skip nhiều frame |
| 13 | | `content_change_thr` | float | 0.12 | 0.0-1.0 | Stability | Threshold detect thay đổi nội dung text so với frame trước. Low=sensitive (phát hiện small changes), High=stable (bỏ qua small jitter). Ảnh hưởng khi text animation/flashing |
| 14 | | `text_motion_thr` | float | 0.08 | 0.0-1.0 | Speed ↑ | Threshold detect chuyển động/transition của text (text moving on screen). Nếu text đang di chuyển, skip OCR tạm thời. Giảm OCR ~10-20% trong scene transitions |
| 15 | | `text_presence_thr` | float | 0.30 | 0.0-1.0 | Accuracy | Threshold detect thay đổi presence (xuất hiện/mất) của text. High=bỏ qua small presence changes, Low=sensitive tới presence changes |
| 16 | | `intensity_spike_thr` | float | 0.25 | 0.0-1.0 | Stability | Threshold detect intensity spike (sudden brightness changes). Giúp detect scene cuts, flash effects. Low=detect mọi changes, High=chỉ detect mạnh mẽ changes |
| **SEGMENTATION (Debounce/Fuzzy)** | | | | | | | |
| 17 | Debounce | `debounce_frames` | int | 2 | 1-10 | Stability | Số frame liên tiếp confirm khi detect text **thay đổi**. Cao hơn = bỏ false positive (OCR error). VD: =2 → phải confirm text mới 2 lần liên tiếp mới tạo cue mới |
| 18 | | `empty_debounce_frames` | int | 2 | 1-10 | Accuracy | Số frame liên tiếp confirm khi detect **empty/no text**. Cao hơn = ít bỏ subtitle (tránh end-frame mất). VD: =3 → cần 3 empty frame liên tiếp mới close cue |
| 19 | | `sim_thr` | float | 0.90 | 0.5-1.0 | Stability | Similarity threshold cho fuzzy matching. 0.90 = accept text với 90% tương đồng. Low=fuzzy (cho phép typo OCR), High=exact match. Ảnh hưởng độ merge subtitle |
| **SRT CLEANUP** | | | | | | | |
| 20 | Cleanup | `min_duration_ms` | int | 400 | 0-5000 | Quality | Minimum subtitle duration (ms). Loại bỏ cues quá ngắn (< 400ms). Tăng = output sạch hơn nhưng có thể mất short subtitles |
| 21 | | `merge_gap_ms` | int | 250 | 0-3000 | Stability | Max gap (ms) để merge 2 cues liên tiếp. Nếu gap < 250ms và text giống, merge thành 1 cue. Tăng = subtitle ít bị fragmented |
| **OUTPUT** | | | | | | | |
| 22 | Output | `output_path` | string | null | path | - | Đường dẫn save .srt file trên server. Nếu null, chỉ return SRT text (không save) |
| 23 | | `prefer_subtitle_stream` | bool | false | T/F | Speed ↑↑↑ | **Fast-path**: Nếu video có embedded subtitle stream, dùng ffmpeg extract thay vì OCR. **20x nhanh hơn OCR**. Fallback tới OCR nếu không có stream |
| **ADVANCED** | | | | | | | |
| 24 | Model | `det_model_v3` | string | auto | "PP-OCRv5_det" | (Future) | Text detection model v3 (không dùng, auto-select) |
| 25 | | `rec_model_v3` | string | auto | "PP-OCRv5_rec" | (Future) | Text recognition model v3 (không dùng, auto-select) |
| 26 | | (reserved) | - | - | - | - | Reserved cho future expansion |

#### **How Parameters Affect the Processing Pipeline**

```
STEP 1: VIDEO INPUT
├─ video: Đường dẫn video
└─ Tác động: Xác định file xử lý

STEP 2: FRAME SAMPLING (Lấy mẫu)
├─ target_fps: Tỷ lệ lấy mẫu
│  └─ Ví dụ: Video 30fps, target_fps=4 → Lấy 1 frame / 7.5 frame
├─ bottom_start: Vùng ROI (0.55 = bỏ top 55%, keep bottom 45%)
├─ max_width: Scale width xuống (ảnh hưởng speed/accuracy)
└─ Tác động: Quyết định số frame được OCR (ảnh hưởng tổng thời gian)

STEP 3: FRAME PREPROCESSING
├─ enhance: Bật CLAHE contrast enhancement
│  └─ True: Tăng contrast subtitle ±10% accuracy
├─ use_textline_orientation: Detect rotated text
│  └─ True: Chậm hơn ±10%, chính xác với text xoay
└─ Tác động: Chuẩn bị frame trước OCR (tăng quality input)

STEP 4: FRAME GATING (Optimization, tiết kiệm 60-80% OCR)
├─ hash_dist_thr: Skip frame nếu giống frame trước
│  └─ VD: hash_dist_thr=6 → skip khi distance < 6 bits
├─ content_change_thr: Detect text content changes
├─ text_motion_thr: Detect text moving/transition
├─ text_presence_thr: Detect text xuất hiện/mất
├─ intensity_spike_thr: Detect scene cuts/flashes
└─ Tác động: Quyết định frame nào cần OCR (skip nếu không cần)

STEP 5: OCR EXECUTION
├─ lang: Ngôn ngữ (auto-select model)
├─ device: CPU/GPU (GPU 3-4x nhanh)
├─ conf_min: Confidence threshold
│  └─ VD: conf_min=0.5 → loại bỏ text < 50% confidence
├─ (det_model, rec_model: Legacy, tự động select)
└─ Tác động: Chạy OCR trên frame đã select (output: text boxes + scores)

STEP 6: TEXT ASSEMBLY & DEBOUNCING
├─ debounce_frames: Confirm text thay đổi
│  └─ VD: debounce_frames=2 → cần 2 frame liên tiếp confirm
├─ empty_debounce_frames: Confirm empty frame
│  └─ VD: empty_debounce_frames=2 → cần 2 empty frame confirm
├─ sim_thr: Fuzzy matching threshold
│  └─ VD: sim_thr=0.90 → accept 90% similar text
└─ Tác động: Ghép text boxes → subtitle, loại bỏ noise (stable output)

STEP 7: SRT CLEANUP & MERGE
├─ min_duration_ms: Loại bỏ cues quá ngắn (< 400ms)
├─ merge_gap_ms: Merge cues liên tiếp nếu gap < 250ms
└─ Tác động: Làm sạch output, loại bỏ fragmented subtitles

STEP 8: OUTPUT
├─ prefer_subtitle_stream: Fast-path với ffmpeg (20x nhanh)
├─ output_path: Save .srt nếu cung cấp
└─ Tác động: Trả về SRT content + stats
```

#### **Parameter Interaction Patterns**

**Pattern 1: Speed vs Accuracy Trade-off**
```python
# Fast Mode (30-45s cho 5min video)
target_fps=2.0          # Ít frame
max_width=640           # Nhỏ
hash_dist_thr=10        # Skip nhiều
debounce_frames=1       # Ít confirm
min_duration_ms=800     # Loại short subs

# Slow Mode (2-3min cho 5min video)
target_fps=8.0          # Nhiều frame
max_width=1920          # Full res
hash_dist_thr=2         # Skip ít
debounce_frames=3       # Nhiều confirm
min_duration_ms=200     # Keep short subs
```

**Pattern 2: Stability vs Detection**
```python
# Stable Mode (ít false positive)
debounce_frames=3           # Delay xác nhận
empty_debounce_frames=3     # Delay kết thúc
sim_thr=0.95                # Exact match
content_change_thr=0.20     # Bỏ small changes

# Sensitive Mode (detect mọi thay đổi)
debounce_frames=1           # Nhanh xác nhận
empty_debounce_frames=1     # Nhanh kết thúc
sim_thr=0.80                # Fuzzy match
content_change_thr=0.05     # Detect mọi changes
```

**Pattern 3: Quality vs Consistency**
```python
# High Quality (99% accuracy, có thể fragmented)
conf_min=0.8                # Confident only
enhance=true                # CLAHE bật
debounce_frames=1           # Quick detect
min_duration_ms=100         # Keep all subs

# High Consistency (85% accuracy, smooth output)
conf_min=0.5                # Accept more
enhance=true
debounce_frames=2           # Stable
merge_gap_ms=500            # Merge aggressive
min_duration_ms=800         # Remove short subs
```

#### **Real-World Tuning Examples**

| Scenario | Recommendation | Tại sao |
|----------|---|---------|
| **Fast subtitle extraction** | `target_fps=1.5, max_width=640, hash_dist_thr=10, prefer_subtitle_stream=true` | Minimize frame processing |
| **High accuracy extraction** | `target_fps=8, max_width=1920, enhance=true, conf_min=0.7` | Maximize OCR coverage |
| **Noisy video (anime/cartoon)** | `debounce_frames=3, sim_thr=0.85, content_change_thr=0.15` | Smooth flickering text |
| **Clean video (news/subtitles)** | `debounce_frames=1, sim_thr=0.95, conf_min=0.6` | Detect every change quickly |
| **Limited resources (CPU only)** | `target_fps=2, max_width=640, hash_dist_thr=8, device=cpu` | Balance speed/accuracy on CPU |
| **High-end GPU available** | `target_fps=6, max_width=1920, debounce_frames=2, device=gpu:0` | Leverage GPU power |
| **With embedded subtitles** | `prefer_subtitle_stream=true, ...` | Use ffmpeg fast-path (20x faster) |
| **Multiple languages** | `lang=en/zh/ja, use_textline_orientation=true` | Auto-select appropriate model |

### 3. Asynchronous Extraction (Non-blocking with Progress)

**Start task:**
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

**Check status:**
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

**Cancel task:**
```bash
curl -X DELETE "http://localhost:8000/task/abc123..."

# Response: {"message": "Task deleted"}
```

### 4. Python Client - Synchronous

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

### 5. Python Client - Asynchronous with Progress

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
        print(f"\\nCompleted!")
        srt_content = task_data["result"]["srt"]
        with open("output.srt", "w", encoding="utf-8") as f:
            f.write(srt_content)
        break
    
    elif task_data["status"] == "failed":
        print(f"\\nFailed: {task_data['error']}")
        break

# Cleanup
requests.delete(f"http://localhost:8000/task/{task_id}")
```

### 6. Batch Processing

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

### 7. Blur Original Subtitles

**Purpose**: Làm mờ phụ đề gốc trong video (trước khi thêm phụ đề mới)

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

**Parameters**:

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `video_path` | string | - | path | Đường dẫn video |
| `srt_detail` | array | - | coords | Danh sách region blur: `[{x1, y1, x2, y2}, ...]` |
| `blur_strength` | int | 25 | 1-100 | Độ mạnh blur (1=nhẹ, 100=rất mạnh) |
| `output_suffix` | string | "blurred" | string | Hậu tố filename output |
| `use_gpu` | bool | true | true/false | GPU acceleration (nhanh 2-3x) |

### 8. Add Subtitles to Video

**Purpose**: Thêm phụ đề SRT vào video

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

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `video_path` | string | - | Đường dẫn video |
| `srt_path` | string | - | Đường dẫn file SRT |
| `output_suffix` | string | "subtitled" | Hậu tố filename output |
| `use_gpu` | bool | true | GPU acceleration |

### 9. Blur and Add Subtitles (Combined)

**Purpose**: Kết hợp blur + subtitle (tối ưu: 1 lần encode video thay vì 2 lần)

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

**Parameters**: Combine blur + subtitle parameters

**Performance**: 
- Separate blur + subtitle: 2x video encoding (slow)
- Combined: 1x video encoding (2x faster)

### 10. TTS Audio Synthesis

#### 10.1 Generate Audio from SRT Content

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/tts/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "srt_content": "1\n00:00:01,000 --> 00:00:05,000\nHello world\n\n2\n00:00:05,000 --> 00:00:10,000\nHow are you?\n",
    "tts_voice": "BV074_streaming",
    "output_filename": "output_audio.wav",
    "return_base64": true
  }'

# Response:
# {
#   "task_id": "550e8400-e29b...",
#   "status": "success",
#   "audio_filename": "output_audio.wav",
#   "audio_path": "/path/to/tts_output/output_audio.wav",
#   "audio_base64": "UklGRiY...",  # Base64 encoded WAV data
#   "duration_ms": 9000,
#   "size_bytes": 144000,
#   "message": "Audio synthesis completed successfully"
# }
```

**Parameters**:

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `srt_content` | string | - | SRT text | SRT subtitle content (full text) |
| `tts_voice` | string | "BV074_streaming" | voice_id | Voice identifier (BV074, BV104, ...) |
| `output_filename` | string | auto | filename | Output audio filename (e.g., "output.wav") |
| `return_base64` | bool | true | true/false | Return audio as base64 (for client-side download) |

**Available Voices**:
- `BV074_streaming` - Default Vietnamese voice (natural, neutral)
- `BV104_streaming` - Alternative Vietnamese voice (slightly different tone)
- Other voices depend on TTS provider capabilities

#### 10.2 Python Client - TTS Synthesis

```python
import requests
import base64
from pathlib import Path

# Example SRT content
srt_content = """1
00:00:01,000 --> 00:00:05,000
Xin chào thế giới

2
00:00:05,000 --> 00:00:10,000
Bạn khỏe không?
"""

response = requests.post(
    "http://localhost:8000/tts/generate",
    json={
        "srt_content": srt_content,
        "tts_voice": "BV074_streaming",
        "output_filename": "vietnamese_audio.wav",
        "return_base64": True
    }
)

if response.status_code == 200:
    result = response.json()
    print(f"Task ID: {result['task_id']}")
    print(f"Status: {result['status']}")
    print(f"Duration: {result['duration_ms']}ms")
    print(f"File size: {result['size_bytes']} bytes")
    
    # Save audio from base64 if returned
    if result.get("audio_base64"):
        audio_data = base64.b64decode(result["audio_base64"])
        output_file = Path("downloads") / result["audio_filename"]
        output_file.parent.mkdir(exist_ok=True)
        output_file.write_bytes(audio_data)
        print(f"Audio saved to: {output_file}")
    else:
        # Or get from file system
        print(f"Audio file: {result['audio_path']}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

#### 10.3 Advanced TTS Configuration

**Using custom voice and output directory:**
```python
import requests

response = requests.post(
    "http://localhost:8000/tts/generate",
    json={
        "srt_content": open("subtitles.srt").read(),
        "tts_voice": "BV104_streaming",  # Different voice
        "output_filename": "custom_output.wav",
        "return_base64": False  # Don't return base64 for large files
    }
)

result = response.json()
# File available at result["audio_path"]
print(f"Audio file: {result['audio_path']}")
```

#### 10.4 TTS Workflow with SRT Extraction

```python
import requests
import os

# Step 1: Extract SRT from video
extract_resp = requests.post(
    "http://localhost:8000/extract-srt",
    json={
        "video": "video.mp4",
        "lang": "vi"
    }
)
srt_content = extract_resp.json()["srt"]

# Step 2: Generate audio from extracted SRT
tts_resp = requests.post(
    "http://localhost:8000/tts/generate",
    json={
        "srt_content": srt_content,
        "tts_voice": "BV074_streaming",
        "output_filename": "synthesized_audio.wav",
        "return_base64": False
    }
)

audio_path = tts_resp.json()["audio_path"]
print(f"Audio synthesis complete: {audio_path}")

# Step 3: Combine original video + synthesized audio (using ffmpeg)
os.system(f"ffmpeg -i video.mp4 -i {audio_path} -c:v copy -c:a aac output.mp4")
```

### 11. Video Upload with Quota Management

#### 11.1 Upload Video File

**cURL Example:**
```bash
# Upload video and auto-generate user ID
curl -X POST "http://localhost:8000/upload-video" \
  -F "file=@/path/to/video.mp4"

# Upload with specific user ID
curl -X POST "http://localhost:8000/upload-video" \
  -F "file=@/path/to/video.mp4" \
  -F "user_id=user-123"

# Response:
# {
#   "id": "550e8400-e29b-41d4-a716-446655440000",
#   "user_id": "abcd1234-ef56-7890-ghij-klmnopqrstuv",
#   "filename": "video.mp4",
#   "file_size": 1048576,
#   "created_at": "2026-02-25T10:30:45.123456",
#   "status": "success",
#   "message": "Video uploaded successfully. ID: 550e8400-e29b-41d4-a716-446655440000"
# }
```

**Python Client - Single Upload:**
```python
import requests
from pathlib import Path

# Upload video
video_file = Path("video.mp4")
with open(video_file, "rb") as f:
    response = requests.post(
        "http://localhost:8000/upload-video",
        files={"file": f},
        data={"user_id": "user-123"}
    )

if response.status_code == 200:
    result = response.json()
    video_id = result["id"]
    print(f"Video uploaded successfully!")
    print(f"Video ID: {video_id}")
    print(f"File size: {result['file_size']} bytes")
    print(f"Uploaded at: {result['created_at']}")
else:
    print(f"Upload failed: {response.status_code}")
    print(response.text)
```

**Python Client - Batch Upload:**
```python
import requests
from pathlib import Path

video_dir = Path("videos")
user_id = "batch-user-001"
video_ids = []

for video_file in video_dir.glob("*.mp4"):
    with open(video_file, "rb") as f:
        response = requests.post(
            "http://localhost:8000/upload-video",
            files={"file": f},
            data={"user_id": user_id}
        )
    
    if response.status_code == 200:
        video_id = response.json()["id"]
        video_ids.append(video_id)
        print(f"✓ Uploaded: {video_file.name} -> {video_id}")
    else:
        print(f"✗ Failed: {video_file.name}")

print(f"\nTotal uploaded: {len(video_ids)}")
```

#### 11.2 Get User Quota Information

**cURL Example:**
```bash
curl -X GET "http://localhost:8000/user/user-123/quota"

# Response:
# {
#   "user_id": "user-123",
#   "video_count": 7,
#   "max_videos": 10,
#   "remaining_quota": 3,
#   "total_size_bytes": 5242880000,
#   "last_updated": "2026-02-25T10:30:45.123456"
# }
```

**Python Client:**
```python
import requests

user_id = "user-123"
response = requests.get(f"http://localhost:8000/user/{user_id}/quota")

if response.status_code == 200:
    quota = response.json()
    print(f"User ID: {quota['user_id']}")
    print(f"Videos uploaded: {quota['video_count']}/{quota['max_videos']}")
    print(f"Remaining quota: {quota['remaining_quota']}")
    print(f"Total size: {quota['total_size_bytes'] / (1024**3):.2f} GB")
else:
    print(f"Error: {response.status_code}")
```

#### 11.3 List User's Videos

**cURL Example:**
```bash
# Get non-deleted videos only
curl -X GET "http://localhost:8000/user/user-123/videos"

# Include deleted videos
curl -X GET "http://localhost:8000/user/user-123/videos?include_deleted=true"

# Response:
# {
#   "user_id": "user-123",
#   "total_count": 7,
#   "videos": [
#     {
#       "id": "550e8400-e29b-41d4-a716-446655440000",
#       "filename": "video.mp4",
#       "file_size": 1048576,
#       "created_at": "2026-02-25T10:30:45.123456",
#       "is_deleted": false,
#       "deleted_at": null
#     },
#     ...
#   ]
# }
```

**Python Client:**
```python
import requests

user_id = "user-123"
response = requests.get(
    f"http://localhost:8000/user/{user_id}/videos",
    params={"include_deleted": False}
)

if response.status_code == 200:
    data = response.json()
    print(f"Total videos: {data['total_count']}")
    for video in data['videos']:
        print(f"- {video['filename']} ({video['file_size']} bytes)")
        print(f"  ID: {video['id']}")
        print(f"  Uploaded: {video['created_at']}")
```

#### 11.4 Delete Video

**cURL Example:**
```bash
curl -X DELETE "http://localhost:8000/video/550e8400-e29b-41d4-a716-446655440000?user_id=user-123"

# Response:
# {
#   "status": "success",
#   "message": "Video 550e8400-e29b-41d4-a716-446655440000 deleted successfully"
# }
```

**Python Client:**
```python
import requests

video_id = "550e8400-e29b-41d4-a716-446655440000"
user_id = "user-123"

response = requests.delete(
    f"http://localhost:8000/video/{video_id}",
    params={"user_id": user_id}
)

if response.status_code == 200:
    print(f"✓ Video deleted successfully")
else:
    print(f"✗ Delete failed: {response.status_code}")
```

#### 11.5 Complete Upload + Extraction Workflow

```python
import requests
from pathlib import Path
import time

user_id = "workflow-demo"
video_file = Path("input.mp4")

# Step 1: Upload video
print("Step 1: Uploading video...")
with open(video_file, "rb") as f:
    upload_resp = requests.post(
        "http://localhost:8000/upload-video",
        files={"file": f},
        data={"user_id": user_id}
    )

video_id = upload_resp.json()["id"]
print(f"✓ Video uploaded: {video_id}")

# Step 2: Check quota
print("\nStep 2: Checking quota...")
quota_resp = requests.get(f"http://localhost:8000/user/{user_id}/quota")
quota = quota_resp.json()
print(f"  Remaining quota: {quota['remaining_quota']}/{quota['max_videos']}")

# Step 3: Get file path from local storage (or use video_id to retrieve)
local_video_path = f"./uploads/{video_id}.mp4"

# Step 4: Extract subtitles from uploaded video
print("\nStep 3: Extracting subtitles...")
extract_resp = requests.post(
    "http://localhost:8000/extract-srt",
    json={
        "video": local_video_path,
        "lang": "vi",
        "target_fps": 4.0
    }
)

srt_content = extract_resp.json()["srt"]
print(f"✓ Extracted {len(srt_content.splitlines()) // 4} subtitle cues")

# Step 5: Generate audio from subtitles
print("\nStep 4: Synthesizing audio...")
tts_resp = requests.post(
    "http://localhost:8000/tts/generate",
    json={
        "srt_content": srt_content,
        "tts_voice": "BV074_streaming",
        "output_filename": f"{video_id}_audio.wav"
    }
)

audio_path = tts_resp.json()["audio_path"]
print(f"✓ Audio synthesized: {audio_path}")

print(f"\n✓ Workflow complete!")
print(f"  Video ID: {video_id}")
print(f"  Subtitles: SRT format available")
print(f"  Audio: {audio_path}")
```

#### 11.6 Upload Configuration

Configure upload behavior in `.env`:

```bash
# Database connection
DATABASE_URL=postgresql://video_user:video_password@localhost:5432/video_srt_db

# Upload settings
UPLOAD_DIR=./uploads
MAX_VIDEOS_PER_USER=10              # Max videos per user before auto-cleanup
MAX_UPLOAD_SIZE_MB=500              # Max file size in MB

# Server settings
HOST=0.0.0.0
PORT=8000
```

**Upload Limits**:
- Default: 10 videos per user
- File size: 500 MB per video
- Formats: mp4, avi, mov, mkv, flv, wmv, webm

**Auto-cleanup behavior**:
- When user uploads 11th video → oldest video (1st uploaded) is deleted
- Deleted videos are marked with `is_deleted=true` in database
- File is removed from disk immediately
- User quota counter updates automatically

### API Response Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Successful extraction |
| 400 | Bad Request | Invalid parameters |
| 404 | Not Found | Task/file not found |
| 503 | Service Unavailable | TTS disabled or service down |
| 500 | Server Error | Processing failed |

## Detailed API Reference

### Extract SRT Response Model

```json
{
  "srt": "string",  # Full SRT content
  "srt_detail": [
    {
      "srt": "string",  # Subtitle text
      "srt_time": "HH:MM:SS,mmm --> HH:MM:SS,mmm",  # Time range
      "x1": "float",  # Top-left X coordinate
      "y1": "float",  # Top-left Y coordinate
      "x2": "float",  # Bottom-right X coordinate
      "y2": "float"   # Bottom-right Y coordinate
    }
  ],
  "stats": {
    "mode": "ocr | stream",  # Extraction mode used
    "frames_seen": "int",  # Total frames in video
    "frames_sampled": "int",  # Frames sampled based on target_fps
    "frames_hashed_skipped": "int",  # Frames skipped due to hash gating
    "frames_ocr": "int",  # Frames actually OCR'd
    "cues": "int",  # Number of subtitle cues
    "timing_ms": {
      "total": "float",  # Total processing time (ms)
      "decode": "float",  # Video decoding time (ms)
      "ocr": "float"  # OCR processing time (ms)
    },
    "video": {
      "width": "int",  # Video width
      "height": "int",  # Video height
      "src_fps": "float",  # Source FPS
      "active_top": "int",  # Y coordinate of letterbox top (0 if none)
      "active_bottom": "int"  # Y coordinate of letterbox bottom
    }
  }
}
```

### Task Status Response Model

```json
{
  "task_id": "string",  # UUID of the task
  "status": "processing | completed | failed",  # Current status
  "progress": 0.0-1.0,  # Progress percentage (0.0 = 0%, 1.0 = 100%)
  "result": "ExtractResponse | null",  # Full result when completed
  "error": "string | null"  # Error message if failed
}
```

### TTS Response Model

```json
{
  "task_id": "string",  # Task UUID
  "status": "success | failed",  # Operation status
  "audio_filename": "string",  # Output filename
  "audio_path": "string",  # Full file path on server
  "audio_base64": "string | null",  # Base64 encoded audio (if return_base64=true)
  "duration_ms": "float",  # Audio duration in milliseconds
  "size_bytes": "int",  # File size in bytes
  "message": "string | null"  # Optional message
}
```

| Scenario | Recommendation | Tại sao |
|----------|---|---------|
| **Fast subtitle extraction** | `target_fps=1.5, max_width=640, hash_dist_thr=10, prefer_subtitle_stream=true` | Minimize frame processing |
| **High accuracy extraction** | `target_fps=8, max_width=1920, enhance=true, conf_min=0.7` | Maximize OCR coverage |
| **Noisy video (anime/cartoon)** | `debounce_frames=3, sim_thr=0.85, content_change_thr=0.15` | Smooth flickering text |
| **Clean video (news/subtitles)** | `debounce_frames=1, sim_thr=0.95, conf_min=0.6` | Detect every change quickly |
| **Limited resources (CPU only)** | `target_fps=2, max_width=640, hash_dist_thr=8, device=cpu` | Balance speed/accuracy on CPU |
| **High-end GPU available** | `target_fps=6, max_width=1920, debounce_frames=2, device=gpu:0` | Leverage GPU power |
| **With embedded subtitles** | `prefer_subtitle_stream=true, ...` | Use ffmpeg fast-path (20x faster) |
| **Multiple languages** | `lang=en/zh/ja, use_textline_orientation=true` | Auto-select appropriate model |

#### **Performance Calculation Examples**

**Example 1: Processing Time Estimation**
```
Input: 10 minute video, 30fps
Parameters:
  - target_fps = 4.0
  - device = gpu:0

Calculation:
1. Total frames = 10 * 60 * 30 = 18,000 frames
2. Sampled frames = 18,000 / (30 / 4) = 18,000 / 7.5 = 2,400 frames
3. Hash gating skip (~70%) = 2,400 * 0.30 = 720 frames to OCR
4. GPU speed: ~1 frame/50ms = 36 frames/sec

Estimated time:
  - Frame decoding: 2,400 * 10ms = 24 seconds
  - OCR processing: 720 / 36 = 20 seconds
  - Total: ~45-60 seconds
```

**Example 2: ROI Calculation**
```
Input: 1080p video (1920x1080)
Parameters:
  - bottom_start = 0.55
  - max_width = 1280

Calculation:
1. Active region height = 1080 * (1 - 0.55) = 486 pixels (bottom 45%)
2. ROI box = (0, 594, 1920, 1080) ~ bottom 486 pixels
3. After scale to max_width=1280:
   - Original aspect: 1920:486 ~ 4:1
   - Scaled: 1280 x 320 pixels
4. OCR area = 1280 * 320 = 409,600 pixels (~21% of original 2,073,600)

Speed benefit: ~79% faster image processing vs full frame
```

**Example 3: Debouncing Effect**
```
Raw OCR output (frame-by-frame):
Frame 1: "Hello"     (conf=0.95) ✓
Frame 2: "Hello"     (conf=0.94) ✓
Frame 3: "Hallo"     (conf=0.45) ✗ (OCR error)
Frame 4: "Hello"     (conf=0.96) ✓
Frame 5: (empty)     ✗
Frame 6: (empty)     ✓
Frame 7: "World"     (conf=0.92) ✓

With debounce_frames=2, empty_debounce_frames=2:
- Frame 1-2: Confirm "Hello" start (2 consecutive matches)
- Frame 3: Ignore "Hallo" (1 bad frame, not debounced)
- Frame 4: Continue "Hello" (consistent)
- Frame 5: Not confirmed empty (need 2 consecutive)
- Frame 6: Confirmed empty (2 consecutive empty)
- Frame 7: Confirm "World" start

Final output:
- Cue 1: 0:00-5:00 "Hello" (frames 1-4)
- Cue 2: 5:00-10:00 "World" (frame 7+)

Benefit: Eliminated 1 false subtitle + 1 early termination
```

**Example 4: Merge Gap Effect**
```
Raw cues output:
- Cue 1: 00:00:00 --> 00:00:05 "Hello"
- Gap: 150ms (< merge_gap_ms=250)
- Cue 2: 00:00:05.150 --> 00:00:10 "Hello world"
- Gap: 500ms (> merge_gap_ms=250)
- Cue 3: 00:00:10.500 --> 00:00:15 "Hello world"

With merge_gap_ms=250, sim_thr=0.90:
- Cue 1 + Cue 2: sim("Hello", "Hello world")=0.67 < 0.90 → NO merge
- Cue 2 + Cue 3: sim("Hello world", "Hello world")=1.0 > 0.90 + gap < 250 → MERGE

Final:
- Cue 1: 00:00:00 --> 00:00:05 "Hello"
- Cue 2: 00:00:05.150 --> 00:00:15 "Hello world" (merged 2+3)
```

#### **Hash Gating Deep Dive**

```python
# How hash gating saves 60-80% OCR calls

Frame comparison using Average Hash (aHash):
- Each frame → 64-bit hash
- Compare: hamming_distance(hash1, hash2)
- If distance < hash_dist_thr → frames similar, skip OCR

Example:
Video: 30fps, 10 minutes = 18,000 frames
target_fps=4 → sample 2,400 frames

Without hash gating:
- OCR all 2,400 frames
- Time: 2,400 * 50ms = 120 seconds (GPU)

With hash_dist_thr=6 (default):
- Static scene (same background):
  - Frames very similar (distance 0-4)
  - Skip ~95% of static frames
  - Dynamic scene (text changes):
  - Frames different (distance 10+)
  - OCR each frame
- Typical result: OCR 700 frames (29% of sampled)
- Time: 700 * 50ms = 35 seconds (GPU)
- Speedup: 3.4x on GPU!
```

## Advanced Usage Examples

### Understanding Parameter Dependencies

Một số parameters không độc lập - chúng có **dependencies** và tương tác với nhau:

**Dependency 1: FPS + Hash Gating**
```
target_fps thấp + hash_dist_thr cao:
  result: Ít frame OCR + nhiều frame skip = rất nhanh nhưng có thể mất subtitle
  ✓ Dùng khi: Video tĩnh, subtitle ít thay đổi

target_fps cao + hash_dist_thr thấp:
  result: Nhiều frame OCR + ít frame skip = chính xác nhưng chậm
  ✓ Dùng khi: Video dynamic, subtitle có animation
```

**Dependency 2: ROI + Accuracy**
```
bottom_start=0.55 + max_width=640:
  result: ROI nhỏ (45% × scaled) = nhanh nhưng OCR chất lượng giảm
  ✓ Dùng khi: Subtitle luôn ở dưới video

bottom_start=0.0 + max_width=1920:
  result: ROI lớn (full frame × full res) = chậm nhưng chính xác
  ✓ Dùng khi: Subtitle có ở nhiều vị trí
```

**Dependency 3: Confidence + Debouncing**
```
conf_min=0.5 + debounce_frames=1:
  result: Accept mọi text + nhanh confirm = nhiều false positive
  ✓ Dùng khi: Kiên nhẫn sửa false positive sau

conf_min=0.8 + debounce_frames=3:
  result: Chỉ text confident + chậm confirm = ít false positive
  ✓ Dùng khi: Cần output sạch ngay
```

**Dependency 4: Merge + Similarity**
```
merge_gap_ms=250 + sim_thr=0.90:
  result: Merge liền kề + exact match = ít merge, output smooth
  ✓ Dùng khi: Subtitle rõ ràng, ít variation

merge_gap_ms=1000 + sim_thr=0.70:
  result: Merge cách xa + fuzzy match = nhiều merge, output clean
  ✓ Dùng khi: Subtitle fragmented, có OCR error
```

**Dependency 5: Frame Gating Thresholds**
```
hash_dist_thr + content_change_thr + text_motion_thr:
  result: Multiple gates cùng hoạt động
  
Nếu cả 3 gate "trigger" (detect change):
  - hash: Frame khác → detect change
  - content: Text nội dung khác → detect change
  - motion: Text đang di chuyển → skip OCR tạm
  - intensity: Flash/scene cut → detect change

→ Trigger nhiều gate = tăng confidence về "điểm này cần OCR"
```

### 

Example 1: Speed-Optimized Extraction (Fast)

```python
import requests

# Configuration for speed (sacrifice some accuracy)
response = requests.post(
    "http://localhost:8000/extract-srt",
    json={
        "video": "video.mp4",
        "lang": "vi",
        "device": "gpu:0",  # GPU 3-4x faster
        "target_fps": 2.0,  # Lower FPS = faster
        "max_width": 640,  # Smaller = faster
        "hash_dist_thr": 10,  # Skip more frames
        "min_duration_ms": 1000,  # Only long subtitles
        "merge_gap_ms": 500  # Merge more aggressively
    }
)

srt = response.json()["srt"]
print(srt)
```

### Example 2: Accuracy-Optimized Extraction (Slow but Accurate)

```python
import requests

# Configuration for accuracy (sacrifice speed)
response = requests.post(
    "http://localhost:8000/extract-srt",
    json={
        "video": "video.mp4",
        "lang": "vi",
        "device": "gpu:0",  # Use GPU still helps
        "target_fps": 8.0,  # Higher FPS = more frames OCR'd
        "max_width": 1920,  # Full resolution
        "enhance": True,  # CLAHE enhancement
        "conf_min": 0.7,  # Higher confidence threshold
        "hash_dist_thr": 2,  # Skip fewer frames
        "debounce_frames": 3,  # More stable
        "min_duration_ms": 200  # Keep short subtitles
    }
)

srt = response.json()["srt"]
print(srt)
```

### Example 3: Balanced Configuration (Recommended)

```python
import requests

# Balanced: good speed & accuracy
response = requests.post(
    "http://localhost:8000/extract-srt",
    json={
        "video": "video.mp4",
        "lang": "vi",
        "device": "gpu:0" if <gpu_available> else "cpu",
        "target_fps": 4.0,  # Default
        "max_width": 1280,  # Default
        "enhance": True,
        "conf_min": 0.5,  # Default
        "hash_dist_thr": 6,  # Default
        "sim_thr": 0.90,
        "debounce_frames": 2,
        "min_duration_ms": 400
    }
)

srt = response.json()["srt"]
print(srt)
```

### Example 4: Using Stream Extraction (If Available)

```python
import requests

# Fast-path: extract embedded subtitles from video
response = requests.post(
    "http://localhost:8000/extract-srt",
    json={
        "video": "video_with_subtitles.mp4",
        "prefer_subtitle_stream": True  # Use ffmpeg if available
    }
)

data = response.json()
if data["stats"]["mode"] == "stream":
    print("✓ Used fast-path subtitle stream extraction (20x faster!)")
else:
    print("✓ Fell back to OCR (no embedded subtitles found)")

srt = data["srt"]
print(srt)
```

### Example 5: Blur + Subtitle Workflow

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

### Example 6: Complete TTS Workflow

```python
import requests
import base64
from pathlib import Path

# Step 1: Extract SRT from video
print("Step 1: Extracting subtitles from video...")
extract_resp = requests.post(
    "http://localhost:8000/extract-srt",
    json={"video": "video.mp4", "lang": "vi"}
)
srt_content = extract_resp.json()["srt"]

# Step 2: Generate audio from SRT
print("Step 2: Generating audio from subtitles...")
tts_resp = requests.post(
    "http://localhost:8000/tts/generate",
    json={
        "srt_content": srt_content,
        "tts_voice": "BV074_streaming",
        "output_filename": "synthesized.wav",
        "return_base64": True
    }
)

result = tts_resp.json()
print(f"✓ Audio generated: {result['audio_path']}")
print(f"  Duration: {result['duration_ms']}ms")
print(f"  Size: {result['size_bytes']} bytes")

# Step 3: Combine video + audio (using ffmpeg)
print("Step 3: Combining video + audio...")
import subprocess
subprocess.run([
    "ffmpeg", "-i", "video.mp4", 
    "-i", result['audio_path'],
    "-c:v", "copy", "-c:a", "aac",
    "-map", "0:v:0", "-map", "1:a:0",
    "output_with_audio.mp4"
])
print("✓ Complete! Output: output_with_audio.mp4")
```

### Example 7: Batch Processing with Progress Tracking

```python
import requests
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

def process_video(video_path):
    """Process single video asynchronously"""
    # Start task
    response = requests.post(
        "http://localhost:8000/extract-srt-async",
        json={
            "video": str(video_path),
            "lang": "vi",
            "output_path": str(video_path.with_suffix(".srt"))
        }
    )
    
    task_id = response.json()["task_id"]
    print(f"Started: {video_path.name} (Task: {task_id})")
    
    # Poll for completion
    while True:
        status_resp = requests.get(f"http://localhost:8000/task/{task_id}")
        task_data = status_resp.json()
        
        if task_data["status"] == "processing":
            progress = task_data.get("progress", 0) * 100
            print(f"  {video_path.name}: {progress:.1f}% complete")
            time.sleep(2)
        
        elif task_data["status"] == "completed":
            print(f"  ✓ {video_path.name}: Done!")
            return video_path.with_suffix(".srt")
        
        elif task_data["status"] == "failed":
            print(f"  ✗ {video_path.name}: Failed - {task_data['error']}")
            return None

# Process multiple videos in parallel
video_dir = Path("videos")
videos = list(video_dir.glob("*.mp4"))

with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(process_video, videos))

print(f"\n✓ Batch processing complete! Generated {len([r for r in results if r])} SRT files")
```

## Error Handling & Troubleshooting

### Common Errors

**Error 1: Video file not found**
```python
# Response:
# HTTPException 404: "Video not found: uploads/video.mp4"

# Solution: Check path exists and is accessible
import os
assert os.path.exists("uploads/video.mp4"), "Video file not found"
```

**Error 2: Invalid SRT format in TTS**
```python
# Response:
# HTTPException 400: "Invalid SRT content or empty"

# Solution: Ensure SRT content is valid
srt_content = """1
00:00:01,000 --> 00:00:05,000
Text here

2
00:00:05,000 --> 00:00:10,000
More text
"""
```

**Error 3: TTS service disabled**
```python
# Response:
# HTTPException 503: "TTS service is not enabled"

# Solution: Check .env file has TTS_ENABLED=true
```

**Error 4: GPU out of memory**
```python
# Response:
# RuntimeError: CUDA out of memory

# Solution: Reduce max_width, target_fps, or use CPU
json={
    "video": "video.mp4",
    "max_width": 640,  # Reduce from 1280
    "target_fps": 2.0,  # Reduce from 4.0
}
```

### Performance Tuning

| Issue | Solution | Impact |
|-------|----------|--------|
| Too slow | Use GPU, reduce target_fps, reduce max_width | ↑ Speed, ↓ Accuracy |
| Low accuracy | Increase target_fps, increase max_width, enable enhance | ↓ Speed, ↑ Accuracy |
| Out of memory | Reduce max_width, reduce batch_size | ↓ Memory |
| Many false positives | Increase conf_min, increase debounce_frames | Cleaner output |
| Fragmented subtitles | Increase merge_gap_ms, decrease sim_thr | ↑ Stability |





## Configuration

### Environment Variables

Key environment variables for tuning:

| Variable | Default | Description | Range |
|----------|---------|-------------|-------|
| `DEFAULT_DEVICE` | `cpu` | Processing device | `cpu`, `gpu:0`, `gpu:1` |
| `DEFAULT_LANG` | `vi` | OCR language | `vi`, `en`, `zh`, `ja`, etc. |
| `DEFAULT_TARGET_FPS` | `4.0` | Frame sampling rate | 1.0 - 32.0 |
| `OCR_CACHE_MAX` | `4` | Max cached OCR engines | 1 - 16 |
| `BATCH_OCR_SIZE` | `8` | OCR batch size | 1 - 32 (GPU benefits from larger) |
| `LOG_LEVEL` | `WARNING` | Logging verbosity | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `DEFAULT_CONF_MIN` | `0.5` | Minimum confidence threshold | 0.0 - 1.0 |

### Tuning Tips

**For Speed (Faster Processing)**:
```bash
DEFAULT_TARGET_FPS=1.0      # Minimum sampling
OCR_CACHE_MAX=1              # Reduce cache overhead
BATCH_OCR_SIZE=4             # Smaller batches
```

**For Quality (More Accurate)**:
```bash
DEFAULT_TARGET_FPS=8.0       # More frames sampled
OCR_CACHE_MAX=8              # Keep more engines
BATCH_OCR_SIZE=16            # Larger batches
DEFAULT_CONF_MIN=0.7         # Higher confidence threshold
```

**For GPU (Accelerated)**:
```bash
DEFAULT_DEVICE=gpu:0         # Use GPU
DEFAULT_TARGET_FPS=6.0       # Can sample more with GPU
OCR_CACHE_MAX=8              # GPU has more memory
BATCH_OCR_SIZE=32            # GPU processes batches efficiently
```

### .env Example

```bash
# .env file
# Server
HOST=0.0.0.0
PORT=8000

# OCR Settings
DEFAULT_DEVICE=cpu
DEFAULT_LANG=vi
DEFAULT_TARGET_FPS=4.0

# Performance
OCR_CACHE_MAX=4
BATCH_OCR_SIZE=8

# Logging
LOG_LEVEL=WARNING

# TTS Settings
TTS_ENABLED=true
TTS_API_KEY=ddjeqjLGMn
TTS_API_TOKEN=your_api_token_here
TTS_DEFAULT_VOICE=BV074_streaming
TTS_OUTPUT_DIR=./tts_output
TTS_TEMP_DIR=./tts_temp
TTS_BATCH_SIZE=1000
TTS_MAX_RETRIES=3

# PaddleOCR Fixes
FLAGS_use_mkldnn=0
```

### TTS Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TTS_ENABLED` | `true` | Enable/disable TTS feature |
| `TTS_API_KEY` | `ddjeqjLGMn` | TTS service API key |
| `TTS_API_TOKEN` | (required) | Authentication token from TTS service |
| `TTS_DEFAULT_VOICE` | `BV074_streaming` | Default voice for synthesis |
| `TTS_OUTPUT_DIR` | `./tts_output` | Directory for generated audio files |
| `TTS_TEMP_DIR` | `./tts_temp` | Temporary directory for processing |
| `TTS_BATCH_SIZE` | `1000` | Batch size for TTS requests |
| `TTS_MAX_RETRIES` | `3` | Maximum retry attempts for failed requests |

## Project Structure

```
video-to-srt/
├── app/                              # Main application package
│   ├── __init__.py
│   ├── main.py                       # FastAPI app entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py                 # API route definitions
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                 # Settings & configuration
│   │   └── logging_config.py         # Logging setup
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py               # Request schemas (Pydantic)
│   │   ├── responses.py              # Response schemas
│   │   └── internal.py               # Internal data models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ocr_service.py            # PaddleOCR engine management
│   │   ├── ffmpeg_service.py         # FFmpeg video operations
│   │   ├── srt_service.py            # SRT subtitle generation
│   │   └── video_processor.py        # Main video processing pipeline
│   └── utils/
│       ├── __init__.py
│       ├── text_utils.py             # Text processing utilities
│       ├── hash_utils.py             # Frame hashing & comparison
│       └── image_utils.py            # Image preprocessing
├── Dockerfile                        # CPU Docker image
├── Dockerfile.gpu                    # GPU Docker image
├── docker-compose.yml                # Docker Compose configuration
├── docker-compose.dev.yml            # Development Docker setup
├── requirements.txt                  # Python dependencies
├── run.py                            # Development server launcher
├── setup.py                          # Package setup
├── .env.example                      # Environment template
├── DOCKER.md                         # Docker deployment guide
├── USAGE.md                          # This file
└── README.md                         # Project overview
```

## Troubleshooting

### ModuleNotFoundError

```bash
# Make sure you're in the project directory
cd d:\LEARN\video-to-srt

# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Reinstall dependencies
pip install -r requirements.txt
```

### FFmpeg not found

```bash
# Add FFmpeg to PATH
# Windows: Set PATH environment variable
# macOS: brew install ffmpeg
# Linux: sudo apt-get install ffmpeg

# Or verify installation
ffmpeg -version
ffprobe -version
```

### GPU not working

```bash
# Check if GPU is available
python -c "import torch; print(torch.cuda.is_available())"

# Or for PaddlePaddle
python -c "import paddle; print(paddle.fluid.is_compiled_with_cuda())"

# Install GPU version
pip uninstall paddlepaddle
pip install paddlepaddle-gpu
```

### Out of Memory

```bash
# Reduce sampling rate
DEFAULT_TARGET_FPS=2.0

# Reduce batch size
BATCH_OCR_SIZE=4

# Reduce cache
OCR_CACHE_MAX=2
```

### Slow Processing

```bash
# Check current settings
curl http://localhost:8000/health

# Try GPU if available
DEFAULT_DEVICE=gpu:0

# Reduce quality if speed is critical
DEFAULT_TARGET_FPS=2.0
```

### Docker container won't start

```bash
# Check logs
docker-compose logs video-to-srt

# Rebuild without cache
docker-compose build --no-cache video-to-srt

# Try again
docker-compose up -d
```

## Performance Benchmarks

Approximate processing times (video without subtitles):

| Duration | Device | FPS | Time | Notes |
|----------|--------|-----|------|-------|
| 1 minute | CPU | 4.0 | 30-45s | Single-threaded |
| 1 minute | GPU | 4.0 | 10-15s | NVIDIA GTX 1060 |
| 10 minutes | CPU | 2.0 | 3-5 min | Reduced FPS for speed |
| 10 minutes | GPU | 6.0 | 1-2 min | Higher FPS with GPU |

*Times vary based on video resolution and content complexity*

## Advanced Usage

### Custom OCR Models

Edit [app/services/ocr_service.py](app/services/ocr_service.py):

```python
# Change detection/recognition models
ocr = PaddleOCR(
    use_angle_cls=True,
    det_model_dir="custom_det_model",
    rec_model_dir="custom_rec_model"
)
```

### Batch Processing Script

See [examples/batch_process.py](examples/batch_process.py) for batch processing script.

### Integration with Other Systems

The API is compatible with:
- **Web frontends**: JavaScript/TypeScript HTTP clients
- **Mobile apps**: Any HTTP-capable framework
- **Scripting**: Python, Node.js, bash, PowerShell
- **Workflows**: CI/CD pipelines, automation tools

## Support

For issues and help:

1. Check [DOCKER.md](DOCKER.md) for Docker-specific issues
2. Check [README.md](README.md) for project details
3. Review logs: `docker-compose logs -f` or console output
4. Check API docs: http://localhost:8000/docs
5. View health: `curl http://localhost:8000/health`

## API Documentation

Full interactive API documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

All endpoints, parameters, and response schemas documented there.
