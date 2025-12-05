# gRPC API Reference

Documentation for ModelMora's gRPC API.

## Connection

```bash
localhost:50051
```

## Service Definitions

### InferenceService

Protocol Buffer definition (`inference.proto`):

```protobuf
syntax = "proto3";

package modelmora.inference;

service InferenceService {
  rpc Infer(InferenceRequest) returns (InferenceResponse);
  rpc InferStream(InferenceRequest) returns (stream InferenceChunk);
}

message InferenceRequest {
  string model_name = 1;
  oneof input {
    string text = 2;
    bytes image = 3;
  }
  map<string, string> options = 4;
}

message InferenceResponse {
  repeated float embeddings = 1;
  string text = 2;
  bytes image = 3;
  map<string, string> metadata = 4;
}

message InferenceChunk {
  bytes data = 1;
  int32 sequence = 2;
  bool final = 3;
}
```

## Python Client Example

```python
import grpc
from modelmora.protos import inference_pb2, inference_pb2_grpc

# Create channel
channel = grpc.insecure_channel('localhost:50051')
stub = inference_pb2_grpc.InferenceServiceStub(channel)

# Text embedding
request = inference_pb2.InferenceRequest(
    model_name="all-MiniLM-L6-v2",
    text="Hello, ModelMora!"
)

response = stub.Infer(request)
print(f"Embeddings: {response.embeddings}")

# Streaming inference (for large outputs)
for chunk in stub.InferStream(request):
    print(f"Chunk {chunk.sequence}: {len(chunk.data)} bytes")
    if chunk.final:
        break
```

## Next Steps

- [REST API Reference](rest.md)
- [Architecture Overview](../architecture.md)
