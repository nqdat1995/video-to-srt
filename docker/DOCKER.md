# Docker Deployment Guide

Complete guide to building and deploying the video-to-srt FastAPI application using Docker and Docker Compose.

## Prerequisites

- **Docker**: 20.10+ 
- **Docker Compose**: 2.0+
- **For GPU support**: 
  - NVIDIA Container Toolkit (nvidia-docker)
  - NVIDIA GPU with CUDA 12.x support
  - NVIDIA Docker runtime configured

## Key Components

- **Python**: 3.10 (slim-bookworm for CPU, CUDA 12.3.1 base for GPU)
- **PaddleOCR**: 3.0.0 (latest stable)
- **PaddlePaddle**: 3.0.0 CPU or 3.0.0 GPU (CUDA 12.x)
- **FastAPI**: 0.128.1
- **FFmpeg**: For video processing
- **uvicorn**: ASGI server with reload support

## Quick Start

### CPU Version (Default)

```bash
# Build and start the service
docker-compose up -d video-to-srt

# Check logs
docker-compose logs -f video-to-srt

# Access API at http://localhost:8000
# API docs at http://localhost:8000/docs
# Health check at http://localhost:8000/health
```

### GPU Version (Faster OCR - Requires NVIDIA GPU)

```bash
# Build and start GPU service with profile
docker-compose --profile gpu up -d video-to-srt-gpu

# Check logs
docker-compose logs -f video-to-srt-gpu

# Access API at http://localhost:8001
# API docs at http://localhost:8001/docs
```

### Development Mode (Hot-Reload)

```bash
# Start development service with hot-reload
docker-compose -f docker-compose.dev.yml up -d

# Logs with auto-follow
docker-compose -f docker-compose.dev.yml logs -f

# API available at http://localhost:8000
# Code changes automatically reload
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (careful: deletes cache and uploads)
docker-compose down -v

# Stop specific service
docker-compose stop video-to-srt
```

## Build Options

### Build CPU Image

```bash
# Standard build
docker build -t video-to-srt:cpu -f Dockerfile .

# With BuildKit (better caching)
DOCKER_BUILDKIT=1 docker build -t video-to-srt:cpu -f Dockerfile .

# No cache (forces fresh download)
docker build --no-cache -t video-to-srt:cpu -f Dockerfile .
```

### Build GPU Image

```bash
# Requires NVIDIA CUDA toolkit
docker build -t video-to-srt:gpu -f Dockerfile.gpu .

# With BuildKit
DOCKER_BUILDKIT=1 docker build -t video-to-srt:gpu -f Dockerfile.gpu .
```

### Build via Docker Compose

```bash
# Build CPU service
docker-compose build video-to-srt

# Build GPU service
docker-compose build video-to-srt-gpu

# Build both
docker-compose build

# Rebuild without cache
docker-compose build --no-cache video-to-srt
```

## Running Containers

### Run CPU Container

```bash
# Basic run
docker run -d \
  --name video-to-srt \
  -p 8000:8000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/cache:/app/cache \
  -v $(pwd)/logs:/app/logs \
  -e DEFAULT_DEVICE=cpu \
  -e DEFAULT_LANG=vi \
  video-to-srt:cpu
```

### Run GPU Container

```bash
# With NVIDIA GPU
docker run -d \
  --name video-to-srt-gpu \
  --gpus all \
  -p 8001:8000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/cache:/app/cache \
  -v $(pwd)/logs:/app/logs \
  -e DEFAULT_DEVICE=gpu:0 \
  -e DEFAULT_LANG=vi \
  video-to-srt:gpu

# Or specify specific GPU
docker run -d \
  --name video-to-srt-gpu \
  --gpus device=0 \
  -p 8001:8000 \
  -e DEFAULT_DEVICE=gpu:0 \
  video-to-srt:gpu
```

### Run Interactive Container

```bash
# For debugging
docker run -it \
  -p 8000:8000 \
  -v $(pwd):/app \
  video-to-srt:cpu \
  /bin/bash
```

## Environment Variables

Configure the application via environment variables in `.env` or via docker-compose:

