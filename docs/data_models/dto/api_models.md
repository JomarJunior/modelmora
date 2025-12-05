# API DTOs (Data Transfer Objects)

**Context:** Cross-Cutting
**Type:** Documentation
**Version:** 1.0.0
**Date:** 2025-12-04

---

## 1. Overview

API DTOs are language-agnostic data structures for REST API request/response serialization. They provide a stable API contract separate from internal domain models.

---

## 2. DTO Pattern

DTOs follow these conventions:

- **Flat structure** - No deep nesting
- **snake_case** - JSON field naming
- **Optional versioning** - API version in URL
- **Validation** - Schema validation at API boundary

---

## 3. Registry API DTOs

### 3.1 RegisterModelRequest

```json
{
  "model_id": "sentence-transformers/all-MiniLM-L6-v2",
  "version": "v2.2.2",
  "task_type": "txt2embed",
  "checksum": "sha256:abc123...",
  "artifact_uri": "https://...",
  "resource_requirements": {
    "memory_mb": 512,
    "gpu_vram_mb": 0,
    "cpu_threads": 2
  },
  "framework": "pytorch",
  "framework_version": "2.0.1"
}
```

### 3.2 ModelResponse

```json
{
  "id": "880e8400-e29b-41d4-a716-446655440004",
  "model_id": "sentence-transformers/all-MiniLM-L6-v2",
  "task_type": "txt2embed",
  "current_version": "v2.2.2",
  "versions": ["v2.2.2", "v2.2.1"],
  "created_at": "2025-12-04T10:30:00Z"
}
```

---

## 4. Lifecycle API DTOs

### 4.1 LoadModelRequest

```json
{
  "model_id": "sentence-transformers/all-MiniLM-L6-v2",
  "version": "v2.2.2"
}
```

### 4.2 LoadedModelResponse

```json
{
  "id": "bb0e8400-e29b-41d4-a716-446655440007",
  "model_id": "sentence-transformers/all-MiniLM-L6-v2",
  "version": "v2.2.2",
  "state": "loaded",
  "memory_usage_mb": 512.5,
  "healthy": true,
  "loaded_at": "2025-12-04T10:25:00Z"
}
```

---

## 5. Inference API DTOs

### 5.1 InferenceRequest

```json
{
  "model_id": "sentence-transformers/all-MiniLM-L6-v2",
  "input": {
    "text": "Hello world"
  },
  "priority": "high",
  "timeout_seconds": 60
}
```

### 5.2 InferenceResponse

```json
{
  "job_id": "ee0e8400-e29b-41d4-a716-446655440010",
  "status": "completed",
  "result": {
    "embedding": [0.123, -0.456, ...]
  },
  "processing_time_ms": 45.3,
  "created_at": "2025-12-04T10:30:00Z",
  "completed_at": "2025-12-04T10:30:00.045Z"
}
```

---

## 6. Common DTOs

### 6.1 ErrorResponse

```json
{
  "error": {
    "code": "MODEL_NOT_FOUND",
    "message": "Model not found in registry",
    "details": {
      "model_id": "invalid/model"
    }
  }
}
```

### 6.2 PaginatedResponse

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 100,
    "total_pages": 5
  }
}
```

---

## 7. DTO Mapping

DTOs map to domain models:

| DTO | Domain Model | Direction |
|-----|--------------|-----------|
| RegisterModelRequest | Model + ModelVersion | Request → Domain |
| ModelResponse | Model | Domain → Response |
| LoadModelRequest | ModelId + Version | Request → Domain |
| LoadedModelResponse | LoadedModel | Domain → Response |
| InferenceRequest | InferenceRequest | Request → Domain |
| InferenceResponse | InferenceJob | Domain → Response |

---

## 8. Validation

DTOs undergo validation at API boundary:

```python
# JSON Schema validation
def validate_dto(dto_data: dict, schema: dict) -> ValidationResult:
    """Validate DTO against JSON Schema"""
    try:
        jsonschema.validate(dto_data, schema)
        return ValidationResult(valid=True)
    except jsonschema.ValidationError as e:
        return ValidationResult(
            valid=False,
            errors=[str(e)]
        )
```

---

## 9. Protocol Buffers (gRPC)

DTOs also defined as Protocol Buffer messages:

```protobuf
message RegisterModelRequest {
  string model_id = 1;
  string version = 2;
  string task_type = 3;
  string checksum = 4;
  string artifact_uri = 5;
  ResourceRequirements resource_requirements = 6;
  string framework = 7;
  string framework_version = 8;
}

message ModelResponse {
  string id = 1;
  string model_id = 2;
  string task_type = 3;
  string current_version = 4;
  repeated string versions = 5;
  google.protobuf.Timestamp created_at = 6;
}
```

---

## 10. Related Documentation

- [API Design](../../api_design.md) - Complete API specifications
- [Data Models](../../data_models.md) - Domain model definitions
- [Error Models](./error_models.md) - Error response structures
