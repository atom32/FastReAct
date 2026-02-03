# FastReAct

> **企业级 Agent 基础设施框架** - 开箱即用，生产就绪 🚀

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version: 1.0.0](https://img.shields.io/badge/version-1.0.0-brightgreen.svg)](https://github.com/atom32/FastReAct)
[![Production Ready](https://img.shields.io/badge/production--ready-brightgreen.svg)]()

---

## 项目概述

**FastReAct** 是一个企业级的 ReAct (Reasoning and Acting) Agent 基础设施框架，目标是让 AI Agent 开发更简单、更快速。项目定位为 **"Bring Your Own Model & Data"**，让企业用 1/10 的成本获得 80% 的 Claude Code 体验。

### 核心价值

- **隐私优先**: 完全离线、本地化部署，数据永不离开基础设施
- **模型灵活**: 支持任何 LLM（DeepSeek、GPT-4o-mini、本地 7B/14B 模型）
- **成本优化**: 高级 token 管理、本地嵌入、智能缓存
- **可定制**: 为特定业务需求定义自己的工具集

---

## 🎯 30 秒快速开始

```bash
# 1. 克隆项目
git clone https://github.com/atom32/FastReAct.git
cd FastReAct

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 API Key（可选，也可在 config.json 中配置）
export FASTREACT_API_KEY=your-api-key

# 4. 运行
python -m fastreact.cli.main run "帮我计算 25 * 34"
```

**输出**: `850`

---

## ✨ 核心特性

### 🚀 开箱即用
- **3 命令启动**: 安装 → 配置 → 运行
- **自动配置**: 从 config.json 或环境变量加载
- **Docker 支持**: 一键部署完整系统
- **CLI 工具**: `python -m fastreact.cli.main chat` 交互式对话

### 🧠 企业级上下文管理
- **Token 计数**: 精确计数，<1ms 延迟
- **智能剪枝**: 减少 40-60% token 使用
- **混合检索**: BM25 + Semantic + RRF
- **渐进压缩**: 4 级压缩（100% → 54% → 52% → 30%）
- **记忆刷新**: 自动总结长对话（压缩比 99.5%）

### 🔒 安全与控制
- **工具策略**: Allow/Deny 列表，风险等级
- **执行审批**: 高风险工具需要用户确认
- **智能重试**: 区分可重试和不可重试错误
- **去重机制**: 防止重复调用（10 秒窗口）

### 📊 完整工具系统
- **内置工具**: Calculator, TavilySearch, Weather, HTTP, Shell, Edit File
- **工具结果截断**: Smart Truncation，防止 Context 爆炸
- **持久化 Shell**: 会话保持
- **MCP 协议**: 完整的 Model Context Protocol 支持

### ⚡ 性能优化
- **异步并发**: 最多同时执行 3 个工具
- **LRU 缓存**: 1000 条缓存，提升 15-25% 命中率
- **连接池复用**: httpx.AsyncClient
- **流式响应**: 支持实时输出

### 🌐 多平台集成
- **WebSocket Gateway**: 实时双向通信
- **多渠道支持**: WeChat, Telegram, Slack
- **Bootstrap 配置**: 工作区管理（AGENTS.md, SOUL.md, TOOLS.md）

---

## 📖 使用方式

### 方式 1: CLI 命令行（推荐）

```bash
# 初始化工作区
python -m fastreact.cli.main init

# 交互式对话
python -m fastreact.cli.main chat

# 单次查询
python -m fastreact.cli.main run "What's the weather in Beijing?"

# 显示推理过程
python -m fastreact.cli.main run "Calculate 15 * 25 + 10" --show-thoughts

# 启动 Gateway 服务器
python -m fastreact.cli.main gateway start --port 8765
```

### 方式 2: Python API

```python
from fastreact import FastReAct

agent = FastReAct(
    api_key="your-api-key",
    base_url="https://api.siliconflow.cn/v1",
    model="deepseek-ai/DeepSeek-V3"
)

result = await agent.run_async("帮我计算 25 * 34")
print(result["answer"])
```

### 方式 3: Docker

```bash
# 使用 Docker Compose
docker-compose up

# 或手动构建
docker build -t fastreact .
docker run -it --env-file .env fastreact
```

---

## ⚙️ 配置

### 方式 1: 环境变量（推荐）

```bash
# .env 文件
FASTREACT_API_KEY=your-api-key
FASTREACT_BASE_URL=https://api.siliconflow.cn/v1
FASTREACT_MODEL=deepseek-ai/DeepSeek-V3
```

### 方式 2: config.json

项目根目录的 `config.json` 包含完整配置：

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
    },
    "default_provider": "siliconflow"
  },
  "context": {
    "max_history_messages": 1000,
    "max_history_tokens": 48000,
    "memory_flush": {
      "enabled": true,
      "soft_threshold_tokens": 50000,
      "hard_threshold_tokens": 55000
    },
    "retrieval": {
      "enabled": false,
      "provider": "modelscope",
      "embedding_model": "Qwen/Qwen3-Embedding-0.6B"
    }
  },
  "react": {
    "max_iterations": 10,
    "max_concurrent_tools": 3,
    "enable_cache": true
  }
}
```

### 方式 3: 代码配置

```python
from fastreact.context import ContextConfig, PruningConfig

