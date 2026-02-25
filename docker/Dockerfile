# Multi-stage build for video-to-srt FastAPI application
# Optimized for PaddleOCR 3.0.0 with PaddlePaddle 3.0.0 (CPU)
# Python 3.10 for better compatibility

# Stage 1: Builder - dependencies installation
FROM python:3.10-slim-bookworm AS builder

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies to /app/venv
RUN python -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.10-slim-bookworm AS runtime

# Install runtime dependencies only (no build tools)
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
    # Runtime utilities
    ca-certificates \
    curl \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/venv /app/venv

# Set working directory
WORKDIR /app

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p /app/uploads /app/cache /app/logs && \
    chmod -R 755 /app/uploads /app/cache /app/logs

# Set environment
ENV PATH="/app/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    # PaddleOCR cache location
    HUB_HOME=/app/cache \
    # Disable MKL-DNN (OneDNN fix for PaddleOCR stability)
    FLAGS_use_mkldnn=0 \
    # Suppress verbose logging
    TF_CPP_MIN_LOG_LEVEL=2 \
    PYTHONWARNINGS=ignore

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default entrypoint
ENTRYPOINT ["python"]
CMD ["run.py"]
