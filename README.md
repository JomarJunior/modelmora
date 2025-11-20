# 🧠 ModelMora

[![Python Version](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Coverage](https://codecov.io/gh/JomarJunior/ModelMora/branch/main/graph/badge.svg)](https://codecov.io/gh/JomarJunior/ModelMora)
[![Status](https://img.shields.io/badge/status-planning-yellow.svg)](#-development-status)

![ModelMora Logo](docs/assets/model-mora-logo.png)

> A dedicated neural network model management and inference serving microservice

**Etymology**: Combining "Model" (neural network models) and "Mora" (Spanish/Portuguese for "to dwell/reside")

## 🚀 Overview

ModelMora is a microservice for managing and serving neural network models with efficient memory management and multi-protocol support. It provides dynamic model loading with LRU eviction, ensuring optimal resource utilization.

Part of the **MiraVeja** ecosystem, ModelMora centralizes neural network operations for image processing and embedding generation.

## ✨ Key Features

- 🎯 **Dynamic Model Loading** - On-demand loading with LRU eviction for optimal memory usage
- 🔌 **Multi-Protocol Support** - gRPC for high performance, REST for management, Kafka for async processing
- 🧠 **Intelligent Memory Management** - Automatic resource optimization and eviction policies
- 📋 **YAML Configuration** - Simple, declarative model registry configuration
- 🔧 **Extensible Architecture** - Provider pattern for easy integration of new model types
- 📊 **Production Ready** - Comprehensive metrics, health checks, and structured logging

## 🛠️ Technology Stack

### 🐍 Core Runtime

- **Python 3.10** - Stable and widely supported version
- **FastAPI** - Modern async web framework for REST APIs
- **gRPC** - High-performance RPC framework
- **Uvicorn** - ASGI server with async support

### 🤖 ML/AI Libraries

- **PyTorch 2.5.0+** - Deep learning framework
- **OpenCLIP** - CLIP model implementation for embeddings
- **Transformers** - Hugging Face model integration

### 🏗️ Infrastructure

- **aiokafka** - Async Kafka client for event streaming
- **Pydantic** - Data validation and settings management
- **prometheus-client** - Metrics collection and monitoring

### 🧪 Development

- **pytest** - Testing framework with async support
- **pytest-grpc** - gRPC testing utilities
- **black** - Code formatter
- **pylint** - Code quality checker

## 🏛️ Architecture

ModelMora follows Domain-Driven Design and clean architecture principles:

```text
src/ModelMora/
├── 📁 Configuration/      # Service and model registry configuration
├── 🧠 Domain/            # Business logic and model abstractions
├── 🎬 Application/       # Use cases and event handlers
├── 🔌 Infrastructure/    # External integrations and providers
└── 🌐 API/              # REST endpoints
```

## 📡 Communication Protocols

1. **gRPC** - Synchronous inference (40-60% lower latency than REST)
2. **Kafka** - Asynchronous event-driven processing
3. **REST** - Management and monitoring operations

## 🎯 Getting Started

### 📋 Prerequisites

- Python 3.10+
- Poetry 2.0+
- Docker & Docker Compose (optional)

### 🚀 Installation

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Start the service
poetry run python -m ModelMora.main
```

### 🐳 Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up modelmora

# Service endpoints:
# REST API: http://localhost:8080
# gRPC: localhost:50051
```

## ⚙️ Configuration

Configure the service using environment variables:

```bash
MODELMORA_REST_PORT=8080              # REST API port
MODELMORA_GRPC_PORT=50051             # gRPC port
MODELMORA_MAX_MODEL_MEMORY_MB=8192    # Memory limit for loaded models
MODELMORA_AUTO_WARMUP=true            # Pre-load models on startup
MODELMORA_GPU_ENABLED=false           # Enable GPU acceleration
```

Models are defined in `Configuration/ModelRegistry.yaml`.

## 🧪 Testing

The project follows PEP8 conventions and comprehensive testing standards:

```bash
# Run all tests
poetry run pytest

# Generate coverage report
poetry run pytest --cov=src/ModelMora --cov-report=html

# Skip slow tests
poetry run pytest -m "not slow"

# Run integration tests
poetry run pytest -m integration
```

See [testing standards](docs/pytest-testing-standards.md) for detailed guidelines.

## 📚 Documentation

- [Architecture Plan](docs/modelmora-architecture-plan.md) - Comprehensive design and implementation details
- [Testing Standards](docs/pytest-testing-standards.md) - Testing conventions and patterns

## 🚧 Development Status

**Planning Phase** - Architecture and design in progress

See the [architecture plan](docs/modelmora-architecture-plan.md) for the implementation roadmap.

## 📄 License

MIT License - See LICENSE file for details.

## 👨‍💻 Author

**Jomar Júnior de Souza Pereira** - <jomarjunior@poli.ufrj.br>

---

Part of the **MiraVeja** ecosystem - A modern image gallery and management platform.
