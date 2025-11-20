# PyTest Testing Standards and Conventions

This document establishes the testing standards, patterns, and conventions for the ModelMora project. All future testing efforts must follow these guidelines to maintain consistency, quality, and maintainability.

## Overview

The ModelMora testing strategy focuses on comprehensive unit testing for neural network model management, inference serving, and gRPC/Kafka integrations. Tests are organized to mirror the source code structure and provide complete coverage of both success and failure scenarios. All code follows PEP8 naming conventions for maximum Python ecosystem compatibility.

## Project Structure and Organization

### Directory Structure

Tests mirror the source code structure exactly, example:

```bash
tests/
├── unit/
│   └── ModelMora/
│       ├── Configuration/
│       │   ├── test_modelmora_config.py
│       │   └── test_model_registry.py
│       ├── Domain/
│       │   ├── Models/
│       │   │   ├── test_model_metadata.py
│       │   │   └── test_model_registry.py
│       │   └── Services/
│       │       └── test_model_manager.py
│       ├── Application/
│       │   ├── Commands/
│       │   │   ├── test_generate_embedding.py
│       │   │   ├── test_load_model.py
│       │   │   └── test_unload_model.py
│       │   └── Subscribers/
│       │       └── test_handle_image_registered.py
│       └── Infrastructure/
│           ├── GRPC/
│           │   └── test_services.py
│           ├── Providers/
│           │   ├── test_base_provider.py
│           │   ├── test_clip_provider.py
│           │   └── test_dinov2_provider.py
│           └── Cache/
│               └── test_model_cache.py
└── integration/
    └── ModelMora/
        ├── test_grpc_server.py
        └── test_kafka_integration.py
```

### File Naming Conventions (PEP8)

- **Test Files**: `test_{module_name}.py` (e.g., `test_model_manager.py`, `test_clip_provider.py`)
- **Multiple Classes**: Extract each class into separate test files when source file contains multiple definitions
- **Test Classes**: `Test{ClassName}` (e.g., `TestModelManager`, `TestClipProvider`)
- **Test Methods**: `test_{action}_{condition}_should_{expected_result}` using snake_case per PEP8

## Code Structure and Patterns

### Test Class Template

```python
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pydantic import ValidationError

from ModelMora.Path.To.Models import ClassName
from ModelMora.Path.To.Exceptions import CustomException


class TestClassName:
    """Test cases for ClassName model."""

    def test_initialize_with_valid_data_should_set_correct_values(self):
        """Test that ClassName initializes with valid data."""
        # Arrange
        # Act  
        # Assert

    def test_initialize_with_invalid_data_should_raise_validation_error(self):
        """Test that ClassName raises validation error with invalid data."""
        with pytest.raises(ValidationError) as exc_info:
            # Act that should raise error
            pass
        
        # Verify error details
        assert "expected error message" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_method_with_valid_input_should_return_expected_result(self):
        """Test async method with valid input."""
        # Arrange
        # Act
        # Assert
```

### Import Standards

```python
# Standard library imports first
import os
import pytest
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import patch, MagicMock, AsyncMock

# Third-party imports
import grpc
import torch
from pydantic import ValidationError

# Project imports - specific and explicit
from ModelMora.Configuration.modelmora_config import ModelMoraConfig
from ModelMora.Domain.Services.model_manager import ModelManager
from ModelMora.Infrastructure.Providers.clip_provider import ClipProvider
```

## Test Method Naming Conventions (PEP8)

### Established Pattern

**Format**: `test_{action}_{condition}_should_{expected_result}`

**Examples**:

- `test_initialize_with_valid_data_should_set_correct_values`
- `test_from_env_with_all_environment_variables_should_set_correct_values`
- `test_validate_filename_with_file_target_and_valid_path_should_create_directory_and_return_path`
- `test_initialize_with_invalid_email_should_raise_validation_error`
- `test_generate_embedding_with_valid_image_should_return_vector`
- `test_load_model_with_insufficient_memory_should_evict_lru_model`

### Naming Components

- **action**: What method/functionality is being tested (snake_case: `initialize`, `from_env`, `validate`, `generate`)
- **condition**: The specific scenario or input condition (snake_case: `with_valid_data`, `with_invalid_email`, `with_no_handlers`)
- **expected_result**: What should happen (snake_case: `should_set_correct_values`, `should_raise_validation_error`, `should_return_new_instance`)

