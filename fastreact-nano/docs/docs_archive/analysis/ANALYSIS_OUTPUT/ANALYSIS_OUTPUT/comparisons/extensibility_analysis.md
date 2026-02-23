# Extensibility Analysis: FastReAct vs OpenClaw vs Nanobot

**Analysis Date**: 2026-02-18
**Projects Analyzed**:
- FastReAct Nano v2.1 (Python)
- OpenClaw (TypeScript)
- Nanobot (Python)

---

## Executive Summary

This analysis measures how easy it is to extend each project with new functionality across three critical scenarios:

1. **Adding a New Tool** - Core agent capabilities
2. **Adding a New Channel/Adapter** - Integration with chat platforms
3. **Adding a New LLM Provider** - Support for new AI models

### Overall Rankings

| Project | Tool Extensibility | Channel Extensibility | LLM Provider Extensibility | **Overall Score** |
|---------|-------------------|----------------------|---------------------------|------------------|
| **Nanobot** | **2/10** (Easiest) | **3/10** (Easy) | **2/10** (Easiest) | **🥇 1st Place** |
| **FastReAct** | **3/10** (Easy) | **6/10** (Moderate) | **3/10** (Easy) | **🥈 2nd Place** |
| **OpenClaw** | **7/10** (Complex) | **8/10** (Complex) | **5/10** (Moderate) | **🥉 3rd Place** |

**Lower score = Easier to extend**

---

## Scenario 1: Adding a New Tool

### FastReAct Nano

**Difficulty**: 3/10 (Easy)

**Files to Edit**: 1-2 files
**Lines of Code**: ~50-150 lines
**Steps**: 3 steps

#### Step-by-Step Guide

**1. Create the tool file** (1 new file)

```python
# src/fastreact/tools/my_tool.py
from pathlib import Path
from typing import Any, Optional
from fastreact.core.tools import Tool

class MyTool(Tool):
    """My custom tool"""

    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "Does something useful"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Input parameter"
                }
            },
            "required": ["input"]
        }

    async def execute(self, input: str) -> str:
        # Tool logic here
        return f"Processed: {input}"
```

**2. Register the tool** (edit `src/fastreact/agent.py`)

```python
# In Agent._setup_tools() method, add:
from fastreact.tools.my_tool import MyTool

def _setup_tools(self):
    # ... existing tools ...

    # Register custom tool
    self._tools.register(MyTool())
```

**3. Update exports** (edit `src/fastreact/tools/__init__.py`)

```python
from fastreact.tools.my_tool import MyTool

__all__ = [
    "ReadFileTool",
    "WriteFileTool",
    "ExecTool",
    "EditFileTool",
    "MyTool",  # Add export
]
```

#### Real Example: ReadFileTool

- **File**: `/Users/xudawei/FastReAct/fastreact-nano/src/fastreact/tools/read_file.py`
- **Lines**: 147 lines
- **Interface**: 3 properties (`name`, `description`, `parameters`) + 1 method (`execute`)
- **Features**: Built-in validation, error handling, async execution

**Pros**:
- Clean, simple interface (3 properties + 1 method)
- JSON Schema validation built-in
- Async-first design
- No complex inheritance chains

**Cons**:
- Must edit `agent.py` to register (no auto-discovery)
- No tool composition/dependencies
- Limited to Python asyncio

---

### Nanobot

**Difficulty**: 2/10 (Easiest)

**Files to Edit**: 1 file
**Lines of Code**: ~40-100 lines
**Steps**: 2 steps

#### Step-by-Step Guide

**1. Create the tool file** (1 new file)

```python
# nanobot/agent/tools/my_tool.py
from typing import Any
from nanobot.agent.tools.base import Tool

class MyTool(Tool):
    """My custom tool"""

    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "Does something useful"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Input parameter"
                }
            },
            "required": ["input"]
        }

    async def execute(self, input: str, **kwargs: Any) -> str:
        return f"Processed: {input}"
```

**2. Register in agent initialization**

```python
# In your bot setup code
from nanobot.agent.tools.my_tool import MyTool

tool_registry.register(MyTool())
```

#### Real Example: ReadFileTool

- **File**: `/Users/xudawei/nanobot/nanobot/agent/tools/filesystem.py`
- **Lines**: 211 lines (includes 3 tools: ReadFileTool, WriteFileTool, EditFileTool)
- **Average per tool**: ~70 lines
- **Interface**: Same 3 properties + 1 method pattern

**Pros**:
- **Simplest interface** - same as FastReAct but with less boilerplate
- **No agent.py edits needed** - tools registered externally
- Built-in validation with type checking
- Clean separation of concerns

**Cons**:
- Less documentation than FastReAct
- No tool composition framework

**Why Nanobot Wins**:
- Fewer steps (2 vs 3)
- No core file editing required
- Same clean interface as FastReAct

---

### OpenClaw

**Difficulty**: 7/10 (Complex)

**Files to Edit**: 3-5 files
**Lines of Code**: ~200-500 lines
**Steps**: 6+ steps

#### Step-by-Step Guide

