# Input Data Model

**Context:** Inference
**Type:** Polymorphic Value Object
**Version:** 1.0.0
**Date:** 2025-12-04

---

## 1. Overview

`InputData` represents task-specific input for inference requests. Structure varies by TaskType.

---

## 2. Task-Specific Structures

### 2.1 txt2embed Input

```json
{
  "task_type": "txt2embed",
  "text": "Hello world",
  "normalize": true
}
```

### 2.2 txt2txt Input

```json
{
  "task_type": "txt2txt",
  "prompt": "Translate to French: Hello",
  "max_tokens": 100,
  "temperature": 0.7
}
```

### 2.3 txt2img Input

```json
{
  "task_type": "txt2img",
  "prompt": "A serene landscape",
  "width": 512,
  "height": 512,
  "steps": 50
}
```

### 2.4 img2txt Input

```json
{
  "task_type": "img2txt",
  "image": "<base64_encoded_image>",
  "max_length": 100
}
```

---

## 3. Common Fields

- **task_type**: TaskType identifier
- **Additional fields**: Task-specific parameters

---

## 4. Validation

Input data MUST conform to TaskType schema (see TaskType model for schemas).

---

## 5. Protocol Buffers

```protobuf
message InputData {
  string task_type = 1;
  google.protobuf.Struct data = 2;  // Flexible task-specific data
}
```

---

## 6. Related Models

- [Task Type](../registry/task_type.md) - Defines input schemas
- [Inference Request](./inference_request.md) - Contains InputData
- [Output Data](./output_data.md) - Corresponding output
