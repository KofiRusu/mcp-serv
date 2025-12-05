# =============================================================================
# ChatOS v1.0 - Multi-stage Dockerfile
# Supports: Linux (x86_64, arm64) and macOS (Apple Silicon, Intel)
# =============================================================================

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# =============================================================================
# Development Stage
# =============================================================================
FROM base as development

# Copy requirements first for caching
COPY ChatOS/requirements.txt ./requirements.txt
COPY requirements-training.txt ./requirements-training.txt

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -r requirements-training.txt || true

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/models /app/logs

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "ChatOS.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Production Stage
# =============================================================================
FROM base as production

# Copy requirements
COPY ChatOS/requirements.txt ./requirements.txt

# Install production dependencies only
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY ChatOS/ ./ChatOS/
COPY data/ ./data/
COPY run.sh run.prod.sh ./

# Create directories
RUN mkdir -p /app/models /app/logs

# Non-root user for security
RUN useradd -m -u 1000 chatos && \
    chown -R chatos:chatos /app
USER chatos

EXPOSE 8000

CMD ["uvicorn", "ChatOS.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# =============================================================================
# Training Stage (GPU support)
# =============================================================================
FROM nvidia/cuda:12.1-runtime-ubuntu22.04 as training

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install Python and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/python3 /usr/bin/python

WORKDIR /app

# Copy requirements
COPY ChatOS/requirements.txt ./requirements.txt
COPY requirements-training.txt ./requirements-training.txt

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -r requirements-training.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p /app/data/persrm /app/models/persrm-continuous /app/logs

EXPOSE 8000

CMD ["python", "-m", "ChatOS.training.persrm_pytorch_trainer"]

