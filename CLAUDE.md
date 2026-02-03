# CLAUDE.md - FastReAct 项目指南

> **面向 AI 助手的项目开发指南**
>
> 本文档提供 FastReAct 项目的架构、规则和最佳实践，确保 AI 助手能够正确理解和扩展代码库。

---

## 一、项目架构概览

### 1.1 核心理念

FastReAct 是一个**轻量级但功能完整**的 ReAct（Reasoning and Acting）Agent 框架，设计原则：

- ✅ **配置驱动**：所有可配置参数必须通过 config 文件或环境变量设置
- ✅ **复用优先**：优先使用现有模块，避免重复造轮子
- ✅ **禁止硬编码**：任何可能变化的值都不应硬编码
- ✅ **模块化设计**：功能按职责分离到独立模块
- ✅ **向后兼容**：新功能不应破坏现有 API

### 1.2 目录结构

```
FastReAct/
├── src/fastreact/           # 源代码
│   ├── __init__.py          # 公共 API 导出
│   ├── core/                # 核心模块
│   │   ├── engine.py        # FastReAct 主引擎
│   │   ├── tool.py          # 工具基类
│   │   ├── streaming.py     # V2: 流式响应
│   │   ├── tool_group.py    # V2: 工具分组
│   │   ├── tool_manager.py  # V2: 工具管理器
│   │   ├── cache.py         # LRU 缓存
│   │   └── ...
│   ├── tools/               # 工具实现
│   │   ├── fn_registry.py   # 函数式工具定义（推荐）
│   │   ├── sandbox_tools.py # 沙箱工具
│   │   └── ...
│   ├── sandbox/             # Docker 沙箱
│   │   ├── docker.py        # Docker 沙箱实现
│   │   └── config.py        # 沙箱配置
│   ├── bootstrap/           # Bootstrap 配置系统
│   │   ├── config_loader.py # 配置加载器
│   │   └── loader.py        # Bootstrap 加载器
│   ├── gateway/             # API Gateway
│   ├── context/             # 上下文管理
│   └── storage/             # 存储层
├── tests/                   # 测试文件
├── docs/                    # 文档
├── config.json              # 用户配置文件
├── config.example.json      # 配置模板
└── CLAUDE.md                # 本文档
```

---

## 二、核心模块详解

### 2.1 配置系统 (`bootstrap/config_loader.py`)

**优先级**（从高到低）：
1. 环境变量
2. 用户配置文件 (`config.json`)
3. 默认值

**环境变量命名规范**：
```
FASTREACT_API_KEY          # LLM API 密钥
FASTREACT_BASE_URL         # LLM API 基础 URL
FASTREACT_MODEL            # 模型名称
FASTREACT_PROVIDER         # LLM 提供商
FASTREACT_ENABLE_PRUNING   # 功能开关
```

**配置获取示例**：
```python
from fastreact.bootstrap.config_loader import load_config, get_api_key, get_base_url, get_model

# 加载完整配置
config = load_config()

# 获取特定配置项
api_key = get_api_key(config)      # 支持环境变量和配置文件
base_url = get_base_url(config)
model = get_model(config)
```

### 2.2 工具系统 (`tools/`)

**工具定义方式（推荐）**：
- ✅ **函数式工具**：`tools/fn_registry.py` 中的工厂函数
- ❌ **类继承工具**：不推荐用于新代码

**工具分组**（V2）：
- `file_ops`: 文件操作（read_file, write_file, edit_file）
- `web`: Web 操作（search, http）
- `code`: 代码操作（ls_repo, cd_repo, refresh_repo）
- `system`: 系统操作（bash） - 默认 DENY_ALL
- `math`: 数学计算（calculator）
- `data`: 数据操作
- `text`: 文本处理
- `ai`: AI 工具

**添加新工具的步骤**：
1. 在 `fn_registry.py` 中创建 `create_xxx_tool()` 函数
2. 设置 `Tool` 对象的 `group` 属性
3. 在 `create_builtin_tools()` 中注册
4. 在 `tools/__init__.py` 中导出

**工具定义模板**：
```python
def create_your_tool(custom_param: str = None) -> Tool:
    """创建你的工具

    Args:
        custom_param: 自定义参数

    Returns:
        Tool 对象
    """
    async def execute(param1: str, param2: int = 10) -> str:
        # 执行逻辑
        return f"Result: {param1}"

    return Tool(
        name="your_tool",
        label="Your Tool",
        description="工具描述，说明用途和参数",
        group="category",  # 必须设置分组
        parameters={
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "参数1"},
                "param2": {"type": "integer", "default": 10}
            },
            "required": ["param1"]
        },
        execute=execute,
    )
```

