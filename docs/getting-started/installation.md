# Installation

This guide will help you install and set up ModelMora.

## Prerequisites

- Python 3.10 or higher (3.10, 3.11, 3.12 supported)
- Poetry 1.8.0 or higher
- Docker (optional, for containerized deployment)
- CUDA 13.0+ (optional, for GPU support)

## Installation Methods

### From Source

1. **Clone the repository**

```bash
git clone https://github.com/JomarJunior/modelmora.git
cd modelmora
```

2. **Install dependencies with Poetry**

```bash
poetry install
```

3. **Activate the virtual environment**

```bash
poetry shell
```

4. **Verify installation**

```bash
modelmora --version
```

### Using Docker

1. **Pull the Docker image**

```bash
docker pull ghcr.io/jomarjunior/modelmora:latest
```

2. **Run the container**

```bash
docker run -p 8000:8000 ghcr.io/jomarjunior/modelmora:latest
```

### Using Docker Compose

1. **Create a `docker-compose.yml`**

```yaml
version: '3.8'

services:
  modelmora:
    image: ghcr.io/jomarjunior/modelmora:latest
    ports:
      - "8000:8000"
      - "50051:50051"  # gRPC
    environment:
      - MODELMORA_DB_PATH=/data/models.db
      - MODELMORA_CACHE_DIR=/cache
    volumes:
      - ./data:/data
      - ./cache:/cache
      - ./config:/app/config
```

2. **Start the service**

```bash
docker-compose up -d
```

## Development Setup

For development work, install with dev dependencies:

```bash
poetry install --with dev,docs
```

Install pre-commit hooks:

```bash
poetry run pre-commit install
```

## GPU Support

### CUDA Setup

ModelMora uses PyTorch with CUDA 13.0 support. Ensure you have:

1. NVIDIA GPU with compute capability 3.5 or higher
2. NVIDIA drivers (version 525.85 or higher)
3. CUDA Toolkit 13.0+

Verify GPU availability:

```bash
poetry run python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### CPU-Only Installation

For CPU-only environments, modify the torch source in `pyproject.toml`:

```toml
torch = {version = "^2.9.0"}
torchvision = {version = "^0.24.0"}
```

Then run:

```bash
poetry lock --no-update
poetry install
```

## Verification

Test your installation:

```bash
# Check health
curl http://localhost:8000/health

# Run tests
poetry run pytest

# Check linting
poetry run black --check .
poetry run pylint src/modelmora
```

## Next Steps

- [Quick Start Guide](quickstart.md)
- [Configuration](configuration.md)
- [API Reference](../api-reference/rest.md)