OpenClaw doesn't have traditional "tools" - it has **Skills**, which are more complex:

**1. Create skill directory structure**

```bash
mkdir -p skills/my-skill/{scripts,references,assets}
cd skills/my-skill
```

**2. Create SKILL.md** (YAML frontmatter + markdown instructions)

```yaml
---
name: my-skill
description: Does something useful. Use when user needs X, Y, or Z functionality.
---

# My Skill

## Quick Start

Instructions for using this skill...

## Workflow

Step-by-step guide...
```

**3. Add optional scripts** (if needed)

```python
# scripts/my_script.py
#!/usr/bin/env python3
import sys

def main():
    # Script logic
    pass

if __name__ == "__main__":
    main()
```

**4. Add optional references** (if needed)

```markdown
<!-- references/api_docs.md -->
# API Documentation

Detailed API reference...
```

**5. Validate skill**

```bash
python3 skills/skill-creator/scripts/quick_validate.py .
```

**6. Package skill**

```bash
python3 skills/skill-creator/scripts/package_skill.py . ../dist/
```

#### Real Example: model-usage Skill

- **Directory**: `/Users/xudawei/openclaw/skills/model-usage/`
- **Structure**:
  - `SKILL.md` (metadata + instructions)
  - `scripts/model_usage.py` (executable Python script)
  - `references/` (optional documentation)

**File: SKILL.md** (~370 lines)
```yaml
---
name: model-usage
description: Summarize CodexBar local cost usage by model. Use when analyzing API costs or token usage.
---

# Model Usage

## Quick Start

Run codexbar cost command...

[... detailed instructions ...]
```

**File: scripts/model_usage.py** (~200+ lines)
- Full Python script with CLI interface
- Data processing logic
- Error handling
- Output formatting

**Pros**:
- **Very powerful** - skills can include scripts, references, assets
- **Progressive disclosure** - metadata only loaded until triggered
- **Markdown-based** - easy to write documentation
- **Validation tooling** - automatic skill validation
- **Packaging system** - `.skill` files for distribution

**Cons**:
- **Much steeper learning curve**
- **No traditional tools** - all functionality must be wrapped in skills
- **More files to manage** (SKILL.md + scripts + references)
- **YAML frontmatter required**
- **No programmatic API** - skills are declarative, not code
- **TypeScript/Python hybrid** - need to understand both ecosystems

**Why OpenClaw Scores Lower**:
- Not a traditional tool system (skills are documentation-focused)
- 6+ steps vs 2-3 for competitors
- No direct code execution interface
- Must write documentation even for simple tools
- Complex directory structure required

---

### Tool Extensibility Comparison Table

| Metric | FastReAct | Nanobot | OpenClaw |
|--------|-----------|---------|----------|
| **Files to Create** | 1 | 1 | 3-5 |
| **Files to Edit** | 2 | 0 | 0 |
| **Lines of Code** | 50-150 | 40-100 | 200-500 |
| **Steps Required** | 3 | 2 | 6+ |
| **Interface Complexity** | Low (3 props + 1 method) | Low (3 props + 1 method) | High (YAML + Markdown + scripts) |
| **Auto-discovery** | No | No | Yes (skills directory) |
| **Validation** | Built-in JSON Schema | Built-in JSON Schema | Manual (validation script) |
| **Difficulty (1-10)** | **3** | **2** 🥇 | **7** |
| **Best For** | Simple to medium tools | Simple tools | Complex workflows, documentation-heavy features |

**Winner**: 🥇 **Nanobot** (fewest steps, cleanest interface)

---

## Scenario 2: Adding a New Channel/Adapter

### FastReAct Nano

**Difficulty**: 6/10 (Moderate)

**Files to Edit**: 1-2 files
**Lines of Code**: ~150-300 lines
**Steps**: 4 steps

#### Step-by-Step Guide

**1. Create the adapter** (1 new file)

```python
# src/fastreact/adapters/my_platform.py
from typing import Optional
from fastreact import Agent, EventType

class MyPlatformAdapter:
    """Custom platform adapter"""

    def __init__(self, agent: Agent):
        self.agent = agent

    async def handle_message(self, message: str) -> str:
        """Handle incoming message"""
        response = ""

        # Subscribe to event stream
        async for event in self.agent.run_event_stream(message):
            if event.type == EventType.SESSION_START:
                print(f"[START] Session: {event.session_id}")

            elif event.type == EventType.THINK:
                # Stream thinking
                print(f"[THINK] {event.content}")

            elif event.type == EventType.TOOL_CALL:
                print(f"[TOOL] {event.tool_name}")

            elif event.type == EventType.TOOL_RESULT:
                print(f"[RESULT] {event.content[:100]}...")

            elif event.type == EventType.SESSION_END:
                response = event.content
                print(f"[DONE] {response}")

        return response

    async def run(self):
        """Main loop"""
        # Platform-specific message receiving loop
        while True:
            message = await self.receive_message()
            await self.handle_message(message)

    async def receive_message(self) -> str:
        # Platform-specific implementation
        pass
```

**2. Create entry point** (optional, for CLI usage)

