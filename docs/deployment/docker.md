# Docker Deployment

Deploy ModelMora using Docker containers.

## Quick Start

```bash
docker run -p 8000:8000 ghcr.io/jomarjunior/modelmora:latest
```

## Docker Compose

Create `docker-compose.yml`:

```yaml
services:
  modelmora:
    image: ghcr.io/jomarjunior/modelmora:latest
    ports:
      - "8000:8000"
      - "50051:50051"
    environment:
      - MODELMORA_DB_PATH=/data/models.db
      - MODELMORA_CACHE_DIR=/cache
      - MODELMORA_MAX_WORKERS=4
      - MODELMORA_DEVICE=cuda
    volumes:
      - ./data:/data
      - ./cache:/cache
      - ./config:/app/config
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Start:

```bash
docker-compose up -d
```

## Build from Source

```bash
docker build -t modelmora:local .
docker run -p 8000:8000 modelmora:local
```

## GPU Support

Ensure NVIDIA Container Toolkit is installed:

```bash
# Install nvidia-container-toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

Run with GPU:

```bash
docker run --gpus all -p 8000:8000 ghcr.io/jomarjunior/modelmora:latest
```

## Next Steps

- [Kubernetes Deployment](kubernetes.md)
- [Configuration Guide](../getting-started/configuration.md)
