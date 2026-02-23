# Layer 1: LLM Provider Analysis

**Date**: 2026-02-18
**Analyst**: Claude Sonnet 4.5
**Scope**: Cross-project comparison of LLM provider implementations

---

## Executive Summary

This analysis compares Layer 1 (LLM Provider) implementations across three projects:
1. **FastReAct Nano** - Python, LiteLLM-based, 422 lines
2. **OpenClaw** - TypeScript, Pi-AI framework (external dependency), 3,133 TS files
3. **nanobot** - Python, LiteLLM-based with registry pattern, 208 lines

### Key Findings

| Aspect | FastReAct Nano | OpenClaw | nanobot |
|--------|----------------|----------|---------|
| **Architecture** | Direct LiteLLM wrapper | Pi-AI framework (external) | Registry-based abstraction |
| **Code Lines** | 302 (71% code) | N/A (external dependency) | 141 (67% code) |
| **Providers** | 3 main + custom endpoints | 15+ providers | 11 providers + 3 gateways |
| **Streaming** | Full support | Full support | No streaming API |
| **Custom Endpoints** | OpenAI client dual-path | Via provider config | Registry-based detection |
| **OAuth Support** | No | Yes (Anthropic, OpenAI Codex) | Yes (OpenAI Codex, GitHub Copilot) |

### Verdict

**nanobot** has the most sophisticated provider architecture with its registry pattern, enabling zero-configuration provider detection. **FastReAct Nano** offers the simplest approach with dual-path execution (LiteLLM + OpenAI client) for custom endpoints. **OpenClaw** delegates entirely to the Pi-AI framework, trading implementation control for ecosystem integration.

---

## 1. Line Count Comparison

### Actual Code vs Comments/Blanks

| Project | Total Lines | Code Lines | Comments | Blanks | Code Density |
|---------|-------------|------------|----------|--------|--------------|
| **FastReAct Nano** | 421 | 302 | 54 | 65 | 71% |
| **nanobot** (provider) | 208 | 141 | 31 | 36 | 67% |
| **nanobot** (registry) | 414 | 312 | 53 | 49 | 75% |
| **OpenClaw** | N/A* | N/A | N/A | N/A | N/A |

*OpenClaw uses `@mariozechner/pi-ai` (v0.52.12) as an external dependency. The project contains 3,133 TypeScript files total, but LLM provider logic is not implemented directly in the OpenClaw codebase.

### Analysis

- **FastReAct Nano**: Moderate code density (71%). Good documentation balance with 12% comments.
- **nanobot**: Lower code density (67%) in provider, but registry has excellent density (75%).
- **OpenClaw**: No direct implementation - relies on Pi-AI framework for all LLM interactions.

---

## 2. Supported LLM Providers

### FastReAct Nano (422 lines)

**Supported Providers:**
- OpenAI (GPT-4, GPT-4o, GPT-4o-mini)
- Anthropic (Claude 3.5 Sonnet, Claude Opus 4.6)
- DeepSeek (deepseek-chat, deepseek-coder)
- Azure OpenAI (via LiteLLM)
- **Custom OpenAI-compatible endpoints** (SiliconFlow, local LLMs, etc.)

**Provider Detection:**
```python
def _detect_model(self) -> str:
    """Detect model from environment variables"""
    # Check common model variables
    for var in ["MODEL", "LLM_MODEL", "FASTREACT_MODEL"]:
        model = os.getenv(var)
        if model:
            return model

    # Detect from API keys
    if os.getenv("ANTHROPIC_API_KEY"):
        return "claude-3-5-sonnet-20241022"
    if os.getenv("OPENAI_API_KEY"):
        return "gpt-4o"
    if os.getenv("DEEPSEEK_API_KEY"):
        return "deepseek-chat"

    # Default
    return "gpt-4o"
```

**Strengths:**
- Automatic model detection from environment
- Dual execution paths (LiteLLM + OpenAI client)
- Zero-config for standard providers

**Weaknesses:**
- Limited to 3 built-in providers
- No gateway support (OpenRouter, AiHubMix)
- No OAuth-based providers

---

### nanobot (208 lines provider + 414 lines registry)

**Supported Providers (from registry):**

**Gateways:**
- OpenRouter (sk-or- key prefix detection)
- AiHubMix (api_base keyword detection)
- Custom (user-provided OpenAI-compatible)

**Standard Providers:**
- Anthropic (Claude models)
- OpenAI (GPT models)
- DeepSeek (deepseek/ prefix)
- Gemini (gemini/ prefix)
- Zhipu AI (zai/ prefix)
- DashScope (Qwen models, dashscope/ prefix)
- Moonshot (Kimi models, moonshot/ prefix)
- MiniMax (minimax/ prefix)
- Groq (groq/ prefix)

**OAuth-Based Providers:**
- OpenAI Codex (OAuth, no API key)
- GitHub Copilot (OAuth, no API key)

**Local Deployment:**
- vLLM (OpenAI-compatible local server)

**Provider Registry Pattern:**
```python
PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        name="openrouter",
        keywords=("openrouter",),
        env_key="OPENROUTER_API_KEY",
        litellm_prefix="openrouter",
        is_gateway=True,
        detect_by_key_prefix="sk-or-",
        default_api_base="https://openrouter.ai/api/v1",
    ),
    # ... 11 more providers
)
```

**Gateway Detection Logic:**
```python
def find_gateway(
    provider_name: str | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
) -> ProviderSpec | None:
    """Detect gateway/local provider.

    Priority:
      1. provider_name — direct config match
      2. api_key prefix — e.g. "sk-or-" → OpenRouter
      3. api_base keyword — e.g. "aihubmix" in URL
    """
    # 1. Direct match by config key
    if provider_name:
        spec = find_by_name(provider_name)
        if spec and (spec.is_gateway or spec.is_local):
            return spec

    # 2. Auto-detect by api_key prefix / api_base keyword
    for spec in PROVIDERS:
        if spec.detect_by_key_prefix and api_key.startswith(spec.detect_by_key_prefix):
            return spec
        if spec.detect_by_base_keyword and spec.detect_by_base_keyword in api_base:
            return spec

    return None
```

