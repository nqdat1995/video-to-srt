# Running the Server (Chạy Server)

## Development Mode (Auto-reload)

### Option 1: Using uv (Recommended - Fastest)

```bash
# Fastest option with auto-reload
uv run python run.py
```

### Option 2: Python Direct

```bash
python run.py
```

## Production Mode (Multiple Workers)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Server with Custom Environment Variables

### Windows

```bash
set OCR_CACHE_MAX=8
set BATCH_OCR_SIZE=16
set DEFAULT_DEVICE=cpu
python run.py
```

### Linux/macOS

```bash
export OCR_CACHE_MAX=8
export BATCH_OCR_SIZE=16
export DEFAULT_DEVICE=cpu
python run.py
```

## Using .env File

### Create .env File

```bash
# Copy template (if exists)
cp .env.example .env

# Or create manually with your settings
```

### Example .env File

```bash
# Server
HOST=0.0.0.0
PORT=8000

# OCR Settings
DEFAULT_DEVICE=cpu        # or gpu:0 for GPU
DEFAULT_LANG=vi
DEFAULT_TARGET_FPS=4.0

# Performance
OCR_CACHE_MAX=4
BATCH_OCR_SIZE=8
LOG_LEVEL=WARNING

# TTS Settings (Optional)
TTS_ENABLED=true
TTS_API_KEY=your_key_here
TTS_API_TOKEN=your_token_here
TTS_DEFAULT_VOICE=BV074_streaming
TTS_OUTPUT_DIR=./tts_output
TTS_TEMP_DIR=./tts_temp
TTS_BATCH_SIZE=1000
TTS_MAX_RETRIES=3

# Database (Optional - for video uploads)
DATABASE_URL=postgresql://video_user:video_password@localhost:5432/video_srt_db
UPLOAD_DIR=./uploads
MAX_VIDEOS_PER_USER=10
MAX_UPLOAD_SIZE_MB=500
```

### Run with .env Settings

```bash
# Just run normally, settings auto-loaded
python run.py
```

## Access API

After server starts (usually on port 8000):

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)
- **Health Check**: http://localhost:8000/health

## Testing Server

```bash
# Simple health check
curl http://localhost:8000/health

# Response: {"status": "ok"}
```

## Troubleshooting Server Issues

### Slow Processing

```bash
# Check current settings
curl http://localhost:8000/health

# Try GPU if available
DEFAULT_DEVICE=gpu:0

# Reduce quality if speed is critical
DEFAULT_TARGET_FPS=2.0
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

### Port Already in Use

```bash
# Change port in command
uvicorn app.main:app --port 8001

# Or set in .env
PORT=8001
```

### Module Import Errors

```bash
# Verify you're in the correct directory
cd d:\LEARN\video-to-srt

# Activate virtual environment
venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```
