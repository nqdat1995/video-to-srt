# Configuration & Troubleshooting (Cấu hình & Xử lý sự cố)

## Environment Variables

Key environment variables for tuning:

| Variable | Default | Range | Description |
|----------|---------|-------|-------------|
| `DEFAULT_DEVICE` | `cpu` | cpu, gpu:0, gpu:1 | Processing device |
| `DEFAULT_LANG` | `vi` | vi, en, zh, ja | OCR language |
| `DEFAULT_TARGET_FPS` | `4.0` | 1.0-32.0 | Frame sampling rate |
| `OCR_CACHE_MAX` | `4` | 1-16 | Max cached OCR engines |
| `BATCH_OCR_SIZE` | `8` | 1-32 | OCR batch size |
| `LOG_LEVEL` | `WARNING` | DEBUG, INFO, WARNING, ERROR | Logging verbosity |
| `DEFAULT_CONF_MIN` | `0.5` | 0.0-1.0 | Min confidence threshold |
| `UPLOAD_DIR` | `./uploads` | path | Directory to store uploaded videos |
| `MAX_VIDEOS_PER_USER` | `10` | 1-1000 | Max videos allowed per user |
| `MAX_UPLOAD_SIZE_MB` | `500` | 1-5000 | Max file size in MB |
| `SRT_OUTPUT_DIR` | `./srt_output` | path | **NEW** Directory to auto-save extracted SRT files |

## Tuning for Speed

```bash
DEFAULT_TARGET_FPS=1.0      # Minimum sampling
OCR_CACHE_MAX=1              # Reduce cache overhead
BATCH_OCR_SIZE=4             # Smaller batches
DEFAULT_DEVICE=gpu:0         # Use GPU if available
```

## Tuning for Quality

```bash
DEFAULT_TARGET_FPS=8.0       # More frames sampled
OCR_CACHE_MAX=8              # Keep more engines
BATCH_OCR_SIZE=16            # Larger batches
DEFAULT_CONF_MIN=0.7         # Higher confidence threshold
```

## Tuning for GPU

```bash
DEFAULT_DEVICE=gpu:0         # Use GPU
DEFAULT_TARGET_FPS=6.0       # Can sample more with GPU
OCR_CACHE_MAX=8              # GPU has more memory
BATCH_OCR_SIZE=32            # GPU processes batches efficiently
```

## Example .env File

```bash
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
LOG_LEVEL=WARNING

# TTS Settings
TTS_ENABLED=true
TTS_API_KEY=ddjeqjLGMn
TTS_API_TOKEN=your_api_token_here
TTS_DEFAULT_VOICE=BV074_streaming
TTS_OUTPUT_DIR=./tts_output
TTS_TEMP_DIR=./tts_temp

# Database (for video uploads)
DATABASE_URL=postgresql://video_user:video_password@localhost:5432/video_srt_db
UPLOAD_DIR=./uploads
MAX_VIDEOS_PER_USER=10
MAX_UPLOAD_SIZE_MB=500
SRT_OUTPUT_DIR=./srt_output

# PaddleOCR Fixes
FLAGS_use_mkldnn=0
```

## Common Errors & Solutions

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
# Verify FFmpeg is installed
ffmpeg -version
ffprobe -version

# Windows: Add to PATH environment variable
# macOS: brew install ffmpeg
# Linux: sudo apt-get install ffmpeg
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

# Or use CPU instead of GPU
DEFAULT_DEVICE=cpu
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

### Docker Container Won't Start

```bash
# Check logs
docker-compose logs video-to-srt

# Rebuild without cache
docker-compose build --no-cache video-to-srt

# Try again
docker-compose up -d
```

### Port Already in Use

```bash
# Change port in docker-compose.yml
# ports:
#   - "8001:8000"

# Or find and stop process using port 8000
# Windows: netstat -ano | findstr :8000
# Linux: lsof -i :8000
```

### Database Connection Error

```bash
# Check if PostgreSQL is running
docker-compose ps

# Start database
docker-compose up -d postgres

# Check connection
docker-compose exec postgres psql -U video_user -d video_srt_db
```

### TTS Service Disabled

```bash
# Check .env file has
TTS_ENABLED=true

# And required credentials
TTS_API_KEY=ddjeqjLGMn
TTS_API_TOKEN=your_token_here
```

## Performance Diagnostics

### Check Health

```bash
curl http://localhost:8000/health
# Response: {"status": "ok"}
```

### Monitor API Docs

Visit: http://localhost:8000/docs

### View Logs

```bash
# Docker logs
docker-compose logs -f video-to-srt

# Or console output if running directly
# Should see: "Uvicorn running on http://0.0.0.0:8000"
```

### Test with Small Video

Before processing large videos, test with small clip:

```python
import requests

response = requests.post(
    "http://localhost:8000/extract-srt",
    json={
        "video": "test_clip_30sec.mp4",
        "lang": "vi"
    }
)

print(f"Status: {response.status_code}")
print(f"Time: {response.json()['stats']['timing_ms']['total']}ms")
```

## Debugging Tips

### Enable Verbose Logging

```bash
LOG_LEVEL=DEBUG python run.py
```

### Check Python Version

```bash
python --version  # Should be 3.10+
```

### Verify Dependencies

```bash
python -c "import paddleocr, fastapi, torch; print('OK')"
```

### Test FFmpeg

```bash
# Basic test
ffmpeg -version

# Test video probe
ffprobe -v error -show_format -show_streams video.mp4
```

### Test GPU

```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA device: {torch.cuda.get_device_name(0)}")
print(f"CUDA version: {torch.version.cuda}")
```

## Performance Optimization Checklist

- [ ] Use GPU if available (`DEFAULT_DEVICE=gpu:0`)
- [ ] Set appropriate `target_fps` for your use case (4.0 default)
- [ ] Enable `enhance=true` for better accuracy
- [ ] Use `hash_dist_thr` to skip duplicate frames (saves 60-80% OCR)
- [ ] Adjust `debounce_frames` for stability (2 is default)
- [ ] Set `merge_gap_ms` to reduce fragmentation
- [ ] Monitor memory usage with large batch operations
- [ ] Use appropriate `OCR_CACHE_MAX` (higher = more memory)
- [ ] Test with small video snippet first
- [ ] Document your optimal settings for different video types

## Getting Help

1. Check logs: `docker-compose logs -f`
2. Visit API docs: http://localhost:8000/docs
3. Test health: `curl http://localhost:8000/health`
4. Review configuration: Check `.env` file
5. Check dependencies: `pip list`
6. Review this guide: See relevant sections above
