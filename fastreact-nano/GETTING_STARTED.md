# FastReAct Nano - 5-Minute Quick Start

**Get started with FastReAct Nano in 5 minutes**

---

## Choose Your Installation Method

### Method 1: uv (Recommended - 1 minute) ⚡

**Fastest installation, 10-100x faster than pip**

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install FastReAct Nano
uv tool install fastreact-nano

# Run FastReAct
fastreact-nano
```

### Method 2: One-Click Script (2 minutes) 🚀

**Automated installation for all platforms**

**Linux/macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/atom32/FastReAct/main/fastreact-nano/deploy/install.sh | bash
```

**Windows (PowerShell):**
```batch
irm https://raw.githubusercontent.com/atom32/FastReAct/main/fastreact-nano/deploy/install.bat | iex
```

### Method 3: Docker Compose (5 minutes) 🐳

**Production-ready deployment with all services**

```bash
# Navigate to deployment directory
cd fastreact-nano/deploy

# Copy environment template
cp .env.example .env

# Edit .env and add your API key
nano .env  # Add: FASTREACT_API_KEY=sk-your-key

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

**Access services:**
- HTTP daemon: http://localhost:8000
- Service console: http://localhost:3000/service

### Method 4: Manual Installation (3 minutes) 📦

**Traditional Python package installation**

```bash
# Install from source
cd fastreact-nano
pip install -e ".[all]"

# Run
fastreact-nano
```

---

## First Steps

### 1. Set Your API Key

FastReAct needs an LLM API key to work. Choose one:

**OpenAI:**
```bash
export FASTREACT_API_KEY=sk-your-openai-key
export FASTREACT_MODEL=gpt-4o-mini
```

**Anthropic:**
```bash
export FASTREACT_API_KEY=sk-ant-your-anthropic-key
export FASTREACT_MODEL=claude-3-5-sonnet-20241022
```

**DeepSeek:**
```bash
export FASTREACT_API_KEY=sk-your-deepseek-key
export FASTREACT_MODEL=deepseek-chat
```

**SiliconFlow:**
```bash
export FASTREACT_API_KEY=sk-your-siliconflow-key
export FASTREACT_API_BASE=https://api.siliconflow.cn/v1
export FASTREACT_MODEL=deepseek-ai/DeepSeek-V3
```

### 2. Run Your First Query

**Using CLI:**
```bash
fastreact "What is 2+2?" --model gpt-4o-mini
```

**Using Python API:**
```python
from fastreact import ask

response = await ask("What is 2+2?")
print(response)
```

**Using HTTP Daemon:**
```bash
# Start HTTP/SSE service daemon
python -m fastreact.adapters.http

# Connect from client
# http://localhost:8000
```

---

## Explore Adapters

FastReAct supports multiple adapters for different use cases:

| Adapter | Use Case | Port |
|---------|----------|------|
| **CLI** | Command-line interface, scripting | - |
| **HTTP** | REST API with streaming, integrations | 8000 |

### Start Specific Adapter

```bash
# CLI (command-line interface)
python -m fastreact.adapters.cli

# HTTP API (REST + SSE)
python -m fastreact.adapters.http

```

---

## Common Issues

### Python Not Found

```bash
# Install Python 3.11
# Ubuntu/Debian:
sudo apt-get update && sudo apt-get install python3.11

# macOS:
brew install python@3.11

# Windows:
# Download from https://www.python.org/downloads/
```

### Permission Denied

```bash
# Use --user flag
pip install --user fastreact-nano

# Or use virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install fastreact-nano
```

### Port Already in Use

```bash
# Find and stop the conflicting service
lsof -i :8000  # Find the process
kill -9 <PID>  # Stop it

# Or change port in .env
echo "FASTREACT_SERVICE_PORT=8001" >> .env
```

### API Key Issues

```bash
# Verify API key is set
echo $FASTREACT_API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $FASTREACT_API_KEY"
```

---

## Next Steps

1. **Read full documentation**: [deploy/README.md](deploy/README.md)
2. **Explore adapters**: [docs/ADAPTERS.md](docs/ADAPTERS.md)
3. **Build custom tools**: [docs/TOOLS.md](docs/TOOLS.md)
4. **Configure production**: [deploy/README.md](deploy/README.md#production-deployment)
5. **View examples**: [examples/](examples/)

---

## Need Help?

- [GitHub Issues](https://github.com/atom32/FastReAct/issues) - Report bugs or request features
- [Full Documentation](../README.md) - Complete project documentation
- [Deployment Guide](deploy/README.md) - Production deployment options
- [Architecture](docs/ARCHITECTURE.md) - Understand how it works

---

**Version**: 2.1.0
**Last Updated**: 2026-02-18

**Happy Hacking!**
