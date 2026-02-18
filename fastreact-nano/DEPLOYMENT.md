# FastReAct Nano - Deployment Guide

Complete guide for deploying FastReAct Nano in production environments.

---

## Table of Contents

1. [Installation](#installation)
2. [Docker Deployment](#docker-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Release Process](#release-process)
5. [Configuration](#configuration)
6. [Monitoring](#monitoring)

---

## Installation

### From PyPI (Recommended)

```bash
# Core package
pip install fastreact-nano

# With CLI
pip install "fastreact-nano[cli]"

# With Gateway (HTTP/WebSocket)
pip install "fastreact-nano[gateway]"

# With Feishu Bot
pip install "fastreact-nano[feishu]"

# With MCP support
pip install "fastreact-nano[mcp]"

# Everything
pip install "fastreact-nano[all]"
```

### From Source

```bash
# Clone repository
git clone https://github.com/atom32/FastReAct.git
cd FastReAct/fastreact-nano

# Install in development mode
pip install -e ".[all]"

# Or install from built package
pip install dist/*.tar.gz
```

---

## Docker Deployment

### Quick Start

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Update .env with your API keys
vim .env

# 3. Start services
docker-compose up -d

# 4. Check status
docker-compose ps

# 5. View logs
docker-compose logs -f
```

### Available Services

#### Gateway Service

HTTP/WebSocket gateway for programmatic access.

```bash
docker-compose up -d gateway
```

- **URL**: http://localhost:9000
- **Health**: http://localhost:9000/health
- **Docs**: http://localhost:9000/docs

#### Web UI

Streamlit-based web interface.

```bash
docker-compose up -d web
```

- **URL**: http://localhost:8501

#### Feishu Bot

Multi-tenant Feishu bot integration.

```bash
docker-compose up -d feishu
```

- **Port**: 8001
- **Webhook**: Configure in Feishu developer console

### Docker Build Arguments

Customize build with optional features:

```bash
# Build with Feishu support
docker build \
  --build-arg FEISHU_ENABLED=true \
  --build-arg MCP_ENABLED=true \
  --target production \
  -t fastreact-nano:custom \
  .
```

### Docker Profiles

Use profiles to manage different deployment scenarios:

```bash
# Development mode (with dev tools)
docker-compose --profile dev up

# Production with monitoring
docker-compose --profile monitoring up

# Full stack
docker-compose --profile dev --profile monitoring up
```

---

## Kubernetes Deployment

### Create Namespace

```bash
kubectl create namespace fastreact
```

### Create ConfigMap

```bash
kubectl create configmap fastreact-config \
  --from-file=config.json \
  --namespace=fastreact
```

### Create Secret

```bash
kubectl create secret generic fastreact-secrets \
  --from-literal=api-key=sk-xxx \
  --from-literal=feishu-app-id=xxx \
  --from-literal=feishu-app-secret=xxx \
  --namespace=fastreact
```

### Deploy Gateway

```yaml
# deployments/k8s/gateway-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastreact-gateway
  namespace: fastreact
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fastreact-gateway
  template:
    metadata:
      labels:
        app: fastreact-gateway
    spec:
      containers:
      - name: gateway
        image: fastreactnano/fastreact-nano:latest
        ports:
        - containerPort: 9000
        env:
        - name: FASTRACT_MODEL
          value: "gpt-4o-mini"
        - name: FASTRACT_API_KEY
          valueFrom:
            secretKeyRef:
              name: fastreact-secrets
              key: api-key
        - name: FASTRACT_WORKSPACE
          value: /workspace
        volumeMounts:
        - name: workspace
          mountPath: /workspace
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 9000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 9000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: workspace
        persistentVolumeClaim:
          claimName: fastreact-workspace-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: fastreact-gateway
  namespace: fastreact
spec:
  selector:
    app: fastreact-gateway
  ports:
  - protocol: TCP
    port: 80
    targetPort: 9000
  type: LoadBalancer
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: fastreact-workspace-pvc
  namespace: fastreact
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
```

Apply deployment:

```bash
kubectl apply -f deployments/k8s/gateway-deployment.yaml
```

---

## Release Process

### Automated Release

Use the `release.sh` script for automated releases:

```bash
# Interactive mode
./release.sh

# Bump patch version (2.0.0 -> 2.0.1)
./release.sh patch

# Bump minor version (2.0.0 -> 2.1.0)
./release.sh minor

# Bump major version (2.0.0 -> 3.0.0)
./release.sh major

# Build without version bump
./release.sh --build-only
```

The script will:
1. ✅ Check dependencies
2. ✅ Bump version in files
3. ✅ Run all tests
4. ✅ Build Python packages (sdist + wheel)
5. ✅ Create release artifacts (checksums, notes)
6. ✅ Build Docker images (3 variants)
7. ✅ Create git tag

### Manual Release

If you prefer manual release:

```bash
# 1. Update version numbers
vim pyproject.toml
vim src/fastreact/__init__.py

# 2. Run tests
python3 -m pytest tests/ -v

# 3. Build packages
python3 -m build

# 4. Build Docker images
docker build --target production -t fastreactnano/fastreact-nano:v2.0.0 .

# 5. Create git tag
git tag -a v2.0.0 -m "Release version 2.0.0"
git push origin v2.0.0

# 6. Publish to PyPI
twine upload dist/*

# 7. Publish to Docker Hub
docker push fastreactnano/fastreact-nano:v2.0.0
docker push fastreactnano/fastreact-nano:latest
```

### PyPI Publishing

```bash
# Install twine
pip install twine

# Test publishing to TestPyPI
twine upload --repository testpypi dist/*

# Publish to production PyPI
twine upload dist/*
```

---

## Configuration

### Environment Variables

Core configuration via environment variables:

```bash
# LLM Configuration
export FASTRACT_MODEL=gpt-4o-mini
export FASTRACT_API_KEY=sk-xxx
export FASTRACT_API_BASE=https://api.openai.com/v1
export FASTRACT_TEMPERATURE=0.7
export FASTRACT_MAX_TOKENS=4096

# Tool Configuration
export FASTRACT_MAX_FILE_SIZE=1048576
export FASTRACT_EXEC_TIMEOUT=30
export FASTRACT_WORKING_DIR=/workspace

# Multi-Tenant Configuration
export FEISHU_MULTITENANT=true
export FEISHU_BASE_WORKSPACE=/workspace
```

### Configuration File

JSON configuration file (optional):

```json
{
  "llm": {
    "model": "gpt-4o-mini",
    "api_base": "https://api.openai.com/v1",
    "api_key": "sk-xxx",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "mcp": {
    "servers": [
      {
        "name": "graphrag",
        "command": "python3",
        "args": ["examples/graph_rag_server.py"],
        "isolation": "lazy_per_user",
        "idle_timeout": 300,
        "max_instances": 10
      }
    ]
  }
}
```

Config search paths:
1. `~/.fastreact/config.json`
2. `./.fastreact/config.json`
3. `./config.json`

---

## Monitoring

### Health Checks

Gateway health endpoint:

```bash
curl http://localhost:9000/health
```

Response:

```json
{
  "status": "healthy",
  "version": "2.0.0",
  "uptime": 12345
}
```

### Metrics (Optional)

Enable Prometheus metrics:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'fastreact'
    static_configs:
      - targets: ['fastreact-gateway:9000']
    metrics_path: '/metrics'
```

### Logging

Logs are written to:

- **Container**: stdout/stderr (Docker logs)
- **File**: `/var/log/fastreact/` (if configured)

View logs:

```bash
# Docker logs
docker-compose logs -f gateway

# Kubernetes logs
kubectl logs -f deployment/fastreact-gateway -n fastreact
```

---

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Check what's using the port
lsof -i :9000

# Change port in docker-compose.yml
ports:
  - "9001:9000"  # Use 9001 instead
```

#### 2. Permission Denied

```bash
# Fix workspace permissions
sudo chown -R $USER:$USER /workspace
```

#### 3. Out of Memory

```bash
# Increase Docker memory limit
# Docker Desktop -> Settings -> Resources -> Memory -> 4GB+
```

#### 4. MCP Server Failed to Start

```bash
# Check MCP server logs
docker-compose exec gateway bash
ps aux | grep graph_rag_server

# Verify server configuration
cat config.json | grep -A 10 '"mcp"'
```

### Debug Mode

Enable debug logging:

```bash
export FASTRACT_LOG_LEVEL=DEBUG
docker-compose up
```

---

## Security

### Production Checklist

- [ ] Use non-root user in containers (✅ done in Dockerfile)
- [ ] Limit container capabilities (add `--cap-drop=ALL`)
- [ ] Use secrets for sensitive data (API keys, passwords)
- [ ] Enable TLS/SSL for external connections
- [ ] Implement rate limiting
- [ ] Regular security updates (`docker-compose pull`)

### Secrets Management

Never commit secrets to git. Use:

```bash
# Docker secrets
echo "sk-xxx" | docker secret create fastreact_api_key -

# Kubernetes secrets
kubectl create secret generic fastreact-secrets \
  --from-literal=api-key="sk-xxx"

# Environment file (gitignored)
cp .env.example .env
vim .env  # Add secrets
git update-index --assume-unchanged .env
```

---

## Performance Tuning

### Resource Limits

```yaml
# docker-compose.yml
services:
  gateway:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Concurrency

Adjust concurrent request handling:

```bash
export FASTRACT_MAX_CONCURRENT_REQUESTS=100
export UVICORN_WORKERS=4
```

---

## Support

- **GitHub Issues**: https://github.com/atom32/FastReAct/issues
- **Documentation**: https://github.com/atom32/FastReAct/tree/main/docs
- **Discord**: (Coming soon)

---

**Last Updated**: 2026-02-18
**Version**: 2.0.0