| Variable | CPU Default | GPU Default | Description |
|----------|-------------|-------------|-------------|
| `HOST` | `0.0.0.0` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | `8000` | Server port |
| `WORKERS` | `1` | `2` | Number of worker processes |
| `DEFAULT_DEVICE` | `cpu` | `gpu:0` | OCR device (`cpu` or `gpu:N`) |
| `DEFAULT_LANG` | `vi` | `vi` | Default OCR language (vi, en, zh, etc.) |
| `DEFAULT_TARGET_FPS` | `4.0` | `6.0` | Frame sampling rate (1.0-32.0) |
| `OCR_CACHE_MAX` | `4` | `8` | Max OCR engines in cache |
| `BATCH_OCR_SIZE` | `8` | `16` | OCR batch size (GPU benefits from larger) |
| `LOG_LEVEL` | `WARNING` | `WARNING` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CUDA_VISIBLE_DEVICES` | N/A | `0` | GPU device ID (0-based indexing) |
| `FLAGS_use_mkldnn` | `0` | `0` | Disable MKL-DNN backend (PaddleOCR fix) |
| `TF_CPP_MIN_LOG_LEVEL` | `2` | `2` | TensorFlow log level (0-3) |
| `PYTHONWARNINGS` | `ignore` | `ignore` | Python warnings handling |
| `HUB_HOME` | `/app/cache` | `/app/cache` | PaddleOCR model cache directory |

### Example .env File

```bash
# .env
# Server
HOST=0.0.0.0
PORT=8000
WORKERS=1

# OCR Configuration
DEFAULT_DEVICE=cpu
DEFAULT_LANG=vi
DEFAULT_TARGET_FPS=4.0

# Performance Tuning
OCR_CACHE_MAX=4
BATCH_OCR_SIZE=8

# Logging
LOG_LEVEL=WARNING

# PaddleOCR Fixes
FLAGS_use_mkldnn=0
TF_CPP_MIN_LOG_LEVEL=2
PYTHONWARNINGS=ignore
```

### Load Environment Variables

```bash
# From docker-compose (automatic)
docker-compose up -d

# From CLI (overrides .env)
docker-compose -e DEFAULT_DEVICE=gpu:0 up -d

# From .env.example template
cp .env.example .env
# Edit .env with your settings
docker-compose up -d
```

## Volume Mounts

### Required Volumes

- `./uploads:/app/uploads` - Storage for uploaded video files
- `./cache:/app/cache` - PaddleOCR model cache (persisted between runs)
- `./logs:/app/logs` - Application logs

### Optional Volumes

- `./.env:/app/.env:ro` - Environment configuration (read-only recommended)

### Data Persistence

```bash
# Data is automatically persisted in:
# - ./uploads/     - uploaded videos
# - ./cache/       - OCR models (1-2GB)
# - ./logs/        - application logs

# Backup data
tar -czf backup-$(date +%Y%m%d).tar.gz uploads/ cache/ logs/

# Restore data
tar -xzf backup-20260207.tar.gz
```

## Health Checks

All containers include built-in health checks that verify the API is responsive:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' video-to-srt

# Health statuses: starting, healthy, unhealthy

# Manual health check
curl http://localhost:8000/health

# Response: {"status": "ok"}

# Full health info
docker inspect video-to-srt | grep -A 5 "Health"
```

### Health Check Configuration

- **Interval**: 30 seconds (checks every 30s)
- **Timeout**: 10 seconds (fails if no response in 10s)
- **Start Period**: 40s CPU / 60s GPU (grace period after start)
- **Retries**: 3 (marks unhealthy after 3 failed checks)

## Docker Compose Commands

### Service Management

```bash
# Start services (background)
docker-compose up -d video-to-srt

# Start with profile (GPU)
docker-compose --profile gpu up -d video-to-srt-gpu

# Start all services
docker-compose --profile gpu up -d

# Rebuild before starting
docker-compose up -d --build

# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes cache/uploads/logs)
docker-compose down -v

# Restart services
docker-compose restart video-to-srt
```

### Logs and Monitoring

```bash
# View logs (follow mode)
docker-compose logs -f video-to-srt

# View last 100 lines
docker-compose logs --tail=100 video-to-srt

# View logs for all services
docker-compose logs -f

# View logs with timestamps
docker-compose logs -f --timestamps

# View specific service logs
docker-compose logs video-to-srt video-to-srt-gpu
```

### Container Inspection

```bash
# List running containers
docker-compose ps

# Show detailed container info
docker inspect video-to-srt

# Check container stats (CPU, memory)
docker stats video-to-srt
```

### Database/Cache Management

```bash
# Clean up old images
docker image prune -a

# Remove stopped containers
docker-compose rm

# Clear volume cache (⚠️ deletes models)
docker volume rm video-to-srt_cache

# Prune unused volumes
docker volume prune
```

### Rebuild Services

```bash
# Rebuild specific service
docker-compose build video-to-srt

# Rebuild and restart
docker-compose up -d --build video-to-srt

# Force rebuild (no cache)
docker-compose build --no-cache video-to-srt
```

## Troubleshooting

### PaddleOCR OneDNN Error

**Error**: `NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support`

**Solution**: Already fixed in our configuration:
- Using PaddleOCR 3.0.0 (latest stable)
- Using PaddlePaddle 3.0.0 (compatible)
- Environment: `FLAGS_use_mkldnn=0` disables problematic backend

