# FastReAct 使用指南

**版本**: v1.0.0
**最后更新**: 2026-02-02

---

## 📚 目录

1. [快速开始](#快速开始)
2. [基础用法](#基础用法)
3. [高级功能](#高级功能)
4. [配置指南](#配置指南)
5. [完整示例](#完整示例)
6. [最佳实践](#最佳实践)

---

## 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/atom32/FastReAct.git
cd FastReAct

# 安装依赖
pip install -r requirements.txt

# 可选：安装 Docker (用于沙箱功能)
# Windows/Mac: 下载 Docker Desktop
```

### 最简单的例子

```python
from fastreact import FastReAct

# 创建 Agent
agent = FastReAct(
    api_key="your-api-key",
    base_url="https://api.siliconflow.cn/v1",
    model="deepseek-ai/DeepSeek-V3"
)

# 运行
result = agent.run("帮我计算 25 * 34")
print(result["answer"])
```

**输出**:
```
850
```

---

## 基础用法

### 1. 使用内置工具

```python
from fastreact import FastReAct
from fastreact.tools import (
    create_calculator_tool,
    create_datetime_tool,
    create_sandbox_exec_tool
)

agent = FastReAct(
    api_key="your-api-key",
    base_url="https://api.siliconflow.cn/v1",
    model="deepseek-ai/DeepSeek-V3",
    tools=[
        create_calculator_tool(),
        create_datetime_tool(),
        create_sandbox_exec_tool()  # Docker 沙箱执行
    ]
)

# 提问
result = agent.run(
    "现在几点？计算 100 * 25，然后在沙箱中执行 ls 命令"
)
```

### 2. 自定义工具（函数式）

```python
from fastreact.tools.fn_registry import Tool

async def search_wikipedia(query: str) -> str:
    """搜索 Wikipedia"""
    # 实现搜索逻辑
    return f"搜索结果: {query}"

search_tool = Tool(
    name="wikipedia_search",
    label="Wikipedia Search",
    description="搜索 Wikipedia 知识库",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词"
            }
        },
        "required": ["query"]
    },
    execute=search_wikipedia
)

agent = FastReAct(
    api_key="your-api-key",
    tools=[search_tool]
)
```

### 3. 沙箱代码执行

```python
from fastreact.tools.sandbox_tools import create_sandbox_exec_tool

agent = FastReAct(
    api_key="your-api-key",
    tools=[create_sandbox_exec_tool()]
)

result = agent.run("""
请编写 Python 代码计算斐波那契数列的前 10 项，
然后在沙箱中执行它。
""")
```

---

## 高级功能

### 1. Context Pruning（智能剪枝）

自动减少 40-60% 的 token 使用：

```python
from fastreact.context import ContextConfig, PruningConfig

# 创建配置
context_config = ContextConfig(
    max_history_tokens=48000,
    smart_truncate=True,
    pruning=PruningConfig(
        enabled=True,
        target_ratio=0.5,  # 减少到 50%
        min_messages=10,
        tool_result_max_lines=50
    )
)

agent = FastReAct(
    api_key="your-api-key",
    context_config=context_config
)
```

### 2. Tool Policy（工具策略）

安全控制工具访问：

```python
from fastreact.core import (
    ToolPolicy,
    ToolPolicyConfig,
    ToolPolicyRule,
    RiskLevel,
    PolicyMode
)

# 创建策略
policy_config = ToolPolicyConfig(
    mode=PolicyMode.PERMISSIVE,  # 或 RESTRICTIVE, CUSTOM
    deny_list=["dangerous_*", "rm_*"],
    rules=[
        ToolPolicyRule(
            pattern="bash*",
            risk_level=RiskLevel.HIGH,
            requires_approval=True
        )
    ]
)

policy = ToolPolicy(policy_config)

# 检查工具是否可以执行
decision = policy.check_tool_access("bash", {"command": "ls"})
if decision.allowed:
    print("工具允许执行")
else:
    print(f"工具被拒绝: {decision.reason}")
```

### 3. Exec Approvals（执行审批）

用户确认危险操作：

```python
from fastreact.core import (
    ApprovalManager,
    ApprovalConfig,
    ApprovalMode
)

# 创建审批管理器
approval_config = ApprovalConfig(
    mode=ApprovalMode.ASK_HIGH_RISK,  # 仅高风险需审批
    default_timeout=60
)

approval = ApprovalManager(approval_config)

# 设置用户输入回调
def user_callback(request):
    print(f"\n⚠️  工具执行请求:")
    print(f"   工具: {request.tool_name}")
    print(f"   风险: {request.risk_level.name}")
    print(f"   参数: {request.parameters}")

    response = input("允许执行? (y/n): ")
    return ApprovalResponse.ALLOW if response.lower() == 'y' else ApprovalResponse.DENY

approval.set_user_input_callback(user_callback)

# 请求审批
decision = approval.request_approval(
    tool_name="bash",
    parameters={"command": "rm -rf /tmp"},
    policy_decision=policy_decision
)

if decision.is_allowed:
    # 执行工具
    pass
```

### 4. Tool Display（友好显示）

美化工具输出：

```python
from fastreact.core import ToolDisplay, DisplayConfig, DisplayMode

# 创建显示配置
display_config = DisplayConfig(
    mode=DisplayMode.NORMAL,  # MINIMAL, NORMAL, VERBOSE
    use_colors=True,
    show_time=True,
    show_risk=True
)

display = ToolDisplay(display_config)

# 格式化工具调用
print(display.format_tool_call(
    tool_name="bash",
    parameters={"command": "ls -la"},
    risk_level="MEDIUM"
))

# 输出:
# 🔧 bash
#   ├─ command: ls -la
#   ├─ Risk: MEDIUM

# 格式化结果
print(display.format_result(
    tool_name="bash",
    result="file1.txt\nfile2.txt",
    execution_time=0.5
))

# 输出:
# ✅ Status: Success (0.50s)
# └─ Result:
#   file1.txt
#   file2.txt
```

### 5. 使用 Context Manager 追踪工具调用

```python
# 自动追踪和显示
with display.track_call("bash", {"command": "ls"}, risk_level="LOW") as info:
    # 执行工具
    result = execute_bash("ls")
    info.status = "success"
    info.result = result

# 自动输出:
# 🔧 bash
#   ├─ command: ls
#   ├─ Risk: LOW
# ✅ Status: Success (0.10s)
# └─ Result: ...
```

---

## 配置指南

### config.json 完整示例

```json
{
  "llm": {
    "providers": {
      "siliconflow": {
        "enabled": true,
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key": "your-api-key",
        "model": "deepseek-ai/DeepSeek-V3"
      },
      "openai": {
        "enabled": false,
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4"
      }
    },
    "default_provider": "siliconflow"
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
    "system_prompt_tokens": 2000,
    "token_model": "gpt-4",
    "smart_truncate": true,

    "memory_flush": {
      "enabled": false,
      "soft_threshold_tokens": 50000,
      "hard_threshold_tokens": 55000
    },

    "pruning": {
      "enabled": true,
      "target_ratio": 0.5,
      "min_messages": 10,
      "tool_result_max_lines": 50
    },

    "retrieval": {
      "enabled": false,
      "provider": "modelscope",
      "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
      "top_k": 3,
      "hybrid_search": {
        "enabled": true,
        "fusion_method": "rrf"
      }
    },

    "compaction": {
      "enabled": false,
      "base_chunk_ratio": 0.4,
      "summary_levels": 3
    }
  },

  "tools": {
    "builtin_enabled": true,
    "available_tools": [
      "Calculator",
      "DateTime",
      "Sandbox",
      "TavilySearch"
    ]
  },

  "tool_policy": {
    "mode": "permissive",
    "deny_list": ["rm_*", "format*"],
    "rules": [
      {
        "pattern": "bash*",
        "risk_level": "high",
        "allowed": true,
        "requires_approval": true
      }
    ]
  },

  "approval": {
    "mode": "ask_high_risk",
    "default_timeout": 60,
    "auto_approve_list": ["read_*", "list_*"],
    "auto_deny_list": ["delete_*", "format_*"]
  },

  "display": {
    "mode": "normal",
    "use_colors": true,
    "show_time": true,
    "show_risk": true,
    "max_result_lines": 50
  }
}
```

---

## 完整示例

### 示例 1: Coding Agent

```python
from fastreact import FastReAct
from fastreact.tools import (
    create_bash_tool,
    create_edit_file_tool,
    create_repo_map_tool
)

# 配置
config = {
    "context": {
        "pruning": {"enabled": True},
        "tool_policy": {
            "mode": "permissive",
            "deny_list": ["rm_*"]
        },
        "approval": {
            "mode": "ask_high_risk"
        }
    }
}

# 创建 Coding Agent
agent = FastReAct(
    api_key="your-api-key",
    base_url="https://api.siliconflow.cn/v1",
    model="deepseek-ai/DeepSeek-V3",
    tools=[
        create_bash_tool(),
        create_edit_file_tool(),
        create_repo_map_tool()
    ],
    config=config
)

# 使用 Agent
result = agent.run("""
帮我查看项目结构，然后找到所有的 TODO 注释，
最后生成一个待办事项列表。
""")
```

### 示例 2: 带审批的 Agent

```python
from fastreact import FastReAct
from fastreact.core import ApprovalManager, ApprovalConfig, ApprovalMode

# 创建审批管理器
approval = ApprovalManager(ApprovalConfig(mode=ApprovalMode.ASK_HIGH_RISK))

# 设置回调
def get_user_approval(request):
    print(f"\n{'='*60}")
    print(f"工具执行请求: {request.tool_name}")
    print(f"风险等级: {request.risk_level.name}")
    print(f"参数: {request.parameters}")
    print(f"{'='*60}")

    while True:
        response = input("允许执行? (y/n/v=查看详情): ").lower()
        if response == 'y':
            return ApprovalResponse.ALLOW
        elif response == 'n':
            return ApprovalResponse.DENY
        elif response == 'v':
            print(f"详细信息: {request.context}")
        else:
            print("请输入 y/n/v")

approval.set_user_input_callback(get_user_approval)

# 创建 Agent
agent = FastReAct(
    api_key="your-api-key",
    approval_manager=approval
)

# 运行（危险操作会询问用户）
result = agent.run("删除所有 .pyc 文件")
```

### 示例 3: 知识库问答

```python
from fastreact import FastReAct
from fastreact.context import ContextConfig, RetrievalConfig

# 配置检索
context_config = ContextConfig(
    retrieval=RetrievalConfig(
        enabled=True,
        provider="modelscope",
        embedding_model="Qwen/Qwen3-Embedding-0.6B",
        top_k=3,
        hybrid_search={
            "enabled": True,
            "fusion_method": "rrf"
        }
    )
)

# 创建带知识库的 Agent
agent = FastReAct(
    api_key="your-api-key",
    context_config=context_config
)

# 第一次对话（会自动索引）
agent.run("FastReAct 的核心特性是什么？")

# 第二次对话（会从知识库检索相关历史）
agent.run("它支持哪些工具？")
```

---

## 最佳实践

### 1. 安全性

**始终使用 Tool Policy**:
```python
from fastreact.core import ToolPolicy, PolicyMode

policy = ToolPolicy(
    ToolPolicyConfig(
        mode=PolicyMode.RESTRICTIVE,
        allow_list=["bash", "ls", "grep", "cat"]
    )
)
```

**启用审批**:
```python
approval = ApprovalManager(
    ApprovalConfig(
        mode=ApprovalMode.ASK_HIGH_RISK
    )
)
```

### 2. 性能优化

**启用 Context Pruning**:
```python
context_config = ContextConfig(
    pruning=PruningConfig(enabled=True)
)
```

**使用缓存**:
```python
agent = FastReAct(
    api_key="your-api-key",
    enable_cache=True
)
```

### 3. 可观测性

**使用 Tool Display**:
```python
display = ToolDisplay(
    DisplayConfig(
        mode=DisplayMode.VERBOSE,
        show_time=True
    )
)
```

**启用事件流**:
```python
agent = FastReAct(
    api_key="your-api-key",
    enable_event_stream=True,
    event_callback=lambda event: print(f"Event: {event.type}")
)
```

### 4. 错误处理

```python
from fastreact.core.exceptions import ToolNotFoundError, RetryableError

try:
    result = agent.run("执行某个任务")
except ToolNotFoundError as e:
    print(f"工具未找到: {e.tool_name}")
except RetryableError as e:
    print(f"可重试错误: {e.message}")
    # 自动重试
    result = agent.run("重试任务")
```

---

## 常见问题

### Q: 如何支持自定义 LLM？

```python
agent = FastReAct(
    api_key="your-key",
    base_url="https://your-llm-api.com/v1",
    model="your-model-name"
)
```

### Q: 如何限制 token 使用？

```python
context_config = ContextConfig(
    max_history_tokens=16000,  # 限制历史 token
    pruning=PruningConfig(
        enabled=True,
        target_ratio=0.5
    )
)
```

### Q: 如何调试工具调用？

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 使用 Tool Display
display = ToolDisplay(DisplayConfig(mode=DisplayMode.VERBOSE))
```

### Q: 如何持久化缓存？

```python
# 即将支持
from fastreact.memory import PersistentEmbeddingCache

cache = PersistentEmbeddingCache(db_path="./cache/embeddings.db")
```

---

## 下一步

- 查看 [examples/](../examples/) 目录了解更多示例
- 阅读 [ARCHITECTURE.md](ARCHITECTURE.md) 了解架构
- 查看 [TODO.md](../TODO.md) 了解开发路线

---

**维护者**: FastReAct Team
**文档版本**: v1.0.0
