# FastReAct Nano v2.0

**真正独立的AI Agent** - 基于Nanobot哲学的极简ReAct实现

## 特性

- **双层循环**: Moltbot风格的内层/外层循环架构
- **极简工具**: Pi哲学，只有4个核心工具
- **Skills系统**: Markdown渐进式披露
- **完全独立**: 无需依赖老FastReact的基础设施
- **轻量级**: 3,178行代码

## 快速开始

### 安装

```bash
cd fastreact-nano
pip install -e .
```

### 使用

```python
# 最简单的方式
from fastreact import ask_sync

response = ask_sync("What can you do?")
print(response)
```

```python
# 完整控制
from fastreact import Agent

agent = Agent()
response = await agent.run(
    "用git workflow创建一个新分支",
    skills=["git_workflow"]
)
```

## 架构

```
fastreact-nano/
├── src/fastreact/
│   ├── core/           # 核心模块
│   │   ├── messages.py   # 消息系统
│   │   ├── callbacks.py  # 回调系统
│   │   ├── react.py      # ReAct双层循环
│   │   ├── tools.py      # 工具基类
│   │   ├── config.py     # 配置管理
│   │   └── streaming.py  # 流式输出
│   ├── tools/          # 4个核心工具
│   │   ├── read_file.py
│   │   ├── write_file.py
│   │   ├── exec.py
│   │   └── edit_file.py
│   ├── skills/         # Skills系统
│   │   ├── base.py
│   │   ├── parser.py
│   │   └── loader.py
│   ├── providers/      # LLM provider
│   └── agent.py        # 完整Agent
└── skills/            # 内置skills
    ├── file_ops/
    ├── code_review/
    └── git_workflow/
```

## 环境变量

```bash
export FASTRACT_MODEL=gpt-4o-mini
export FASTRACT_API_KEY=your-api-key
export FASTRACT_MAX_ITERATIONS=20
export FASTRACT_ENABLE_STEERING=true
export FASTRACT_ENABLE_FOLLOWUP=true
```

## 与老FastReact的区别

| 特性 | 老FastReact | FastReAct Nano |
|------|------------|----------------|
| 架构 | Gateway + Channels + Bus | 直接Python进程 |
| 代码量 | 大型 | 3,178行 |
| 依赖 | 复杂 | 最小化 |
| 部署 | 需要WebSocket服务器 | 直接运行 |
| Skills | 插件系统 | Markdown文件 |

## 测试

```bash
pytest tests/unit/ -v
```

## License

MIT