```python
# src/fastreact/adapters/my_platform_main.py
import asyncio
from fastreact import Agent
from fastreact.adapters.my_platform import MyPlatformAdapter

async def main():
    agent = Agent()
    adapter = MyPlatformAdapter(agent)
    await adapter.run()

if __name__ == "__main__":
    asyncio.run(main())
```

**3. Update exports** (optional)

```python
# src/fastreact/adapters/__init__.py
__all__ = [..., "MyPlatformAdapter"]
```

**4. Add optional extras to pyproject.toml** (if dependencies needed)

```toml
[project.optional-dependencies]
my_platform = ["platform-sdk>=1.0"]
```

#### Real Example: HTTP Adapter

- **File**: `/Users/xudawei/FastReAct/fastreact-nano/src/fastreact/adapters/http.py`
- **Lines**: ~200+ lines
- **Features**:
  - FastAPI web server
  - SSE (Server-Sent Events) streaming
  - OpenAI-compatible API format
  - Event-driven architecture

**Code Sample** (simplified):
```python
@app.post("/v1/chat/completions")
async def chat_completion(request: ChatRequest):
    """OpenAI-compatible chat endpoint"""
    agent = get_agent()
    response_stream = agent.run_event_stream(
        query=request.messages[-1]["content"],
        session_id=request.session_id
    )

    async def event_generator():
        async for event in response_stream:
            if event.type == EventType.THINK:
                yield f"data: {json.dumps({'content': event.content})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Pros**:
- **Event-driven protocol** - clean separation from agent core
- **No base class required** - full flexibility
- **Async/await** - modern Python concurrency
- **Can be standalone** - adapters don't modify core

**Cons**:
- **Must implement event stream handling** - more boilerplate
- **No base class** - no common interface to follow
- **Manual event type filtering** - must check EventType enum
- **Less guidance** - fewer examples to follow

---

### Nanobot

**Difficulty**: 3/10 (Easy)

**Files to Edit**: 2 files
**Lines of Code**: ~100-200 lines
**Steps**: 3 steps

#### Step-by-Step Guide

**1. Create channel class** (1 new file)

```python
# nanobot/channels/my_platform.py
from typing import Any
from nanobot.channels.base import BaseChannel
from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus
from loguru import logger

class MyPlatformChannel(BaseChannel):
    """My custom platform channel"""

    name = "my_platform"

    def __init__(self, config: Any, bus: MessageBus):
        super().__init__(config, bus)
        # Platform-specific initialization
        self.client = MyPlatformClient(config.api_key)

    async def start(self) -> None:
        """Start listening for messages"""
        self._running = True

        # Platform-specific message loop
        while self._running:
            msg = await self.client.receive_message()
            await self._handle_message(
                sender_id=msg.sender_id,
                chat_id=msg.chat_id,
                content=msg.content
            )

    async def stop(self) -> None:
        """Stop the channel"""
        self._running = False
        await self.client.close()

    async def send(self, msg: OutboundMessage) -> None:
        """Send message through platform"""
        await self.client.send_message(
            chat_id=msg.chat_id,
            content=msg.content,
            media=msg.media
        )
```

**2. Add config schema** (edit `nanobot/config/schema.py`)

```python
class MyPlatformConfig(Base):
    """My platform channel configuration."""

    enabled: bool = False
    api_key: str = ""
    allow_from: list[str] = Field(default_factory=list)
```

**3. Register in manager** (edit `nanobot/channels/manager.py`)

```python
def _init_channels(self) -> None:
    # ... existing channels ...

    # My Platform channel
    if self.config.channels.my_platform.enabled:
        try:
            from nanobot.channels.my_platform import MyPlatformChannel
            self.channels["my_platform"] = MyPlatformChannel(
                self.config.channels.my_platform,
                self.bus
            )
            logger.info("My Platform channel enabled")
        except ImportError as e:
            logger.warning(f"My Platform channel not available: {e}")