## Testing Categories and Coverage Requirements

### 1. Initialization Tests

**Purpose**: Verify object creation with various input scenarios

```python
def test_initialize_with_default_values_should_set_correct_defaults(self):
    """Test that model initializes with correct default values."""

def test_initialize_with_custom_values_should_set_correct_values(self):
    """Test that model initializes with custom values correctly."""

def test_initialize_with_invalid_data_should_raise_validation_error(self):
    """Test that model raises validation error with invalid data."""
```

### 2. Factory Method Tests

**Purpose**: Test static/class methods that create instances

```python
@patch.dict(os.environ, {"MODELMORA_KEY": "value"})
def test_from_env_with_all_environment_variables_should_set_correct_values(self):
    """Test that factory method creates instance from environment variables."""

@patch('torch.load')
def test_load_model_with_mocked_checkpoint_should_return_new_instance(self, mock_load):
    """Test that load method creates new instance with mocked dependencies."""
```

### 3. Validation Tests

**Purpose**: Comprehensive validation of business rules and constraints

```python
def test_validate_field_with_valid_input_should_accept_value(self):
    """Test that validation accepts valid input."""

def test_validate_field_with_invalid_input_should_raise_validation_error(self):
    """Test that validation rejects invalid input with appropriate error."""

def test_validate_model_config_with_invalid_memory_limit_should_raise_error(self):
    """Test that model config validation rejects invalid memory limits."""
```

### 4. Behavior Tests

**Purpose**: Test specific behaviors and side effects

```python
@patch('os.makedirs')
def test_cache_model_with_new_weights_should_create_directory(self, mock_makedirs):
    """Test that model caching creates necessary directories."""

@pytest.mark.asyncio
async def test_generate_embedding_with_valid_image_should_invoke_model(self):
    """Test that embedding generation invokes the model correctly."""
```

## Exception Handling Patterns

### Pydantic ValidationError

```python
def test_initialize_with_invalid_data_should_raise_validation_error(self):
    """Test that initialization raises validation error with invalid data."""
    with pytest.raises(ValidationError) as exc_info:
        ModelConfig(max_memory_mb=-1)
    
    assert "expected error substring" in str(exc_info.value)
```

### Custom Domain/Infrastructure/Application Exceptions

```python
def test_load_model_with_insufficient_memory_should_raise_out_of_memory_error(self):
    """Test that model loading raises custom exception when memory insufficient."""
    with pytest.raises(OutOfMemoryError) as exc_info:
        await model_manager.load_model("large-model")
    
    assert exc_info.value.message == "Insufficient memory to load model"

@pytest.mark.asyncio
async def test_generate_embedding_with_timeout_should_raise_grpc_deadline_exceeded(self):
    """Test that embedding generation raises gRPC deadline error on timeout."""
    with pytest.raises(grpc.RpcError) as exc_info:
        await client.generate_embedding(image_data, timeout=0.001)
    
    assert exc_info.value.code() == grpc.StatusCode.DEADLINE_EXCEEDED
```

## Mocking Strategies

### Environment Variables

```python
@patch.dict(os.environ, {"MODELMORA_MAX_MODEL_MEMORY_MB": "8192"}, clear=True)
def test_from_env_with_specific_variables_should_use_environment_values(self):
    """Test environment variable usage."""

@patch.dict(os.environ, {}, clear=True)
def test_from_env_with_no_variables_should_use_defaults(self):
    """Test default behavior when environment variables are not set."""
```

### External Dependencies

```python
@patch('os.makedirs')
def test_cache_directory_creation_should_call_makedirs(self, mock_makedirs):
    """Test that method calls external file system operations."""
    # Test logic
    mock_makedirs.assert_called_once_with("/models/cache", exist_ok=True)

@patch('torch.load')
@pytest.mark.asyncio
async def test_model_initialization_should_load_checkpoint(self, mock_torch_load):
    """Test model initialization with mocked PyTorch loading."""
    mock_torch_load.return_value = MagicMock()
    # Test logic

@patch('grpc.aio.insecure_channel')
@pytest.mark.asyncio
async def test_grpc_client_should_establish_connection(self, mock_channel):
    """Test gRPC client connection establishment."""
    mock_channel.return_value = AsyncMock()
    # Test logic
```

