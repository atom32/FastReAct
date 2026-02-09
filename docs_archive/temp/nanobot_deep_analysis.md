# nanobot 深度分析报告：从代码到设计哲学

## 执行摘要

**nanobot 的核心成就**：用 7,095 行代码实现了完整功能，比 Moltbot 减少 99%，Token 成本降低 72%。

**核心创新**：Skills 系统 + 渐进式加载 + Bootstrap 文件驱动

---

## 一、Skills 系统深度解析

### 1.1 技能文件结构

```
~/.nanobot/skills/
├── github/
│   └── SKILL.md
├── weather/
│   └── SKILL.md
└── code_analysis/
    └── SKILL.md
```

### 1.2 SKILL.md 格式（实际实现）

```yaml
---
name: github
description: "Interact with GitHub using the `gh` CLI..."
metadata: {
  "nanobot": {
    "emoji": "🐙",
    "requires": {
      "bins": ["gh"]  # 需要的 CLI 工具
    },
    "install": [{
      "id": "brew",
      "kind": "brew",
      "formula": "gh",
      "bins": ["gh"],
      "label": "Install GitHub CLI (brew)"
    }]
  }
}
---
# GitHub 技能

## 如何使用

您可以通过以下命令与 GitHub 交互：

### 搜索仓库
\```bash
gh search repos "language:python stars:>1000"
\```

### 查看问题
\```bash
gh issue list --repo user/repo
\```

### 创建 PR
\```bash
gh pr create --repo user/repo --title "Fix bug"
\```

## 注意事项

- 需要先安装 `gh` CLI
- 需要进行 `gh auth login`
- 某些操作需要repo权限
```

**关键点**：
- YAML Frontmatter - 元数据和配置
- Markdown 正文 - 技能描述
- 依赖声明 - 自动检查可用性
- 渐进式披露 - 可以引用其他文件

### 1.3 技能加载策略（三级加载）

```python
class SkillsLoader:
    def build_system_prompt_parts(self):
        parts = []

        # Level 1: 核心身份（~200 词）
        parts.append(self._get_identity())

        # Level 2: Bootstrap 文件（~1000 词）
        parts.append(self._load_bootstrap_files())

        # Level 3: Always 技能 - 完整内容（~3000 词）
        always_skills = self.get_always_skills()
        parts.append(self.load_skills_for_context(always_skills))

        # Level 4: Available 技能 - XML 摘要（~500 词）
        skills_summary = self.build_skills_summary()  # XML 格式
        parts.append(skills_summary)

        # 总计: ~4700 词
        return "\n\n---\n\n".join(parts)
```

**Token 节省对比**：

| 方案 | Token 消耗 | 节省 |
|------|-----------|------|
| Moltbot（所有工具） | ~10,000 | - |
| nanobot（渐进式） | ~2,800 | **72%** |

### 1.4 XML 摘要格式（巧妙设计）

```xml
<skills>
  <skill available="true">
    <name>github</name>
    <description>Interact with GitHub using gh CLI</description>
    <location>/path/to/skills/github/SKILL.md</location>
  </skill>
  <skill available="false">
    <name>weather</name>
    <description>Get weather information</description>
    <location>/path/to/skills/weather/SKILL.md</location>
    <requires>CLI: curl, ENV: WEATHER_API_KEY</requires>
  </skill>
</skills>
```

**关键点**：
- `available="true/false"` - 依赖是否满足
- `<requires>` - 显示缺失的依赖
- Agent 可以通过 `read_file` 按需加载

---

## 二、ReAct 循环实现

### 2.1 核心循环（极简设计）

