# Output Data Model

**Context:** Inference
**Type:** Polymorphic Value Object
**Version:** 1.0.0
**Date:** 2025-12-04

---

## 1. Overview

`OutputData` represents task-specific inference results. Structure varies by TaskType.

---

## 2. Task-Specific Structures

### 2.1 txt2embed Output

```json
{
  "task_type": "txt2embed",
  "embedding": [0.123, -0.456, 0.789, ...]
}
```

### 2.2 txt2txt Output

```json
{
  "task_type": "txt2txt",
  "text": "Bonjour",
  "tokens_used": 15
}
```

### 2.3 txt2img Output

```json
{
  "task_type": "txt2img",
  "image": "<base64_encoded_image>",
  "format": "png"
}
```

### 2.4 classification Output

```json
{
  "task_type": "classification",
  "classes": [
    {"label": "positive", "score": 0.95},
    {"label": "negative", "score": 0.05}
  ]
}
```

---

## 3. Common Fields

- **task_type**: TaskType identifier
- **Additional fields**: Task-specific results

---

## 4. Protocol Buffers

```protobuf
message OutputData {
  string task_type = 1;
  google.protobuf.Struct data = 2;  // Flexible task-specific data
}
```

---

## 5. Related Models

- [Task Type](../registry/task_type.md) - Defines output schemas
- [Inference Job](./inference_job.md) - Contains OutputData as result
- [Input Data](./input_data.md) - Corresponding input
