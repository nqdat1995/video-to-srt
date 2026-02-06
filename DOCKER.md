# Docker Deployment Guide
This guide explains how to build and run the video-to-srt application using Docker.

## Prerequisites

- Docker 20.10+ installed
- Docker Compose 2.0+ installed
- For GPU support: NVIDIA Docker runtime installed
- FFmpeg (will be installed in Docker image)
- PaddleOCR 2.7.0.3 with PaddlePaddle 3.0.0 (stable versions without OneDNN issues)

## Quick Start

### CPU Version (Default)

```bash
# Build and start the service
docker-compose up -d video-to-srt

# Check logs
docker-compose logs -f video-to-srt

# Access API at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### GPU Version (Faster OCR)

```bash
# Build and start GPU service
docker-compose --profile gpu up -d video-to-srt-gpu

# Check logs
docker-compose logs -f video-to-srt-gpu

# Access API at http://localhost:8001
```

### Development Mode (Hot-Reload)

```bash
# Start development service with hot-reload
docker-compose -f docker-compose.dev.yml up -d

# Logs with auto-follow
docker-compose -f docker-compose.dev.yml logs -f

# API available at http://localhost:8000
```

### Production Mode with Multiple Workers

```bash
# Start production service with 4 workers
docker-compose up -d video-to-srt

# Scale to multiple instances (requires load balancer)
docker-compose up -d --scale video-to-srt=4
```

## Build Options

### Build CPU Image

```bash
docker build -t video-to-srt:cpu -f Dockerfile .
```

### Build GPU Image

```bash
docker build -t video-to-srt:gpu -f Dockerfile.gpu .
```

### Build with Custom Cache

```bash
# Use BuildKit for better caching
DOCKER_BUILDKIT=1 docker build -t video-to-srt:latest .
```

## Running Containers

### Run CPU Container

```bash
docker run -d \
--name video-to-srt \
-p 8000:8000 \
-v $(pwd)/uploads:/app/uploads \
-v $(pwd)/cache:/app/cache \
-e DEFAULT_DEVICE=cpu \
video-to-srt:cpu
```

### Run GPU Container

```bash
docker run -d \
--name video-to-srt-gpu \
--gpus all \
-p 8001:8000 \
-v $(pwd)/uploads:/app/uploads \
-v $(pwd)/cache:/app/cache \
-e DEFAULT_DEVICE=gpu:0 \
video-to-srt:gpu
```

## Environment Variables

Configure the application via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |
| `WORKERS` | `1` | Number of worker processes |
| `DEFAULT_DEVICE` | `cpu` | OCR device (`cpu` or `gpu:0`) |
| `DEFAULT_LANG` | `vi` | Default OCR language |
| `DEFAULT_TARGET_FPS` | `4.0` | Target sampling FPS (1.0-32.0) |
| `LOG_LEVEL` | `WARNING` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CUDA_VISIBLE_DEVICES` | `0` | GPU device ID (GPU only) |
| `OCR_CACHE_MAX` | `4` | Max OCR engines to cache |
| `BATCH_OCR_SIZE` | `8` | OCR batch size for GPU |
| `FLAGS_use_mkldnn` | `0` | Disable MKL-DNN (OneDNN fix) |

Example with `.env` file:

```bash
# .env
DEFAULT_DEVICE=cpu
DEFAULT_LANG=vi
DEFAULT_TARGET_FPS=4.0
LOG_LEVEL=WARNING
OCR_CACHE_MAX=4
BATCH_OCR_SIZE=8
FLAGS_use_mkldnn=0
```

## Volume Mounts

### Required Volumes

- `./uploads:/app/uploads` - Store uploaded video files
- `./cache:/app/cache` - Cache PaddleOCR models
- `./logs:/app/logs` - Application logs

### Optional Volumes

- `./.env:/app/.env:ro` - Environment configuration (read-only)

## Health Checks

The container includes built-in health checks:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' video-to-srt

# Manual health check
curl http://localhost:8000/health
```

## Docker Compose Commands

### Start Services

```bash
# CPU service
docker-compose up -d video-to-srt

# GPU service
docker-compose --profile gpu up -d video-to-srt-gpu

# All services
docker-compose --profile gpu up -d
```

### Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f video-to-srt

# Last 100 lines
docker-compose logs --tail=100 video-to-srt
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

### OneDNN Inference Error (ConvertPirAttribute2RuntimeAttribute)

**Issue**: `NotImplementedError: (Unimplemented) ConvertPirAttribute2RuntimeAttribute not support [pir::ArrayAttribute<pir::DoubleAttribute>]`

**Solution**: This is already fixed in our Docker images and requirements using:
- PaddleOCR 2.7.0.3 (stable version)
- PaddlePaddle 3.0.0 (compatible version)
- Environment flag: `FLAGS_use_mkldnn=0` (disables MKL-DNN backend)

If you still encounter this error:
```bash
# Ensure container has the fix applied
docker-compose logs -f

# Rebuild without cache to get latest dependencies
docker-compose build --no-cache video-to-srt
docker-compose up -d
```

### GPU Not Detected

```bash
# Check NVIDIA Docker runtime
docker run --rm --gpus all nvidia/cuda:12.3.0-base-ubuntu22.04 nvidia-smi

# If error, install nvidia-docker2
# Ubuntu/Debian:
sudo apt-get install nvidia-docker2
sudo systemctl restart docker
```

### Container Won't Start

```bash
# Check logs
docker-compose logs video-to-srt

# Check container status
docker ps -a | grep video-to-srt

# Inspect container
docker inspect video-to-srt
```

### Permission Issues

```bash
# Fix volume permissions
sudo chown -R $USER:$USER uploads cache logs

# Or run container with specific user
docker-compose run --user $(id -u):$(id -g) video-to-srt
```

### Out of Memory

```bash
# Limit container memory
docker-compose up -d --memory=4g video-to-srt

# Or in docker-compose.yml:
# deploy:
#   resources:
#     limits:
#       memory: 4G
```

### Cache Issues

```bash
# Clear PaddleOCR cache
rm -rf cache/*

# Rebuild without cache
docker-compose build --no-cache
```

## Performance Tuning

### CPU Optimization

```yaml
# docker-compose.yml
environment:
- WORKERS=4  # Increase workers
- OMP_NUM_THREADS=4  # OpenMP threads
```

### GPU Optimization

```yaml
# docker-compose.yml
environment:
- CUDA_VISIBLE_DEVICES=0,1  # Use multiple GPUs
- WORKERS=2  # One worker per GPU
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
   restart: always  # or unless-stopped
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
tar -xzf backup-20260205.tar.gz
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
-F "video_file=@test.mp4" \
-F "lang=vi" \
-F "device=cpu"

# Response: {"task_id": "abc123", "status": "processing"}

# 3. Check progress
curl "http://localhost:8000/task-status/abc123"

# 4. Download result when done
curl "http://localhost:8000/download-srt/abc123" -o output.srt
```

## Support

For issues and questions:
- Check logs: `docker-compose logs -f`
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health