```python
class AgentLoop:
    async def _process_message(self, msg: InboundMessage):
        # 1. 获取/创建会话
        session = self.sessions.get_or_create(msg.session_key)

        # 2. 构建上下文
        messages = self.context.build_messages(
            history=session.get_history(),
            current_message=msg.content,
            media=msg.media,
            channel=msg.channel,
            chat_id=msg.chat_id,
        )

        # 3. ReAct 循环（最多20次迭代）
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1

            # 调用 LLM
            response = await self.provider.chat(
                messages=messages,
                tools=self.tools.get_definitions(),
                model=self.model
            )

            # 处理工具调用
            if response.has_tool_calls:
                for tool_call in response.tool_calls:
                    result = await self.tools.execute(
                        tool_call.name,
                        tool_call.arguments
                    )
                    messages = self.context.add_tool_result(
                        messages,
                        tool_call.id,
                        tool_call.name,
                        result
                    )

                # 添加 assistant消息
                messages = self.context.add_assistant_message(
                    messages,
                    content=response.content,
                    tool_calls=[tc.to_dict() for tc in response.tool_calls],
                    reasoning_content=response.reasoning_content
                )
            else:
                # 无工具调用，结束循环
                final_content = response.content
                break

        # 4. 保存会话并返回
        session.save()
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=final_content
        )
```

**关键设计**：
- ✅ **极简**：核心循环只有 50 行
- ✅ **清晰**：单一职责，易理解
- ✅ **可靠**：最大迭代保护
- ❌ **功能单一**：只支持 ReAct（这也是优势）

### 2.2 与 FastReAct 对比

| 维度 | nanobot | FastReAct |
|------|---------|-----------|
| **代码量** | 377 行（loop.py） | 3043 行（engine.py） |
| **循环次数** | 20 次（硬编码） | 可配置（默认20） |
| **复杂度评估** | 无 | 有（400 行） |
| **Double Check** | 无 | 有（500 行） |
| **模式选择** | 无 | 有（GraphAgent/IEL） |
| **流式输出** | 有（推理内容） | 有 |

**结论**：nanobot 专注 ReAct，FastReAct 功能全面但复杂

---

## 三、上下文构建策略

### 3.1 Bootstrap 文件系统

```python
BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "IDENTITY.md"]
```

**文件作用**：

- **AGENTS.md** - Agent 角色和行为
- **SOUL.md** - 个性特征
- **USER.md** - 用户偏好
- **TOOLS.md** - 工具使用指南
- **IDENTITY.md** - 身份信息

**优势**：
- ✅ 文件驱动 - 用户可通过 Markdown 定制
- ✅ 无需修改代码
- ✅ 版本控制友好
- ✅ 易于测试和迭代

### 3.2 记忆系统（双层次）

```python
class MemoryStore:
    def get_memory_context(self) -> str:
        """获取记忆上下文"""
        parts = []

        # 长期记忆
        memory_file = self.workspace / "memory" / "MEMORY.md"
        if memory_file.exists():
            parts.append(memory_file.read_text())

        # 每日笔记
        today = datetime.now().strftime("%Y-%m-%d")
        daily_file = self.workspace / "memory" / f"{today}.md"
        if daily_file.exists():
            parts.append(daily_file.read_text())

        return "\n\n".join(parts)
```

**优势**：
- ✅ 长期记忆 - 持久化知识
- ✅ 每日笔记 - 临时信息
- ✅ 文件系统 - 易于备份
- ✅ 用户可编辑

---

## 四、工具系统设计

### 4.1 工具基类（极简）

```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def description(self) -> str: pass

    @property
    @abstractmethod
    def parameters(self) -> dict: pass

    @abstractmethod
    async def execute(self, **kwargs) -> str: pass

    def validate_params(self, params: dict) -> list[str]:
        """验证参数（内置 JSON Schema 验证）"""
        ...
```

**关键点**：
- ✅ 异步执行
- ✅ 参数验证
- ✅ 错误返回（字符串，不抛异常）

### 4.2 安全防护（模式匹配）

