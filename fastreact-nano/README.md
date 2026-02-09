# FastReAct Nano

**Lightweight Multi-Channel ReAct Agent Framework**

FastReAct Nano is a minimalist yet powerful AI agent framework combining the best of Nanobot, Moltbot, and FastReAct v1.

## Features

- **Lightweight**: ~3,000 lines of core code
- **Fast**: <1 second startup, <2 second first response
- **Multi-Channel**: Support for Telegram, WeChat, CLI, HTTP (extensible)
- **Token-Aware**: Smart context management with monitoring
- **Plugin System**: Hot-reload skills and tools
- **File-Based**: Simple JSONL storage, no database needed
- **Real-Time**: WebSocket support for streaming responses

## Quick Start

### Installation

```bash
# Install from source
cd fastreact-nano
pip install -e .

# Or install with channel support
pip install -e ".[channels]"
```

### Configuration

Create a `.env` file or set environment variables:

```bash
# LLM Configuration
export ANTHROPIC_API_KEY="sk-xxx"  # or OPENAI_API_KEY, DEEPSEEK_API_KEY
export MODEL="claude-3-5-sonnet-20241022"  # optional

# FastReAct Configuration
export FASTREACT_BASE_DIR=".fastreact"
```

Or create `fastreact.yaml`:

```yaml
llm:
  model: "claude-3-5-sonnet-20241022"
  temperature: 0.7
  max_tokens: 4096

paths:
  base_dir: ".fastreact"
  data_dir: ".fastreact/data"
  sessions_dir: ".fastreact/data/sessions"
  memory_dir: ".fastreact/data/memory"
```

### Basic Usage

```python
import asyncio
from fastreact import LiteLLMProvider, ToolRegistry, ReActCore, EchoTool

async def main():
    # Setup LLM
    llm = LiteLLMProvider()

    # Setup tools
    tools = ToolRegistry()
    tools.register(EchoTool())

    # Create agent
    agent = ReActCore(llm=llm, tools=tools)

    # Run
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Echo 'Hello World'"},
    ]

    response = await agent.run(messages)
    print(response)

asyncio.run(main())
```

## Architecture

```
Channels (Telegram/WeChat/CLI/HTTP)
        |
    ChannelManager
        |
    MessageBus (async queue)
        |
    ReActCore (Think-Act-Observe)
        |
    Context/Tools/LLM/Cache
```

## Project Status

**Version**: 2.0.0-alpha
**Progress**: 50% complete

### Completed
- [x] MessageBus (async queues)
- [x] ReActCore (Think-Act-Observe loop)
- [x] LLM Provider (LiteLLM integration)
- [x] Tool System (JSON Schema validation)
- [x] ContextManager (Token monitoring)
- [x] File Storage (JSONL sessions)

### In Progress
- [ ] WebSocket Gateway
- [ ] Channel System
- [ ] CLI Channel
- [ ] Telegram Channel

### Planned
- [ ] Plugin System
- [ ] LRU Cache
- [ ] Stream Callbacks
- [ ] Unit Tests

## Design Principles

1. **No Emojis**: Use text markers `[OK]`, `[ERROR]`, `[WARNING]`
2. **No Hardcoded Paths**: Use `pathlib.Path` and configuration
3. **UTF-8 Encoding**: Specify for all file operations
4. **Module Independence**: No layer penetration
5. **DRY**: Don't repeat yourself
6. **Cross-Platform**: Windows/Linux compatible

## Documentation

- [Implementation Tracker](../docs_archive/temp/implementation_tracker.md)
- [Universal Agent Design v2](../docs_archive/temp/universal_agent_design_v2.md)

## License

MIT License - see LICENSE file

## Contributing

Please follow CLAUDE.md rules:
- No emojis in code
- No hardcoded paths
- UTF-8 encoding
- Module independence
- DRY principle
