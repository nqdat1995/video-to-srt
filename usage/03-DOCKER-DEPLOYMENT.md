# Docker Deployment (Triển khai Docker)

## Quick Start

### CPU Version (Default)

```bash
docker-compose up -d video-to-srt

# View logs
docker-compose logs -f video-to-srt

# Access: http://localhost:8000
```

### GPU Version (Requires NVIDIA GPU)

```bash
docker-compose --profile gpu up -d video-to-srt-gpu

# View logs
docker-compose logs -f video-to-srt-gpu

# Access: http://localhost:8001
```

### Development Version (Hot-reload)

```bash
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Access: http://localhost:8000
```

## Stop Services

```bash
docker-compose down

# Or specific service
docker-compose down video-to-srt
```

## Common Commands

### Restart Service

```bash
docker-compose restart video-to-srt
```

### Rebuild Image

```bash
docker-compose build --no-cache video-to-srt
```

### View Logs in Real-time

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f video-to-srt

# Last 100 lines
docker-compose logs --tail=100 video-to-srt
```

### Run One-off Command

```bash
docker-compose exec video-to-srt python -c "import paddleocr; print('OK')"
```

## Docker Troubleshooting

### Container won't start

```bash
# Check logs for errors
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
#   - "8001:8000"  # Changed from 8000

# Or run on different port
docker-compose -f docker-compose.yml -p myapp up -d
```

### GPU Not Recognized

```bash
# Check Docker GPU support
docker run --rm --gpus all nvidia/cuda:12.0-runtime-ubuntu22.04 nvidia-smi

# If this fails, install nvidia-docker first
# https://github.com/NVIDIA/nvidia-docker
```

### Out of Memory

```bash
# In docker-compose.yml, add memory limit
services:
  video-to-srt:
    deploy:
      resources:
        limits:
          memory: 4G
```

## Full Documentation

See [DOCKER.md](../DOCKER.md) for complete Docker deployment guide with advanced configurations.
