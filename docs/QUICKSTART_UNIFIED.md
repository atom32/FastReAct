# FastReAct 快速开始指南

> **最后更新**: 2026-01-30
> **版本**: v0.3.0

本指南帮助你在 5 分钟内快速上手 FastReAct。

## 目录

1. [环境准备](#环境准备)
2. [基础配置](#基础配置)
3. [第一个示例](#第一个示例)
4. [功能指南](#功能指南)
5. [常见问题](#常见问题)

---

## 环境准备

### 系统要求

- **Python**: 3.10+
- **操作系统**: Windows, macOS, Linux
- **Docker** (可选): 用于沙箱功能
- **内存**: 建议 4GB+

### 安装

```bash
# 克隆项目
git clone https://github.com/atom32/FastReAct.git
cd FastReAct

# 安装依赖
pip install -r requirements.txt

# 可选：安装 Docker
# Windows/Mac: 下载 Docker Desktop
# Linux: sudo apt install docker.io
```

---

## 基础配置

### 创建配置文件

创建 `config.json`:

```json
{
  "llm": {
    "providers": {
      "siliconflow": {
        "enabled": true,
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key": "your-api-key-here",
        "model": "deepseek-ai/DeepSeek-V3"
      }
    },
    "default_provider": "siliconflow"
  },
  "react": {
    "max_iterations": 10,
    "enable_cache": true
  },
  "tools": {
    "builtin_enabled": true
  }
}
```

### 获取 API Key

**选项 1: SiliconFlow** (推荐，性价比高)
1. 访问 [https://siliconflow.cn](https://siliconflow.cn)
2. 注册账号
3. 获取 API Key
4. 替换配置文件中的 `your-api-key-here`

**选项 2: OpenAI**
1. 访问 [https://platform.openai.com](https://platform.openai.com)
2. 生成 API Key
3. 更新配置文件

### 可选：Tavily 搜索配置

如需使用搜索功能，配置 Tavily API Key:

1. 访问 [https://tavily.com](https://tavily.com) 注册（免费 1000 次/月）
2. 获取 API Key
3. 在 `config.json` 中添加：

```json
{
  "tools": {
    "tavily": {
      "api_key": "tvly-your-key-here"
    }
  }
}
```

---

## 第一个示例

### 示例 1: 基础工具调用

创建 `first_example.py`:

```python
import asyncio
import json
from fastreact import FastReAct
from fastreact.tools import create_calculator_tool, create_datetime_tool

async def main():
    # 加载配置
    with open("config.json") as f:
        config = json.load(f)

    provider = config["llm"]["default_provider"]
    llm_config = config["llm"]["providers"][provider]

    # 创建 Agent
    agent = FastReAct(
        api_key=llm_config["api_key"],
        base_url=llm_config["base_url"],
        model=llm_config["model"],
        tools=[
            create_calculator_tool(),
            create_datetime_tool()
        ]
    )

    # 提问
    result = await agent.run_async("现在是几点？计算 100 * 25")

    print(f"答案: {result['answer']}")
    await agent.close()

asyncio.run(main())
```

运行：
```bash
python first_example.py
```

### 示例 2: 沙箱代码执行

```python
from fastreact.tools.sandbox_tools import create_sandbox_exec_tool

agent = FastReAct(
    api_key="your-api-key",
    base_url="https://api.siliconflow.cn/v1",
    model="deepseek-ai/DeepSeek-V3",
    tools=[create_sandbox_exec_tool()]
)

result = await agent.run_async("""
用 Python 计算斐波那契数列的前 10 项
""")

print(result['answer'])
```

---

## 功能指南

### 1. ReACT 工具调用

FastReAct 自动选择合适的工具：

```python
# 内置工具
from fastreact.tools import (
    create_calculator_tool,      # 计算器
    create_datetime_tool,        # 日期时间
    create_sandbox_exec_tool,    # Docker 沙箱
    create_search_tool           # 搜索
)
```

### 2. 自定义工具

```python
from fastreact.tools.fn_registry import Tool

async def my_tool(param: str) -> str:
    return f"处理: {param}"

tool = Tool(
    name="my_tool",
    label="My Tool",
    description="工具描述",
    parameters={
        "type": "object",
        "properties": {
            "param": {"type": "string"}
        }
    },
    execute=my_tool
)
```

### 3. GraphRAG 集成

详细指南: [GRAPHrag_INTEGRATION.md](GRAPHrag_INTEGRATION.md)

### 4. MCP 客户端

详细指南: [MCP_CLIENT_GUIDE.md](MCP_CLIENT_GUIDE.md)

### 5. Bootstrap 配置

详细指南: [BOOTSTRAP_GUIDE.md](BOOTSTRAP_GUIDE.md)

---

## 常见问题

### Q1: Docker 沙箱无法使用

**错误**: `Failed to connect to Docker`

**解决**:
1. 确保 Docker 已安装并运行
2. 检查: `docker info`

### Q2: API Key 无效

**错误**: `Error code: 401`

**解决**:
1. 检查 `config.json` 中的 API Key
2. 确认账户有足够余额

### Q3: 模块导入错误

**错误**: `ModuleNotFoundError`

**解决**:
```bash
pip install -e .
```

### Q4: 需要全部功能吗？

不需要！核心功能只需计算器、时间工具即可：

```bash
python examples/01_basic.py  # 基础演示
```

---

## 下一步

- 📖 [完整示例](../examples/) - 更多代码示例
- 🏗️ [架构文档](ARCHITECTURE.md) - 深入了解架构
- 📊 [功能对比](FEATURES_COMPARISON.md) - 与其他框架对比
- 🗺️ [改进路线图](IMPROVEMENT_ROADMAP.md) - 未来规划

---

## 获取帮助

- 查看 [文档索引](DOCS_INDEX.md)
- 提交 [Issue](https://github.com/atom32/FastReAct/issues)
- 加入讨论区

祝你使用愉快！🚀
