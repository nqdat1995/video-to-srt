---
description: This document outlines the constructor implementation standards for this project
---

# 📘 Hướng dẫn phát triển Video-to-SRT (Developer Guide)

**Phiên bản**: 1.1.0  
**Cập nhật lần cuối**: Tháng 2, 2026  
**Dành cho**: Developers mới vào dự án

---

## 📑 Mục lục

1. [Giới thiệu dự án](#giới-thiệu-dự-án)
2. [Cài đặt môi trường](#cài-đặt-môi-trường)
3. [Cấu trúc dự án](#cấu-trúc-dự-án)
4. [Chạy ứng dụng](#chạy-ứng-dụng)
5. [Hiểu rõ kiến trúc](#hiểu-rõ-kiến-trúc)
6. [Các module chính](#các-module-chính)
7. [Quy tắc viết code](#quy-tắc-viết-code)
8. [API endpoints](#api-endpoints)
9. [Database](#database)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Giới thiệu dự án

### Mục đích

**Video-to-SRT** là một ứng dụng FastAPI trích xuất phụ đề từ video bằng OCR và chuyển đổi thành định dạng SRT (SubRip Text).

### Tính năng chính

✅ Trích xuất phụ đề từ video bằng PaddleOCR v3  
✅ Hỗ trợ xử lý async/background với progress tracking  
✅ Tối ưu hóa GPU với batch OCR processing  
✅ Kiến trúc modular dễ mở rộng  
✅ Upload video API với PostgreSQL storage  
✅ Quản lý quota - tự động xóa video cũ  
✅ Tracking người dùng dựa trên GUID  
✅ Text-to-Speech tích hợp (TTS)  

### Tech Stack

| Thành phần | Phiên bản | Mục đích |
|-----------|----------|---------|
| **FastAPI** | 0.128.1 | Web framework |
| **PostgreSQL** | 16 | Database |
| **PaddleOCR** | 2.7.0.3 | Engine OCR |
| **PaddlePaddle** | 3.0.0 | ML framework |
| **SQLAlchemy** | 2.0+ | ORM |
| **OpenCV** | 4.8.0+ | Xử lý video/hình ảnh |
| **FFmpeg** | Latest | Xử lý video |

---

## 🔧 Cài đặt môi trường

### Bước 1: Clone hoặc tải repository

```bash
cd d:\LEARN\video-to-srt
```

### Bước 2: Tạo virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### Bước 3: Cài đặt dependencies

**Phương án A: Dùng `uv` (Khuyến nghị - Nhanh hơn)**
```bash
pip install uv
uv pip install -r requirements.txt
```

**Phương án B: Dùng `pip` (Truyền thống)**
```bash
pip install -r requirements.txt
```

### Bước 4: Cài đặt FFmpeg

**Windows:**
1. Download từ https://ffmpeg.org/download.html
2. Giải nén và thêm vào PATH
3. Verify: `ffmpeg -version`

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

### Bước 5: Cấu hình environment

Copy `.env.example` thành `.env` và điều chỉnh:

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/video_srt

# OCR Settings
DEFAULT_TARGET_FPS=4.0
DEFAULT_LANG=vi
DEFAULT_DEVICE=cpu  # hoặc gpu:0, gpu:1

# Paths
TEMP_DIR=./tmp_files
SRT_OUTPUT_DIR=./srt_output

# TTS (Optional)
TTS_ENABLED=true
TTS_API_KEY=your_key_here
TTS_DEFAULT_VOICE=BV074_streaming
```

### Bước 6: Setup Database

```bash
# PostgreSQL phải đang chạy
psql -U postgres

# Create database
CREATE DATABASE video_srt;

# Exit
\q
```

Chạy migrations:
```bash
cd migrations
python migrate.py upgrade
```

### Bước 7: Verify cài đặt

```bash
python -c "import paddleocr; import fastapi; print('✓ Installation OK')"
```

---

## 📁 Cấu trúc dự án

```
video-to-srt/
│
├── 📄 README.md                    # Tổng quan dự án
├── 📄 DEVELOPER_GUIDE.md          # File này (hướng dẫn developers)
├── 📄 setup.py                     # Cài đặt package
├── 📄 requirements.txt             # Dependencies
├── 📄 run.py                       # Script chạy dev server
├── 📄 .env.example                 # Template environment variables
│
├── 📂 app/                         # MAIN APPLICATION
│   ├── __init__.py
│   ├── main.py                     # FastAPI app entry point
│   │
│   ├── 📂 api/
│   │   ├── __init__.py
│   │   └── routes.py              # API endpoints định nghĩa ở đây
│   │
│   ├── 📂 core/
│   │   ├── __init__.py
│   │   ├── config.py              # Configuration từ env variables
│   │   ├── database.py            # Database connection setup
│   │   └── logging_config.py      # Logging configuration
│   │
│   ├── 📂 models/
│   │   ├── __init__.py
│   │   ├── database.py            # SQLAlchemy ORM models
│   │   ├── internal.py            # Internal data structures
│   │   ├── requests.py            # Pydantic request schemas
│   │   └── responses.py           # Pydantic response schemas
│   │
│   ├── 📂 services/               # Business logic
│   │   ├── __init__.py
│   │   ├── video_processor.py     # Main OCR pipeline orchestrator
│   │   ├── ocr_service.py         # PaddleOCR wrapper + caching
│   │   ├── ffmpeg_service.py      # FFmpeg/FFprobe wrapper
│   │   ├── srt_service.py         # SRT generation & cleanup
│   │   ├── storage_service.py     # File storage management
│   │   ├── database_service.py    # Database operations
│   │   └── tts_service.py         # Text-to-Speech integration
│   │
│   ├── 📂 utils/                  # Utility functions
│   │   ├── __init__.py
│   │   ├── text_utils.py          # Text normalization & similarity
│   │   ├── hash_utils.py          # Image hashing (ahash, hamming)
│   │   └── image_utils.py         # Image processing utilities
│   │
│   └── 📂 adapters/               # External service adapters (optional)
│
├── 📂 migrations/                 # Database migrations
│   ├── 001_initial_schema.py
│   ├── 002_add_audio_quota_columns.py
│   └── migrate.py
│
├── 📂 docker/                     # Docker configuration
│   ├── Dockerfile
│   ├── Dockerfile.gpu
│   ├── docker-compose.yml
│   └── docker-compose.dev.yml
│
├── 📂 usage/                      # Documentation
│   ├── 00-DATABASE-SETUP.md
│   ├── 01-INSTALLATION.md
│   ├── 02-RUNNING-SERVER.md
│   ├── 03-DOCKER-DEPLOYMENT.md
│   ├── 04-EXTRACT-SRT.md
│   ├── 05-PARAMETER-TUNING.md
│   ├── 06-VIDEO-PROCESSING.md
│   ├── 07-TTS-SYNTHESIS.md
│   ├── 08-VIDEO-UPLOAD.md
│   ├── 09-CONFIGURATION.md
│   ├── 10-API-REFERENCE.md
│   ├── 11-CHANGELOG.md
│   └── README.md
│
├── 📂 tmp_files/                  # Temporary files (không commit)
│   ├── uploads/
│   ├── srt_temp/
│   ├── srt_output/
│   ├── tts_temp/
│   └── tts_output/
│
├── 📂 audio_output/               # Audio output files
│
└── 📂 .venv/                      # Virtual environment (không commit)
```

---

## 🚀 Chạy ứng dụng

### Chạy dev server

```bash
# Từ thư mục gốc
python run.py

# Hoặc dùng uvicorn trực tiếp
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server sẽ chạy tại: **http://localhost:8000**

### Truy cập API documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

### Chạy với Docker

```bash
# Development
docker-compose -f docker/docker-compose.dev.yml up

# Production
docker-compose -f docker/docker-compose.yml up -d
```

### Chạy migrations

```bash
cd migrations
python migrate.py upgrade    # Upgrade database
python migrate.py downgrade  # Downgrade database
```

---

## 🏗️ Hiểu rõ kiến trúc

### Layered Architecture

```
┌─────────────────────────────────────┐
│      API Layer (routes.py)          │  ← HTTP requests/responses
├─────────────────────────────────────┤
│   Service Layer (services/)         │  ← Business logic
├─────────────────────────────────────┤
│   Data Layer (models/)              │  ← Data validation & ORM
├─────────────────────────────────────┤
│   Utility Layer (utils/)            │  ← Helper functions
├─────────────────────────────────────┤
│   Core Layer (core/)                │  ← Config, Database, Logging
└─────────────────────────────────────┘
```

### Data Flow - Extraction Request

```
1. Client POST /extract-srt
        ↓
2. API Router (routes.py) validates request
        ↓
3. VideoProcessor.extract_srt() 
        ↓
4. Sample frames from video
        ↓
5. Process mỗi frame:
   - Detect subtitle region (ROI)
   - Enhance image (CLAHE)
   - Run OCR (PaddleOCR)
   - Extract text
        ↓
6. Text Assembly:
   - Group multi-line text
   - Filter by confidence
   - Normalize
        ↓
7. SRT Segmentation:
   - Debounce (loại bỏ duplicates)
   - Fuzzy matching
   - Merge cues gần nhau
        ↓
8. Generate SRT output
        ↓
9. Save to database (nếu video_id)
        ↓
10. Return response
```

### Pipeline OCR Chi tiết

```
Video File
    ↓
[FFmpeg] Sample frames ở target_fps
    ↓
Frame Processing Loop:
    ├─ Detect active vertical region (letterbox)
    ├─ Extract ROI (Region of Interest)
    ├─ Calculate content hash (gating)
    ├─ Enhance image (CLAHE nếu enable)
    ├─ Run OCR (PaddleOCR)
    └─ Extract text & confidence
    ↓
Text Assembly:
    ├─ Group multi-line text
    ├─ Filter by confidence threshold
    ├─ Normalize whitespace
    └─ Strip quotes
    ↓
SRT Segmentation:
    ├─ Debounce duplicates
    ├─ Fuzzy match similar text
    ├─ Detect transitions
    ├─ Merge nearby cues
    └─ Apply min duration
    ↓
SRT Output
```

---

## 📦 Các module chính

### 1. API Layer (`api/routes.py`)

**Chức năng**: Định nghĩa tất cả HTTP endpoints

```python
# Main endpoints
POST   /extract-srt          # Sync extraction
POST   /extract-srt-async    # Async extraction
GET    /task/{task_id}       # Check task status
DELETE /task/{task_id}       # Cleanup task
POST   /upload-video         # Upload video
GET    /videos/{video_id}    # Get video info
GET    /user-quota           # Check quota
POST   /generate-tts         # TTS generation
```

**Quy tắc**:
- Tất cả routes trong một file
- Dùng Pydantic models cho request/response
- Proper error handling (HTTPException)
- Async functions cho I/O operations

### 2. Services Layer (`services/`)

**`video_processor.py`** - OCR Pipeline Orchestrator
- `extract_srt()`: Main extraction workflow
- `blur_and_add_subtitles()`: Blur + add subtitles to video
- Internal frame processing methods

**`ocr_service.py`** - OCR Wrapper + Caching
- Wraps PaddleOCR
- Model caching theo lang/device
- Batch processing support

**`ffmpeg_service.py`** - FFmpeg Integration
- Frame extraction
- Video probing
- Subtitle stream extraction
- GPU encoding support

**`srt_service.py`** - SRT Generation
- Generate SRT content
- Debouncing logic
- Text cleanup & merging
- Cue segmentation

**`storage_service.py`** - File Management
- Save/load files
- Temp file management
- Path handling

**`database_service.py`** - Database Operations
- Video CRUD
- User quota management
- Statistics tracking

**`tts_service.py`** - Text-to-Speech
- WebSocket communication
- Audio generation
- WAV file merging

### 3. Models (`models/`)

**`requests.py`** - Request Schemas
```python
ExtractRequest          # Extraction parameters
BlurRequest            # Blur parameters
SubtitleRequest        # Subtitle parameters
TTSGenerateRequest     # TTS parameters
VideoUploadRequest     # Upload parameters
```

**`responses.py`** - Response Schemas
```python
ExtractResponse        # Extraction result
TaskStatusResponse     # Task status
VideoUploadResponse    # Upload result
UserQuotaResponse      # Quota info
```

**`database.py`** - SQLAlchemy Models
```python
Video                  # Video metadata
User                   # User tracking
```

**`internal.py`** - Internal Data Structures
```python
CueDraft              # SRT cue draft
OCRResult             # OCR output
```

### 4. Utils (`utils/`)

**`text_utils.py`**
- `normalize_text()`: Chuẩn hóa text
- `similarity()`: So sánh độ tương đồng text
- `strip_quotes()`: Loại bỏ quotes

**`hash_utils.py`**
- `ahash()`: Average hash của image
- `hamming64()`: Hamming distance

**`image_utils.py`**
- `detect_subtitle_region()`: Tìm vùng phụ đề
- `detect_active_vertical_region()`: Detect letterbox
- `enhance_roi()`: CLAHE enhancement
- `detect_roi_content_change()`: Detect changes
- `detect_text_motion()`: Detect motion
- `detect_intensity_spike()`: Detect intensity changes

### 5. Core (`core/`)

**`config.py`** - Configuration từ environment
```python
APP_NAME, VERSION, DESCRIPTION
OCR_CACHE_MAX, BATCH_OCR_SIZE
DEFAULT_TARGET_FPS, DEFAULT_LANG
DATABASE_URL
TTS settings...
```

**`database.py`** - Database connection
```python
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker()
Base = DeclarativeBase()
init_db() # Create tables
get_db() # Dependency injection
```

**`logging_config.py`** - Logging setup
- Suppress noisy libraries
- Configure levels
- Format output

---

## 📝 Quy tắc viết code

### Naming Conventions

```python
# Classes - PascalCase
class VideoProcessor: pass
class ExtractRequest: pass

# Functions - snake_case
def extract_srt(): pass
def normalize_text(): pass

# Constants - UPPER_SNAKE_CASE
DEFAULT_TARGET_FPS = 4.0
LUMA_THRESHOLD = 18

# Private/Protected - prefix _
_TASKS = {}
self._cache = {}

# File names - lowercase with underscores
video_processor.py
ocr_service.py
text_utils.py
```

### Type Hints (MANDATORY)

```python
from typing import Optional, List, Dict, Tuple, Any

def extract_srt(
    req: ExtractRequest,
    db: Session = Depends(get_db)
) -> ExtractResponse:
    """Extract subtitles."""
    ...

class VideoProcessor:
    def __init__(self) -> None:
        self.cache: Dict[str, Any] = {}
    
    def process_frame(
        self, 
        frame: np.ndarray
    ) -> Tuple[str, float]:
        """Process frame and return text, confidence."""
        ...
```

**Guideline**:
- Dùng `Optional[T]` thay vì `Union[T, None]`
- Python 3.8 compatibility: `List[T]`, `Dict[K, V]` từ typing
- Luôn specify return type, không dùng `...`

### Docstrings (MANDATORY)

```python
def extract_srt(req: ExtractRequest) -> ExtractResponse:
    """Extract subtitles from video using OCR.
    
    Supports both direct OCR extraction and subtitle stream extraction
    via FFmpeg. Handles image enhancement, frame sampling, and SRT
    generation with configurable parameters.
    
    Args:
        req: Extraction request with video path and parameters
        
    Returns:
        ExtractResponse with generated SRT and statistics
        
    Raises:
        HTTPException: If video file not found or OCR fails
        ValueError: If parameters are invalid
        
    Examples:
        >>> req = ExtractRequest(video="/path/to/video.mp4")
        >>> response = processor.extract_srt(req)
        >>> print(response.srt[:100])
    """
```

### Code Style

- **Line length**: Max 100 chars (soft), 120 hard
- **Indentation**: 4 spaces (NEVER tabs)
- **Blank lines**: 2 between top-level, 1 between methods
- **String quotes**: Double quotes `"..."` (không single)
- **Imports**: Standard → Third-party → Local

```python
# ✓ Good
import os
from typing import List, Optional

import numpy as np
from fastapi import FastAPI

from .models import ExtractRequest
from .services import video_processor
```

```python
# ✗ Bad
from app.models import *  # No wildcard imports
import os, sys, typing    # One import per line
import os                 
import sys
# inconsistent order
from .services import video_processor
import numpy as np
```

### Error Handling

```python
# ✗ Bad - Silent failure
try:
    result = ocr_service.run(frame)
except:
    pass

# ✓ Good - Explicit handling
try:
    result = ocr_service.run(frame)
except OCRError as e:
    logger.error(f"OCR failed: {e}")
    raise HTTPException(status_code=500, detail="OCR processing failed")
```

### Comments

Comments giải thích **WHY**, không **WHAT**:

```python
# ✗ Bad
count = count + 1  # Increment count

# ✓ Good
# Skip duplicate frames with identical content hash
count = count + 1

# ✗ Bad
if confidence > 0.5:  # Check confidence

# ✓ Good
# Filter out low-confidence OCR results to improve accuracy
if confidence > settings.DEFAULT_CONF_MIN:
```

---

## 🔌 API Endpoints

### Health Check
```
GET /health
```
Response: `{"status": "ok"}`

### Extract SRT (Synchronous)
```
POST /extract-srt
Content-Type: application/json

{
  "video": "/path/to/video.mp4",
  "target_fps": 4.0,
  "conf_min": 0.5,
  "lang": "vi",
  "device": "cpu"
}

Response:
{
  "srt": "00:00:01,000 --> 00:00:03,000\nHello...",
  "frame_count": 120,
  "text_count": 5,
  "processing_time_sec": 45.2
}
```

### Extract SRT (Async)
```
POST /extract-srt-async
Content-Type: application/json

{
  "video": "/path/to/video.mp4",
  "target_fps": 4.0,
  ...
}

Response:
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued"
}
```

### Check Task Status
```
GET /task/{task_id}

Response:
{
  "task_id": "550e8400...",
  "status": "processing",
  "progress": 45,
  "result": null
}

Status values: queued, processing, completed, failed
```

### Cleanup Task
```
DELETE /task/{task_id}

Response:
{
  "message": "Task cleaned up"
}
```

### Upload Video
```
POST /upload-video
Content-Type: multipart/form-data

[File upload]

Response:
{
  "video_id": "550e8400...",
  "filename": "video.mp4",
  "file_size": 1024000,
  "created_at": "2024-03-14T09:30:14"
}
```

### Get Video Info
```
GET /videos/{video_id}

Response:
{
  "video_id": "550e8400...",
  "filename": "video.mp4",
  "file_path": "/uploads/video.mp4",
  "file_size": 1024000,
  "created_at": "2024-03-14T09:30:14"
}
```

### Get User Quota
```
GET /user-quota

Response:
{
  "total_quota_mb": 1000,
  "used_quota_mb": 250,
  "remaining_quota_mb": 750,
  "video_count": 3
}
```

### Generate TTS
```
POST /generate-tts
Content-Type: application/json

{
  "srt_content": "00:00:01,000 --> 00:00:03,000\nHello",
  "voice": "BV074_streaming",
  "language": "vi"
}

Response:
{
  "audio_file": "/tts_output/audio.wav",
  "duration_seconds": 2.5,
  "generated_at": "2024-03-14T09:30:14"
}
```

Chi tiết đầy đủ xem: `usage/10-API-REFERENCE.md`

---

## 🗄️ Database

### Setup Database

```bash
# PostgreSQL connection
psql -U postgres

# Create database
CREATE DATABASE video_srt;

# Create user (optional)
CREATE USER video_user WITH PASSWORD 'password';
ALTER ROLE video_user WITH SUPERUSER;

# Exit
\q
```

### Run Migrations

```bash
cd migrations
python migrate.py upgrade    # Chạy tất cả migrations
python migrate.py downgrade  # Rollback 1 migration
```

### Schema

**Videos Table**
```sql
CREATE TABLE videos (
    id VARCHAR(36) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_size BIGINT,
    created_at DATETIME,
    updated_at DATETIME,
    deleted_at DATETIME  -- Soft delete
);
```

**Users Table** (optional tracking)
```sql
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    guid VARCHAR(36),  -- GUID-based identification
    total_quota_mb INTEGER,
    used_quota_mb INTEGER,
    created_at DATETIME
);
```

### Using ORM

```python
from sqlalchemy.orm import Session
from app.models.database import Video

# Create
video = Video(
    id=str(uuid.uuid4()),
    filename="video.mp4",
    file_path="/path/to/video.mp4"
)
db.add(video)
db.commit()

# Read
video = db.query(Video).filter(Video.id == video_id).first()

# Update
video.filename = "new_name.mp4"
db.commit()

# Delete (Soft delete)
video.deleted_at = datetime.now()
db.commit()
```

---

## 🐛 Troubleshooting

### PaddleOCR Issues

**Lỗi**: `PIR attribute issue` hoặc `oneDNN error`

**Giải pháp**: Đã được xử lý trong `run.py` và `app/main.py`
```python
os.environ['PADDLE_DISABLE_FAST_MATH'] = '1'
os.environ['FLAGS_use_mkldnn'] = '0'
```

**Nếu vẫn lỗi**:
```bash
# Reinstall PaddleOCR
pip uninstall paddleocr paddlepaddle -y
pip install paddleocr==2.7.0.3 paddlepaddle==3.0.0
```

### FFmpeg Not Found

**Lỗi**: `ffmpeg: command not found`

**Giải pháp**:
- Windows: Download từ https://ffmpeg.org/download.html và thêm vào PATH
- Linux: `sudo apt-get install ffmpeg`
- macOS: `brew install ffmpeg`

**Verify**: `ffmpeg -version`

### Database Connection Error

**Lỗi**: `could not connect to server: Connection refused`

**Giải pháp**:
1. Check PostgreSQL đang chạy
2. Check DATABASE_URL trong `.env`
3. Verify user/password

```bash
# Test connection
psql postgresql://user:password@localhost:5432/video_srt

# Windows (powershell)
$env:DATABASE_URL="postgresql://user:password@localhost:5432/video_srt"
```

### GPU Not Detected

**Lỗi**: Device "gpu:0" not found, falling back to CPU

**Giải pháp**:
1. Cài đặt NVIDIA driver + CUDA 12.x
2. Cài `paddlepaddle-gpu`:
```bash
pip uninstall paddlepaddle -y
pip install paddlepaddle-gpu==3.2.1 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
```
3. Set `DEFAULT_DEVICE=gpu:0` trong `.env`

### Out of Memory (OOM)

**Lỗi**: `CUDA out of memory` hoặc `Killed (OOM)`

**Giải pháp**:
- Giảm `BATCH_OCR_SIZE` trong `.env`
- Giảm `DEFAULT_TARGET_FPS` (ít frames)
- Giảm `DEFAULT_MAX_WIDTH` (ít pixels)
- Sử dụng CPU thay vì GPU

```env
BATCH_OCR_SIZE=4
DEFAULT_TARGET_FPS=2.0
DEFAULT_MAX_WIDTH=960
DEFAULT_DEVICE=cpu
```

### Slow Processing

**Nguyên nhân**: OCR chậm, GPU không được dùng

**Giải pháp**:
1. Verify GPU availability: `DEFAULT_DEVICE=gpu:0`
2. Increase `BATCH_OCR_SIZE` (nếu GPU memory đủ)
3. Decrease `DEFAULT_TARGET_FPS`
4. Enable `CLAHE_ENHANCEMENT` để improve quality

### API Returns 404

**Lỗi**: `404 Not Found` on valid endpoint

**Giải pháp**:
1. Check server đang chạy: `http://localhost:8000/health`
2. Check endpoint URL chính xác
3. Check request method (GET/POST)
4. Check `api/routes.py` có endpoint đó không

### Test Connection

```python
# test_connection.py
import requests

url = "http://localhost:8000/health"
try:
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
```

```bash
python test_connection.py
```

---

## 💡 Tips & Best Practices

### Development

1. **Dùng virtual environment** - Tránh conflicts với system packages
2. **Reload server** - Run.py enable reload, code changes reflect immediately
3. **Test endpoints** - Dùng Swagger UI (`/docs`)
4. **Check logs** - Terminal output rất hữu ích

### Performance

1. **GPU acceleration** - Nhanh hơn CPU ~10x
2. **Batch OCR** - Xử lý multiple frames cùng lúc
3. **Caching** - OCR models được cache, không init lại mỗi lần
4. **Parameter tuning** - `target_fps`, `conf_min` ảnh hưởng đến quality/speed

### Code Quality

1. **Type hints** - Help với debugging và IDE autocomplete
2. **Docstrings** - Document tất cả public functions
3. **Error handling** - Luôn catch specific exceptions
4. **Testing** - Write tests cho new features

### Debugging

```python
# Quick debug prints
print(f"DEBUG: frame shape = {frame.shape}")
print(f"DEBUG: ocr result = {result}")

# Use logging (production)
import logging
logger = logging.getLogger(__name__)
logger.info(f"Extracted {len(text)} characters")
logger.error(f"OCR failed: {error}")

# Python debugger
import pdb
pdb.set_trace()  # Pause execution here
```

---

## 📚 Tài liệu thêm

- `usage/01-INSTALLATION.md` - Cài đặt chi tiết
- `usage/02-RUNNING-SERVER.md` - Chạy server
- `usage/03-DOCKER-DEPLOYMENT.md` - Docker deployment
- `usage/04-EXTRACT-SRT.md` - API examples
- `usage/05-PARAMETER-TUNING.md` - Tuning OCR
- `usage/09-CONFIGURATION.md` - Cấu hình
- `usage/10-API-REFERENCE.md` - API chi tiết

---

## 🆘 Liên hệ & Support

### Thắc mắc thường gặp

- **Q**: Làm sao tăng accuracy của OCR?
  - **A**: Tuning `target_fps`, `conf_min`, `lang`, `enhance`

- **Q**: Tại sao processing lâu?
  - **A**: Check GPU enable, reduce `target_fps`, increase `batch_size`

- **Q**: Làm sao deploy production?
  - **A**: Xem `usage/03-DOCKER-DEPLOYMENT.md`

- **Q**: Có test suite không?
  - **A**: Chưa, contributions welcome!

---

## ✅ Checklist khi vào dự án

- [ ] Clone repository
- [ ] Tạo virtual environment
- [ ] Cài dependencies (`pip install -r requirements.txt`)
- [ ] Cài FFmpeg
- [ ] Setup PostgreSQL database
- [ ] Copy `.env.example` → `.env` và edit
- [ ] Chạy migrations (`python migrations/migrate.py upgrade`)
- [ ] Start server (`python run.py`)
- [ ] Test health endpoint (`http://localhost:8000/health`)
- [ ] Browse API docs (`http://localhost:8000/docs`)
- [ ] Đọc `usage/` documents

---

**Good luck! 🚀 Happy coding!**

---

*Last updated: February 2026*
