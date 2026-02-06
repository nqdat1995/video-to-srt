# Logging Configuration Guide

This document explains how to control logging output from the video-to-srt application and its dependencies (especially PaddleOCR).

## Quick Start

To suppress PaddleOCR debug logs and minimize terminal output:

```bash
# Using uv (recommended)
uv run python run.py

# Using Python directly
python run.py
```

By default, the application runs with `LOG_LEVEL=WARNING`, which suppresses all DEBUG and INFO logs from PaddleOCR.

**Note:** You may still see occasional WARNING messages like `"Since the angle classifier is not initialized..."` during OCR processing. These are informational warnings from PaddleOCR and are expected behavior - they do not indicate any errors. The verbose DEBUG logs (which were previously flooding the terminal) are completely suppressed.

## Configuration

### Via Environment Variable

```bash
# Set LOG_LEVEL before running
set LOG_LEVEL=WARNING
uv run python run.py
```

### Via .env File

Create or edit `.env` file in the project root:

```env
LOG_LEVEL=WARNING
```

Then run normally:
```bash
uv run python run.py
```

### Docker

```bash
# Run with custom log level
docker-compose up -d
# Or modify docker-compose.yml to change LOG_LEVEL environment variable
```

## Log Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| `CRITICAL` | Only critical errors | Production - minimal output |
| `ERROR` | Errors and critical messages | Production environments |
| `WARNING` | Warnings, errors (default) | Standard operation - recommended |
| `INFO` | Info messages, warnings, errors | Development - some detail |
| `DEBUG` | All messages (verbose) | Troubleshooting - very detailed |

## Log Level Examples

### WARNING (Default - Recommended)
```bash
set LOG_LEVEL=WARNING
uv run python run.py
```
Output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```
✅ Clean terminal, PaddleOCR debug logs suppressed

### INFO
```bash
set LOG_LEVEL=INFO
uv run python run.py
```
Output includes informational messages from dependencies.

### DEBUG
```bash
set LOG_LEVEL=DEBUG
uv run python run.py
```
⚠️ Very verbose! Shows all debug messages from PaddleOCR, Paddle, OpenCV, etc.

## What Gets Suppressed

By default (WARNING level), these loggers are suppressed:

- `paddleocr` - PaddleOCR debug messages
- `paddle` - PaddlePaddle framework logs
- `paddlex` - PaddleX utility logs
- `PIL` - Pillow image library logs
- `cv2` - OpenCV logs
- `urllib3` - HTTP client logs

## Implementation Details

### run.py
Sets up logging before importing any PaddleOCR modules:

```python
import logging
import os

# Suppress at environment level
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['PYTHONWARNINGS'] = 'ignore'

# Suppress at Python logging level
logging.basicConfig(level=logging.WARNING)
for logger_name in ['paddleocr', 'paddle', 'paddlex', 'PIL', 'cv2']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)
```

### app/main.py
Same logging suppression setup before FastAPI imports.

### app/services/ocr_service.py

**Multi-layer approach for log suppression:**

1. **Module-level logger configuration:**
   ```python
   logging.getLogger('paddleocr').setLevel(logging.WARNING)
   logging.getLogger('paddle').setLevel(logging.WARNING)
   logging.getLogger('paddlex').setLevel(logging.WARNING)
   ```

2. **During initialization (logging.disable() wrapper):**
   ```python
   logging.disable(logging.CRITICAL)
   try:
       engine = PaddleOCR(
           lang=lang,
           show_log=False  # Disable PaddleOCR's internal logging
       )
   finally:
       logging.disable(logging.NOTSET)  # Re-enable logging
   ```

3. **During inference (stdout/stderr suppression):**
   ```python
   # Suppress direct stdout/stderr writes from PaddleOCR
   with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
       result = entry.engine.ocr(img_rgb)
   ```

The three-layer approach ensures that:
- Logger output is configured at WARNING level (initialization)
- Logging module is disabled during engine creation (initialization)
- Direct stdout/stderr writes are redirected during inference (runtime)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `WARNING` | Python logging level |
| `TF_CPP_MIN_LOG_LEVEL` | `2` | TensorFlow log level (0=all, 3=error only) |
| `PYTHONWARNINGS` | `ignore` | Suppress Python warnings |

## Troubleshooting

### Still seeing logs?

**DEBUG logs still showing?** (formatted like `[2026/02/05 21:47:22] ppocr DEBUG: ...`)
1. Check your LOG_LEVEL setting - should be `WARNING` or higher
2. Restart the application to apply changes

**WARNING logs still showing?** (like `"Since the angle classifier is not initialized..."`)
These are expected and normal - they are informational warnings from PaddleOCR about features that weren't requested. The important DEBUG logs (which were previously flooding the terminal) are completely suppressed.

**Need to debug an issue?**

```bash
set LOG_LEVEL=DEBUG
uv run python run.py
```

This will show all debug messages, including PaddleOCR initialization and model loading details.

### PaddleOCR initialization messages

When first creating a PaddleOCR engine, you may see:

- `WARNING: Since the angle classifier is not initialized...` 

This is a normal PaddleOCR message indicating the angle classifier was not requested. It's non-critical.

### ccache warning

```
UserWarning: No ccache found. Please be aware that recompiling all source files may be required.
```

This is a non-critical warning from PaddleOCR about optional build optimization. It can be safely ignored.

## Performance Impact

Logging levels have minimal performance impact:
- **WARNING** (default): No noticeable overhead
- **DEBUG**: Slight overhead from generating debug messages, but still acceptable

The application will process videos at the same speed regardless of logging level.

## For Production Deployment

### Recommended Settings

```env
LOG_LEVEL=ERROR
FLAGS_use_mkldnn=0
DEFAULT_DEVICE=cpu
OCR_CACHE_MAX=4
BATCH_OCR_SIZE=8
```

This configuration:
- Minimizes terminal output (ERROR level only)
- Ensures stability (OneDNN disabled)
- Balances memory and performance

### Docker Production

```yaml
services:
  video-to-srt:
    environment:
      - LOG_LEVEL=ERROR
      - FLAGS_use_mkldnn=0
```

## See Also

- [README.md](README.md) - Main documentation
- [USAGE.md](USAGE.md) - Usage guide with examples
- [.env.example](.env.example) - Example configuration file