```

#### Real Example: Telegram Channel

- **File**: `/Users/xudawei/nanobot/nanobot/channels/telegram.py`
- **Lines**: ~200+ lines
- **Interface**:
  - `start()` - connect and listen for messages
  - `stop()` - cleanup and disconnect
  - `send()` - send outbound messages
  - `_handle_message()` - inbound message processing

**Code Sample** (simplified):
```python
class TelegramChannel(BaseChannel):
    name = "telegram"

    def __init__(self, config: TelegramConfig, bus: MessageBus, groq_api_key: str | None = None):
        super().__init__(config, bus)
        self.app = Application.builder().token(config.token).build()

    async def start(self) -> None:
        """Start Telegram bot"""
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message))
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

    async def _on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming message"""
        await self._handle_message(
            sender_id=update.effective_user.id,
            chat_id=update.effective_chat.id,
            content=update.message.text
        )

    async def send(self, msg: OutboundMessage) -> None:
        """Send message"""
        await self.app.bot.send_message(chat_id=msg.chat_id, text=msg.content)
```

**Pros**:
- **Clear base class** - `BaseChannel` defines the contract
- **Built-in permission system** - `is_allowed()` method
- **Message bus integration** - automatic routing
- **Config schema** - type-safe configuration
- **Manager auto-discovery** - channels auto-loaded based on config

**Cons**:
- Must inherit from `BaseChannel` (less flexible)
- Need to edit 2 core files (schema.py, manager.py)
- Requires understanding message bus events

**Why Nanobot Wins**:
- **Clear base class** with 3 simple methods
- **Manager auto-discovery** pattern
- **Built-in permission checking**
- **Message bus abstraction** handles routing

---

### OpenClaw

**Difficulty**: 8/10 (Complex)

**Files to Edit**: 5-10 files
**Lines of Code**: ~500-1000+ lines
**Steps**: 8+ steps

OpenClaw uses **Extensions** for channel integrations. These are npm packages with complex setup.

#### Step-by-Step Guide

**1. Create extension directory structure**

```bash
mkdir -p openclaw/extensions/my-platform/{src,assets}
cd openclaw/extensions/my-platform
npm init
```

**2. Create TypeScript channel implementation**

```typescript
// src/index.ts
import { Channel, ChannelPayload, ChannelResult } from 'openclaw';

export class MyPlatformChannel implements Channel {
  readonly type = 'my-platform';

  async send(payload: ChannelPayload): Promise<ChannelResult> {
    // Platform-specific send logic
    return { success: true };
  }

  async connect(): Promise<void> {
    // Connection logic
  }

  async disconnect(): Promise<void> {
    // Disconnection logic
  }
}
```

**3. Create extension manifest** (package.json)

```json
{
  "name": "openclaw-my-platform",
  "version": "1.0.0",
  "openclaw": {
    "type": "extension",
    "channel": {
      "type": "my-platform",
      "displayName": "My Platform",
      "capabilities": ["text", "media"]
    }
  }
}
```

**4. Add channel types** (edit `src/config/types.channels.ts`)

```typescript
export interface MyPlatformChannelConfig {
  enabled: boolean;
  apiKey: string;
  // ... other config
}
```

**5. Add Zod schema** (edit `src/config/zod-schema.channels.ts`)

```typescript
export const myPlatformChannelSchema = z.object({
  enabled: z.boolean().default(false),
  apiKey: z.string().default(""),
});
```

**6. Implement channel adapters** (edit `src/infra/outbound/channel-adapters.ts`)

```typescript
export async function sendToMyPlatform(
  payload: ChannelPayload,
  config: MyPlatformChannelConfig
): Promise<ChannelResult> {
  // Adapter implementation
}
```

**7. Add channel summary** (edit `src/infra/channel-summary.ts`)

```typescript
export function summarizeMyChannel(config: MyPlatformChannelConfig): string {
  return `My Platform: ${config.enabled ? 'enabled' : 'disabled'}`;
}
```

**8. Add tests** (create `src/*.test.ts`)

```typescript
describe('MyPlatformChannel', () => {
  it('should send messages', async () => {
    // Test implementation
  });
});
```

**9. Build and package**

```bash
npm run build
npm pack
```

#### Real Example: Matrix Extension

- **Directory**: `/Users/xudawei/openclaw/extensions/matrix/`
- **Structure**:
  - `src/index.ts` - Main channel implementation
  - `src/tool-actions.ts` - Tool integration
  - `assets/` - UI assets
  - `package.json` - Extension manifest
  - Multiple test files

**Estimated Complexity**:
- **TypeScript required** - no Python alternative
- **Complex type system** - interfaces, generics, Zod schemas
- **Multiple integration points** - config, adapters, summaries, tests
- **npm package management** - versioning, dependencies

**Pros**:
- **Type-safe** - TypeScript + Zod validation
- **Extremely powerful** - full extension capabilities
- **UI integration** - can add custom UI elements
- **Tool integration** - channels can provide tools
- **Professional** - npm ecosystem, semantic versioning

**Cons**:
- **Very high complexity** - 8+ steps, 5-10 files
- **TypeScript required** - learning curve for Python developers
- **Multiple touchpoints** - config, adapters, summaries, tests all need updates
- **No simple examples** - all extensions are complex production code
- **Heavy boilerplate** - even simple channels need lots of code

**Why OpenClaw Scores Lowest**:
- Most complex by far (8+ steps vs 3-4)
- TypeScript requirement (Python developers excluded)
- Multiple files to edit (5-10 vs 1-2)
- No simple "hello world" example
- Enterprise-grade complexity for simple use cases

---

### Channel/Adapter Extensibility Comparison Table

| Metric | FastReAct | Nanobot | OpenClaw |
|--------|-----------|---------|----------|
| **Files to Create** | 1-2 | 1 | 5-10 |
| **Files to Edit** | 0-1 | 2 | 3-5 |
| **Lines of Code** | 150-300 | 100-200 | 500-1000+ |
| **Steps Required** | 4 | 3 | 8+ |
| **Base Class** | No (flexible) | Yes (BaseChannel) | Yes (Channel interface) |
| **Language** | Python | Python | TypeScript |
| **Config System** | Environment variables | Pydantic models | Zod schemas |
| **Auto-discovery** | No | Yes (manager) | Yes (extensions) |
| **Permission System** | Manual | Built-in | Manual |
| **Difficulty (1-10)** | **6** | **3** 🥇 | **8** |
| **Best For** | Custom integrations, simple adapters | Chat platforms, bots | Enterprise extensions, UI integration |

**Winner**: 🥇 **Nanobot** (simplest base class, clearest pattern, fewest steps)

---

## Scenario 3: Adding a New LLM Provider

### FastReAct Nano

**Difficulty**: 3/10 (Easy)

**Files to Edit**: 0-1 files
**Lines of Code**: ~0-50 lines
**Steps**: 1-2 steps

#### Step-by-Step Guide

FastReAct uses **LiteLLM**, which already supports 100+ providers out of the box. To add a new provider:

**Option 1: Use LiteLLM's built-in support** (0 files, 0 code)

```bash
# Just set environment variables
export FASTRACT_MODEL="provider/model-name"  # e.g., "deepseek/deepseek-chat"
export PROVIDER_API_KEY="sk-xxx"
export FASTRACT_API_BASE="https://api.provider.com/v1"  # if custom endpoint
```

That's it! LiteLLM handles provider detection, prefixing, and API calls automatically.

**Option 2: Custom OpenAI-compatible endpoint** (0-1 files, ~20 lines)

If you have a custom OpenAI-compatible API:

```python
# No code needed! Just configure:
from fastreact import Agent

agent = Agent(
    config=Config(
        llm=LLMConfig(
            model="custom-model-name",
            api_base="https://my-api.com/v1",
            api_key="my-custom-key"
        )
    )
)
```

The `LiteLLMProvider` automatically detects `api_base` and switches to direct OpenAI client mode.

**Option 3: Full custom provider** (1 file, ~100 lines)

If LiteLLM doesn't support your provider:

```python
# src/fastreact/providers/my_provider.py
from typing import AsyncIterator
from fastreact.providers.litellm import LiteLLMProvider, LLMResponse

class MyProvider(LiteLLMProvider):
    """Custom LLM provider"""

    async def _call_llm(self, messages: list, **kwargs) -> LLMResponse:
        # Custom API call logic
        response = await my_http_client.post(
            "https://my-provider.com/v1/chat",
            json={"messages": messages}
        )
        return LLMResponse(
            content=response["text"],
            tool_calls=response.get("tool_calls", [])
        )
```

Then register in config:
```python
# Just use the provider class
from fastreact.providers.my_provider import MyProvider

agent = Agent(config=Config(
    llm=LLMConfig(model="my-model")
))
```

#### Real Example: Custom API Base

FastReAct's `LiteLLMProvider` already handles custom endpoints:

```python
# From src/fastreact/providers/litellm.py
class LiteLLMProvider:
    def __init__(self, model=None, api_base=None, api_key=None, ...):
        self._use_openai_client = api_base is not None

        if self._use_openai_client:
            # Auto-switch to OpenAI client for custom endpoints
            from openai import AsyncOpenAI
            self._openai_client = AsyncOpenAI(
                api_key=api_key,
                base_url=api_base,
                http_client=self._http_client,
            )
```

**Supported Providers** (via LiteLLM):
- OpenAI, Anthropic, DeepSeek, Azure
- Google, Cohere, HuggingFace
- Custom OpenAI-compatible APIs (Ollama, vLLM, local models)

**Pros**:
- **Zero code required** for 100+ providers (LiteLLM)
- **Environment variable driven** - no config file edits
- **Custom endpoint support** built-in
- **Auto-detection** - provider detected from model name
- **OpenAI client fallback** - for custom APIs

**Cons**:
- Limited to LiteLLM's provider list (though it's extensive)
- No provider registry for custom logic
- Less fine-grained control than Nanobot

---

### Nanobot

**Difficulty**: 2/10 (Easiest)

**Files to Edit**: 1 file
**Lines of Code**: ~10-20 lines
**Steps**: 1 step

#### Step-by-Step Guide

Nanobot has a **Provider Registry** system that makes adding providers trivial:

**Step 1: Add provider to registry** (edit 1 file)

```python
# nanobot/providers/registry.py

PROVIDERS: tuple[ProviderSpec, ...] = (
    # ... existing providers ...

    # === My New Provider =====================================
    ProviderSpec(
        name="my_provider",
        keywords=("myprovider", "my-model"),
        env_key="MY_PROVIDER_API_KEY",
        display_name="My Provider",
        litellm_prefix="myprovider",          # my-model → myprovider/my-model
        skip_prefixes=("myprovider/",),
        env_extras=(),
        is_gateway=False,
        is_local=False,
        detect_by_key_prefix="sk-mp-",        # Detect by API key prefix
        detect_by_base_keyword="myprovider",  # Or detect by API base URL
        default_api_base="https://api.myprovider.com/v1",
        strip_model_prefix=False,
        model_overrides=(
            # Per-model parameter overrides
            ("my-model-v2", {"temperature": 1.0}),
        ),
    ),
)
```

**That's it!** The provider is now available.

**Usage**:
```python
# Set environment variable
export MY_PROVIDER_API_KEY="sk-mp-xxx"

# Use in config
config = Config(
    providers=ProvidersConfig(
        my_provider=MyProviderConfig(
            api_key="sk-mp-xxx",
            default_model="my-model-v1"
        )
    )
)

# Or just specify the model name
# Nanobot auto-detects provider from model name
agent.run(query="Hello", model="myprovider/my-model-v1")
```

#### Real Example: Adding DeepSeek Provider

```python
# nanobot/providers/registry.py (actual code)

ProviderSpec(
    name="deepseek",
    keywords=("deepseek",),
    env_key="DEEPSEEK_API_KEY",
    display_name="DeepSeek",
    litellm_prefix="deepseek",
    skip_prefixes=("deepseek/",),
    is_gateway=False,
),
```

**Features**:
- **Auto-detection**: Model name "deepseek/deepseek-coder" → uses DeepSeek provider
- **Auto-prefixing**: Model "deepseek-coder" → becomes "deepseek/deepseek-coder"
- **Auto-env-setup**: Sets `DEEPSEEK_API_KEY` automatically
- **Custom API base**: Supports custom endpoints
- **Model overrides**: Per-model parameter tuning

**Advanced: Gateway Provider** (for OpenRouter, etc.)

```python
ProviderSpec(
    name="my_gateway",
    keywords=("mygateway",),
    env_key="MY_GATEWAY_API_KEY",
    display_name="My Gateway",
    litellm_prefix="mygateway",
    is_gateway=True,                      # ← Can route ANY model
    detect_by_key_prefix="sk-mg-",        # Detect by key prefix
    detect_by_base_keyword="gateway",     # Or by API base
    default_api_base="https://gateway.my.com/v1",
    strip_model_prefix=True,              # Strip provider prefix before re-prefixing
),
```

**Pros**:
- **Single file edit** - just add to registry tuple
- **Zero code** - declarative configuration
- **Auto-everything** - detection, prefixing, env setup
- **Gateway support** - for multi-provider gateways
- **Model overrides** - per-model parameter tuning
- **Documentation built-in** - spec fields explain everything

**Cons**:
- Requires understanding ProviderSpec fields
- Must edit core file (but it's well-structured)

**Why Nanobot Wins**:
- **Single line addition** (copy-paste template)
- **Most comprehensive** - gateways, overrides, detection
- **Best documentation** - inline comments explain everything
- **Zero code required** - pure configuration

---

### OpenClaw

**Difficulty**: 5/10 (Moderate)

**Files to Edit**: 2-4 files
**Lines of Code**: ~50-200 lines
**Steps**: 3-5 steps

OpenClaw supports multiple LLM providers through its configuration system and provider usage tracking.

#### Step-by-Step Guide

**1. Add provider configuration** (edit `src/config/types.ts`)

```typescript
// src/config/types.ts
export interface ProviderConfig {
  // ... existing providers ...

  myProvider?: {
    baseUrl: string;
    apiKey: string;
    models: {
      [key: string]: ModelConfig;
    };
  };
}
```

**2. Add Zod validation schema** (edit `src/config/zod-schema.ts`)

```typescript
// src/config/zod-schema.ts
export const myProviderConfigSchema = z.object({
  baseUrl: z.string().url(),
  apiKey: z.string().default(""),
  models: z.record(z.object({
    primary: z.string(),
    fallbacks: z.array(z.string()).optional(),
  })).optional(),
});
```

**3. Add provider usage fetcher** (create `src/infra/provider-usage.fetch.myprovider.ts`)

```typescript
// src/infra/provider-usage.fetch.myprovider.ts
export async function fetchMyProviderUsage(
  apiKey: string
): Promise<ProviderUsage> {
  const response = await fetch('https://api.myprovider.com/v1/usage', {
    headers: { 'Authorization': `Bearer ${apiKey}` }
  });
  return await response.json();
}
```

**4. Register in provider usage loader** (edit `src/infra/provider-usage.load.ts`)

```typescript
// src/infra/provider-usage.load.ts
import { fetchMyProviderUsage } from './provider-usage.fetch.myprovider';

export async function loadProviderUsage(config: Config): Promise<ProviderUsage[]> {
  const usages: ProviderUsage[] = [];

  // ... existing providers ...

  if (config.providers?.myProvider?.apiKey) {
    usages.push(await fetchMyProviderUsage(config.providers.myProvider.apiKey));
  }

  return usages;
}
```

**5. Add to model config schema** (edit `src/config/types.models.ts`)

```typescript
export const MODEL_ALIASES: Record<string, string> = {
  // ... existing aliases ...

  'MyProvider': 'myprovider/my-model-v1',
};
```

#### Real Example: OpenAI Provider Setup

OpenClaw has extensive provider configuration:

```typescript
// From src/config/types.ts (simplified)
interface OpenAIProviderConfig {
  baseUrl?: string;
  apiKey?: string;
  organizationId?: string;
  models?: {
    'gpt-4'?: ModelConfig;
    'gpt-3.5-turbo'?: ModelConfig;
  };
}

// From src/infra/provider-usage.fetch.ts
export async function fetchOpenAIUsage(apiKey: string): Promise<ProviderUsage> {
  const response = await fetch('https://api.openai.com/v1/usage', {
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
  });
  // ... usage tracking logic
}
```

**Supported Providers** (from config):
- OpenAI (`openai`)
- Anthropic (`anthropic`)
- Azure OpenAI (`azure`)
- MiniMax (`minimax`)
- OpenAI Codex (`openai_codex` - OAuth-based)
- Custom providers via generic configuration

**Pros**:
- **Type-safe** - TypeScript + Zod validation
- **Usage tracking** - built-in cost monitoring
- **Model aliases** - convenient shortcuts
- **Fallback models** - automatic failover
- **Enterprise features** - org IDs, rate limits

**Cons**:
- **Multiple files** - config, schema, fetchers, loaders
- **TypeScript required** - no Python interface
- **Manual wiring** - must connect all pieces
- **More verbose** - ~200 lines vs Nanobot's ~10 lines
- **Less declarative** - more code than configuration

**Why OpenClaw Scores Middle**:
- More complex than FastReAct/Nanobot (3-5 files vs 0-1)
- TypeScript requirement
- But still manageable with good patterns
- Usage tracking is unique feature

---

### LLM Provider Extensibility Comparison Table

| Metric | FastReAct | Nanobot | OpenClaw |
|--------|-----------|---------|----------|
| **Files to Create** | 0-1 | 0 | 1-2 |
| **Files to Edit** | 0 | 1 | 2-4 |
| **Lines of Code** | 0-50 | 10-20 | 50-200 |
| **Steps Required** | 1-2 | 1 | 3-5 |
| **Language** | Python | Python | TypeScript |
| **Provider Support** | 100+ (via LiteLLM) | 50+ (via registry) | 5+ (manual) |
| **Auto-detection** | Yes (LiteLLM) | Yes (registry) | Partial |
| **Custom Endpoints** | Built-in | Built-in | Manual |
| **Usage Tracking** | No | No | Yes 🥇 |
| **Gateway Support** | Yes | Yes | No |
| **Model Overrides** | No | Yes 🥇 | Partial |
| **Declarative Config** | Yes | Yes 🥇 | Partial |
| **Difficulty (1-10)** | **3** | **2** 🥇 | **5** |
| **Best For** | Quick integration, standard providers | Custom providers, gateways | Enterprise, usage tracking |

**Winner**: 🥇 **Nanobot** (single file, declarative, most features)

---

## Code Examples: Minimal Tool Implementation

### FastReAct - Simple Echo Tool

```python
# src/fastreact/tools/echo.py
from fastreact.core.tools import Tool

class EchoTool(Tool):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echo back the input text"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to echo"}
            },
            "required": ["text"]
        }

    async def execute(self, text: str) -> str:
        return f"[ECHO] {text}"

# Register in agent.py
# self._tools.register(EchoTool())
```

**Lines of Code**: 23 lines
**Files**: 1 new, 1 edit

---

### Nanobot - Simple Echo Tool

```python
# nanobot/agent/tools/echo.py
from nanobot.agent.tools.base import Tool

class EchoTool(Tool):
    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echo back the input text"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "required": ["text"]
        }

    async def execute(self, text: str, **kwargs) -> str:
        return f"[ECHO] {text}"

# Register externally
# tool_registry.register(EchoTool())
```

**Lines of Code**: 24 lines
**Files**: 1 new, 0 edits

**Advantage**: No core file editing required

---

### OpenClaw - Echo "Skill"

```yaml
---
name: echo
description: Echo back input text. Use when you need to repeat or mirror user input.
---

# Echo Skill

## Quick Start

Use this skill to echo text back to the user.

## Usage

When the user asks to echo text, simply repeat it back verbatim.

Example:
- User: "Echo 'hello world'"
- Response: "hello world"
```

```bash
# Directory structure
skills/echo/
├── SKILL.md  (above)
└── scripts/
    └── echo.py  (optional)

# scripts/echo.py
#!/usr/bin/env python3
import sys

def main():
    print(sys.argv[1])

if __name__ == "__main__":
    main()
```

**Lines of Code**: ~30 lines (YAML + Python)
**Files**: 2 new, 0 edits

**Advantage**: No registration needed (auto-discovery)
**Disadvantage**: Must write documentation even for simple tools

---

## Difficulty Scoring Summary

### Tool Extensibility

| Project | Score | Rationale |
|---------|-------|-----------|
| **Nanobot** 🥇 | **2/10** | Simplest interface (3 props + 1 method), no core edits, external registration |
| **FastReAct** | **3/10** | Same interface as Nanobot, but requires editing agent.py for registration |
| **OpenClaw** | **7/10** | Skills are powerful but complex - must write YAML + Markdown + scripts, 6+ steps |

### Channel/Adapter Extensibility

| Project | Score | Rationale |
|---------|-------|-----------|
| **Nanobot** 🥇 | **3/10** | Clear base class (3 methods), manager auto-discovery, built-in permissions |
| **FastReAct** | **6/10** | No base class (flexible but requires more code), manual event handling |
| **OpenClaw** | **8/10** | TypeScript required, multiple integration points, 8+ steps, heavy boilerplate |

### LLM Provider Extensibility

| Project | Score | Rationale |
|---------|-------|-----------|
| **Nanobot** 🥇 | **2/10** | Single line in registry, zero code, most comprehensive (gateways, overrides, detection) |
| **FastReAct** | **3/10** | Zero code for 100+ providers (LiteLLM), custom endpoints supported |
| **OpenClaw** | **5/10** | Multiple files, TypeScript required, but manageable with good patterns |

---

## Overall Extensibility Ranking

### 🥇 First Place: Nanobot (2.3/10 average)

**Strengths**:
- **Cleanest interfaces** - simple, consistent patterns
- **Least code required** - declarative where possible
- **Best documentation** - inline comments explain everything
- **Most flexible** - external registration, no core edits
- **Provider registry** - single-line provider additions

**Weaknesses**:
- Less feature-rich than competitors
- Fewer built-in examples

**Best For**:
- Developers who want simplicity
- Quick prototyping
- Custom integrations

---

### 🥈 Second Place: FastReAct (4.0/10 average)

**Strengths**:
- **LiteLLM integration** - 100+ providers out of the box
- **Event-driven architecture** - clean separation of concerns
- **No base classes** - maximum flexibility for adapters
- **Good documentation** - clear examples

**Weaknesses**:
- Requires core file editing for tools
- No base class guidance for adapters (more boilerplate)
- Less provider control than Nanobot

**Best For**:
- Projects using diverse LLM providers
- Custom adapter integrations
- Event-driven architectures

---

### 🥉 Third Place: OpenClaw (6.7/10 average)

**Strengths**:
- **Most powerful** - skills can include scripts, references, assets
- **Type-safe** - TypeScript + Zod validation
- **Enterprise features** - usage tracking, model aliases, fallbacks
- **Professional** - npm ecosystem, semantic versioning
- **Progressive disclosure** - efficient context management

**Weaknesses**:
- **Steepest learning curve** - complex patterns
- **TypeScript required** - excludes Python developers
- **Most verbose** - 5-10 files for simple additions
- **Over-engineered** for simple use cases

**Best For**:
- Enterprise deployments
- Complex multi-step workflows
- Projects requiring usage tracking
- Teams comfortable with TypeScript

---

## Winner by Category

| Category | Winner | Why |
|----------|--------|-----|
| **Tool Extensibility** | 🥇 Nanobot | Simplest interface, no core edits, external registration |
| **Channel Extensibility** | 🥇 Nanobot | Clear base class, auto-discovery, built-in permissions |
| **LLM Provider Extensibility** | 🥇 Nanobot | Single-line config, zero code, most comprehensive |
| **Overall** | 🥇 **Nanobot** | Consistently simplest across all scenarios |

---

## Recommendations

### Choose Nanobot if you want:
- ✅ **Fastest development** - add features in minutes
- ✅ **Simplest patterns** - learn once, apply everywhere
- ✅ **Flexibility** - external registration, no core edits
- ✅ **Python-only** - no TypeScript required

### Choose FastReAct if you want:
- ✅ **Provider diversity** - 100+ LLM providers via LiteLLM
- ✅ **Event-driven** - clean architecture for complex apps
- ✅ **Adapter flexibility** - no base class constraints
- ✅ **Production-ready** - safety policies, context monitoring

### Choose OpenClaw if you want:
- ✅ **Enterprise features** - usage tracking, cost monitoring
- ✅ **Complex workflows** - multi-step skills with bundled resources
- ✅ **Type safety** - TypeScript + Zod validation
- ✅ **Professional deployment** - npm packages, versioning

---

## Conclusion

**Nanobot wins overall extensibility** with the simplest, most consistent patterns across all three scenarios. Its clean interfaces and declarative configuration make adding new functionality trivial.

**FastReAct takes second place** with good extensibility powered by LiteLLM and event-driven architecture. It's more flexible than Nanobot but requires more code.

**OpenClaw takes third place** due to its complexity, but it's important to note that this complexity buys significant power. For enterprise deployments requiring usage tracking, cost monitoring, and complex workflow orchestration, OpenClaw's extensibility model may be worth the additional effort.

The right choice depends on your priorities:
- **Speed & simplicity** → Nanobot
- **Flexibility & events** → FastReAct
- **Enterprise features** → OpenClaw

---

**Analysis Methodology**:
- Examined actual code from all three projects
- Counted files, lines of code, and steps required
- Tested extensibility claims against real implementations
- Considered both initial complexity and maintenance burden

**Files Analyzed**:
- FastReAct: `/Users/xudawei/FastReAct/fastreact-nano/src/fastreact/{tools,adapters,providers}`
- Nanobot: `/Users/xudawei/nanobot/nanobot/{agent/tools,channels,providers}`
- OpenClaw: `/Users/xudawei/openclaw/{skills,extensions,src/config,src/infra}`
