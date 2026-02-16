# FastReAct Nano Branch

**Branch**: `nano`
**Focus**: Lightweight ReAct-based AI Agent with Web UI

---

## Branch Structure

This branch contains a simplified, streamlined version of FastReAct:

```
FastReAct/
├── fastreact-nano/          # Backend (Python)
│   ├── src/fastreact/       # Core agent logic
│   ├── tests/               # Unit & integration tests
│   ├── CLAUDE.md            # Development rules
│   └── pyproject.toml       # Python dependencies
│
├── fastreact-nano-web/      # Frontend (Next.js + React)
│   ├── app/                 # Next.js app directory
│   ├── components/          # React components
│   ├── lib/                 # Utilities and types
│   └── package.json         # Node dependencies
│
├── start.sh                 # Quick start script
├── stop.sh                  # Stop script
└── README_NANO.md          # This file
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- API Key (OpenAI/Anthropic/DeepSeek/etc.)

### Installation

```bash
# Backend
cd fastreact-nano
pip install -e ".[all]"

# Frontend
cd ../fastreact-nano-web
npm install
```

### Configuration

**Backend** (`fastreact-nano/.env`):
```bash
# Copy example
cp .env.example .env

# Edit and add your API key
# FASTRACT_API_KEY=sk-xxx
# FASTRACT_MODEL=gpt-4o-mini
```

**Frontend** (`fastreact-nano-web/.env.local`):
```bash
NEXT_PUBLIC_API_URL=ws://localhost:9000/ws
```

### Start Services

**Option 1: Use startup script** (Recommended)
```bash
cd /Users/xudawei/FastReAct
./start.sh
```

**Option 2: Manual start**
```bash
# Terminal 1 - Gateway
cd fastreact-nano
python3 -m fastreact.adapters.gateway

# Terminal 2 - Web UI
cd fastreact-nano-web
npm run dev
```

### Access

- **Web UI**: http://localhost:3000
- **Gateway**: ws://localhost:9000/ws

### Stop Services

```bash
cd /Users/xudawei/FastReAct
./stop.sh
```

---

## Features

### ✅ Implemented

1. **Non-Blocking Chat**
   - Input field always enabled
   - Send multiple messages rapidly
   - No loading spinners

2. **Graceful Interrupt**
   - Send "stop" to halt long tasks
   - LLM acknowledges naturally
   - Maintains conversation context

3. **No Duplicate Messages**
   - Each user message appears once
   - Clean chat interface

4. **WebSocket Communication**
   - Real-time event streaming
   - Auto-reconnection
   - Session persistence

5. **MCP Protocol Support**
   - Model Context Protocol
   - Tool integration
   - Server management

### 🚧 In Progress

- Visual indicators for interrupt
- Resume interrupted tasks
- Tool cancellation tokens

---

## Architecture

### Backend (fastreact-nano)

**Brain-Body Split**:
- **Core** (`src/fastreact/core/react.py`): Pure reasoning
- **Agent** (`src/fastreact/agent.py`): Loop control & tool execution

**Event-Driven**:
- Unified `AgentEvent` stream
- Real-time WebSocket delivery
- No callbacks, clean architecture

**Key Components**:
- `Gateway`: WebSocket server
- `Agent`: Task orchestration
- `Core`: LLM reasoning
- `Tools`: File operations, shell commands

### Frontend (fastreact-nano-web)

**Tech Stack**:
- Next.js 15 (App Router)
- React 19
- TypeScript
- Tailwind CSS
- WebSocket API

**Key Components**:
- `ChatInterface`: Main chat UI
- `ChatInput`: Non-blocking input
- `ChatMessage`: Message display
- `useFastReActWS`: WebSocket hook

---

## Development

### Backend Development

```bash
cd fastreact-nano

# Run tests
python3 -m pytest tests/ -v

# Run specific test
python3 -m pytest tests/unit/test_agent.py -v

# Type checking
python3 -m pytest tests/ --mypy

# Coverage
python3 -m pytest tests/ --cov=src/fastreact
```

### Frontend Development

```bash
cd fastreact-nano-web

# Type checking
npx tsc --noEmit

# Linting
npm run lint

# Build
npm run build
```

### Code Quality

**Follow CLAUDE.md rules**:
- No emojis (use `[OK]`, `[ERROR]`, etc.)
- No hardcoded paths (use `pathlib`)
- UTF-8 encoding for file I/O
- Cross-platform compatible

---

## Testing

### Automated Tests

```bash
# Quick web test
python3 tests/integration/quick_web_test.py

# Full test suite
python3 tests/integration/test_web_chat_features.py

# All tests
python3 run_tests.py all
```

### Manual Testing

1. Open http://localhost:3000
2. Send "Hello" → should see one message
3. Send "stop" → should see graceful interrupt
4. Send multiple messages rapidly → should not block

---

## Documentation

### Development Docs

- `CLAUDE.md` - Development rules & standards
- `DOCS_INDEX.md` - Documentation navigation
- `IMPLEMENTATION_SUMMARY.md` - Recent changes
- `WEB_CHAT_FIX_SUMMARY.md` - Web features implementation

### User Docs

- `QUICKSTART.md` - Getting started
- `GETTING_STARTED.md` - Detailed guide
- `TESTING_GUIDE.md` - Testing procedures

---

## Troubleshooting

### Gateway not starting

```bash
# Check logs
tail -f /tmp/fastreact-gateway.log

# Check if port is in use
lsof -i :9000

# Kill existing process
pkill -f fastreact.adapters.gateway
```

### Web UI not connecting

```bash
# Check Gateway is running
ps aux | grep gateway

# Check WebSocket URL
echo $NEXT_PUBLIC_API_URL  # Should be ws://localhost:9000/ws

# Check browser console for errors
```

### Tests failing

```bash
# Check API key is set
echo $FASTRACT_API_KEY

# Run with verbose output
python3 -m pytest tests/unit/test_agent.py -v -s
```

---

## Difference from Main Branch

### Main Branch (V1)
- **Dual Mode**: ReAct + IEL/ToolGraph
- **Full Features**: Complete enterprise framework
- **Complex**: More configuration options
- **Location**: `/src`, `/tests` (root)

### Nano Branch
- **Single Mode**: ReAct only
- **Simplified**: Essential features only
- **Web UI**: Built-in React interface
- **Location**: `/fastreact-nano`, `/fastreact-nano-web`

---

## Contributing

1. Follow `CLAUDE.md` rules
2. Add tests for new features
3. Update documentation
4. Run tests before committing
5. Use conventional commit messages

---

## License

MIT License - See main branch LICENSE file

---

**Branch Maintainer**: @atom32
**Last Updated**: 2026-02-16
**Version**: 2.1.0