```python
class ExecTool(Tool):
    def __init__(self):
        # 危险命令黑名单
        self.deny_patterns = [
            r"\brm\s+-[rf]{1,2}\b",     # rm -r, rm -rf
            r"\bdd\s+if=",                 # dd
            r">\s*/dev/sd",                # 写入磁盘
            r"\b(shutdown|reboot)\b",      # 系统关机
        ]

    async def execute(self, command: str, **kwargs) -> str:
        # 检查危险命令
        for pattern in self.deny_patterns:
            if re.search(pattern, command):
                return f"Error: Command blocked for safety: {command}"

        # 执行命令
        ...
```

**优势**：
- ✅ 安全防护
- ✅ 用户可配置
- ✅ 正则表达式灵活

---

## 五、LLM Provider 抽象

### 5.1 注册表模式

```python
PROVIDERS: tuple[ProviderSpec, ...] = (
    # 网关优先
    ProviderSpec(
        name="openrouter",
        keywords=("openrouter",),
        env_key="OPENROUTER_API_KEY",
        is_gateway=True,
        detect_by_key_prefix="sk-or-",
    ),

    # 标准提供者
    ProviderSpec(
        name="deepseek",
        keywords=("deepseek",),
        env_key="DEEPSEEK_API_KEY",
        litellm_prefix="deepseek",
    ),

    # 本地模型
    ProviderSpec(
        name="ollama",
        keywords=("ollama",),
        is_local=True,
    ),
)
```

**关键点**：
- ✅ 自动检测 - 根据模型名匹配
- ✅ 网关优先 - OpenRouter, AiHubMix
- ✅ 本地支持 - Ollama, vLLM
- ✅ 11+ 提供商

---

## 六、Session 管理

### 6.1 JSONL 格式

```jsonl
{"role": "user", "content": "Hello"}
{"role": "assistant", "content": "Hi there!"}
{"role": "user", "content": "How are you?"}
{"role": "assistant", "content": "I'm doing well!"}
```

**关键点**：
- ✅ 每行一个 JSON
- ✅ 易于追加
- ✅ 人类可读
- ✅ Git 友好

### 6.2 历史截断

```python
def get_history(self, max_messages: int = 50) -> list[dict]:
    """获取LLM上下文用的历史消息"""
    recent = self.messages[-max_messages:] if len(self.messages) > max_messages else self.messages
    return [{"role": m["role"], "content": m["content"]} for m in recent]
```

**关键点**：
- ✅ 限制消息数量（50 条）
- ✅ 只保留 role 和 content
- ✅ Token 节省

---

## 七、关键启发点

### 7.1 值得借鉴的设计

#### 1. **Skills 系统** ⭐⭐⭐⭐⭐

**为什么优秀**：
- ✅ 文件驱动（Markdown）
- ✅ 渐进式加载（3 级）
- ✅ 依赖检查（自动）
- ✅ Agent 可理解
- ✅ Token 节省 72%

**如何应用到 FastReAct v2.0**：
```python
# 1. 实现 SkillsLoader
skills_loader = SkillsLoader(workspace)

# 2. 构建上下文时加载
context = skills_loader.build_system_prompt()

# 3. 添加工具让 Agent 自写技能
tools.register(CreateSkillTool())
```

#### 2. **Bootstrap 文件** ⭐⭐⭐⭐⭐

**为什么优秀**：
- ✅ 用户可通过 Markdown 定制
- ✅ 无需修改代码
- ✅ 版本控制友好
- ✅ 易于测试

**应用**：
```
~/.fastreact/
├── AGENTS.md      # Agent 角色
├── TOOLS.md       # 工具指南
└── CONSTRAINTS.md # 约束条件
```

#### 3. **工具安全防护** ⭐⭐⭐⭐

**为什么优秀**：
- ✅ 模式匹配黑名单
- ✅ 防止危险操作
- ✅ 用户可配置

**应用**：
```python
deny_patterns = [
    r"\brm\s+-[rf]{1,2}\b",
    r"\bdd\s+if=",
    r">\s*/dev/sd",
]
```