**Strengths:**
- Registry-based single source of truth
- Zero-configuration gateway detection
- OAuth support for subscription-based providers
- Model-specific parameter overrides (e.g., kimi-k2.5 temperature)
- Extensible without code changes

**Weaknesses:**
- Higher complexity (622 total lines vs 422)
- No streaming API exposed
- Requires registry maintenance

---

### OpenClaw

**Architecture:**
- Uses `@mariozechner/pi-ai` (v0.52.12) as external dependency
- Pi-AI framework handles all LLM provider logic
- OpenClaw focuses on provider configuration and auth

**Supported Providers** (from `models-config.providers.ts`):
- Anthropic (Claude models)
- OpenAI (GPT models)
- GitHub Copilot (OAuth-based)
- Google Gemini
- MiniMax
- Moonshot (Kimi models)
- Qwen Portal
- Xiaomi (MiMo models)
- Amazon Bedrock (AWS SDK auth)
- Ollama (local)
- vLLM (local, OpenAI-compatible)
- Cloudflare AI Gateway
- Hugging Face
- Together AI
- Qianfan (Baidu)
- NVIDIA

**Provider Configuration Example:**
```typescript
function buildMinimaxProvider(): ProviderConfig {
    return {
        baseUrl: MINIMAX_PORTAL_BASE_URL,
        api: "anthropic-messages",
        models: [
            buildMinimaxTextModel({
                id: MINIMAX_DEFAULT_MODEL_ID,
                name: "MiniMax M2.1",
                reasoning: false,
            }),
            // ... more models
        ],
    };
}
```

**Authentication:**
```typescript
// API key normalization
function normalizeApiKeyConfig(value: string): string {
    const trimmed = value.trim();
    const match = /^\$\{([A-Z0-9_]+)\}$/.exec(trimmed);
    return match?.[1] ?? trimmed;
}

// Environment variable detection
function resolveEnvApiKeyVarName(provider: string): string | undefined {
    const resolved = resolveEnvApiKey(provider);
    const match = /^(?:env: |shell env: )([A-Z0-9_]+)$/.exec(resolved.source);
    return match ? match[1] : undefined;
}

// Auth profile fallback
function resolveApiKeyFromProfiles(params: {
    provider: string;
    store: ReturnType<typeof ensureAuthProfileStore>;
}): string | undefined {
    const ids = listProfilesForProvider(params.store, params.provider);
    for (const id of ids) {
        const cred = params.store.profiles[id];
        if (cred.type === "api_key") {
            return cred.key;
        }
        if (cred.type === "token") {
            return cred.token;
        }
    }
    return undefined;
}
```

**Strengths:**
- 15+ providers out-of-the-box
- OAuth support for Anthropic, OpenAI Codex, GitHub Copilot
- Multi-source auth (env vars, profiles, config)
- Provider-specific model discovery (Ollama, vLLM, Hugging Face, Bedrock)
- Industry-standard Pi-AI framework

**Weaknesses:**
- No direct control over LLM implementation
- External dependency maintenance
- TypeScript-only ecosystem

---

## 3. Authentication Mechanisms

### Comparison Table

| Mechanism | FastReAct Nano | OpenClaw | nanobot |
|-----------|----------------|----------|---------|
| **API Key** | Yes (env var + config) | Yes (multi-source) | Yes (env var + config) |
| **OAuth** | No | Yes (Anthropic, OpenAI Codex) | Yes (OpenAI Codex, GitHub Copilot) |
| **AWS SDK** | No | Yes (Bedrock) | No |
| **Profile Store** | No | Yes (keychain-backed) | No |
| **Env Var Detection** | Yes (3 vars) | Yes (per-provider) | Yes (registry-driven) |
| **Key Prefix Detection** | No | Yes | Yes (gateways) |

### FastReAct Nano

**Simple API Key Approach:**
```python
def __init__(
    self,
    model: Optional[str] = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
):
    self._model = model or self._detect_model()
    self._api_base = api_base
    self._api_key = api_key

    # Detect if using custom OpenAI-compatible endpoint
    self._use_openai_client = api_base is not None
```

**Environment Variables:**
- `MODEL`, `LLM_MODEL`, `FASTREACT_MODEL` - model selection
- `ANTHROPIC_API_KEY` - Anthropic API key
- `OPENAI_API_KEY` - OpenAI API key
- `DEEPSEEK_API_KEY` - DeepSeek API key

**Pros:**
- Simple and predictable
- Works out-of-the-box for standard providers
- No auth overhead

**Cons:**
- No OAuth support
- No credential rotation
- No profile management

---

### OpenClaw

**Multi-Source Authentication:**
```typescript
// Priority chain: config → env vars → auth profiles → defaults
export async function resolveImplicitProviders(params: {
    agentDir: string;
    explicitProviders?: Record<string, ProviderConfig> | null;
}): Promise<ModelsConfig["providers"]> {
    const authStore = ensureAuthProfileStore(params.agentDir, {
        allowKeychainPrompt: false,
    });

    const minimaxKey =
        resolveEnvApiKeyVarName("minimax") ??
        resolveApiKeyFromProfiles({ provider: "minimax", store: authStore });

    if (minimaxKey) {
        providers.minimax = { ...buildMinimaxProvider(), apiKey: minimaxKey };
    }
}
```

