FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==2.0.1
RUN poetry config virtualenvs.create false

# Copy Poetry configuration files
COPY ./pyproject.toml ./poetry.lock ./README.md ./

# Install dependencies
RUN poetry install --only main --no-root

# Copy application source
COPY ./src ./src

# Install the ModelMora package itself
RUN poetry install --only-root

# Expose ports
# 8080 for REST API
EXPOSE 8080
# 50051 for gRPC
EXPOSE 50051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

CMD ["poetry", "run", "python", "-m", "ModelMora.main"]