#### 4. **记忆系统** ⭐⭐⭐⭐

**为什么优秀**：
- ✅ 长期记忆（MEMORY.md）
- ✅ 每日笔记（YYYY-MM-DD.md）
- ✅ 文件系统存储

**应用**：
```python
memory_store.get_memory_context()
# 返回 MEMORY.md + 2025-02-09.md 的内容
```

---

## 八、与 FastReAct v1.0 的详细对比

### 8.1 代码规模

| 模块 | nanobot | FastReAct v1 | 差异 |
|------|---------|--------------|------|
| **核心引擎** | 377 行 | 3,043 行 | **8x** |
| **上下文** | 235 行 | ~1500 行 | **6x** |
| **Skills** | 228 行 | 0 | **新增** |
| **Provider** | ~800 行 | ~1000 行 | 相当 |
| **工具** | ~1000 行 | ~4000 行 | 4x |
| **CLI** | 851 行 | ~3000 行 | 3.5x |
| **总计** | **7,095** | **50,792** | **7.2x** |

### 8.2 功能对比

| 功能 | nanobot | FastReAct v1 |
|------|---------|--------------|
| **ReAct** | ✅ | ✅ |
| **GraphAgent** | ❌ | ✅ |
| **IEL** | ❌ | ✅ |
| **Skills** | ✅ | ❌ |
| **Bootstrap** | ✅ | ❌ |
| **多 Provider** | ✅ (11+) | ✅ (3) |
| **多渠道** | ✅ (6+) | ✅ (5+) |
| **向量存储** | ❌ | ✅ |
| **检查点** | ❌ | ✅ |
| **可观测性** | ⚠️ 基础 | ✅ 完整 |

---

## 九、FastReAct v2.0 设计方案

### 9.1 基于 nanobot 改造

**保留 nanobot 的 70%**：
- ✅ Skills 系统（完整）
- ✅ Bootstrap 文件（完整）
- ✅ 记忆系统（完整）
- ✅ Provider 抽象（完整）
- ✅ 工具安全（完整）

**增强的部分**：
- 🔄 核心引擎（添加 MessageBus）
- 🔄 插件系统（企业特性）
- 🔄 多渠道（统一接口）

**新增的部分**：
- ➕ MessageBus 桥接层
- ➕ 插件系统
- ➕ 更丰富的渠道

### 9.2 目录结构（基于 nanobot）

```
fastreact/
├── core/                      # 核心引擎（基于 nanobot）
│   ├── loop.py               # ReAct 循环（~400 行）
│   ├── context.py            # 上下文构建（~250 行）
│   ├── skills.py             # Skills 加载（~250 行）
│   └── session.py            # 会话管理（~200 行）
│
├── bridge/                    # 桥接层（新增）
│   ├── messagebus.py         # 消息总线（~100 行）
│   └── message.py            # 标准消息（~50 行）
│
├── channels/                 # 渠道层（基于 nanobot）
│   ├── cli.py                # CLI 渠道（~400 行）
│   ├── web.py                # Web 渠道（~500 行）
│   ├── telegram.py           # IM 渠道（~500 行）
│   └── discord.py            # IM 渠道（~400 行）
│
├── tools/                     # 工具（简化）
│   ├── filesystem.py         # 文件操作（~400 行）
│   ├── shell.py              # Shell（~300 行）
│   └── web.py                # Web（~300 行）
│
├── providers/                 # LLM 提供商（基于 nanobot）
│   └── registry.py           # 提供商注册（~300 行）
│
├── plugins/                   # 插件（新增）
│   ├── observability/         # 可观测性（~500 行）
│   └── storage/               # 存储（~400 行）
│
└── templates/                 # 模板文件
    ├── AGENTS.md             # Bootstrap 文件
    ├── TOOLS.md
    └── skills/               # Skills 模板
```