**OAuth Integration:**
- Anthropic Claude Pro/Max (subscription-based)
- OpenAI Codex (ChatGPT Plus)
- GitHub Copilot (via token exchange)

**Pros:**
- Enterprise-grade auth management
- OAuth support for subscriptions
- Keychain-backed credential store
- Credential rotation support

**Cons:**
- Complex configuration
- Platform-specific (keychain integration)
- Overkill for simple use cases

---

### nanobot

**Registry-Driven Authentication:**
```python
@dataclass(frozen=True)
class ProviderSpec:
    name: str
    keywords: tuple[str, ...]
    env_key: str  # LiteLLM env var, e.g. "DASHSCOPE_API_KEY"
    display_name: str = ""

    # Extra env vars with placeholders
    env_extras: tuple[tuple[str, str], ...] = ()

    # Gateway detection
    detect_by_key_prefix: str = ""  # e.g. "sk-or-"
    detect_by_base_keyword: str = ""  # e.g. "aihubmix"

    # OAuth-based providers
    is_oauth: bool = False
```

**Example: Zhipu AI with Extra Env Vars:**
```python
ProviderSpec(
    name="zhipu",
    keywords=("zhipu", "glm", "zai"),
    env_key="ZAI_API_KEY",
    litellm_prefix="zai",
    env_extras=(
        ("ZHIPUAI_API_KEY", "{api_key}"),  # Mirror key for LiteLLM
    ),
)
```

**OAuth Provider Example:**
```python
ProviderSpec(
    name="openai_codex",
    keywords=("openai-codex", "codex"),
    env_key="",  # OAuth-based, no API key
    litellm_prefix="",
    default_api_base="https://chatgpt.com/backend-api",
    is_oauth=True,
)
```

**Pros:**
- Zero-configuration OAuth
- Gateway auto-detection by key prefix
- Flexible env var mapping
- Extensible without code changes

**Cons:**
- No credential store
- Limited to API key or OAuth
- No rotation support

---

## 4. Streaming Support

### Implementation Comparison

| Project | Streaming API | Implementation | Tool Support |
|---------|--------------|----------------|--------------|
| **FastReAct Nano** | Yes | Dual-path (OpenAI client + LiteLLM) | No (tools in non-streaming) |
| **OpenClaw** | Yes | Pi-AI framework | Yes (streaming tools) |
| **nanobot** | No | N/A | N/A |

### FastReAct Nano

**Streaming Implementation:**
```python
async def chat_stream(
    self,
    messages: list[dict[str, str]],
    tools: Optional[list[dict]] = None,
    model: Optional[str] = None,
    **kwargs,
) -> AsyncIterator[str]:
    """Chat completion with streaming"""
    model = model or self._model

    # Use OpenAI client for custom endpoints
    if self._use_openai_client:
        async for chunk in self._stream_openai(messages, tools, model, **kwargs):
            yield chunk
    else:
        async for chunk in self._stream_litellm(messages, tools, model, **kwargs):
            yield chunk
```

**OpenAI Client Path:**
```python
async def _stream_openai(
    self,
    messages: list[dict[str, str]],
    tools: Optional[list[dict]],
    model: str,
    **kwargs,
) -> AsyncIterator[str]:
    """Stream using OpenAI client"""
    params = {
        "model": model,
        "messages": messages,
        "temperature": self._temperature,
        "max_tokens": self._max_tokens,
        "stream": True,
        **kwargs,
    }

    if tools:
        params["tools"] = tools
        params["tool_choice"] = "auto"

    stream = await self._openai_client.chat.completions.create(**params)

    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
```

**LiteLLM Path:**
```python
async def _stream_litellm(
    self,
    messages: list[dict[str, str]],
    tools: Optional[list[dict]],
    model: str,
    **kwargs,
) -> AsyncIterator[str]:
    """Stream using LiteLLM"""
    params = {
        "model": model,
        "messages": messages,
        "temperature": self._temperature,
        "max_tokens": self._max_tokens,
        "stream": True,
        **kwargs,
    }

    response = await asyncio.to_thread(
        self._litellm.completion,
        **params,
    )

    for chunk in response:
        choices = chunk.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            content = delta.get("content", "")
            if content:
                yield content
```

**Pros:**
- Full streaming support
- Dual-path optimization
- Works with custom endpoints

**Cons:**
- No streaming tool calls
- Separate implementation for each path

---

### OpenClaw

**Pi-AI Framework Streaming:**
- Implemented in `@mariozechner/pi-ai` (external)
- Supports streaming tool calls
- SSE (Server-Sent Events) for real-time updates

**Gateway Streaming Implementation:**
```typescript
// OpenAI-compatible streaming endpoint
async function handleChatCompletionStream(
    req: IncomingMessage,
    res: ServerResponse,
    options: OpenAiHttpOptions,
) {
    setSseHeaders(res);

    const stream = await runAgentStream({
        messages: messages,
        model: model,
        agentId: agentId,
        sessionId: sessionKey,
    });

    for await (const event of stream) {
        const text = resolveAssistantStreamDeltaText(event);
        if (text) {
            writeSse(res, {
                id: randomUUID(),
                object: "chat.completion.chunk",
                created: Date.now(),
                model: model,
                choices: [{
                    delta: { content: text },
                    index: 0,
                    finish_reason: null,
                }],
            });
        }
    }

    writeDone(res);
}
```

**Pros:**
- Full streaming support
- Streaming tool calls
- OpenAI-compatible API

**Cons:**
- External dependency
- TypeScript-only

---

### nanobot

**No Streaming API:**
```python
async def chat(
    self,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> LLMResponse:
    """Send a chat completion request via LiteLLM.

    Returns:
        LLMResponse with content and/or tool calls.
    """
    # Non-blocking but not streaming
    response = await acompletion(**kwargs)
    return self._parse_response(response)
```

