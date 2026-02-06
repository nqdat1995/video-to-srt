# Multi-stage build for video-to-srt FastAPI application
# Optimized for PaddleOCR 2.7.x with Python 3.10
# Note: Using stable PaddleOCR 2.7.0.3 to avoid OneDNN inference issues

# Stage 1: Base image with system dependencies
FROM python:3.10-slim-bookworm AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
   # FFmpeg for video processing
   ffmpeg \
   # OpenCV dependencies
   libgl1-mesa-glx \
   libglib2.0-0 \
   libsm6 \
   libxext6 \
   libxrender-dev \
   libgomp1 \
   # Cleanup
   && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Stage 2: Dependencies installation
FROM base AS dependencies

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
   pip install --no-cache-dir -r requirements.txt

# Stage 3: Application
FROM dependencies AS application

# Copy application code
COPY . .

# Create directories for uploads and cache
RUN mkdir -p /app/uploads /app/cache /app/logs && \
   chmod -R 755 /app/uploads /app/cache /app/logs

# Environment variables
ENV PYTHONUNBUFFERED=1 \
   PYTHONDONTWRITEBYTECODE=1 \
   # PaddleOCR cache
   HUB_HOME=/app/cache \
   # Uvicorn settings
   HOST=0.0.0.0 \
   PORT=8000 \
   WORKERS=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
   CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Run application
CMD ["python", "run.py"]
