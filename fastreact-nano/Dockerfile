# FastReAct Nano - Production Dockerfile
# Multi-stage build with support for different feature sets

# Stage 1: Base Builder
FROM python:3.11-slim AS base-builder

# Set build arguments for optional features
ARG FEISHU_ENABLED=false
ARG MCP_ENABLED=true
ARG GATEWAY_ENABLED=true

WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/

# Build extras list based on features
RUN if [ "$FEISHU_ENABLED" = "true" ]; then \
        EXTRAS="$EXTRAS,feishu"; \
    fi && \
    if [ "$MCP_ENABLED" = "true" ]; then \
        EXTRAS="$EXTRAS,mcp"; \
    fi && \
    if [ "$GATEWAY_ENABLED" = "true" ]; then \
        EXTRAS="$EXTRAS,gateway"; \
    fi && \
    echo "Installing with extras: [$EXTRAS]" && \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e ".[cli,dev${EXTRAS}]"

# Stage 2: Production Runtime
FROM python:3.11-slim AS production

# Set metadata
LABEL maintainer="FastReAct Team <contact@fastreact.dev>"
LABEL version="2.0.0"
LABEL description="FastReAct Nano - Lightweight ReAct Agent with Event-Driven Architecture"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r fastreact && useradd -r -g fastreact -s /bin/bash fastreact

# Set up directories
WORKDIR /app
RUN mkdir -p /workspace /.fastreact /var/log/fastreact && \
    chown -R fastreact:fastreact /app /workspace /.fastreact /var/log/fastreact

# Copy Python environment from builder
COPY --from=base-builder --chown=fastreact:fastreact /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base-builder --chown=fastreact:fastreact /usr/local/bin /usr/local/bin
COPY --from=base-builder --chown=fastreact:fastreact /build/src /app/src
COPY --from=base-builder --chown=fastreact:fastreact /build/pyproject.toml /app/

# Switch to non-root user
USER fastreact
WORKDIR /workspace

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    FASTRACT_WORKSPACE=/workspace \
    FASTRACT_CONFIG_DIR=/app/.fastreact

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Expose ports
# 8501: Streamlit Web UI
# 9000: Gateway HTTP/WebSocket
# 8001: Feishu Webhook (optional)
EXPOSE 8501 9000 8001

# Default command (can be overridden)
CMD ["python", "-m", "fastreact.adapters.gateway"]

# Stage 3: Development Environment
FROM production AS development

USER root

# Install development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    htop \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Install additional dev dependencies
RUN pip install --no-cache-dir \
    jupyter \
    ipython \
    pytest-asyncio \
    pytest-cov

USER fastreact

# Override for development
CMD ["bash"]
