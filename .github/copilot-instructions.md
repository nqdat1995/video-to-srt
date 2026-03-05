# GitHub Copilot Instructions for video-to-srt

## Project Overview
FastAPI application extracting subtitles from videos via OCR (PaddleOCR v3) and converting to SRT format. Layered architecture: API Routes → Services → Utilities.

## Architectural Layers

**API Layer** (`app/api/routes.py`): HTTP endpoints accepting `VideoExtractionRequest` or `VideoExtractionByIdRequest`, delegating to services via `BackgroundTasks`.

**Service Layer** (`app/services/`):
- `ocr_service`: PaddleOCR instance with caching (`OcrEntry` internal model)
- `video_processor`: Frame sampling (4 FPS default) + preprocessing (letterbox detection, ROI extraction, CLAHE)
- `srt_service`: Text assembly, debouncing, fuzzy matching with `similarity_threshold` parameter
- `ffmpeg_service`, `tts_service`, `storage_service`, `database_service`: Supporting operations

**Model Layer** (`app/models/`):
- `requests.py`: User input validation (Pydantic BaseModel)
- `responses.py`: API response schemas
- `internal.py`: `CueDraft` (subtitle state), `OcrEntry` (cache entries), `Frame`

**Config** (`app/core/config.py`): Single source for environment-configurable settings; all parameters exposed via `Settings` class.

## Critical Patterns

### Async Task Tracking
```python
# Routes use BackgroundTasks for long operations, tracking via _TASKS dict
from fastapi import BackgroundTasks
_TASKS = {}  # UUID → {"status": "processing", "progress": 0, "result": None}
tasks.add_task(process_video, video_id, background_callback=update_task_progress)
```

### Service Singletons
Instantiate once at module level, reuse across requests:
```python
# app/services/ocr_service.py
ocr_instance = PaddleOCR(...)
def extract_text(frame): return ocr_instance.ocr(frame)
```

### Request/Response Separation
- Input validation: `app/models/requests.py` (e.g., `VideoExtractionRequest`)
- Output schemas: `app/models/responses.py` (e.g., `ExtractionResponse`)
- Internal state: `app/models/internal.py` (e.g., `CueDraft`, `OcrEntry`)

### Hash-Gating for Deduplication
Prevent redundant frame processing:
```python
frame_hash = compute_frame_hash(frame)  # app/utils/hash_utils.py
if frame_hash in processed_hashes and time_delta < HASH_THRESHOLD:
    skip_processing()  # Reuse cached OCR result
```

### SRT Assembly with Fuzzy Matching
Text assembly uses `similarity_threshold` (configurable in `config.py`) for cue merging:
```python
# app/services/srt_service.py
if fuzz.ratio(cue1.text, cue2.text) > settings.similarity_threshold:
    merge_cues(cue1, cue2)  # Debounce similar subtitles
```

### Database & Migrations
- SQLAlchemy ORM in `app/core/database.py`
- Migrations: `migrations/` folder, numeric naming (`001_initial_schema.py`, `002_add_audio_quota_columns.py`)
- Run: `python migrations/migrate.py up` or `migrate.migrate_down()`

### Configuration Convention
All tunable parameters in `app/core/config.py`:
```python
class Settings(BaseSettings):
    FRAME_SAMPLE_RATE: int = 4  # FPS
    SIMILARITY_THRESHOLD: float = 0.85
    LETTERBOX_THRESHOLD: int = 10
    # Use Field(default=..., description="...") for documentation
```
Access via `from app.core.config import settings`.

### Error Handling
Use `HTTPException` for API errors; propagate exceptions with context:
```python
from fastapi import HTTPException
if not video_exists:
    raise HTTPException(status_code=404, detail="Video not found")
```

### Logging
Suppress PaddleOCR verbose output in `app/main.py`:
```python
os.environ["PADDLEOCR_HOME"] = "/path/to/cache"  # Quiet mode
```

## Video Processing Pipeline
1. **Frame Sampling**: Extract at configurable FPS (default 4)
2. **Preprocessing**: Letterbox detection → ROI extraction → CLAHE enhancement (`app/services/video_processor.py`)
3. **OCR**: PaddleOCR with hash-based caching (`app/services/ocr_service.py`)
4. **Text Assembly**: Multi-line grouping, confidence filtering
5. **SRT Generation**: Debouncing, fuzzy matching, similarity thresholding (`app/services/srt_service.py`)
6. **Output**: SRT file + optional TTS synthesis

## Key File Locations
- Routes: `app/api/routes.py`
- Models: `app/models/{requests,responses,internal,database}.py`
- Services: `app/services/{ocr_service,video_processor,srt_service,ffmpeg_service,tts_service,storage_service,database_service}.py`
- Utilities: `app/utils/{hash_utils,image_utils,text_utils}.py`
- Config: `app/core/config.py`
- Logging: `app/core/logging_config.py`

## Development
- Start: `python run.py` (auto-reload enabled)
- Environment: `.env` file or environment variables (prefix-based)
- Dependencies: `requirements.txt` (PaddleOCR 2.7.0.3, PaddlePaddle 3.0.0 with `PADDLE_DISABLE_FAST_MATH=1`)
- Docker: `docker/Dockerfile` and `docker-compose.yml` available

## External Dependencies
- **PaddleOCR**: OCR engine; requires `PADDLE_DISABLE_FAST_MATH=1` flag
- **FFmpeg/FFprobe**: Video frame capture, subtitle extraction, rendering
- **PostgreSQL**: Video metadata + user quotas
- **WebSocket**: TTS API integration (optional)

## Preference Order
In extraction requests: `video_id` (DB lookup) > `video` (local path).
