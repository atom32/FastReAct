# FastReAct 快速开始

**5 分钟上手 FastReAct - 企业级 Agent 基础设施框架**

---

## 🚀 安装

```bash
# 1. 克隆项目
git clone https://github.com/atom32/FastReAct.git
cd FastReAct

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key
cp config.example.json config.json
# 编辑 config.json，填入你的 API Key
```

---

## ⚡ 30 秒运行第一个 Agent

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

## 📚 三种使用方式

### 方式 1: 基础 Agent

```python
from fastreact import FastReAct

agent = FastReAct(
    api_key="your-api-key",
    model="deepseek-ai/DeepSeek-V3"
)

agent.run("今天天气怎么样？")
```

### 方式 2: 带工具的 Agent

```python
from fastreact import FastReAct
from fastreact.tools import (
    create_calculator_tool,
    create_datetime_tool,
    create_sandbox_exec_tool
)

agent = FastReAct(
    api_key="your-api-key",
    tools=[
        create_calculator_tool(),
        create_datetime_tool(),
        create_sandbox_exec_tool()
    ]
)

agent.run("现在几点？计算 100 * 25")
```

### 方式 3: Coding Agent（完整功能）

```python
from fastreact import FastReAct
from fastreact.tools import (
    create_bash_tool,
    create_edit_file_tool,
    create_repo_map_tool
)
from fastreact.context import ContextConfig, PruningConfig
from fastreact.core import ToolPolicy, PolicyMode

# 配置上下文剪枝
context_config = ContextConfig(
    pruning=PruningConfig(enabled=True)
)

# 配置工具策略
policy = ToolPolicy(
    ToolPolicyConfig(
        mode=PolicyMode.PERMISSIVE,
        deny_list=["rm_*", "format*"]
    )
)

# 创建 Coding Agent
agent = FastReAct(
    api_key="your-api-key",
    tools=[
        create_bash_tool(),
        create_edit_file_tool(),
        create_repo_map_tool()
    ],
    context_config=context_config,
    policy=policy
)

# 使用
agent.run("帮我查看项目结构，找出所有 TODO")
```

---

## 🎯 核心功能速查

| 功能 | 代码示例 |
|------|----------|
| **沙箱执行** | `create_sandbox_exec_tool()` |
| **代码编辑** | `create_edit_file_tool()` |
| **仓库地图** | `create_repo_map_tool()` |
| **Shell 命令** | `create_bash_tool()` |
| **上下文剪枝** | `ContextConfig(pruning=PruningConfig(enabled=True))` |
| **工具策略** | `ToolPolicy(ToolPolicyConfig(mode=PolicyMode.PERMISSIVE))` |
| **执行审批** | `ApprovalManager(ApprovalConfig(mode=ApprovalMode.ASK_HIGH_RISK))` |

---

## 📖 配置文件示例

创建 `config.json`:

```json
{
  "llm": {
    "providers": {
      "siliconflow": {
        "enabled": true,
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key": "your-api-key",
        "model": "deepseek-ai/DeepSeek-V3"
      }
    }
  },
  "context": {
    "pruning": {
      "enabled": true,
      "target_ratio": 0.5
    }
  },
  "tool_policy": {
    "mode": "permissive",
    "deny_list": ["rm_*"]
  }
}
```

使用配置文件:

```python
from fastreact import FastReAct
from fastreact.bootstrap import load_config

config = load_config("config.json")
agent = FastReAct.from_config(config)
```

---

## 🎓 示例代码

查看 `examples/` 目录：

| 示例 | 说明 |
|------|------|
| [01_basic.py](../examples/01_basic.py) | 基础 ReACT 使用 |
| [02_async_concurrent.py](../examples/02_async_concurrent.py) | 异步并发 |
| [03_custom_tools.py](../examples/03_custom_tools.py) | 自定义工具 |
| [08_context_pruning_demo.py](../examples/08_context_pruning_demo.py) | 上下文剪枝 |
| [09_tool_policy_demo.py](../examples/09_tool_policy_demo.py) | 工具策略 |
| [10_approval_demo.py](../examples/10_approval_demo.py) | 执行审批 |
| [11_tool_display_demo.py](../examples/11_tool_display_demo.py) | 工具显示 |

运行示例：

```bash
python examples/01_basic.py
```

---

## 💡 常见用例

### 1. 代码助手

```python
agent = FastReAct(
    api_key="your-api-key",
    tools=[create_bash_tool(), create_edit_file_tool()]
)

agent.run("帮我找到所有的 TODO 注释")
```

### 2. 数据分析

```python
agent = FastReAct(
    api_key="your-api-key",
    tools=[create_sandbox_exec_tool()]
)

agent.run("分析 data.csv 文件，生成统计报告")
```

### 3. 知识库问答

```python
from fastreact.context import RetrievalConfig

agent = FastReAct(
    api_key="your-api-key",
    context_config=ContextConfig(
        retrieval=RetrievalConfig(enabled=True)
    )
)

agent.run("根据之前的对话，总结一下项目目标")
```

---

## ⚙️ 高级配置

### 启用所有功能

```python
from fastreact import FastReAct
from fastreact.context import ContextConfig, PruningConfig
from fastreact.core import ToolPolicy, ApprovalManager, ToolDisplay

# 上下文剪枝
context_config = ContextConfig(
    pruning=PruningConfig(
        enabled=True,
        target_ratio=0.5
    )
)

# 工具策略
policy = ToolPolicy(
    ToolPolicyConfig(
        mode=PolicyMode.PERMISSIVE,
        deny_list=["dangerous_*"]
    )
)

# 执行审批
approval = ApprovalManager(
    ApprovalConfig(mode=ApprovalMode.ASK_HIGH_RISK)
)

# 工具显示
display = ToolDisplay()

# 创建完整功能的 Agent
agent = FastReAct(
    api_key="your-api-key",
    context_config=context_config,
    policy=policy,
    approval=approval,
    display=display
)
```

---

## 🛠️ 故障排查

### 问题 1: 模块未找到

```bash
# 确保从项目根目录运行
cd FastReAct
python your_script.py
```

### 问题 2: API Key 错误

```python
# 检查 config.json 中的 api_key
agent = FastReAct(
    api_key="sk-...",  # 确保正确
    base_url="https://api.siliconflow.cn/v1"
)
```

### 问题 3: Docker 沙箱无法使用

```bash
# 确保 Docker 正在运行
docker ps

# Windows: 确保 Docker Desktop 运行
# Mac: 确保 Docker Desktop 运行
# Linux: sudo systemctl start docker
```

---

## 📚 更多资源

- **[完整使用指南](USAGE_GUIDE.md)** - 详细的使用文档
- **[架构文档](ARCHITECTURE.md)** - 系统架构和设计
- **[优化分析](OPTIMIZATION_ANALYSIS.md)** - 性能优化建议
- **[更新日志](../CHANGELOG.md)** - 版本历史

---

## 🆘 获取帮助

- GitHub Issues: [https://github.com/atom32/FastReAct/issues](https://github.com/atom32/FastReAct/issues)
- 文档: [docs/](./) 目录
- 示例: [examples/](../examples/) 目录

---

**版本**: v1.0.0
**最后更新**: 2026-02-02