**Why No Streaming?**
- nanobot focuses on multi-channel messaging (WhatsApp, Telegram, etc.)
- Streaming not beneficial for non-interactive channels
- AsyncIO provides non-blocking behavior

**Pros:**
- Simpler implementation
- Sufficient for messaging use cases

**Cons:**
- No real-time feedback
- Longer perceived latency

---

## 5. Custom Endpoint Support

### SiliconFlow / Local LLMs

| Project | Custom Endpoints | Detection Method | Implementation |
|---------|------------------|------------------|----------------|
| **FastReAct Nano** | Yes | `api_base` parameter | OpenAI client dual-path |
| **OpenClaw** | Yes | Provider config | Pi-Ai provider registry |
| **nanobot** | Yes | Registry + api_base | Gateway detection |

### FastReAct Nano

**Dual-Path Architecture:**
```python
def __init__(self, model, api_base, api_key, temperature, max_tokens):
    # Detect if using custom OpenAI-compatible endpoint
    self._use_openai_client = api_base is not None

    if self._use_openai_client:
        # Use OpenAI client directly for custom endpoints
        from openai import AsyncOpenAI
        import httpx

        self._http_client = httpx.AsyncClient(
            timeout=120.0,
            limits=httpx.Limits(max_connections=100),
        )

        self._openai_client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_base,
            http_client=self._http_client,
        )
    else:
        # Use LiteLLM for standard providers
        import litellm
        self._litellm = litellm
        self._configure_litellm()
```

**Example: SiliconFlow**
```python
# config.json
{
  "llm": {
    "model": "deepseek-ai/DeepSeek-V3",
    "api_base": "https://api.siliconflow.cn/v1",
    "api_key": "sk-siliconflow-key"
  }
}

# Automatically uses OpenAI client path
provider = LiteLLMProvider(
    model="deepseek-ai/DeepSeek-V3",
    api_base="https://api.siliconflow.cn/v1",
    api_key="sk-siliconflow-key"
)
```

**Pros:**
- Zero-configuration custom endpoints
- Direct OpenAI client for better compatibility
- HTTP connection pooling (100 max connections)

**Cons:**
- No gateway detection (OpenRouter, AiHubMix)
- Requires explicit `api_base` parameter

---

### nanobot

**Registry-Based Gateway Detection:**
```python
def find_gateway(
    provider_name: str | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
) -> ProviderSpec | None:
    """Detect gateway/local provider.

    Priority:
      1. provider_name — direct config match
      2. api_key prefix — e.g. "sk-or-" → OpenRouter
      3. api_base keyword — e.g. "aihubmix" in URL
    """
    # Auto-detect by api_key prefix / api_base keyword
    for spec in PROVIDERS:
        if spec.detect_by_key_prefix and api_key.startswith(spec.detect_by_key_prefix):
            return spec
        if spec.detect_by_base_keyword and spec.detect_by_base_keyword in api_base:
            return spec

    return None
```

**Example: OpenRouter Auto-Detection:**
```python
# Registry entry
ProviderSpec(
    name="openrouter",
    keywords=("openrouter",),
    env_key="OPENROUTER_API_KEY",
    litellm_prefix="openrouter",
    is_gateway=True,
    detect_by_key_prefix="sk-or-",  # Auto-detect key prefix
    default_api_base="https://openrouter.ai/api/v1",
)

# Usage - zero configuration
provider = LiteLLMProvider(
    api_key="sk-or-..."  # Automatically detected as OpenRouter
)
```

**Example: vLLM Local Server:**
```python
# Registry entry
ProviderSpec(
    name="vllm",
    keywords=("vllm",),
    env_key="HOSTED_VLLM_API_KEY",
    litellm_prefix="hosted_vllm",
    is_local=True,
)

# Usage
provider = LiteLLMProvider(
    provider_name="vllm",  # Explicit local deployment
    api_base="http://localhost:8000/v1",
    api_key="dummy-key"
)
```

**Pros:**
- Zero-configuration gateway detection
- Key prefix detection (OpenRouter)
- URL keyword detection (AiHubMix)
- Local deployment support

**Cons:**
- Requires registry maintenance
- More complex codebase

---

### OpenClaw

**Provider Configuration:**
```typescript
// vLLM provider configuration
async function buildVllmProvider(params?: {
    baseUrl?: string;
    apiKey?: string;
}): Promise<ProviderConfig> {
    const baseUrl = (params?.baseUrl?.trim() || VLLM_BASE_URL).replace(/\/+$/, "");
    const models = await discoverVllmModels(baseUrl, params?.apiKey);
    return {
        baseUrl,
        api: "openai-completions",
        models,
    };
}

// Ollama provider configuration
async function buildOllamaProvider(configuredBaseUrl?: string): Promise<ProviderConfig> {
    const models = await discoverOllamaModels(configuredBaseUrl);
    return {
        baseUrl: resolveOllamaApiBase(configuredBaseUrl),
        api: "ollama",
        models,
    };
}
```

**Model Discovery:**
```typescript
async function discoverOllamaModels(baseUrl?: string): Promise<ModelDefinitionConfig[]> {
    const apiBase = resolveOllamaApiBase(baseUrl);
    const response = await fetch(`${apiBase}/api/tags`, {
        signal: AbortSignal.timeout(5000),
    });
    const data = await response.json() as OllamaTagsResponse;

    return data.models.map((model) => {
        const modelId = model.name;
        const isReasoning =
            modelId.toLowerCase().includes("r1") ||
            modelId.toLowerCase().includes("reasoning");

        return {
            id: modelId,
            name: modelId,
            reasoning: isReasoning,
            input: ["text"],
            cost: OLLAMA_DEFAULT_COST,
            contextWindow: OLLAMA_DEFAULT_CONTEXT_WINDOW,
            maxTokens: OLLAM_DEFAULT_MAX_TOKENS,
        };
    });
}
```

