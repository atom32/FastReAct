# FastReAct Nano - Deployment Guide

**Production-ready deployment guide for FastReAct Nano v2.0**

---

## Table of Contents

- [Quick Start](#quick-start)
- [Deployment Methods](#deployment-methods)
  - [Method 1: uv (Recommended)](#method-1-uv-recommended)
  - [Method 2: One-Click Installation Script](#method-2-one-click-installation-script)
  - [Method 3: Docker Compose](#method-3-docker-compose-recommended-for-production)
  - [Method 4: Manual pip Installation](#method-4-manual-pip-installation)
  - [Method 5: Cloud Platforms](#method-5-cloud-platforms)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Choose Your Deployment Method

| Method | Time Required | Difficulty | Best For |
|--------|--------------|------------|----------|
| **uv** | 1 minute | Easy | Development, quick testing |
| **Installation Script** | 2 minutes | Easy | First-time users |
| **Docker Compose** | 5 minutes | Medium | Production, servers |
| **Manual pip** | 3 minutes | Easy | Custom environments |
| **Cloud Platform** | 5-10 minutes | Easy | Zero-server deployment |

---

## Deployment Methods

### Method 1: uv (Recommended)

**uv** is a modern Python package manager from Astral, 10-100x faster than pip.

#### Prerequisites

None! uv will install Python if needed.

#### Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install FastReAct Nano
uv tool install fastreact-nano

# Run FastReAct Nano
fastreact-nano
```

#### Advantages

- Fastest installation (10-100x faster than pip)
- Automatic Python version management
- Isolated environment (no conflicts)
- Cross-platform consistency

---

### Method 2: One-Click Installation Script

Automated installation script for Linux, macOS, and Windows.

#### Linux / macOS

```bash
# Download and run installation script
curl -sSL https://raw.githubusercontent.com/atom32/FastReAct/main/fastreact-nano/deploy/install.sh | bash

# Or download and run manually
wget https://raw.githubusercontent.com/atom32/FastReAct/main/fastreact-nano/deploy/install.sh
chmod +x install.sh
./install.sh
```

#### Windows

```batch
REM Download and run installation script (PowerShell)
irm https://raw.githubusercontent.com/atom32/FastReAct/main/fastreact-nano/deploy/install.bat | iex

REM Or download and run manually
REM 1. Download install.bat from GitHub
REM 2. Double-click install.bat
```

#### What the Script Does

1. Checks Python installation (requires 3.10+)
2. Detects operating system
3. Installs uv if available (recommended)
4. Falls back to pip if uv not found
5. Creates desktop shortcut (Linux)
6. Provides next steps

---

### Method 3: Docker Compose (Recommended for Production)

Complete production-ready deployment with all services.

#### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+

#### Quick Start

```bash
# 1. Navigate to the deployment directory
cd fastreact-nano/deploy

# 2. Copy environment template
cp .env.example .env

# 3. Edit .env and add your API keys
nano .env  # or use your preferred editor

# 4. Start services
docker-compose up -d

# 5. Check service status
docker-compose ps

# 6. View logs
docker-compose logs -f
```

#### Services

The Docker Compose setup includes:

- **service**: HTTP/SSE agentic service daemon (port 18741)
- **prometheus**: Monitoring (port 9090, optional)
- **grafana**: Metrics dashboard (port 3000, optional)

#### Starting Specific Services

```bash
# Start the HTTP daemon
docker-compose up -d service

# Start with monitoring
docker-compose --profile monitoring up -d

# Start development environment
docker-compose --profile dev up -d
```

#### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# View logs for the daemon
docker-compose logs -f service
```

#### Production Configuration

For production deployment, consider:

1. **Use external database**: Uncomment PostgreSQL configuration in `.env`
2. **Enable HTTPS**: Use reverse proxy (nginx, traefik)
3. **Resource limits**: Adjust memory/CPU limits in `docker-compose.yml`
4. **Secrets management**: Use Docker secrets or external secret manager
5. **Monitoring**: Enable Prometheus and Grafana profiles

---

### Method 4: Manual pip Installation

Traditional Python package installation.

#### Prerequisites

- Python 3.10 or higher
- pip 23.0 or higher

#### Installation

```bash
# Install core package
pip install fastreact-nano

# Install with CLI adapter
pip install "fastreact-nano[cli]"

# Install with all features
pip install "fastreact-nano[all]"

# Install from local source
cd fastreact-nano
pip install -e ".[all]"
```

#### Verification

```bash
# Verify installation
python -c "from fastreact import Agent; print('[OK] Installation successful')"

# Run CLI
fastreact "Hello, FastReAct!" --model gpt-4o-mini
```

---

### Method 5: Cloud Platforms

Deploy to cloud platforms without managing servers.

#### Replit (Free Tier Available)

1. Fork the FastReAct template on Replit
2. Click "Run" button
3. Set environment variables in Secrets tab
4. Access via provided URL

**Template**: [FastReAct on Replit](https://replit.com/@atom32/FastReAct)

#### Railway

1. Connect GitHub account to Railway
2. Select FastReAct repository
3. Configure environment variables
4. Deploy automatically

**Configuration File**: `deploy/railway.json`

```bash
# Install Railway CLI
npm install -g railway

# Link project
railway link

# Deploy
railway up
```

#### Render

1. Connect GitHub account to Render
2. Create new "Web Service"
3. Select FastReAct repository
4. Configure environment variables
5. Deploy automatically

**Configuration File**: `deploy/render.yaml`

#### Zeabur

1. Connect GitHub account to Zeabur
2. Create new service from FastReAct repository
3. Configure environment variables
4. Deploy automatically

---

## Configuration

### Environment Variables

Create a `.env` file in the deployment directory:

```bash
# Required: LLM Configuration
FASTREACT_MODEL=gpt-4o-mini
FASTREACT_API_KEY=sk-your-api-key-here

# Optional: Custom API base
# FASTREACT_API_BASE=https://api.openai.com/v1

# Optional: LLM parameters
FASTREACT_TEMPERATURE=0.7
FASTREACT_MAX_TOKENS=4096

# Optional: Service port
FASTREACT_SERVICE_PORT=18741

```

### Config File (Alternative)

Create `~/.fastreact/config.json`:

```json
{
  "llm": {
    "model": "gpt-4o-mini",
    "api_key": "sk-your-api-key-here",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "react": {
    "enable_safety": true,
    "max_iterations": 128
  }
}
```

**Priority**: Constructor parameters > Config file > Environment variables > Defaults

---

## Troubleshooting

### Installation Issues

#### Python Not Found

```bash
# Check Python installation
python3 --version

# Install Python (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install python3.11

# Install Python (macOS)
brew install python@3.11
```

#### Permission Denied

```bash
# Use user installation
pip install --user fastreact-nano

# Or use virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install fastreact-nano
```

#### Docker Build Fails

```bash
# Clean Docker cache
docker system prune -a

# Rebuild without cache
docker-compose build --no-cache

# Check Docker logs
docker-compose logs
```

### Runtime Issues

#### API Key Not Set

```bash
# Set environment variable
export FASTREACT_API_KEY=sk-your-key

# Or add to .env file
echo "FASTREACT_API_KEY=sk-your-key" >> .env
```

#### Port Already in Use

```bash
# Change port in .env
echo "FASTREACT_SERVICE_PORT=8002" >> .env

# Or find and stop the conflicting service
lsof -i :18741
```

#### Connection Refused

```bash
# Check if service is running
docker-compose ps

# Restart service
docker-compose restart service

# Check logs
docker-compose logs -f service
```

### Getting Help

- [GitHub Issues](https://github.com/atom32/FastReAct/issues)
- [Documentation](https://github.com/atom32/FastReAct#readme)
- [Community Chat](https://discord.gg/fastreact)

---

## Advanced Configuration

### Production Deployment Checklist

- [ ] Set strong API keys in `.env`
- [ ] Enable HTTPS with reverse proxy
- [ ] Configure external database (PostgreSQL)
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Configure log aggregation
- [ ] Set up automated backups
- [ ] Configure rate limiting
- [ ] Enable firewall rules
- [ ] Set up health checks
- [ ] Configure auto-scaling

### Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use strong passwords** for database
3. **Enable firewall** rules to restrict access
4. **Use HTTPS** in production
5. **Rotate API keys** regularly
6. **Monitor logs** for suspicious activity
7. **Keep dependencies** updated

### Performance Tuning

1. **Adjust worker counts** based on CPU cores
2. **Enable caching** for repeated queries
3. **Use CDN** for static assets
4. **Optimize database queries** with indexes
5. **Enable compression** for API responses

---

## Next Steps

After deployment:

1. [Read the User Guide](../README_NANO.md)
2. [Explore Adapters](../docs/ADAPTERS.md)
3. [Build Custom Tools](../docs/TOOLS.md)
5. [Set Up Monitoring](../docs/MONITORING.md)

---

**Last Updated**: 2026-02-18
**Version**: 2.0.0
