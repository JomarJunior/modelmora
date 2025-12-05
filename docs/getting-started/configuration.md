# Configuration

ModelMora provides flexible configuration through environment variables, YAML files, and command-line arguments.

## Configuration Hierarchy

Configuration is loaded in the following order (later sources override earlier ones):

1. Default values
2. YAML configuration file
3. Environment variables
4. Command-line arguments

## Environment Variables

### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `MODELMORA_HOST` | Server host | `0.0.0.0` |
| `MODELMORA_PORT` | REST API port | `8000` |
| `MODELMORA_GRPC_PORT` | gRPC API port | `50051` |
| `MODELMORA_LOG_LEVEL` | Logging level | `INFO` |
| `MODELMORA_DB_PATH` | Database file path | `./data/models.db` |
| `MODELMORA_CACHE_DIR` | Model cache directory | `~/.cache/modelmora` |

### Resource Management

| Variable | Description | Default |
|----------|-------------|---------|
| `MODELMORA_MAX_WORKERS` | Maximum worker processes | `4` |
| `MODELMORA_MAX_MEMORY_GB` | Memory limit (GB) | `8` |
| `MODELMORA_GPU_MEMORY_FRACTION` | GPU memory fraction | `0.8` |
| `MODELMORA_WORKER_TIMEOUT` | Worker timeout (seconds) | `300` |

### Queue Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `MODELMORA_QUEUE_SIZE` | Request queue size | `1000` |
| `MODELMORA_BATCH_SIZE` | Default batch size | `16` |
| `MODELMORA_BATCH_TIMEOUT_MS` | Batch timeout (ms) | `100` |

### Model Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `MODELMORA_LAZY_LOAD` | Enable lazy loading | `true` |
| `MODELMORA_DEVICE` | Default device | `cuda` |
| `MODELMORA_MODEL_TTL` | Model TTL (seconds) | `3600` |

## YAML Configuration

### Basic Configuration

`config/modelmora.yml`:

```yaml
server:
  host: 0.0.0.0
  port: 8000
  grpc_port: 50051
  log_level: INFO

resources:
  max_workers: 4
  max_memory_gb: 8
  gpu_memory_fraction: 0.8
  worker_timeout: 300

queue:
  size: 1000
  batch_size: 16
  batch_timeout_ms: 100

models:
  lazy_load: true
  device: cuda
  ttl: 3600
  cache_dir: ${HOME}/.cache/modelmora
```

### Model Definitions

`config/models.yml`:

```yaml
models:
  # Text embedding model
  - name: all-MiniLM-L6-v2
    source: sentence-transformers/all-MiniLM-L6-v2
    task: text-embedding
    version: 1.0.0
    device: ${DEVICE:-cuda}
    priority: high
    config:
      max_seq_length: 512
      batch_size: 32
      normalize_embeddings: true

  # Image embedding model
  - name: clip-vit-base
    source: openai/clip-vit-base-patch32
    task: image-embedding
    device: cuda
    config:
      image_size: 224
      batch_size: 16

  # Text generation model
  - name: llama-7b
    source: meta-llama/Llama-2-7b-hf
    task: text-generation
    device: cuda:0
    config:
      max_length: 2048
      temperature: 0.7
      top_p: 0.9

  # Image generation model
  - name: stable-diffusion
    source: runwayml/stable-diffusion-v1-5
    task: text-to-image
    device: cuda:1
    config:
      height: 512
      width: 512
      num_inference_steps: 50
      guidance_scale: 7.5
```

### Environment Variable Interpolation

```yaml
# Use environment variables with defaults
database:
  path: ${DB_PATH:-./data/models.db}
  pool_size: ${DB_POOL_SIZE:-10}

cache:
  dir: ${CACHE_DIR:-~/.cache/modelmora}
  max_size_gb: ${CACHE_SIZE_GB:-50}

# Required environment variables (no default)
auth:
  jwt_secret: ${JWT_SECRET}
  token_url: ${AUTH_TOKEN_URL}
```

## Command-Line Arguments

```bash
# Start server with custom configuration
poetry run modelmora serve \
  --host 0.0.0.0 \
  --port 8080 \
  --config config/modelmora.yml \
  --models config/models.yml \
  --log-level DEBUG \
  --workers 8

# Initialize with specific device
poetry run modelmora init \
  --config config/models.yml \
  --device cuda:0

# Install model with custom cache
poetry run modelmora install \
  sentence-transformers/all-MiniLM-L6-v2 \
  --cache-dir /mnt/models \
  --device cpu
```

## Docker Configuration

### Environment File

`.env`:

```env
MODELMORA_HOST=0.0.0.0
MODELMORA_PORT=8000
MODELMORA_LOG_LEVEL=INFO
MODELMORA_DB_PATH=/data/models.db
MODELMORA_CACHE_DIR=/cache
MODELMORA_MAX_WORKERS=4
MODELMORA_DEVICE=cuda
```

### Docker Compose

`docker-compose.yml`:

```yaml
version: '3.8'

services:
  modelmora:
    image: ghcr.io/jomarjunior/modelmora:latest
    ports:
      - "8000:8000"
      - "50051:50051"
    env_file:
      - .env
    environment:
      - MODELMORA_MAX_WORKERS=8
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

## Kubernetes Configuration

### ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: modelmora-config
data:
  modelmora.yml: |
    server:
      host: 0.0.0.0
      port: 8000
    resources:
      max_workers: 4
      max_memory_gb: 16
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: modelmora
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: modelmora
        image: ghcr.io/jomarjunior/modelmora:latest
        env:
        - name: MODELMORA_PORT
          value: "8000"
        - name: MODELMORA_DB_PATH
          value: "/data/models.db"
        volumeMounts:
        - name: config
          mountPath: /app/config
        - name: cache
          mountPath: /cache
      volumes:
      - name: config
        configMap:
          name: modelmora-config
      - name: cache
        persistentVolumeClaim:
          claimName: modelmora-cache
```

## Validation

Validate your configuration:

```bash
# Check configuration syntax
poetry run modelmora config validate --file config/modelmora.yml

# Show effective configuration
poetry run modelmora config show

# Test model loading
poetry run modelmora config test-models --config config/models.yml
```

## Next Steps

- [API Reference](../api-reference/rest.md)
- [Deployment Guide](../deployment/docker.md)
- [Architecture Overview](../architecture.md)
