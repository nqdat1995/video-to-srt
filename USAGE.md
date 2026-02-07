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
#   "stats": {
#     "duration_seconds": 120.5,
#     "total_frames": 2880,
#     "frames_sampled": 240,
#     "frames_ocr": 150,
#     "timing_ms": {...}
#   }
# }
```

### 3. Asynchronous Extraction (Non-blocking)

**Start task:**
```bash
curl -X POST "http://localhost:8000/extract-srt-async" \
  -H "Content-Type: application/json" \
  -d '{
    "video": "uploads/long_video.mp4",
    "lang": "vi",
    "device": "cpu"
  }'

# Response: {"task_id": "abc123..."}
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
stats = data["stats"]

print(f"Extracted {len(srt_content.split('\\n\\n'))} subtitle blocks")
print(f"Time taken: {stats['timing_ms']['total_ms']/1000:.2f}s")

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

# PaddleOCR Fixes
FLAGS_use_mkldnn=0
```

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