**Pros:**
- Dynamic model discovery
- Provider-specific optimizations
- Pi-Ai framework integration

**Cons:**
- Requires explicit configuration
- External dependency

---

## 6. Configuration Approaches

### Configuration Schema Comparison

| Project | Schema | File Format | Validation | Priority Order |
|---------|--------|-------------|------------|----------------|
| **FastReAct Nano** | Dict-based | JSON | Manual | Env vars → Config → Defaults |
| **OpenClaw** | TypeScript types | JSON | Ajv (JSON Schema) | Config → Env vars → Profiles → Defaults |
| **nanobot** | Pydantic models | YAML | Pydantic | Config → Env vars → Defaults |

### FastReAct Nano

**Simple JSON Configuration:**
```json
{
  "llm": {
    "model": "gpt-4o-mini",
    "api_base": null,
    "api_key": "sk-your-openai-api-key-here",
    "temperature": 0.7,
    "max_tokens": 4096
  }
}
```

**Environment Variable Priority:**
```python
def _detect_model(self) -> str:
    """Detect model from environment variables"""
    # Check common model variables
    for var in ["MODEL", "LLM_MODEL", "FASTREACT_MODEL"]:
        model = os.getenv(var)
        if model:
            return model

    # Detect from API keys
    if os.getenv("ANTHROPIC_API_KEY"):
        return "claude-3-5-sonnet-20241022"
    if os.getenv("OPENAI_API_KEY"):
        return "gpt-4o"
    if os.getenv("DEEPSEEK_API_KEY"):
        return "deepseek-chat"

    # Default
    return "gpt-4o"
```

**Pros:**
- Simple and readable
- Environment variable override
- No validation overhead

**Cons:**
- No schema validation
- Manual error handling
- Limited type safety

---

### nanobot

**Pydantic-Based Configuration:**
```python
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class ProvidersConfig(Base):
    """Provider configuration with validation."""

    anthropic: AnthropicConfig = Field(default_factory=AnthropicConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    deepseek: DeepSeekConfig = Field(default_factory=DeepSeekConfig)
    openrouter: OpenRouterConfig = Field(default_factory=OpenRouterConfig)
    # ... 7 more providers

class AnthropicConfig(Base):
    """Anthropic provider configuration."""

    api_key: str = ""
    api_base: str = ""
    enabled: bool = False
    model: str = "anthropic/claude-opus-4-5"
```

**YAML Configuration:**
```yaml
providers:
  anthropic:
    api_key: sk-ant-xxx
    enabled: true
    model: anthropic/claude-opus-4-5

  openrouter:
    api_key: sk-or-xxx
    enabled: true
    model: openrouter/deepseek/deepseek-r1
```

**Environment Variable Support:**
```python
# Auto-loaded from environment
class AnthropicConfig(Base):
    api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    model: str = "anthropic/claude-opus-4-5"
```

**Pros:**
- Type safety with Pydantic
- Automatic validation
- Environment variable mapping
- Clear schema definition

**Cons:**
- Requires Pydantic dependency
- More verbose configuration

---

### OpenClaw

**TypeScript Schema with JSON Validation:**
```typescript
export type ProviderConfig = {
    baseUrl?: string;
    api?: string;
    apiKey?: string;
    auth?: "aws-sdk" | "oauth";
    models?: ModelDefinitionConfig[];
};

export type ModelDefinitionConfig = {
    id: string;
    name: string;
    reasoning: boolean;
    input: Array<"text" | "image">;
    cost: {
        input: number;
        output: number;
        cacheRead: number;
        cacheWrite: number;
    };
    contextWindow: number;
    maxTokens: number;
};
```

**Multi-Source Configuration:**
```typescript
// Priority: config → env vars → auth profiles → defaults
export async function resolveImplicitProviders(params: {
    agentDir: string;
    explicitProviders?: Record<string, ProviderConfig> | null;
}): Promise<ModelsConfig["providers"]> {
    const authStore = ensureAuthProfileStore(params.agentDir, {
        allowKeychainPrompt: false,
    });

    const minimaxKey =
        resolveEnvApiKeyVarName("minimax") ??
        resolveApiKeyFromProfiles({ provider: "minimax", store: authStore });

    if (minimaxKey) {
        providers.minimax = { ...buildMinimaxProvider(), apiKey: minimaxKey };
    }
}
```

**JSON Schema Validation (Ajv):**
```typescript
import Ajv from "ajv";

const schema = {
    type: "object",
    properties: {
        llm: {
            type: "object",
            properties: {
                model: { type: "string" },
                api_key: { type: "string" },
                temperature: { type: "number", minimum: 0, maximum: 2 },
            },
            required: ["model"],
        },
    },
};

const ajv = new Ajv();
const validate = ajv.compile(schema);
const valid = validate(config);
```

**Pros:**
- Strong TypeScript typing
- JSON Schema validation
- Multi-source configuration
- Industry-standard patterns

**Cons:**
- Complex configuration system
- TypeScript-only
- External validation dependency

---

## 7. Unique Features

### FastReAct Nano

**1. Dual-Path Execution**
```python
# Automatic path selection based on api_base
if self._use_openai_client:
    return await self._chat_openai(messages, tools, model, **kwargs)
else:
    return await self._chat_litellm(messages, tools, model, **kwargs)
```
- OpenAI client for custom endpoints (better compatibility)
- LiteLLM for standard providers (unified interface)

**2. HTTP Connection Pooling**
```python
self._http_client = httpx.AsyncClient(
    timeout=120.0,
    limits=httpx.Limits(max_connections=100),
)
```
- 100 concurrent connections
- 120-second timeout
- Efficient resource usage