### 2.3 沙箱系统 (`sandbox/`)

**配置类** (`sandbox/config.py`)：
- `SandboxConfig`: 沙箱配置（内存、CPU、网络、挂载点）
- `NetworkMode`: 网络隔离模式
- `SandboxPreset`: 预设配置（SAFE, STANDARD, PERFORMANCE, UNRESTRICTED）

**使用方式**：
```python
from fastreact.sandbox import (
    DockerSandbox,
    SandboxConfig,
    get_preset_config,
    SandboxPreset,
    create_config_with_mounts,
)

# 方式 1: 使用预设
config = get_preset_config(SandboxPreset.SAFE)
sandbox = DockerSandbox(config=config)

# 方式 2: 自定义配置
config = SandboxConfig(
    memory_limit="1g",
    cpu_limit=1.0,
    network_mode=NetworkMode.DISABLED,
)
sandbox = DockerSandbox(config=config)

# 方式 3: 带挂载点
config = create_config_with_mounts(
    workspace_path="./workspace",
    read_only_paths=["/readonly/path"],
)
sandbox = DockerSandbox(config=config)
```

### 2.4 流式响应 (`core/streaming.py`)

**StreamChunk 类型**：
- `METADATA`: 元数据（开始、结束、统计）
- `THINKING`: 推理过程（`<thinking>` 标签）
- `TOOL_CALL`: 工具调用
- `TOOL_RESULT`: 工具执行结果
- `ANSWER`: 最终答案
- `ERROR`: 错误信息
- `CONTROL`: 控制信号

**使用方式**：
```python
from fastreact import FastReAct, StreamChunkType

agent = FastReAct(api_key="...", model="...")

async for chunk in agent.run_streaming("你的查询"):
    if chunk.type == StreamChunkType.THINKING:
        print(f"Thinking: {chunk.content}")
    elif chunk.type == StreamChunkType.TOOL_CALL:
        print(f"Tool: {chunk.tool_name}({chunk.tool_params})")
    elif chunk.type == StreamChunkType.ANSWER:
        print(f"Answer: {chunk.content}")
```

---

## 三、开发规则

### 3.1 禁止硬编码

❌ **错误示例**：
```python
# 硬编码的 API 地址
BASE_URL = "https://api.openai.com/v1"

# 硬编码的模型名称
MODEL = "gpt-4"

# 硬编码的配置值
TIMEOUT = 30
MAX_ITERATIONS = 10
```

✅ **正确做法**：
```python
# 从配置获取
from fastreact.bootstrap.config_loader import load_config

config = load_config()
base_url = get_base_url(config)
model = get_model(config)

# 或者使用函数参数
def my_function(timeout: int = None):
    config = load_config()
    timeout = timeout or config.get("react", {}).get("timeout", 30)
```

### 3.2 复用优先原则

**在使用代码前，先检查是否存在**：
1. 搜索 `src/fastreact/` 目录
2. 检查 `tools/` 中是否有类似工具
3. 查看配置系统是否已支持该功能

**复用清单**：
- ✅ 配置加载：`bootstrap/config_loader.py`
- ✅ 工具定义：`tools/fn_registry.py`
- ✅ 日志系统：`utils/logger.py`
- ✅ 异常处理：`core/exceptions.py`
- ✅ 缓存系统：`core/cache.py`

### 3.3 配置驱动设计

**所有可配置项必须**：
1. 在 `_get_default_config()` 中定义默认值
2. 支持 config.json 覆盖
3. 支持环境变量覆盖

**示例**：
```python
# bootstrap/config_loader.py
def _get_default_config() -> Dict[str, Any]:
    return {
        "your_feature": {
            "enabled": True,
            "param1": "default_value",
            "param2": 100,
        }
    }

# 在代码中使用
from fastreact.bootstrap.config_loader import load_config

config = load_config()
feature_config = config.get("your_feature", {})
enabled = feature_config.get("enabled", True)
param1 = feature_config.get("param1", "default_value")
```

---

## 四、配置系统详解

### 4.1 config.json 结构

```json
{
  "llm": {
    "providers": {
      "siliconflow": {
        "enabled": true,
        "api_key": "your-api-key",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "deepseek-ai/DeepSeek-V3"
      },
      "openai": {
        "enabled": false,
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4"
      }
    },
    "default_provider": "siliconflow"
  },
  "tools": {
    "builtin_enabled": true,
    "tavily": {
      "api_key": "your-tavily-key"
    },
    "sandbox": {
      "enabled": true,
      "default_preset": "standard",
      "auto_pull_images": false
    }
  },
  "react": {
    "max_iterations": 10,
    "max_concurrent_tools": 3,
    "enable_cache": true,
    "enable_streaming": false
  },
  "context": {
    "max_history_messages": 1000,
    "max_history_tokens": 48000,
    "reserve_tokens": 12000,
    "pruning": {
      "enabled": true,
      "target_ratio": 0.5
    }
  }
}
```

