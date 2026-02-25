# Video-to-SRT Usage Documentation

Tài liệu hướng dẫn sử dụng Video-to-SRT API và công cụ.

## Quick Navigation

### Getting Started
- [**01-INSTALLATION.md**](01-INSTALLATION.md) - Setup and prerequisites
- [**02-RUNNING-SERVER.md**](02-RUNNING-SERVER.md) - Start the server
- [**03-DOCKER-DEPLOYMENT.md**](03-DOCKER-DEPLOYMENT.md) - Docker deployment options

### Using the API
- [**04-EXTRACT-SRT.md**](04-EXTRACT-SRT.md) - Extract subtitles from videos
- [**05-PARAMETER-TUNING.md**](05-PARAMETER-TUNING.md) - Optimize extraction parameters
- [**06-VIDEO-PROCESSING.md**](06-VIDEO-PROCESSING.md) - Blur and add subtitles to videos
- [**07-TTS-SYNTHESIS.md**](07-TTS-SYNTHESIS.md) - Text-to-speech audio synthesis
- [**08-VIDEO-UPLOAD.md**](08-VIDEO-UPLOAD.md) - Upload videos with quota management

### Reference & Troubleshooting
- [**09-CONFIGURATION.md**](09-CONFIGURATION.md) - Configuration and troubleshooting
- [**10-API-REFERENCE.md**](10-API-REFERENCE.md) - Complete API endpoint reference

## Common Use Cases

### I want to extract subtitles from a video

1. Start the server: [02-RUNNING-SERVER.md](02-RUNNING-SERVER.md)
2. Extract subtitles: [04-EXTRACT-SRT.md](04-EXTRACT-SRT.md)
3. Optimize parameters: [05-PARAMETER-TUNING.md](05-PARAMETER-TUNING.md)

### I want to add subtitles to a video

1. Extract subtitles: [04-EXTRACT-SRT.md](04-EXTRACT-SRT.md)
2. Process video: [06-VIDEO-PROCESSING.md](06-VIDEO-PROCESSING.md)

### I want to generate audio from subtitles

1. Extract subtitles: [04-EXTRACT-SRT.md](04-EXTRACT-SRT.md)
2. Generate audio: [07-TTS-SYNTHESIS.md](07-TTS-SYNTHESIS.md)

### I want to upload and manage videos

1. Setup: [01-INSTALLATION.md](01-INSTALLATION.md)
2. Upload videos: [08-VIDEO-UPLOAD.md](08-VIDEO-UPLOAD.md)

### The system is running slowly

1. Check configuration: [09-CONFIGURATION.md](09-CONFIGURATION.md)
2. Tune parameters: [05-PARAMETER-TUNING.md](05-PARAMETER-TUNING.md)

### I'm getting an error

1. Check troubleshooting: [09-CONFIGURATION.md](09-CONFIGURATION.md)
2. See API reference: [10-API-REFERENCE.md](10-API-REFERENCE.md)

## Key Features

✓ **Extract SRT Subtitles** - Extract text and coordinates from video subtitles using OCR
✓ **Extract Embedded Subtitles** - Fast 20x extraction if video has embedded subtitles
✓ **Blur Original Subtitles** - Replace or blur original video subtitles
✓ **Add Subtitles** - Embed extracted subtitles into video
✓ **Generate Audio** - Synthesize speech from subtitle text
✓ **Upload & Manage** - Upload videos with automatic quota and cleanup
✓ **Batch Processing** - Process multiple files concurrently
✓ **Async Processing** - Monitor long-running tasks with progress tracking
✓ **GPU Support** - 3-4x faster processing with NVIDIA GPU
✓ **Multiple Languages** - Support for Vietnamese, English, Chinese, Japanese

## Quick Start

```bash
# 1. Installation
cd d:\LEARN\video-to-srt
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 2. Run server
python run.py

# 3. Test API
curl http://localhost:8000/health

# 4. Extract subtitles
curl -X POST "http://localhost:8000/extract-srt" \
  -H "Content-Type: application/json" \
  -d '{"video": "video.mp4", "lang": "vi"}'
```

## API Documentation

Interactive API documentation at: http://localhost:8000/docs

## System Requirements

- Python 3.10+
- FFmpeg with ffprobe
- 4GB+ RAM (8GB+ recommended)
- NVIDIA GPU optional (3-4x faster)

## Project Structure

```
usage/
├── 01-INSTALLATION.md          # Installation and setup
├── 02-RUNNING-SERVER.md        # Start the server
├── 03-DOCKER-DEPLOYMENT.md     # Docker configuration
├── 04-EXTRACT-SRT.md           # SRT extraction guide
├── 05-PARAMETER-TUNING.md      # Parameter optimization
├── 06-VIDEO-PROCESSING.md      # Video blur and subtitle
├── 07-TTS-SYNTHESIS.md         # Text-to-speech synthesis
├── 08-VIDEO-UPLOAD.md          # Video upload management
├── 09-CONFIGURATION.md         # Configuration and troubleshooting
├── 10-API-REFERENCE.md         # Complete API reference
└── README.md                   # This file
```

## Performance Benchmarks

| Task | Time | Device |
|------|------|--------|
| Extract 1 min video | 30-45s | CPU |
| Extract 1 min video | 10-15s | GPU (GTX 1060) |
| Generate 1 min audio | 2-5s | TTS |
| Blur 1 min video | 20-30s | CPU/GPU |
| Add subtitles 1 min | 30-45s | CPU/GPU |

## Support & Help

1. **Installation issues**: See [01-INSTALLATION.md](01-INSTALLATION.md)
2. **Server problems**: See [02-RUNNING-SERVER.md](02-RUNNING-SERVER.md)
3. **API help**: See [10-API-REFERENCE.md](10-API-REFERENCE.md)
4. **Troubleshooting**: See [09-CONFIGURATION.md](09-CONFIGURATION.md)
5. **Parameter tuning**: See [05-PARAMETER-TUNING.md](05-PARAMETER-TUNING.md)

## Configuration Files

- **`.env`** - Environment variables (create from template)
- **`docker-compose.yml`** - Docker services
- **`requirements.txt`** - Python dependencies

See [09-CONFIGURATION.md](09-CONFIGURATION.md) for detailed setup.

## Next Steps

1. **Getting Started**: Read [01-INSTALLATION.md](01-INSTALLATION.md)
2. **Run Server**: Follow [02-RUNNING-SERVER.md](02-RUNNING-SERVER.md)
3. **Extract Subtitles**: Try [04-EXTRACT-SRT.md](04-EXTRACT-SRT.md)
4. **Optimize**: Use [05-PARAMETER-TUNING.md](05-PARAMETER-TUNING.md)

## Additional Resources

- Main README: See `../README.md`
- Docker guide: See `../DOCKER.md`
- Project structure: See [09-CONFIGURATION.md](09-CONFIGURATION.md#project-structure)

---

**Last Updated**: 2026-02-25
**Documentation Version**: 1.0
