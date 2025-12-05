# REST API Reference

Documentation for ModelMora's REST API endpoints.

## Base URL

```bash
http://localhost:8000
```

## Authentication

Currently, ModelMora MVP does not require authentication. Authentication will be added in Phase 2.

## Endpoints

### Health Check

#### `GET /health`

Check service health status.

**Response:**

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 3600,
  "models_loaded": 2,
  "workers": {
    "active": 2,
    "idle": 1
  }
}
```

### Model Registry

#### `GET /models`

List all registered models.

**Query Parameters:**

- `task` (optional): Filter by task type
- `device` (optional): Filter by device
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20)

**Response:**

```json
{
  "models": [
    {
      "name": "all-MiniLM-L6-v2",
      "version": "1.0.0",
      "task": "text-embedding",
      "device": "cuda",
      "state": "loaded",
      "created_at": "2025-12-04T10:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "pages": 1
}
```

#### `GET /models/{name}`

Get specific model details.

**Response:**

```json
{
  "name": "all-MiniLM-L6-v2",
  "version": "1.0.0",
  "source": "sentence-transformers/all-MiniLM-L6-v2",
  "task": "text-embedding",
  "device": "cuda",
  "state": "loaded",
  "config": {
    "max_seq_length": 512,
    "batch_size": 32
  },
  "stats": {
    "requests_total": 1523,
    "requests_failed": 2,
    "avg_latency_ms": 15.2
  }
}
```

#### `POST /models`

Register a new model.

**Request:**

```json
{
  "name": "all-MiniLM-L6-v2",
  "source": "sentence-transformers/all-MiniLM-L6-v2",
  "task": "text-embedding",
  "device": "cuda",
  "config": {
    "max_seq_length": 512,
    "batch_size": 32
  }
}
```

**Response:** `201 Created`

### Inference

#### `POST /infer/{model_name}`

Execute synchronous inference.

**Request:**

```json
{
  "text": "ModelMora is awesome",
  "options": {
    "normalize": true
  }
}
```

**Response:**

```json
{
  "result": {
    "embeddings": [0.123, -0.456, ...]
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

## Error Responses

### 400 Bad Request

```json
{
  "error": "ValidationError",
  "detail": "Invalid input format",
  "code": "INVALID_INPUT"
}
```

### 404 Not Found

```json
{
  "error": "ModelNotFound",
  "detail": "Model 'unknown-model' not found",
  "code": "MODEL_NOT_FOUND"
}
```

### 504 Gateway Timeout

```json
{
  "error": "InferenceTimeout",
  "detail": "Request exceeded timeout of 30s",
  "code": "INFERENCE_TIMEOUT"
}
```

For interactive API documentation, visit `/docs` or `/redoc` when the service is running.
