# FastReAct Nano - Docker Quickstart

This guide shows you how to run FastReAct Nano with Docker in less than 2 minutes.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+ (or `docker compose` v2)

## Quick Start (2 minutes)

### 1. Copy Environment File

```bash
cp .env.example .env
```

### 2. Edit Configuration

Edit `.env` and add your API key:

```bash
FASTRACT_API_KEY=sk-your-api-key-here
FASTRACT_MODEL=gpt-4o-mini
```

### 3. Start Web UI

```bash
docker compose up -d web
```

### 4. Access Web UI

Open your browser: http://localhost:8501

### 5. Stop Services

```bash
docker compose down
```

## Available Services

### Web UI (Port 8501)

ChatGPT-like interface for interacting with FastReAct.

```bash
docker compose up -d web
```

Access at: http://localhost:8501

**Features:**
- Chat interface
- Real-time event streaming
- Session history
- Configuration sidebar
- File operations
- Code execution

### Gateway (Port 9000)

WebSocket gateway for custom integrations.

```bash
docker compose up -d gateway
```

Access at: http://localhost:9000

**Features:**
- WebSocket communication
- Session management
- Real-time streaming
- Multi-client support

### Both Services

```bash
docker compose up -d
```

## Development

### View Logs

```bash
# Web service logs
docker compose logs -f web

# Gateway service logs
docker compose logs -f gateway

# All logs
docker compose logs -f
```

### Restart Services

```bash
docker compose restart web
```

### Rebuild After Code Changes

```bash
docker compose up -d --build web
```

### Access Container Shell

```bash
docker compose exec web bash
```

## Configuration

### Environment Variables

All configuration via `.env` file:

```bash
# LLM Configuration
FASTRACT_MODEL=gpt-4o-mini
FASTRACT_API_KEY=sk-xxx
FASTRACT_API_BASE=https://api.openai.com/v1
FASTRACT_TEMPERATURE=0.7
FASTRACT_MAX_TOKENS=4096

# Tool Configuration
FASTRACT_MAX_FILE_SIZE=1048576
FASTRACT_EXEC_TIMEOUT=30
FASTRACT_WORKING_DIR=/workspace

# Streamlit Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
```

### Volume Mounts

The following directories are mounted:

- `./workspace:/workspace` - Working directory for file operations
- `./src:/app/src:ro` - Source code (read-only, for hot-reload)
- `./.fastreact:/app/.fastreact:ro` - Configuration (read-only)

## Troubleshooting

### Port Already in Use

If ports 8501 or 9000 are already in use:

```bash
# Check what's using the port
lsof -i :8501
lsof -i :9000

# Change ports in docker-compose.yml
ports:
  - "8502:8501"  # Use 8502 instead
```

### Container Won't Start

Check logs:

```bash
docker compose logs web
```

Common issues:
- Missing API key in `.env`
- Invalid API base URL
- Network connectivity issues

### Permission Issues

If container can't write to workspace:

```bash
# Fix workspace permissions
chmod 755 ./workspace
```

### Health Check Failing

The container includes a health check. If it fails:

```bash
# Check health status
docker compose ps

# Check logs
docker compose logs web
```

## Production Deployment

### Use Image from Docker Hub (TODO)

```bash
docker pull fastreact/nano:latest
docker run -p 8501:8501 -v $(pwd)/workspace:/workspace fastreact/nano:latest
```

### Custom Configuration

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  web:
    image: fastreact/nano:latest
    ports:
      - "8501:8501"
    volumes:
      - ./workspace:/workspace
    environment:
      - FASTRACT_API_KEY=${FASTRACT_API_KEY}
      - FASTRACT_MODEL=${FASTRACT_MODEL}
    restart: always
```

Run with:

```bash
docker compose -f docker-compose.prod.yml up -d
```

## Next Steps

- Read [README_NANO.md](README_NANO.md) for full documentation
- Check [CLAUDE.md](CLAUDE.md) for development rules
- Explore [examples/](../examples/) for usage examples
- Visit [DOCS_INDEX.md](DOCS_INDEX.md) for all documentation

## Support

- GitHub Issues: https://github.com/atom32/FastReAct/issues
- Documentation: https://github.com/atom32/FastReAct
