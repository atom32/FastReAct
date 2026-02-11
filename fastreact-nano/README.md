# FastReAct Nano

**Ultra-Lightweight Event-Driven AI Agent SDK**

FastReAct Nano is a minimalist, production-ready AI agent framework with a clean Brain-Body split architecture.

## Features

- **180-Line Core**: Pure intent generator, human-readable
- **Brain-Body Split**: Clean separation of reasoning and execution
- **Event-Driven**: Unified AgentEvent protocol for all communication
- **Token-Aware**: Smart context management with monitoring
- **Safety-First**: Built-in guardrails for dangerous operations
- **Zero-Copy Protocol**: 74% performance gain through optimized message flow
- **Filesystem Memory**: Ghost Map for context-aware navigation
- **Steering Support**: Real-time intervention into agent execution
- **Extensible**: Skills, tools, and adapter system

## Quick Start

### Installation

```bash
# Install from source
cd fastreact-nano
pip install -e .

# Or install with CLI support
pip install -e ".[cli]"
```

### Configuration

Create a `.env` file or set environment variables:

```bash
# LLM Configuration
export ANTHROPIC_API_KEY="sk-xxx"  # or OPENAI_API_KEY, DEEPSEEK_API_KEY
export MODEL="claude-3-5-sonnet-20241022"

# FastReAct Configuration (optional)
export FASTREACT_BASE_DIR=".fastreact"
```

Or create `fastreact.yaml`:

```yaml
llm:
  model: "claude-3-5-sonnet-20241022"
  temperature: 0.7
  max_tokens: 4096

react:
  enable_safety: true
  enable_filesystem_memory: true
  max_iterations: 20
```

### Basic Usage

```python
import asyncio
from fastreact import Agent

async def main():
    # Create agent
    agent = Agent()

    # Run with event stream
    async for event in agent.run_event_stream("What is 2+2?"):
        if event.type == EventType.THINK:
            print(f"Thinking: {event.content}")
        elif event.type == EventType.TOOL_CALL:
            print(f"Calling: {event.tool_name}")
        elif event.type == EventType.SESSION_END:
            print(f"Answer: {event.content}")

asyncio.run(main())
```

### Simple API

```python
from fastreact import ask

# Quick query
response = await ask("Analyze this codebase")
print(response)
```

## Architecture: Brain-Body Split

```
User Query → Agent (Body) → Core (Brain)
                   ↓              ↓
              ┌────────────────────────┐
              │  Loop Control          │
              │  - Safety Checks       │    ┌──────────────┐
              │  - Tool Execution      │ ←→ │ Pure Intent  │
              │  - Context Monitor     │    │ - LLM Call   │
              │  - Filesystem Memory   │    │ - Emit Event │
              └────────────────────────┘    └──────────────┘
                   595 lines                  180 lines
```

**The Brain (Core)**: 180 lines of pure reasoning
- Calls LLM
- Emits THINK events
- Emits TOOL_CALL intents
- Zero execution, zero side effects

**The Body (Agent)**: Full execution layer
- Loop control
- Tool execution
- Safety checks
- Context monitoring
- Filesystem memory
- Steering injection

## Event Protocol

All communication flows through `AgentEvent`:

```python
class EventType:
    SESSION_START = "session_start"
    THINK = "think"              # LLM reasoning
    TOOL_CALL = "tool_call"      # Intent to use tool
    TOOL_RESULT = "tool_result"  # Tool execution result
    STEP_END = "step_end"        # Reasoning step complete
    SESSION_END = "session_end"
    ERROR = "error"
    ASK_USER = "ask_user"        # Confirmation request
```

## Project Status

**Version**: 2.1.0
**Status**: Production Ready

### Completed
- [x] Brain-Body Split Architecture
- [x] 180-Line Core (Pure Intent Generator)
- [x] Event-Driven Protocol
- [x] Safety Policy (Guardrails)
- [x] Context Monitor (Token Management)
- [x] Filesystem Memory (Ghost Map)
- [x] Steering System (Real-time Intervention)
- [x] CLI Adapter
- [x] HTTP Adapter (SSE Streaming)
- [x] REPL Adapter (Session Management)
- [x] Gateway Adapter (WebSocket)

### Adapters
- **CLI**: Command-line interface with Rich UI
- **HTTP**: REST API with Server-Sent Events
- **REPL**: Interactive session with history
- **Gateway**: WebSocket support for web UIs

## Design Principles

1. **Anti-Entropy**: Core is locked at 180 lines, preventing AI-induced bloat
2. **SDK-First**: Core as high-concurrency logic engine
3. **Human-Comprehensible**: Code is readable and modifiable
4. **Ecosystem Isolation**: All adapters are replaceable plugins

## Compliance

| Principle | Score | Notes |
|-----------|-------|-------|
| 反熵增 (Anti-Entropy) | 100/100 | Core locked at 180 lines |
| SDK化 (SDK-First) | 100/100 | Pure intent generator |
| 人类掌控 (Human Control) | 100/100 | Readable, intervenable |
| 生态隔离 (Ecosystem) | 100/100 | Adapters are plugins |

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Event Protocol](docs/EVENTS.md)
- [Safety System](docs/SAFETY.md)
- [Adapter Guide](docs/ADAPTERS.md)

## License

MIT License - see LICENSE file

## Contributing

Please follow CLAUDE.md rules:
- No emojis in code
- No hardcoded paths
- UTF-8 encoding
- Module independence
- DRY principle