**预计代码量**：
- 核心：~1100 行
- 桥接：~150 行
- 渠道：~1800 行
- 工具：~1000 行
- 提供商：~300 行
- 插件：~900 行
- **总计：~5250 行**（v1.0 的 10%）

---

## 十、总结与建议

### 10.1 核心结论

**nanobot 的成功秘诀**：
1. Skills 系统 - Token 节省 72%
2. 渐进式加载 - 上下文优化
3. Bootstrap 文件 - 用户可定制
4. 极简核心 - 只做 ReAct
5. 工具安全 - 模式匹配防护

**FastReAct v2.0 应该**：
1. ✅ 采用 Skills 系统（完整）
2. ✅ 采用 Bootstrap 文件
3. ✅ 保留企业特性（插件）
4. ✅ 简化核心（只做 ReAct）
5. ✅ 支持多渠道（统一接口）

### 10.2 实施建议

**阶段 1：Fork 和审查（1 周）**
```bash
git clone https://github.com/hmac0202/nanobot.git fastreact-v2
cd fastreact-v2

# 审查核心文件
- agent/loop.py
- agent/context.py
- agent/skills.py
- providers/registry.py
```

**阶段 2：架构调整（1 周）**
- 添加 bridge/ 目录
- 实现 MessageBus
- 实现标准消息格式
- 解耦核心和渠道

**阶段 3：功能迁移（2 周）**
- 迁移 FastReAct Prompt
- 添加插件系统
- 增强工具
- 添加可观测性

**阶段 4：测试和发布（2 周）**
- 集成测试
- 性能测试
- 文档编写
- 发布 v2.0

### 10.3 最终目标

**FastReAct v2.0 = nanobot 的简洁 + FastReAct 的企业特性**

- ✅ <6000 行代码
- ✅ Skills 系统
- ✅ Bootstrap 文件
- ✅ 多渠道支持
- ✅ 插件系统
- ✅ 生产就绪

---

## 十一、Provider Registry 系统（11+ 提供商）

### 11.1 ProviderSpec 数据类

**设计亮点**：
```python
@dataclass(frozen=True)
class ProviderSpec:
    # 核心标识
    name: str                       # 配置字段名，如 "dashscope"
    keywords: tuple[str, ...]       # 模型名关键词（用于匹配）
    env_key: str                    # LiteLLM 环境变量，如 "DASHSCOPE_API_KEY"
    display_name: str = ""          # 在 status 中显示的名称

    # 模型前缀
    litellm_prefix: str = ""                 # "dashscope" → 模型变为 "dashscope/{model}"
    skip_prefixes: tuple[str, ...] = ()      # 如果模型已此前缀，不再添加

    # 网关/本地检测
    is_gateway: bool = False                 # 可路由任何模型（OpenRouter, AiHubMix）
    is_local: bool = False                   # 本地部署（vLLM, Ollama）
    detect_by_key_prefix: str = ""           # 匹配 api_key 前缀，如 "sk-or-"
    detect_by_base_keyword: str = ""         # 匹配 api_base URL 中的关键词
    default_api_base: str = ""               # 默认基础 URL
```

**优势**：
- ✅ frozen dataclass - 不可变，线程安全
- ✅ 单一数据源 - 所有元数据集中管理
- ✅ 自动推导 - env vars、前缀、匹配都从此推导

### 11.2 智能匹配策略

**三级匹配优先级**：

1. **网关优先** - OpenRouter、AiHubMix
   - 通过 api_key 前缀检测：`sk-or-` → OpenRouter
   - 通过 api_base 关键词检测：`aihubmix` → AiHubMix

2. **标准提供商** - 通过模型名关键词匹配
   ```python
   def find_by_model(model: str) -> ProviderSpec | None:
       model_lower = model.lower()
       for spec in PROVIDERS:
           if spec.is_gateway or spec.is_local:
               continue
           if any(kw in model_lower for kw in spec.keywords):
               return spec
       return None
   ```