### 4.2 环境变量映射

| 环境变量 | 配置路径 | 说明 |
|----------|----------|------|
| `FASTREACT_API_KEY` | `llm.api_key` | LLM API 密钥 |
| `FASTREACT_BASE_URL` | `llm.base_url` | API 基础 URL |
| `FASTREACT_MODEL` | `llm.model` | 模型名称 |
| `FASTREACT_PROVIDER` | `llm.default_provider` | 默认提供商 |
| `FASTREACT_ENABLE_PRUNING` | `context.pruning.enabled` | 启用上下文修剪 |
| `FASTREACT_STREAMING_ENABLED` | `react.enable_streaming` | 启用流式响应 |

---

## 五、关键功能点

### 5.1 工具注册和发现

**工具注册流程**：
1. 工具通过 `create_xxx_tool()` 工厂函数创建
2. 在 `create_builtin_tools()` 中注册
3. 支持通过配置文件启用/禁用工具
4. 工具自动分配到分组

**获取工具的方式**：
```python
# 方式 1: 使用工厂函数
from fastreact.tools import create_builtin_tools
tools = create_builtin_tools()

# 方式 2: 通过工具管理器（V2）
from fastreact import ToolManager
manager = ToolManager(auto_register=True)
tools = manager.get_tools_by_groups(["file_ops", "math"])
```

### 5.2 Agent 初始化参数

```python
from fastreact import FastReAct

agent = FastReAct(
    # 必需参数
    api_key="...",           # LLM API 密钥（或通过环境变量）

    # 可选参数 - 从配置系统获取
    base_url="...",         # API 基础 URL
    model="...",            # 模型名称

    # 工具相关
    tools=None,              # 工具列表（None = 使用内置工具）
    enable_groups=None,       # V2: 启用的工具分组
    respect_group_policies=True,  # V2: 遵守分组策略

    # 性能参数
    max_iterations=10,       # 最大迭代次数
    max_concurrent_tools=3,  # 最大并发工具数
    enable_cache=True,       # 启用 LRU 缓存

    # V2: 流式响应
    enable_streaming=False,  # 启用流式输出

    # 上下文管理
    enable_bootstrap=True,   # 启用 Bootstrap 配置
    workspace=None,          # Bootstrap 工作区路径

    # 沙箱
    enable_sandbox=None,     # 启用沙箱（待实现）
    sandbox_config=None,     # 沙箱配置
)
```

### 5.3 配置加载器使用

**始终使用配置加载器获取配置**：
```python
from fastreact.bootstrap.config_loader import load_config

# 在模块/函数开始时加载
def my_function():
    config = load_config()

    # 获取配置项
    api_key = config.get("api_key")
    if not api_key:
        api_key = get_api_key(config)  # 使用辅助函数

    # 使用配置
    max_iterations = config.get("react", {}).get("max_iterations", 10)
```

---

## 六、测试要求

### 6.1 测试文件结构

```
tests/
├── test_core/              # 核心功能测试
├── test_tools/             # 工具测试
├── test_sandbox.py         # 沙箱测试
├── test_streaming.py       # 流式响应测试
├── test_sandbox_comprehensive.py  # 沙箱完整测试套件
└── test_e2e/              # 端到端测试
```

### 6.2 测试编写规范

**测试用例必须包含**：
1. 清晰的测试目的说明
2. 正常场景测试
3. 边界条件测试
4. 错误处理测试
5. 清理资源（如有需要）

**测试模板**：
```python
"""
模块功能测试
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastreact import FastReAct


async def test_feature():
    """测试特定功能"""
    # Arrange
    config = load_config()
    agent = FastReAct(api_key=get_api_key(config))

    # Act
    result = await agent.run_async("test query")

    # Assert
    assert result["answer"] is not None
    assert "error" not in result

    await agent.close()


if __name__ == "__main__":
    asyncio.run(test_feature())
```

---

## 七、常见问题和最佳实践

### 7.1 添加新功能的检查清单