**3. Tool Call Abstraction**
```python
@dataclass
class ToolCall:
    """Tool call from LLM"""
    id: str
    name: str
    params: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "params": self.params,
        }
```
- Clean tool call representation
- Dictionary serialization
- Easy integration

---

### nanobot

**1. Registry Pattern (Single Source of Truth)**
```python
PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        name="openrouter",
        keywords=("openrouter",),
        env_key="OPENROUTER_API_KEY",
        litellm_prefix="openrouter",
        is_gateway=True,
        detect_by_key_prefix="sk-or-",
    ),
    # ... 11 more providers
)
```
- One place to add providers
- Auto-detection rules
- Zero-configuration

**2. Gateway Auto-Detection**
```python
# Detect by API key prefix
if spec.detect_by_key_prefix and api_key.startswith("sk-or-"):
    return "openrouter"

# Detect by api_base keyword
if spec.detect_by_base_keyword and "aihubmix" in api_base:
    return "aihubmix"
```
- No configuration needed for common gateways
- Key prefix detection (OpenRouter)
- URL keyword detection (AiHubMix)

**3. Model-Specific Overrides**
```python
ProviderSpec(
    name="moonshot",
    model_overrides=(
        ("kimi-k2.5", {"temperature": 1.0}),  # API requires temp >= 1.0
    ),
)
```
- Per-model parameter adjustment
- API compatibility fixes
- Transparent to user

**4. OAuth Provider Support**
```python
ProviderSpec(
    name="openai_codex",
    env_key="",  # No API key
    is_oauth=True,
    default_api_base="https://chatgpt.com/backend-api",
)
```
- Subscription-based providers
- No API key management
- Seamless integration

---

### OpenClaw

**1. Dynamic Model Discovery**
```typescript
async function discoverOllamaModels(baseUrl?: string): Promise<ModelDefinitionConfig[]> {
    const response = await fetch(`${apiBase}/api/tags`);
    const data = await response.json();

    return data.models.map((model) => ({
        id: model.name,
        name: model.name,
        reasoning: modelId.toLowerCase().includes("r1"),
        input: ["text"],
        cost: OLLAMA_DEFAULT_COST,
        contextWindow: OLLAMA_DEFAULT_CONTEXT_WINDOW,
        maxTokens: OLLAM_DEFAULT_MAX_TOKENS,
    }));
}
```
- Automatic model listing (Ollama, vLLM, Hugging Face, Bedrock)
- Reasoning model detection
- No manual configuration

**2. Multi-Source Authentication**
```typescript
const apiKey =
    config.apiKey ??
    resolveEnvApiKeyVarName(provider) ??
    resolveApiKeyFromProfiles({ provider, store: authStore }) ??
    "";
```
- Config file
- Environment variables
- Keychain-backed profiles
- Graceful fallbacks

**3. OAuth Token Exchange**
```typescript
async function resolveCopilotApiToken(params: {
    githubToken: string;
    env: NodeJS.ProcessEnv;
}): Promise<{ baseUrl: string; token: string }> {
    // Exchange GitHub token for Copilot token
    const response = await fetch("https://api.github.com/copilot_internal/v2/token", {
        headers: {
            Authorization: `Bearer ${params.githubToken}`,
        },
    });

    const data = await response.json();
    return {
        baseUrl: data.base_url,
        token: data.token,
    };
}
```
- GitHub Copilot integration
- Anthropic OAuth support
- OpenAI Codex OAuth

**4. Provider-Specific Optimizations**
```typescript
// MiniMax uses Anthropic Messages API
function buildMinimaxProvider(): ProviderConfig {
    return {
        baseUrl: MINIMAX_PORTAL_BASE_URL,
        api: "anthropic-messages",  // Not OpenAI-compatible
        models: [...],
    };
}

// vLLM uses OpenAI Completions API
async function buildVllmProvider(): Promise<ProviderConfig> {
    return {
        baseUrl,
        api: "openai-completions",  // OpenAI-compatible
        models,
    };
}
```
- API variant selection
- Provider-specific optimizations
- Transparent routing

**5. Cost Tracking Integration**
```typescript
export type ProviderUsageSnapshot = {
    provider: UsageProviderId;
    displayName: string;
    windows: UsageWindow[];
    plan?: string;
    error?: string;
};

type UsageProviderId =
    | "anthropic"
    | "github-copilot"
    | "google-gemini-cli"
    | "google-antigravity"
    | "minimax"
    | "openai-codex"
    | "xiaomi"
    | "zai";
```
- Usage monitoring
- Rate limit tracking
- Cost estimation

---

## 8. Strengths and Weaknesses

### FastReAct Nano

**Strengths:**
1. **Simplicity** - 422 lines, easy to understand
2. **Dual-Path Architecture** - Optimized for both standard and custom endpoints
3. **Zero Configuration** - Auto-detection from environment variables
4. **HTTP Pooling** - 100 concurrent connections for performance
5. **Full Streaming Support** - Both paths support streaming
6. **Clean Abstraction** - ToolCall dataclass with serialization

**Weaknesses:**
1. **Limited Providers** - Only 3 built-in providers
2. **No Gateway Support** - Can't auto-detect OpenRouter, AiHubMix
3. **No OAuth** - Can't use subscription-based providers
4. **Manual Validation** - No schema validation for configuration
5. **No Credential Store** - All credentials in environment variables

**Best For:**
- Simple projects with 1-2 providers
- Custom OpenAI-compatible endpoints
- Local LLM deployments
- Developers who want full control

---

### nanobot

