# FastReAct Nano v2.0

**Event-Driven AI Agent - Microkernel + Adapters Architecture**

```
Core: ~3,000 lines of pure logic
Adapters: Optional interface layers
Philosophy: Zero-Copy, Event-Driven, Stateless
```

## Performance Benchmark

**Zero-Copy Protocol: 74% Faster**

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| File Listing (with tool) | 50.74s | **13.38s** | **4x faster** |
| Simple Calculation | 2.87s | **1.45s** | **49% faster** |

**How?** By not repeating tool outputs that the user can already see in their terminal.

```python
# Old way (50s):
User: "List files"
→ LLM: "I will list files..." (5s)
→ Tool: ls -la (0.1s)
→ LLM: "Here are ALL the files: 1. file1, 2. file2..." (45s) # WASTE

# New way (13s):
User: "List files"
→ LLM: [uses tool directly] (5s)
→ Tool: ls -la (0.1s)
→ LLM: "Found 32 items." (1s) # EFFICIENT
```

## Quick Start

### Minimal Installation (Core Only)

```bash
pip install fastreact-nano
```

```python
import asyncio
from fastreact import Agent

async def main():
    agent = Agent()

    # Event streaming (full visibility)
    async for event in agent.run_event_stream("What is 2+2?"):
        if event.type == EventType.THINK:
            print(f"Thinking: {event.content}")
        elif event.type == EventType.SESSION_END:
            print(f"Done: {event.content}")

asyncio.run(main())
```

### CLI Usage

```bash
# Install with CLI adapter
pip install fastreact-nano[cli]

# Run queries
fastreact "List files in current directory"
fastreact "Analyze this codebase" --model deepseek-chat

# Interactive mode
fastreact interactive
```

### HTTP Server (SSE Streaming)

```bash
# Install with HTTP adapter
pip install fastreact-nano[http]

# Start server
python -m fastreact.adapters.http

# OpenAI-compatible endpoint
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"content": "What is 2+2?"}], "stream": true}'
```

## Architecture

```
┌─────────────────────────────────────────┐
│     User Interfaces (Adapters)           │
│  CLI  │  HTTP-SSE  │  Gateway  │  SDK   │
└──────────────┬───────────────────────────┘
               │ AgentEvent Stream
┌──────────────▼───────────────────────────┐
│        FastReAct Nano Kernel             │
│      (Stateless, Event-Driven)           │
│                                          │
│  • ReActCore - Pure event generator      │
│  • Zero-Copy Protocol - No repetition    │
│  • Token Guard - Context monitoring      │
│  • Ghost Map - Filesystem memory         │
│  • Safety - Guardrails & confirmation    │
│  • 4 Tools (read/write/exec/edit)        │
└──────────────┬───────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼─────────┐    ┌─────▼─────┐
│  LiteLLM    │    │  Skills   │
│  Provider   │    │  (MD)     │
└─────────────┘    └───────────┘
```

## Key Features

### Event-Driven Architecture

All communication through `AgentEvent` stream:

```python
class EventType(Enum):
    SESSION_START = "session_start"
    THINK = "think"           # LLM reasoning
    TOOL_CALL = "tool_call"   # Tool invocation
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    SESSION_END = "session_end"
```

### Cortex Components (Advanced)

- **Token Guard** - Context monitoring with smart truncation
- **Ghost Map** - Filesystem memory for efficient navigation
- **Safety** - Guardrails with confirmation dialogs

### Zero-Copy Protocol

LLM doesn't repeat what user already sees:
- Tool outputs visible in terminal → LLM stays silent
- File contents shown → LLM confirms briefly
- Directory listed → LLM reports count only

## Configuration

```bash
# Environment variables
export FASTRACT_MODEL=deepseek-ai/DeepSeek-V3.2
export FASTRACT_API_BASE=https://api.siliconflow.cn/v1
export FASTRACT_API_KEY=sk-xxx
export FASTRACT_MAX_TOKENS=4096
```

```python
# Python config
from fastreact import Config, Agent

config = Config()
config.llm.model = "gpt-4o"
config.llm.temperature = 0.7
config.react.max_iterations = 20

agent = Agent(config=config)
```

## Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read file content with line range support |
| `write_file` | Atomic file write with backup |
| `exec` | Execute shell commands (cross-platform) |
| `edit_file` | Text replacement editing |

## Skills (Optional)

Load skills from Markdown files:

```python
agent = Agent(skills_dir="./skills")
response = await agent.run("Create git branch", skills=["git_workflow"])
```

Built-in skills:
- `file_ops` - Advanced file operations
- `code_review` - Code quality analysis
- `git_workflow` - Git workflow automation

## Installation Variants

```bash
# Core (minimal)
pip install fastreact-nano

# CLI adapter
pip install fastreact-nano[cli]

# HTTP adapter (SSE)
pip install fastreact-nano[http]

# WebSocket gateway
pip install fastreact-nano[gateway]

# Everything
pip install fastreact-nano[all]
```

## Python SDK

```python
# Simple (blocking)
from fastreact import ask_sync
response = ask_sync("What is 2+2?")

# Async with streaming
import asyncio
from fastreact import Agent, EventType

async def main():
    agent = Agent()

    async for event in agent.run_event_stream("List files"):
        if event.type == EventType.TOOL_CALL:
            print(f"Calling: {event.tool_name}")
        elif event.type == EventType.THINK:
            print(f"Thinking: {event.content}")

asyncio.run(main())
```

## Testing

```bash
# Install dev dependencies
pip install fastreact-nano[dev]

# Run tests
pytest tests/ -v

# E2E test with real LLM
python test_e2e_real.py
```

## Documentation

- [USAGE.md](USAGE.md) - Complete usage guide
- [INSTALLATION.md](INSTALLATION.md) - Installation instructions
- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Development status

## License

MIT License - see LICENSE file for details

---

**FastReAct Nano v2.0 - Event-Driven, Zero-Copy, Production Ready**