- [ ] 配置项已添加到 `_get_default_config()`
- [ ] 支持环境变量覆盖
- [ ] 支持配置文件覆盖
- [ ] 没有硬编码的值
- [ ] 复用了现有模块
- [ ] 添加了工具分组（如适用）
- [ ] 编写了测试用例
- [ ] 更新了文档
- [ ] 向后兼容性验证

### 7.2 代码风格约定

1. **导入顺序**：
   ```python
   # 标准库
   import asyncio
   from pathlib import Path

   # 第三方库
   import docker

   # 本地模块
   from ..core import engine
   from .tools import fn_registry
   ```

2. **异常处理**：
   ```python
   # 使用自定义异常
   from fastreact.core.exceptions import ToolNotFoundError

   try:
       tool = self.get_tool(name)
   except ToolNotFoundError as e:
       logger.error(f"Tool not found: {name}")
       raise
   ```

3. **日志记录**：
   ```python
   from fastreact.utils.logger import get_logger

   logger = get_logger(__name__)
   logger.info("Information message")
   logger.warning("Warning message")
   logger.error("Error message")
   ```

### 7.3 性能优化建议

1. **使用异步**：所有 I/O 操作必须异步
2. **启用缓存**：默认启用 LRU 缓存
3. **并发执行**：工具调用支持并发
4. **流式响应**：长时间任务使用流式输出
5. **上下文修剪**：大对话使用智能修剪

### 7.4 安全注意事项

1. **系统工具**：`bash` 等系统工具默认禁用（DENY_ALL 策略）
2. **沙箱隔离**：不可信代码必须在沙箱中执行
3. **输入验证**：所有用户输入必须验证
4. **敏感信息**：不在日志中输出 API Key 等敏感信息

---

## 八、快速参考

### 8.1 常用导入

```python
# 核心模块
from fastreact import FastReAct, StreamChunkType

# 配置系统
from fastreact.bootstrap.config_loader import (
    load_config,
    get_api_key,
    get_base_url,
    get_model,
)

# 工具系统
from fastreact.tools import (
    Tool,
    create_builtin_tools,
    create_xxx_tool,  # 你的工具
)

# 工具分组（V2）
from fastreact import (
    ToolGroup,
    GroupPolicy,
    ToolManager,
    get_global_manager,
)

# 沙箱系统
from fastreact.sandbox import (
    DockerSandbox,
    SandboxConfig,
    get_preset_config,
    SandboxPreset,
    create_config_with_mounts,
)
```

### 8.2 配置获取模式

```python
# 模式 1: 直接加载
config = load_config()
api_key = config["llm"]["api_key"]

# 模式 2: 使用辅助函数（推荐）
api_key = get_api_key(config)

# 模式 3: 带默认值
timeout = config.get("react", {}).get("timeout", 30)
```

### 8.3 工具创建模式

```python
# 工厂函数
def create_my_tool() -> Tool:
    async def execute(param: str) -> str:
        return f"Result: {param}"

    return Tool(
        name="my_tool",
        label="My Tool",
        description="工具描述",
        group="category",  # 必须设置
        parameters={...},
        execute=execute,
    )

# 注册到内置工具
def create_builtin_tools(config):
    tools = [...]
    tools.append(create_my_tool())
    return tools
```

---

## 九、版本更新说明

### V2 新特性（当前版本）

1. **流式响应** (`core/streaming.py`)
   - 实时输出 `<thinking>` 和工具调用
   - 支持 SSE 和 WebSocket
   - CLI `--stream` 选项

2. **工具分组** (`core/tool_group.py`, `core/tool_manager.py`)
   - 8 个预定义分组
   - 基于分组的访问控制
   - 灵活的政策系统

3. **Docker 沙箱增强** (`sandbox/config.py`)
   - 预设配置（SAFE, STANDARD, PERFORMANCE）
   - 挂载点支持
   - 网络隔离模式
   - 完整测试套件

### 向后兼容性

- ✅ V1 API 完全兼容
- ✅ 所有现有工具继续工作
- ✅ 配置文件向后兼容

---

## 十、总结

**记住这些核心原则**：

1. ✅ **配置驱动** - 一切可配置
2. ✅ **禁止硬编码** - 使用配置系统
3. ✅ **复用优先** - 检查现有模块
4. ✅ **工具分组** - 归类管理工具
5. ✅ **测试覆盖** - 每个功能都有测试

**在编写代码前**：
- 搜索现有代码库
- 查看配置系统
- 检查是否有类似工具
- 阅读相关模块文档

**在提交代码前**：
- 运行测试套件
- 验证配置加载
- 检查向后兼容性
- 更新相关文档

---

**文档版本**: 1.0.0
**最后更新**: 2026-02-03
**维护者**: FastReAct Team