### Model Inference Mocking

```python
@patch('torch.inference_mode')
@pytest.mark.asyncio
async def test_generate_embedding_with_mocked_inference_should_return_vector(self, mock_inference):
    """Test embedding generation with mocked model inference."""
    expected_embedding = torch.randn(768)
    mock_model = AsyncMock()
    mock_model.encode_image.return_value = expected_embedding
    
    result = await provider.generate_embedding(image_data)
    
    assert result.shape == (768,)
    assert torch.allclose(result, expected_embedding)
```

## Test Data Management

### Valid Test Data

```python
class TestData:
    """Centralized test data for consistent testing."""
    VALID_MODEL_NAME = "clip-vit-g-14"
    VALID_IMAGE_SIZE = (224, 224)
    VALID_EMBEDDING_DIM = 768
    VALID_BATCH_SIZE = 32
    
    @staticmethod
    def create_valid_model_config():
        return {
            "name": TestData.VALID_MODEL_NAME,
            "type": "embedding",
            "provider": "ClipProvider",
            "config": {
                "pretrained": "laion2b_s12b_b42k",
                "architecture": "ViT-g-14"
            },
            "resources": {
                "memory_mb": 2048,
                "gpu_required": False,
                "cpu_threads": 4
            }
        }
    
    @staticmethod
    def create_test_image_tensor():
        """Create a test image tensor for inference testing."""
        import torch
        return torch.randn(3, 224, 224)
```

### Edge Cases and Invalid Data

Always test boundary conditions:

- Empty strings (`""`)
- None values
- Maximum length values
- Minimum length values
- Invalid formats
- Type mismatches

## Documentation Standards

### Test Method Docstrings

Each test method must have a descriptive docstring explaining:

```python
def test_method_name_condition_should_expectation(self):
    """Test that [Class/Method] [specific behavior] when [condition]."""
```

### Class Docstrings

```python
class TestClassName:
    """Test cases for ClassName [domain/model/service] [purpose]."""
```

### Inline Comments

Use comments sparingly, only for complex test logic:

```python
# Arrange - complex setup
# Act - the action being tested  
# Assert - verification with explanation if complex
```

## Assertion Patterns

### Basic Assertions

```python
assert result == expected
assert isinstance(result, ExpectedType)
assert result.field == expected_value
assert len(result.collection) == expected_count
```

### Exception Assertions

```python
with pytest.raises(ExceptionType) as exc_info:
    # Action that should raise exception
    
assert "expected message" in str(exc_info.value)
assert exc_info.value.code == expected_code
```

### Mock Assertions

```python
mock_method.assert_called_once()
mock_method.assert_called_once_with(expected_args)
mock_method.assert_not_called()
assert mock_method.call_count == expected_count
```

## Configuration and Dependencies

### pytest Configuration

Tests follow `pyproject.toml` configuration:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=src/ModelMora",
    "--cov-report=html",
    "--cov-report=term-missing:skip-covered",
    "--cov-fail-under=80"
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "gpu: marks tests that require GPU"
]
```

### Required Dependencies

```python
# Core testing
pytest>=8.2.0
pytest-cov
pytest-asyncio>=0.21.0
pytest-grpc>=0.8.0

# Mocking and fixtures
unittest.mock (built-in)

# Type checking support
pydantic>=2.0.0
typing

# ML/AI testing support
torch>=2.5.0
torchvision>=0.20.0
```

## Code Quality Standards

### Coverage Requirements

- **Target Coverage**: 80% minimum per `pyproject.toml`
- **Domain Models & Services**: Aim for 95%+ coverage
- **Application Commands**: Minimum 90% coverage
- **Infrastructure Providers**: Minimum 85% coverage
- **gRPC/Kafka Integration**: Minimum 75% coverage

### Naming Compliance (PEP8)

All test code follows PEP8 standards:

- Functions and methods: `snake_case`
- Variables: `snake_case`
- Constants: `UPPER_CASE`
- Classes: `PascalCase`
- File names: `test_module_name.py`
- Private methods: `_leading_underscore`

### Type Hints

Use type hints for complex test fixtures and helper methods:

```python
def create_test_model_config(
    name: str = "clip-vit-g-14",
    memory_mb: int = 2048
) -> Dict[str, Any]:
    """Create a test model configuration with specified parameters."""
    return {
        "name": name,
        "type": "embedding",
        "provider": "ClipProvider",
        "resources": {
            "memory_mb": memory_mb,
            "gpu_required": False,
            "cpu_threads": 4
        }
    }

