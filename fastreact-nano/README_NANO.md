# FastReAct Nano v2.0

**极简AI Agent - 内核 + 适配器架构**

```
内核: 2,847行核心代码
适配器: 可选的交互层
哲学: 按需使用，快速启动
```

## ⚡ 快速开始

### 最小安装 (核心)

```bash
pip install fastreact-nano
```

```python
from fastreact import ask_sync

response = ask_sync("分析这个代码库")
print(response)
```

### CLI使用

```bash
pip install fastreact-nano[cli]
fastreact "分析这个代码库"
fastreact interactive  # 交互模式
```

### HTTP服务

```bash
pip install fastreact-nano[http]
python -m fastreact.adapters.http
# 访问 http://localhost:8000
```

### WebSocket Gateway

```bash
pip install fastreact-nano[gateway]
python -m fastreact.adapters.gateway
# 访问 http://localhost:9000
```

## 📦 架构

```
┌─────────────────────────────────────┐
│    用户接口 (可选适配器)              │
│  CLI | HTTP | WebSocket | Gateway   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│     FastReAct Nano Kernel           │
│     (2,847 lines, minimal deps)     │
│                                     │
│  • ReActCore (双层循环)             │
│  • 4 Tools (Pi哲学)                 │
│  • Skills (Markdown渐进式)          │
│  • Config (环境变量)                │
│  • Agent (完整实现)                 │
└──────────────┬──────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼────┐         ┌─────▼────┐
│ LiteLLM │         │  Skills  │
└─────────┘         └──────────┘
```

## 🛠️ 核心工具

- **read_file** - 读取文件 (支持行范围)
- **write_file** - 写入文件 (原子操作)
- **exec** - 执行Shell命令 (跨平台)
- **edit_file** - 文本替换编辑

## 📚 内置Skills

- **file_ops** - 高级文件操作
- **code_review** - 代码质量分析
- **git_workflow** - Git工作流

## ⚙️ 配置

```bash
# 环境变量
export FASTRACT_MODEL=gpt-4o-mini
export FASTRACT_API_KEY=sk-xxx
export FASTRACT_MAX_ITERATIONS=20
```

```python
# Python配置
from fastreact import Config, Agent

config = Config()
config.llm.model = "gpt-4o"

agent = Agent(config=config)
```

## 📖 文档

- [USAGE.md](USAGE.md) - 完整使用指南
- [PROJECT_STATUS.md](PROJECT_STATUS.md) - 项目现状分析

## 🚀 使用示例

```python
# 最简单
from fastreact import ask_sync
response = ask_sync("分析代码")

# 完整控制
import asyncio
from fastreact import Agent

async def main():
    agent = Agent()
    response = await agent.run(
        "创建git分支",
        skills=["git_workflow"]
    )
    print(response)

asyncio.run(main())
```

## 📊 依赖管理

```bash
# 核心 (必需)
pip install fastreact-nano

# CLI适配器
pip install fastreact-nano[cli]

# HTTP适配器
pip install fastreact-nano[http]

# Gateway适配器
pip install fastreact-nano[gateway]

# 全功能
pip install fastreact-nano[all]
```

## 🧪 测试

```bash
pip install fastreact-nano[dev]
pytest tests/ -v
```

## 📝 License

MIT

---

**FastReAct Nano - 极简、快速、强大** ⚡
