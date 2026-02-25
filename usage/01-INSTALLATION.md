# Installation Guide (Hướng dẫn cài đặt)

## Prerequisites (Yêu cầu hệ thống)

- Python 3.10+
- FFmpeg installed and in system PATH
- (Optional) NVIDIA GPU with CUDA 12.x for GPU acceleration

## Step 1: Clone or Download Repository

```bash
cd d:\LEARN\video-to-srt
```

## Step 2: Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

## Step 3: Install Dependencies

**Option A: Using uv (Recommended - Much Faster)**
```bash
pip install uv
uv pip install -r requirements.txt
```

**Option B: Using pip (Traditional)**
```bash
pip install -r requirements.txt
```

## Step 4: Install FFmpeg

- **Windows**: Download from https://ffmpeg.org/download.html and add to PATH
- **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
- **macOS**: `brew install ffmpeg`

## Step 5: Verify Installation

```bash
# Check Python packages
python -c "import paddleocr; import fastapi; print('OK')"

# Check FFmpeg
ffmpeg -version
```

## Troubleshooting Installation

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

# Add to PATH if needed:
# Windows: Set PATH environment variable
# macOS: brew install ffmpeg
# Linux: sudo apt-get install ffmpeg
```

### GPU Support (Optional)

```bash
# Check if GPU is available
python -c "import torch; print(torch.cuda.is_available())"

# Or for PaddlePaddle
python -c "import paddle; print(paddle.fluid.is_compiled_with_cuda())"

# Install GPU version (if CPU installed by default)
pip uninstall paddlepaddle
pip install paddlepaddle-gpu
```