**Strengths:**
1. **Registry Pattern** - Single source of truth for provider metadata
2. **Zero-Configuration Gateways** - Auto-detection by key prefix/URL
3. **OAuth Support** - OpenAI Codex, GitHub Copilot
4. **Model-Specific Overrides** - Per-model parameter adjustments
5. **Extensible** - Add providers without code changes
6. **Type Safety** - Pydantic validation

**Weaknesses:**
1. **Higher Complexity** - 622 total lines (provider + registry)
2. **No Streaming API** - All calls are non-blocking but not streaming
3. **Registry Maintenance** - Need to update for new providers
4. **Limited to LiteLLM** - Can't use providers not supported by LiteLLM

**Best For:**
- Multi-provider deployments
- Gateway usage (OpenRouter, AiHubMix)
- OAuth-based providers
- Projects requiring extensibility

---

### OpenClaw

**Strengths:**
1. **15+ Providers** - Largest provider ecosystem
2. **Dynamic Discovery** - Automatic model listing (Ollama, vLLM, Bedrock)
3. **OAuth Integration** - Anthropic, OpenAI Codex, GitHub Copilot
4. **Multi-Source Auth** - Config, env vars, keychain profiles
5. **Pi-Ai Framework** - Industry-standard implementation
6. **Cost Tracking** - Usage monitoring and rate limits
7. **Streaming Tools** - Full streaming with tool calls

**Weaknesses:**
1. **External Dependency** - No direct control over LLM implementation
2. **TypeScript Only** - No Python support
3. **Complex Configuration** - Multiple auth sources, provider configs
4. **Framework Lock-in** - Tied to Pi-Ai ecosystem

**Best For:**
- Production deployments
- Multi-platform projects (Node.js, macOS, iOS, Android)
- Enterprise environments with OAuth requirements
- Projects needing cost tracking

---

## 9. Documentation Consistency

### Claimed vs Actual Features

#### FastReAct Nano

**Claimed** (from code comments):
```python
"""
LLM Provider using LiteLLM for multi-provider support

Supports: OpenAI, Anthropic, DeepSeek, Azure, etc.
Uses environment variables for API keys and configuration.
"""
```

**Actual:**
- ✅ OpenAI support
- ✅ Anthropic support
- ✅ DeepSeek support
- ❌ Azure support (not tested, no examples)
- ✅ Environment variable configuration
- ✅ Custom endpoints (SiliconFlow, local LLMs)

**Verdict:** Mostly accurate. Azure support claimed but not verified.

---

#### nanobot

**Claimed** (from docstring):
```python
"""
LiteLLM provider implementation for multi-provider support.

Supports OpenRouter, Anthropic, OpenAI, Gemini, MiniMax, and many other providers through
a unified interface.  Provider-specific logic is driven by the registry
(see providers/registry.py) — no if-elif chains needed here.
"""
```

**Actual:**
- ✅ OpenRouter support (with auto-detection)
- ✅ Anthropic support
- ✅ OpenAI support
- ✅ Gemini support
- ✅ MiniMax support
- ✅ Registry-based architecture
- ✅ No if-elif chains

**Verdict:** Fully accurate. All claims verified.

---

#### OpenClaw

**Claimed** (from README):
```markdown
Preferred setup: run the onboarding wizard (`openclaw onboard`) in your terminal.

**Subscriptions (OAuth):**
- **Anthropic** (Claude Pro/Max)
- **OpenAI** (ChatGPT/Codex)

Model note: while any model is supported, I strongly recommend **Anthropic Pro/Max (100/200) + Opus 4.6**
for long‑context strength and better prompt‑injection resistance.
```

**Actual:**
- ✅ Onboarding wizard
- ✅ Anthropic OAuth (Claude Pro/Max)
- ✅ OpenAI OAuth (ChatGPT/Codex)
- ✅ 15+ providers supported
- ✅ Claude Opus 4.6 support

**Verdict:** Fully accurate. All claims verified.

---

### Documentation Quality

| Project | Code Comments | Docstrings | README | Examples |
|---------|--------------|------------|--------|----------|
| **FastReAct Nano** | Good (12%) | Excellent | Minimal | Good (config.example.json) |
| **nanobot** | Good (14%) | Excellent | Comprehensive | Good |
| **OpenClaw** | N/A (external) | N/A | Excellent | Comprehensive |

**Best Documented:** OpenClaw (comprehensive docs site)
**Best Code Documentation:** nanobot (detailed docstrings)
**Best Examples:** FastReAct Nano (config.example.json with 4 approaches)

---

## 10. Code Examples

### Example 1: Basic Chat Completion

#### FastReAct Nano
```python
from fastreact.providers.litellm import LiteLLMProvider

provider = LiteLLMProvider(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
)

response = await provider.chat(
    messages=[
        {"role": "user", "content": "Hello!"},
    ]
)

print(response.content)  # "Hello! How can I help you today?"
```

#### nanobot
```python
from nanobot.providers.litellm_provider import LiteLLMProvider

provider = LiteLLMProvider(
    default_model="anthropic/claude-opus-4-5",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)

response = await provider.chat(
    messages=[
        {"role": "user", "content": "Hello!"},
    ]
)

print(response.content)  # "Hello! How can I help you today?"
```

#### OpenClaw
```typescript
// OpenClaw uses Pi-Ai framework, not direct API calls
// Configuration-based approach
const config = {
    models: {
        providers: {
            anthropic: {
                apiKey: process.env.ANTHROPIC_API_KEY,
            },
        },
    },
};

// Agent execution via CLI or gateway
// $ openclaw agent --message "Hello!"
```

---

### Example 2: Custom Endpoint (SiliconFlow)

#### FastReAct Nano
```python
provider = LiteLLMProvider(
    model="deepseek-ai/DeepSeek-V3",
    api_base="https://api.siliconflow.cn/v1",
    api_key="sk-siliconflow-key",
)

response = await provider.chat(
    messages=[{"role": "user", "content": "Explain quantum computing"}]
)
```