```bash
# If still occurring, rebuild without cache
docker-compose build --no-cache video-to-srt
docker-compose up -d
```

### Container Won't Start

```bash
# Check logs
docker-compose logs video-to-srt

# Full logs with timestamps
docker-compose logs --timestamps video-to-srt

# Inspect container
docker inspect video-to-srt

# Try running in foreground for debugging
docker-compose run video-to-srt python -c "import paddleocr; print('OK')"
```

### GPU Not Detected

```bash
# Check NVIDIA Docker runtime
docker run --rm --gpus all nvidia/cuda:12.3.1-base-ubuntu22.04 nvidia-smi

# If error, install nvidia-docker
# Ubuntu:
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker

# Verify
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.3.1-base-ubuntu22.04 nvidia-smi
```

### Permission Issues

```bash
# Fix directory ownership
sudo chown -R $USER:$USER uploads cache logs

# Or run with specific user
docker-compose run --user $(id -u):$(id -g) video-to-srt python run.py
```

### Out of Memory (OOM)

```bash
# Check memory usage
docker stats video-to-srt

# Reduce batch size in .env
OCR_CACHE_MAX=2
BATCH_OCR_SIZE=4

# Limit container memory
docker-compose up -d --memory=2g video-to-srt

# Or in docker-compose.yml under deploy.resources.limits
```

### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Use different port
docker run -p 9000:8000 video-to-srt:cpu

# Or modify docker-compose.yml
# ports:
#   - "9000:8000"
```

### Cache Issues / Stale Models

```bash
# Clear cache completely
docker volume rm video-to-srt_cache

# Or manually
rm -rf cache/*

# Rebuild will re-download models
docker-compose up -d
```

### Windows-Specific Issues

```bash
# Enable WSL 2 for Docker Desktop
# Settings > Resources > WSL Integration

# Use correct path format in docker-compose.yml
volumes:
  - ${PWD}/uploads:/app/uploads  # Instead of $(pwd)

# Or use absolute Windows path
volumes:
  - C:/Projects/video-to-srt/uploads:/app/uploads
```

## Performance Tuning

### CPU Optimization

```yaml
# docker-compose.yml
environment:
  - WORKERS=4  # Increase workers
  - OMP_NUM_THREADS=4  # OpenMP threads
```

### GPU Optimization

```yaml
# docker-compose.yml
environment:
  - CUDA_VISIBLE_DEVICES=0,1  # Use multiple GPUs
  - WORKERS=2  # One worker per GPU
  - BATCH_OCR_SIZE=32  # Larger batches for GPU
```

### Memory Limits

```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
    reservations:
      memory: 4G
```

## Production Deployment

### With Nginx Reverse Proxy

```nginx
# nginx.conf
upstream video_to_srt {
  server localhost:8000;
}

server {
  listen 80;
  server_name example.com;

  client_max_body_size 500M;

  location / {
    proxy_pass http://video_to_srt;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 600s;
  }
}
```

### With Auto-Restart

```yaml
# docker-compose.yml
services:
  video-to-srt:
    restart: always  # or unless-stopped
```

### With Logging Driver

```yaml
# docker-compose.yml
services:
  video-to-srt:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Security Best Practices

1. **Don't run as root**:
   ```dockerfile
   RUN useradd -m -u 1000 appuser
   USER appuser
   ```

2. **Use read-only volumes**:
   ```yaml
   - ./.env:/app/.env:ro
   ```

3. **Limit resources**:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '4'
         memory: 8G
   ```

4. **Use secrets for sensitive data**:
   ```yaml
   secrets:
     - api_key
   ```

## Maintenance

### Update Dependencies

```bash
# Pull latest base image
docker pull python:3.10-slim-bookworm

# Rebuild with latest packages
docker-compose build --pull video-to-srt
```

### Backup Data

```bash
# Backup uploads and cache
tar -czf backup-$(date +%Y%m%d).tar.gz uploads/ cache/

# Restore
tar -xzf backup-20260207.tar.gz
```

### Clean Up

```bash
# Remove stopped containers
docker-compose rm

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune
```

## Example Usage

```bash
# 1. Start service
docker-compose up -d video-to-srt

# 2. Upload and process video
curl -X POST "http://localhost:8000/extract-srt-async" \
  -H "Content-Type: application/json" \
  -d '{
    "video": "uploads/test.mp4",
    "lang": "vi",
    "device": "cpu"
  }'

# Response: {"task_id": "abc123", "status": "processing"}

# 3. Check progress
curl "http://localhost:8000/task/abc123"

# 4. View health
curl "http://localhost:8000/health"
```

## Support

For issues and questions:
- Check logs: `docker-compose logs -f`
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health