config = ContextConfig(
    max_history_tokens=48000,
    pruning=PruningConfig(
        enabled=True,
        target_ratio=0.5
    )
)

agent = FastReAct(
    api_key="your-api-key",
    context_config=config
)
```

---

## 🎓 示例

| 示例 | 说明 |
|------|------|
| [examples/01_basic.py](examples/01_basic.py) | 基础 ReACT 使用 |
| [examples/02_async_concurrent.py](examples/02_async_concurrent.py) | 异步并发 |
| [examples/03_custom_tools.py](examples/03_custom_tools.py) | 自定义工具 |
| [examples/04_events_and_retry.py](examples/04_events_and_retry.py) | 事件流和重试 |
| [examples/06_context_management.py](examples/06_context_management.py) | 上下文管理 |
| [examples/08_context_pruning_demo.py](examples/08_context_pruning_demo.py) | 上下文剪枝 |
| [examples/09_tool_policy_demo.py](examples/09_tool_policy_demo.py) | 工具策略 |
| [examples/12_production_agent.py](examples/12_production_agent.py) | 生产级示例 |
| [examples/mcp_client_demo.py](examples/mcp_client_demo.py) | MCP 客户端 |
| [examples/streaming_demo.py](examples/streaming_demo.py) | 流式响应 |

---

## 🏗️ 项目结构

```
FastReAct/
├── src/fastreact/          # 核心源代码
│   ├── core/               # 核心引擎模块
│   │   ├── engine.py       # ReACT 引擎实现
│   │   ├── tool.py         # 工具基类
│   │   ├── tool_policy.py  # 工具策略
│   │   ├── approval.py     # 执行审批
│   │   ├── tool_display.py # 工具显示
│   │   ├── cache.py        # LRU 缓存
│   │   ├── config.py       # 核心配置
│   │   ├── callbacks.py    # 回调系统
│   │   └── exceptions.py   # 异常处理
│   ├── context/            # 上下文管理
│   │   ├── context_builder.py
│   │   ├── context_pruning.py
│   │   ├── token_counter.py
│   │   ├── config.py       # 上下文配置
│   │   └── compaction.py   # 上下文压缩
│   ├── tools/              # 工具系统
│   │   ├── fn_registry.py  # 函数注册表
│   │   ├── shell_tool.py   # Shell 工具
│   │   ├── edit_tool.py    # 文件编辑
│   │   ├── calculator.py   # 计算器
│   │   ├── search.py       # 搜索工具
│   │   └── http.py         # HTTP 工具
│   ├── agents/             # 智能体系统
│   │   ├── base.py         # 基础智能体
│   │   ├── router.py       # 路由器
│   │   └── specialized.py  # 专用智能体
│   ├── bootstrap/          # 配置加载
│   │   ├── config_loader.py
│   │   ├── loader.py
│   │   └── workspace.py    # 工作区管理
│   ├── channels/           # 通信渠道
│   │   ├── slack.py        # Slack 集成
│   │   ├── telegram.py     # Telegram 集成
│   │   └── wechat.py       # 微信集成
│   ├── gateway/            # 网关服务
│   ├── memory/             # 记忆系统
│   ├── observability/      # 可观测性
│   ├── utils/              # 工具函数
│   └── cli/                # 命令行工具
│       └── main.py         # CLI 入口
├── examples/               # 示例代码
├── tests/                  # 测试文件
├── docs/                   # 文档
├── config.json            # 配置文件
├── requirements.txt        # 依赖列表
├── pyproject.toml         # 项目配置
├── docker-compose.yml     # Docker 编排
└── README.md              # 项目说明
```

---

## 📚 文档

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - 系统架构详解
- **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - 快速入门指南
- **[docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md)** - 完整使用指南
- **[docs/DOCS_INDEX.md](docs/DOCS_INDEX.md)** - 文档索引

---

## 🔧 安装

### 方式 1: 自动安装（推荐）

```bash
# Linux/Mac
bash scripts/install.sh

