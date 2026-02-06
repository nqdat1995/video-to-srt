# Hướng dẫn sử dụng (Usage Guide)
## Cài đặt (Installation)

### 1. Clone repository
```bash
cd d:\SOURCE\SamplePython
```

### 2. Tạo virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Cài đặt dependencies

**Option A: Using uv (Recommended - Faster)**
```bash
pip install uv
uv pip install -r requirements.txt
```

**Option B: Using pip (Traditional)**
```bash
pip install -r requirements.txt
```

### 4. Cài đặt FFmpeg
- **Windows**: Download từ https://ffmpeg.org/download.html
- **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
- **macOS**: `brew install ffmpeg`

## Chạy server

### Development mode (với auto-reload) - Using uv (Recommended)
```bash
uv run python run.py
```

### Development mode - Using Python directly
```bash
python run.py
```

### Production mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Với environment variables (using uv)
```bash
# Copy và chỉnh sửa .env file
cp .env.example .env

# Chạy với custom config (Windows)
set OCR_CACHE_MAX=8 && set BATCH_OCR_SIZE=16 && uv run python run.py

# Chạy với custom config (Linux/Mac)
OCR_CACHE_MAX=8 BATCH_OCR_SIZE=16 uv run python run.py
```

### Với environment variables (traditional Python)
```bash
# Chạy với custom config (Windows)
set OCR_CACHE_MAX=8
set BATCH_OCR_SIZE=16
python run.py

# Chạy với custom config (Linux/Mac)
OCR_CACHE_MAX=8 BATCH_OCR_SIZE=16 python run.py
```

## Cấu trúc Project

```
SamplePython/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py          # API route handlers
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py          # Configuration settings
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py        # Request schemas
│   │   ├── responses.py       # Response schemas
│   │   └── internal.py        # Internal data models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ocr_service.py     # OCR engine management
│   │   ├── ffmpeg_service.py  # FFmpeg operations
│   │   ├── srt_service.py     # SRT generation
│   │   └── video_processor.py # Main video processing
│   └── utils/
│       ├── __init__.py
│       ├── text_utils.py      # Text processing utilities
│       ├── hash_utils.py      # Hash-based frame comparison
│       └── image_utils.py     # Image processing utilities
├── requirements.txt
├── setup.py
├── run.py                     # Development run script
├── .env.example
├── .gitignore
├── README.md
└── USAGE.md
```

## API Examples

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. Synchronous Extraction
```bash
curl -X POST "http://localhost:8000/extract-srt" \
-H "Content-Type: application/json" \
-d '{
   "video": "D:/videos/sample.mp4",
   "lang": "vi",
   "device": "cpu",
   "output_path": "D:/output/subtitles.srt"
}'
```

### 3. Asynchronous Extraction
```bash
# Start task
TASK_ID=$(curl -X POST "http://localhost:8000/extract-srt-async" \
-H "Content-Type: application/json" \
-d '{
   "video": "D:/videos/sample.mp4",
   "lang": "en",
   "device": "gpu:0"
}' | jq -r '.task_id')

# Check status
curl "http://localhost:8000/task/$TASK_ID"

# Delete task
curl -X DELETE "http://localhost:8000/task/$TASK_ID"
```

### 4. Python Client
```python
import requests
import time

# Sync extraction
response = requests.post(
   "http://localhost:8000/extract-srt",
   json={
       "video": "D:/videos/sample.mp4",
       "lang": "vi",
       "target_fps": 4.0,
       "conf_min": 0.6,
       "output_path": "D:/output/subtitles.srt"
   }
)

result = response.json()
print(result["srt"])
print(result["stats"])

# Async extraction with progress tracking
async_response = requests.post(
   "http://localhost:8000/extract-srt-async",
   json={
       "video": "D:/videos/long_video.mp4",
       "lang": "vi",
       "device": "gpu:0"
   }
)

task_id = async_response.json()["task_id"]

# Poll for status
while True:
   status = requests.get(f"http://localhost:8000/task/{task_id}")
   data = status.json()

   print(f"Progress: {data['progress']*100:.1f}%")

   if data['status'] == 'completed':
       print("SRT:", data['result']['srt'])
       break
   elif data['status'] == 'failed':
       print("Error:", data['error'])
       break

   time.sleep(1)

# Cleanup
requests.delete(f"http://localhost:8000/task/{task_id}")
```

## Configuration Options

### Environment Variables
- `OCR_CACHE_MAX`: Maximum OCR engines to cache (default: 4)
- `BATCH_OCR_SIZE`: Batch size for GPU processing (default: 8)
- `DEFAULT_TARGET_FPS`: Target frames per second for video sampling (range: 1.0-32.0, default: 4.0)
  - Lower values (1-2 FPS): Fast processing, basic subtitle quality
  - Medium values (4-6 FPS): Balanced speed and accuracy (recommended)
  - Higher values (10-32 FPS): High quality, slower processing
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL, default: WARNING)
  - WARNING (default): Minimal output, suppresses PaddleOCR debug logs
  - DEBUG: Verbose output for troubleshooting
  - INFO: Shows informational messages

### Request Parameters
Xem file [README.md](README.md) section "Request Parameters" để biết chi tiết 22 parameters có thể tuning.

## Troubleshooting

### Import errors
```bash
# Đảm bảo đang ở root directory và activate venv
cd d:\SOURCE\SamplePython
venv\Scripts\activate
python run.py
```

### Module not found
```bash
pip install -r requirements.txt
```

### GPU not working
```bash
# Uninstall CPU version
pip uninstall paddlepaddle

# Install GPU version
pip install paddlepaddle-gpu
```

### FFmpeg not found
- Thêm FFmpeg vào system PATH
- Hoặc specify full path trong environment

## Testing

### Manual test với curl
```bash
# Prepare test video
# Place video at D:/videos/test.mp4

# Run extraction
curl -X POST "http://localhost:8000/extract-srt" \
-H "Content-Type: application/json" \
-d '{
   "video": "D:/videos/test.mp4",
   "lang": "en",
   "output_path": "D:/output/test.srt"
}'
```

### Performance monitoring
```python
import requests
import time

start = time.time()
response = requests.post(
   "http://localhost:8000/extract-srt",
   json={"video": "D:/videos/test.mp4", "lang": "vi"}
)
elapsed = time.time() - start

stats = response.json()["stats"]
print(f"Total time: {elapsed:.2f}s")
print(f"OCR time: {stats['timing_ms']['ocr']/1000:.2f}s")
print(f"Decode time: {stats['timing_ms']['decode']/1000:.2f}s")
print(f"Frames processed: {stats['frames_ocr']}")
print(f"Frames skipped: {stats['frames_hashed_skipped']}")
```