3. **本地部署** - 通过配置键显式指定
   - vLLM：需要用户在配置中显式设置

**支持的提供商**：
- ✅ OpenRouter（网关）
- ✅ AiHubMix（网关）
- ✅ Anthropic (Claude)
- ✅ OpenAI (GPT)
- ✅ DeepSeek
- ✅ Gemini
- ✅ Zhipu AI (GLM)
- ✅ DashScope (Qwen)
- ✅ Moonshot (Kimi)
- ✅ vLLM（本地）
- ✅ Groq（辅助）

### 11.3 灵活的配置系统

**环境变量映射**：
```python
# 自动映射
env_extras=(
    ("ZHIPUAI_API_KEY", "{api_key}"),  # 自动复制 api_key
    ("MOONSHOT_API_BASE", "{api_base}"),  # 自动使用 api_base
)
```

**模型级覆盖**：
```python
# Moonshot Kimi K2.5 要求 temperature >= 1.0
model_overrides=(
    ("kimi-k2.5", {"temperature": 1.0}),
)
```

**智能前缀处理**：
```python
# AiHubMix 的特殊处理
strip_model_prefix=True  # anthropic/claude-3 → claude-3 → openai/claude-3
```

---

## 十二、工具系统（Tools System）

### 12.1 Tool 基类（极简设计）

**核心接口**（103 行）：
```python
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称，用于函数调用"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具功能描述"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema 格式的参数定义"""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """执行工具，返回字符串结果"""
        pass

    def validate_params(self, params: dict) -> list[str]:
        """验证参数，返回错误列表"""
        ...
```

**关键点**：
- ✅ 异步执行 - 原生 async/await
- ✅ 字符串返回 - 统一结果格式
- ✅ 内置验证 - JSON Schema 验证
- ✅ 错误列表 - 返回多个验证错误

### 12.2 ToolRegistry（动态注册）

**核心功能**（74 行）：
```python
class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool

    def get_definitions(self) -> list[dict[str, Any]]:
        """获取所有工具的 OpenAI 格式定义"""
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute(self, name: str, params: dict) -> str:
        """执行工具（带验证）"""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found"

        errors = tool.validate_params(params)
        if errors:
            return f"Error: Invalid parameters: " + "; ".join(errors)

        return await tool.execute(**params)
```

**优势**：
- ✅ 动态注册 - 运行时添加/移除工具
- ✅ 统一验证 - 所有工具自动验证
- ✅ 错误处理 - 友好的错误消息
- ✅ OpenAI 格式 - 直接用于 LLM

### 12.3 安全防护：ExecTool

**危险命令黑名单**（142 行）：
```python
self.deny_patterns = [
    r"\brm\s+-[rf]{1,2}\b",          # rm -r, rm -rf
    r"\bdel\s+/[fq]\b",              # del /f, del /q
    r"\brmdir\s+/s\b",               # rmdir /s
    r"\b(format|mkfs|diskpart)\b",   # 磁盘操作
    r"\bdd\s+if=",                   # dd
    r">\s*/dev/sd",                  # 写入磁盘
    r"\b(shutdown|reboot|poweroff)\b",  # 系统关机
    r":\(\)\s*\{.*\};\s*:",          # Fork 炸弹
]
```

**安全特性**：
- ✅ 模式匹配黑名单
- ✅ 可选白名单模式
- ✅ 工作目录限制
- ✅ 路径遍历检测（`../`）
- ✅ 超时保护（默认 60 秒）
- ✅ 输出截断（最大 10000 字符）

