# Quick Start

Get ModelMora up and running in minutes.

## Start the Service

```bash
# Using Poetry
poetry run modelmora serve

# Using Docker
docker run -p 8000:8000 ghcr.io/jomarjunior/modelmora:latest
```

The service will start on:
- REST API: `http://localhost:8000`
- gRPC API: `localhost:50051`
- API Documentation: `http://localhost:8000/docs`

## Register Your First Model

### Using CLI

```bash
# Install a model from HuggingFace Hub
poetry run modelmora install sentence-transformers/all-MiniLM-L6-v2

# List installed models
poetry run modelmora list

# Get model info
poetry run modelmora info all-MiniLM-L6-v2
```

### Using REST API

```bash
# Register a model
curl -X POST http://localhost:8000/models \
  -H "Content-Type: application/json" \
  -d '{
    "name": "all-MiniLM-L6-v2",
    "source": "sentence-transformers/all-MiniLM-L6-v2",
    "task": "text-embedding",
    "device": "cuda"
  }'

# List models
curl http://localhost:8000/models

# Get model details
curl http://localhost:8000/models/all-MiniLM-L6-v2
```

## Run Inference

### Text Embedding Example

```bash
curl -X POST http://localhost:8000/infer/all-MiniLM-L6-v2 \
  -H "Content-Type: application/json" \
  -d '{
    "text": "ModelMora is a high-performance inference server"
  }'
```

Response:

```json
{
  "result": {
    "embeddings": [0.123, -0.456, 0.789, ...]
  },
  "metadata": {
    "model": "all-MiniLM-L6-v2",
    "version": "1.0.0",
    "device": "cuda:0"
  },
  "timing": {
    "queue_time_ms": 0.7,
    "inference_time_ms": 15.2,
    "total_time_ms": 15.9
  }
}
```

### Using Python Client

```python
import requests

# Submit inference request
response = requests.post(
    "http://localhost:8000/infer/all-MiniLM-L6-v2",
    json={"text": "Hello, ModelMora!"}
)

result = response.json()
embeddings = result["result"]["embeddings"]
print(f"Embedding dimension: {len(embeddings)}")
```

### Using gRPC Client

```python
import grpc
from modelmora.protos import inference_pb2, inference_pb2_grpc

# Create channel and stub
channel = grpc.insecure_channel('localhost:50051')
stub = inference_pb2_grpc.InferenceServiceStub(channel)

# Submit request
request = inference_pb2.InferenceRequest(
    model_name="all-MiniLM-L6-v2",
    text="Hello, ModelMora!"
)

response = stub.Infer(request)
print(f"Result: {response.embeddings}")
```

## Configuration File

Create `config/models.yml`:

```yaml
models:
  - name: all-MiniLM-L6-v2
    source: sentence-transformers/all-MiniLM-L6-v2
    task: text-embedding
    device: ${DEVICE:-cuda}
    config:
      max_seq_length: 512
      batch_size: 32

  - name: stable-diffusion-v1-5
    source: runwayml/stable-diffusion-v1-5
    task: text-to-image
    device: cuda
    config:
      guidance_scale: 7.5
      num_inference_steps: 50
```

Load models from config:

```bash
poetry run modelmora init --config config/models.yml
```

## Health Check

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 3600,
  "models_loaded": 2,
  "total_requests": 1523,
  "workers": {
    "active": 2,
    "idle": 1
  }
}
```

## Next Steps

- [Configuration Guide](configuration.md)
- [REST API Reference](../api-reference/rest.md)
- [gRPC API Reference](../api-reference/grpc.md)
- [Deployment Guide](../deployment/docker.md)

## Common Issues

### Model Not Found

```bash
# Download model cache
poetry run modelmora install <model-name>
```

### CUDA Out of Memory

```yaml
# Reduce batch size in config/models.yml
config:
  batch_size: 8  # Lower value
```

### Port Already in Use

```bash
# Change port
poetry run modelmora serve --port 8080
```