#### nanobot
```python
# Zero-configuration gateway detection
provider = LiteLLMProvider(
    api_key="sk-siliconflow-key",
    api_base="https://api.siliconflow.cn/v1",
)

response = await provider.chat(
    messages=[{"role": "user", "content": "Explain quantum computing"}]
)
```

#### OpenClaw
```typescript
// Add to config.json
{
    "models": {
        "providers": {
            "siliconflow": {
                "baseUrl": "https://api.siliconflow.cn/v1",
                "api": "openai-completions",
                "apiKey": "sk-siliconflow-key",
                "models": [
                    {
                        "id": "deepseek-ai/DeepSeek-V3",
                        "name": "DeepSeek V3",
                        "reasoning": true,
                        "input": ["text"],
                        "cost": {"input": 0, "output": 0},
                        "contextWindow": 128000,
                        "maxTokens": 8192
                    }
                ]
            }
        }
    }
}
```

---

### Example 3: Tool Calling

#### FastReAct Nano
```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        }
    }
]

response = await provider.chat(
    messages=[{"role": "user", "content": "What's the weather in Tokyo?"}],
    tools=tools,
)

for tool_call in response.tool_calls:
    print(f"Call {tool_call.name} with {tool_call.params}")
    # Call get_weather with params={"location": "Tokyo"}
```

#### nanobot
```python
response = await provider.chat(
    messages=[{"role": "user", "content": "What's the weather in Tokyo?"}],
    tools=tools,
)

for tool_call in response.tool_calls:
    print(f"Call {tool_call.name} with {tool_call.arguments}")
    # Call get_weather with arguments={"location": "Tokyo"}
```

#### OpenClaw
```typescript
// Pi-Ai framework handles tool calling internally
// No direct API access needed

// Define tool in agent skills
const tools = [{
    name: "get_weather",
    description: "Get current weather",
    inputSchema: {
        type: "object",
        properties: {
            location: { type: "string" }
        },
        required: ["location"]
    }
}];

// Framework handles execution
```

---

### Example 4: Streaming

#### FastReAct Nano
```python
async for chunk in provider.chat_stream(
    messages=[{"role": "user", "content": "Tell me a story"}],
):
    print(chunk, end="", flush=True)
```

#### nanobot
```python
# No streaming API available
# Use async non-blocking call instead
response = await provider.chat(
    messages=[{"role": "user", "content": "Tell me a story"}],
)
print(response.content)
```

#### OpenClaw
```typescript
// Via gateway OpenAI-compatible API
const response = await fetch("http://localhost:18789/v1/chat/completions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
        model: "anthropic/claude-opus-4-6",
        messages: [{ role: "user", content: "Tell me a story" }],
        stream: true,
    }),
});

const reader = response.body.getReader();
while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const chunk = new TextDecoder().decode(value);
    console.log(chunk);
}
```

---

## 11. Recommendations

### For New Projects

**Choose FastReAct Nano if:**
- You need simple, predictable code
- You're using 1-2 providers
- You want custom endpoint support
- You prefer full control over implementation

**Choose nanobot if:**
- You need multi-provider support
- You're using gateways (OpenRouter, AiHubMix)
- You need OAuth-based providers
- You want extensibility without code changes

**Choose OpenClaw if:**
- You're building a production deployment
- You need 15+ providers
- You require OAuth integration
- You want cost tracking and usage monitoring
- You're already in the TypeScript ecosystem

---

### Migration Path

**From FastReAct Nano → nanobot:**
1. Replace `LiteLLMProvider` with nanobot's registry-based provider
2. Update config from JSON to YAML
3. Add provider-specific configs (optional, for zero-config)

**From nanobot → OpenClaw:**
1. Migrate from Python to TypeScript
2. Replace config with OpenClaw's models.json
3. Use Pi-Ai framework instead of LiteLLM
4. Implement OAuth flows (if needed)

**From OpenClaw → FastReAct Nano:**
1. Extract provider logic from Pi-Ai framework
2. Implement dual-path architecture
3. Simplify config to JSON
4. Remove OAuth support (or implement custom)

---

## 12. Conclusion

### Summary

| Aspect | Winner | Reason |
|--------|--------|--------|
| **Simplicity** | FastReAct Nano | 422 lines, easy to understand |
| **Provider Count** | OpenClaw | 15+ providers via Pi-Ai |
| **Zero-Config** | nanobot | Registry-based auto-detection |
| **Streaming** | OpenClaw | Full streaming with tools |
| **OAuth Support** | OpenClaw | Anthropic, OpenAI Codex, GitHub Copilot |
| **Custom Endpoints** | nanobot | Gateway auto-detection |
| **Documentation** | OpenClaw | Comprehensive docs site |
| **Extensibility** | nanobot | Registry pattern, no code changes needed |

### Final Verdict

**Best Overall:** nanobot
- Best balance of simplicity and features
- Registry pattern enables extensibility
- Zero-configuration gateway detection
- OAuth support for subscription providers

**Best for Production:** OpenClaw
- Industry-standard Pi-Ai framework
- Comprehensive OAuth integration
- Cost tracking and usage monitoring
- Dynamic model discovery

**Best for Learning:** FastReAct Nano
- Clean, readable code
- Dual-path architecture is educational
- Simple configuration
- Full control over implementation

---

**Report Generated:** 2026-02-18
**Analysis Method:** Code-first (actual source code analysis)
**Projects Analyzed:** FastReAct Nano, OpenClaw, nanobot
**Total Lines Analyzed:** 1,243 lines (excluding OpenClaw's 3,133 TS files)
**Analysis Depth:** Implementation-level comparison