**实现**：
```python
def _guard_command(self, command: str, cwd: str) -> str | None:
    """最佳努力安全防护"""
    # 1. 检查黑名单
    for pattern in self.deny_patterns:
        if re.search(pattern, command.lower()):
            return "Error: Command blocked (dangerous pattern)"

    # 2. 检查白名单（如果启用）
    if self.allow_patterns:
        if not any(re.search(p, command.lower()) for p in self.allow_patterns):
            return "Error: Command blocked (not in allowlist)"

    # 3. 路径遍历检测
    if self.restrict_to_workspace:
        if "..\\" in command or "../" in command:
            return "Error: Command blocked (path traversal)"

        # 4. 检查路径是否在工作目录内
        cwd_path = Path(cwd).resolve()
        for path in extract_paths(command):
            if cwd_path not in path.parents and path != cwd_path:
                return "Error: Command blocked (outside working dir)"
```

### 12.4 文件系统工具

**路径解析和权限控制**：
```python
def _resolve_path(path: str, allowed_dir: Path | None = None) -> Path:
    """解析路径并可选地强制目录限制"""
    resolved = Path(path).expanduser().resolve()
    if allowed_dir and not str(resolved).startswith(str(allowed_dir.resolve())):
        raise PermissionError(f"Path {path} is outside allowed directory")
    return resolved
```

**四个核心工具**：

1. **ReadFileTool** - 读取文件
   - UTF-8 编码
   - 路径权限检查
   - 错误处理（不存在、不是文件）

2. **WriteFileTool** - 写入文件
   - 自动创建父目录
   - UTF-8 编码
   - 返回写入字节数

3. **EditFileTool** - 替换编辑
   - 精确匹配 `old_text`
   - 检查重复出现
   - 单次替换（避免批量错误）

4. **ListDirTool** - 列出目录
   - 排序输出
   - 文件夹/文件区分（emoji）
   - 空目录检测

---

## 十三、与 FastReAct v1.0 的工具对比

### 13.1 工具基类对比

| 维度 | nanobot | FastReAct v1 |
|------|---------|--------------|
| **代码量** | 103 行 | ~200 行 |
| **验证机制** | 内置 JSON Schema | 外部验证 |
| **错误处理** | 返回错误列表 | 抛出异常 |
| **返回格式** | 固定字符串 | 可自定义 |
| **异步支持** | 原生 async | 部分同步 |

### 13.2 Shell 工具对比

| 维度 | nanobot | FastReAct v1 |
|------|---------|--------------|
| **安全防护** | 8 种危险模式 | 3 种危险模式 |
| **路径限制** | 工作目录 + 路径检查 | 基础路径检查 |
| **超时保护** | 默认 60 秒 | 可配置 |
| **输出截断** | 10000 字符 | 无限制 |
| **并发控制** | 单实例 Shell | 持久化 Shell |

**结论**：nanobot 的安全防护更全面

---

## 十四、总结：nanobot 的成功秘诀

### 14.1 核心设计原则

1. **极简核心**
   - ReAct 循环：50 行
   - Tool 基类：103 行
   - Registry：74 行
   - 总计：<300 行实现完整功能

2. **智能抽象**
   - ProviderSpec：单一数据源
   - Tool：最小接口
   - Skills：文件驱动

3. **安全第一**
   - Shell：8 种危险模式
   - Filesystem：路径权限检查
   - 配置：工作目录限制

4. **渐进式加载**
   - 4 层上下文构建
   - 3 级技能加载
   - Token 节省 72%

### 14.2 可复用的设计模式

**值得完全采纳**：
- ✅ Tool 基类（103 行）
- ✅ ToolRegistry（74 行）
- ✅ ProviderSpec（frozen dataclass）
- ✅ Shell 安全防护（8 种模式）
- ✅ Filesystem 路径解析

**需要增强**：
- 🔄 Shell 持久化（FastReAct 的单例 Shell）
- 🔄 工具并发控制
- 🔄 输出流式处理

**可以简化**：
- 🔄 Provider 注册表（11+ → 6+ 够用）
- 🔄 技能加载（合并到 Bootstrap）

---

**nanobot 已经证明了 Less is More！** 🚀