# Windows
scripts\install.bat
```

### 方式 2: 手动安装

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置
cp .env.example .env
vim .env  # 添加 API Key

# 3. 运行
python -m fastreact.cli.main chat
```

### 方式 3: Docker

```bash
# 构建镜像
docker build -t fastreact .

# 运行
docker run -it --env-file .env fastreact
```

---

## 🎯 核心功能对比

| 特性 | FastReAct | LangChain | AutoGPT |
|------|-----------|-----------|---------|
| **开箱即用** | ✅ 3 命令 | ⚠️ 需编程 | ⚠️ 需配置 |
| **Context 管理** | ⭐⭐⭐⭐⭐ | ⚠️ 简单 | ⚠️ 简单 |
| **Docker 沙箱** | ✅ | ❌ | ✅ |
| **环境变量** | ✅ | ⚠️ 部分 | ⚠️ 简单 |
| **工具策略** | ✅ | ⚠️ 简单 | ✅ |
| **剪枝优化** | ✅ 40-60% | ❌ | ❌ |
| **CLI 工具** | ✅ | ❌ | ✅ |
| **数据隐私** | ✅ 完全离线 | ⚠️ 依赖云 | ⚠️ 依赖云 |
| **MCP 协议** | ✅ | ❌ | ❌ |

---

## 🚀 生产环境部署

### Docker Compose

```yaml
# docker-compose.yml
services:
  fastreact:
    image: fastreact:latest
    environment:
      - FASTREACT_API_KEY=${API_KEY}
      - FASTREACT_BASE_URL=${BASE_URL}
    volumes:
      - ./workspace:/app/workspace
      - /var/run/docker.sock:/var/run/docker.sock
```

```bash
docker-compose up -d
```

### Kubernetes

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastreact
spec:
  template:
    spec:
      containers:
      - name: fastreact
        image: fastreact:latest
        env:
        - name: FASTREACT_API_KEY
          valueFrom:
            secretKeyRef:
              name: fastreact-secrets
              key: api-key
```

---

## 📊 性能指标

| 指标 | 数值 |
|------|------|
| **Token 减少** | 40-60% (Context Pruning) |
| **缓存命中** | +15-25% (LRU 淘汰) |
| **记忆刷新压缩** | 99.5% |
| **Token 计数延迟** | <1ms |
| **上下文构建** | ~8-15ms |
| **平均响应** | <5 秒 |
| **并发工具** | 3+ |

---

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

- **Claude Code** - 产品灵感来源
- **Moltbot** - 架构参考
- **LangChain** - Agent 框架先驱

---

## 📮 联系方式

- **Issues**: [GitHub Issues](https://github.com/atom32/FastReAct/issues)
- **Discussions**: [GitHub Discussions](https://github.com/atom32/FastReAct/discussions)

---

<p align="center">
  <b>FastReAct</b> - 让 AI Agent 开发更简单，更快速
</p>