@pytest.fixture
async def mock_model_provider() -> AsyncMock:
    """Create a mocked model provider for testing."""
    provider = AsyncMock()
    provider.generate_embedding.return_value = torch.randn(768)
    return provider
```

## Anti-Patterns to Avoid

### ❌ Don't Do

```python
# Vague test names
def test_model():
def test_validation():

# Non-PEP8 naming
def test_LoadModel_ShouldSucceed(self):

# Missing docstrings
def test_something(self):

# Non-descriptive assertions
assert result
assert not result

# Testing multiple concerns in one test
def test_everything(self):
    # Tests initialization, validation, inference, and caching

# Hard-coded values without meaning
assert result.shape[0] == 768  # Why 768?

# Forgetting @pytest.mark.asyncio for async tests
async def test_async_method(self):  # Will fail!
```

### ✅ Do This Instead

```python
# Descriptive PEP8 test names
def test_initialize_with_valid_config_should_set_model_name(self):
def test_validate_memory_limit_should_reject_negative_values(self):

# Clear docstrings
def test_from_env_with_missing_variables_should_use_defaults(self):
    """Test that config loads default values when environment variables are missing."""

# Meaningful assertions
assert model_config.name == expected_model_name
assert embedding.shape == (EXPECTED_EMBEDDING_DIM,)

# Single concern per test
@pytest.mark.asyncio
async def test_generate_embedding_with_valid_image_should_return_vector(self):
    # Only tests embedding generation

# Named constants
EXPECTED_EMBEDDING_DIM = 768
assert result.shape[0] == EXPECTED_EMBEDDING_DIM

# Proper async test marking
@pytest.mark.asyncio
async def test_async_load_model_should_cache_weights(self):
    """Test that async model loading caches weights properly."""
```

## Future Extensions

### Integration Testing

When adding integration tests:

- Use separate `tests/integration/` directory
- Follow same naming conventions with PEP8
- Focus on component interactions (gRPC, Kafka, model loading)
- Use test fixtures for external services
- Mark with `@pytest.mark.integration`

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_grpc_server_embedding_generation_end_to_end(self):
    """Test complete embedding generation flow via gRPC."""
```

### Performance Testing

For performance-critical code (model inference, batch processing):

- Use `pytest-benchmark` for timing tests
- Create separate `tests/performance/` directory
- Establish baseline performance metrics
- Mark with `@pytest.mark.slow`

```python
@pytest.mark.slow
def test_embedding_generation_performance_should_meet_sla(benchmark):
    """Test that embedding generation meets 100ms SLA."""
    result = benchmark(generate_embedding, test_image)
    assert result.stats.mean < 0.1  # 100ms
```

### Property-Based Testing

For complex validation logic (model configurations, tensor shapes):

- Use `hypothesis` library
- Generate test data automatically
- Focus on edge cases and invariants

```python
from hypothesis import given, strategies as st

@given(st.integers(min_value=1, max_value=10000))
def test_model_cache_with_any_memory_limit_should_not_exceed_limit(memory_mb):
    """Test that model cache respects any valid memory limit."""
```

## Conclusion

These standards ensure:

1. **Consistency**: All tests follow PEP8 and Python community best practices
2. **Maintainability**: Clear snake_case naming and structure make tests easy to understand and modify
3. **Reliability**: Comprehensive coverage and proper async/mock patterns ensure test accuracy
4. **Quality**: High standards for documentation, type hints, and code quality
5. **Scalability**: Patterns that work for both small and large test suites
6. **Performance**: Specialized patterns for ML/AI inference testing and resource management

All future testing efforts for ModelMora must adhere to these PEP8-compliant standards. Any deviations should be documented and approved through the standard code review process.
