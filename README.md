# FastReAct

> **企业级 AI Agent 基础设施框架** - 双模式执行引擎（ReAct + IEL）

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version: 1.1.0-alpha](https://img.shields.io/badge/version-1.1.0--alpha-orange.svg)](https://github.com/atom32/FastReAct)
[![MCP Support](https://img.shields.io/badge/MCP-supported-brightgreen.svg)](https://modelcontextprotocol.io)

---

## 项目简介

**FastReAct** 是一个支持双模式执行的 AI Agent 框架：
- **标准 ReAct 模式**：适用于简单查询和单步任务
- **高级 IEL 模式**：适用于复杂工作流和动态重规划

### 设计目标

- **双模式执行**: ReAct（轻量）+ IEL/ToolGraph（高级）
- **隐私优先**: 支持完全离线部署，数据不离开本地环境
- **模型灵活**: 支持任何 OpenAI-compatible API
- **成本可控**: 通过智能上下文管理优化 Token 使用
- **可扩展**: 支持自定义工具和 MCP 协议集成

### 当前状态

**版本**: v1.1.0-alpha
- 核心功能可用
- 部分高级功能开发中
- 生产使用需谨慎
- 适合学习和原型开发

---

## 快速开始

### 安装

```bash
git clone https://github.com/atom32/FastReAct.git
cd FastReAct
pip install -e .
```

### 配置

```bash
# 方法 1: 使用用户配置（推荐）
mkdir -p ~/.fastreact
cp user_config.example.json ~/.fastreact/config.json
# 编辑添加你的 API keys

# 方法 2: 使用环境变量
export FASTREACT_API_KEY=your-api-key-here
```

### 使用

```bash
# 交互式对话
python -m fastreact.cli.main shell

# 单次查询
python -m fastreact.cli.main run "帮我计算 25 * 34"

# 启动 Gateway
python scripts/run_gateway.py
```

详细指南: [INSTALLATION.md](INSTALLATION.md) | [NEW_ENVIRONMENT_SETUP.md](NEW_ENVIRONMENT_SETUP.md)

---

## 功能概览

### 已实现功能

#### 1. 双模式执行引擎

**模式 A：标准 ReAct 循环**
- 推理-行动-观察循环 (Thought → Action → Observation)
- 异步工具执行
- 错误处理和重试机制
- 会话管理
- **默认模式，用于简单查询**

**模式 B：IEL + ToolGraph（高级）**
- **IEL (Interactive Execution Loop)**: Plan → Execute → Reflect → Replan
- **ToolGraph**: DAG 工作流编排
- 动态图修改（插入/删除/替换节点）
- Human-in-the-loop（用户中断）
- 快照和回滚机制
- **可选模式，用于复杂工作流**

#### 2. 智能上下文管理
- **Memory Flush**: 自动总结长对话（50k tokens 触发）
- **Memory Retrieval**: 向量检索历史对话（可选）
- **Progressive Compaction**: 多层压缩（已实现，未完全集成）

#### 3. 工具系统
- 13 个内置工具（Calculator, Search, HTTP, Bash 等）
- MCP 协议集成（GitHub, Apollo Core）
- 工具策略控制（Allow/Deny 列表）
- 风险分级和审批机制

#### 4. 配置系统
- 4 层配置优先级（ENV > USER > PROJECT > DEFAULT）
- 支持多租户场景
- 灵活的配置管理

#### 5. 用户接口
- CLI REPL（交互式命令行）
- WebSocket Gateway（实时通信）
- Web UI（通过 FastReAct-web 项目）

### 开发中功能

- Progressive Compaction 完全集成
- 多 Agent 协作（规划 v2.0.0）
- Agent 编排（规划 v2.0.0）
- 自动工具发现（规划 v2.0.0）
- 完整的生产环境支持

---

## 架构

### 双模式执行引擎

FastReAct 提供两种执行模式，根据任务复杂度自动选择：

#### 模式 A：标准 ReAct 循环（默认）

适用于简单查询和单步任务：
```
用户查询 → LLM 推理 → 工具执行 → 观察结果 → 循环/结束
```

**特点**：
- 轻量级、响应快
- 适合对话式问答
- REPL 的默认模式

#### 模式 B：IEL + ToolGraph（高级）

适用于复杂多步骤任务：
```
Tool Graph (DAG) → IEL 执行循环 → 动态重规划 → 快照回滚
```

**特点**：
- 支持复杂工作流编排
- 动态图修改（插入/替换节点）
- Human-in-the-loop（用户中断）
- 失败重试和回滚机制

**组件**：
- `IELLoop` - 交互式执行循环
- `IELExecutionContext` - 可变状态管理
- `ToolGraph` - DAG 图执行
- `Replanner` - 反思和重规划
- `StepExecutor` - 步进执行

### 系统架构

```
┌─────────────────────────────────────────┐
│  用户接口层                              │
│  CLI REPL / WebSocket Gateway / Web UI  │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  双模式执行引擎                          │
│  ┌────────────────┐  ┌───────────────┐ │
│  │ ReAct Loop     │  │ IEL + ToolGraph│ │
│  │ (默认/简单)    │  │ (高级/复杂)   │ │
│  └────────────────┘  └───────────────┘ │
│  - 上下文管理 (Memory Flush)            │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  工具层                                 │
│  ┌─────────┐  ┌──────────┐  ┌────────┐ │
│  │ Builtin │  │  Memory   │  │  MCP   │ │
│  │ Tools   │  │ Retrieval │  │ Servers│ │
│  └─────────┘  └──────────┘  └────────┘ │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  基础设施层                             │
│  LLM 抽象 / 配置系统 / 存储层            │
└─────────────────────────────────────────┘
```

### 何时使用哪种模式？

| 场景 | 推荐模式 | 示例 |
|------|---------|------|
| 简单问答 | ReAct | "2+2=?" |
| 单步工具 | ReAct | "搜索最新 AI 新闻" |
| 复杂工作流 | IEL + ToolGraph | 多步骤数据分析 |
| 需要重规划 | IEL + ToolGraph | 代码生成→测试→修复 |
| Human-in-loop | IEL + ToolGraph | 需要用户审批的流程 |

---

## 使用示例

### 基础查询

```python
from fastreact import FastReAct

agent = FastReAct(api_key="your-api-key")
result = agent.run("2 + 2 * 3 = ?")
print(result['answer'])  # 8
```

### 工具调用

```bash
# 在 REPL 中
>>> 计算 (25 + 35) * 2 - 10
>>> 搜索最新的 AI 新闻
>>> 在 atom32/FastReAct 创建一个 issue
```

### Gateway + Web UI

```bash
# 终端 1：启动 Gateway
python scripts/run_gateway.py

# 终端 2：启动 Web UI（需要 FastReAct-web 项目）
cd ../FastReAct-web
npm run dev

# 浏览器访问 http://localhost:3001
```

---

## 技术亮点

### 1. 双模式执行架构
- **ReAct 循环**: 轻量级、快速响应，适合简单任务
- **IEL + ToolGraph**: 复杂工作流、动态重规划、Human-in-loop
- 根据任务复杂度自动选择
- 两种模式可独立使用，也可组合

### 2. IEL (Interactive Execution Loop)
- Plan → Execute → Reflect → Replan 循环
- 动态图修改（运行时插入/替换节点）
- 快照和回滚机制
- 用户中断和输入处理
- 失败自动重试和修复

### 3. ToolGraph 系统
- 声明式工作流定义（`node1 >> node2`）
- DAG 执行和依赖解析
- 并行执行（`(node1 | node2) >> node3`）
- 条件执行和循环支持

### 4. Memory Flush (自动上下文管理)
- 触发阈值: 50000 (soft) / 55000 (hard) tokens
- 自动总结旧消息
- 压缩比约 70%
- 已实现并集成

### 5. MCP 协议集成
- 标准化工具协议
- 支持 GitHub MCP、Apollo Core
- 100+ 社区 MCP servers 可用
- 已实现并可用

### 6. 4 层配置优先级
- ENV > USER > PROJECT > DEFAULT
- 支持多租户场景
- 敏感信息隔离
- 已实现并验证

### 7. 工具策略控制
- 风险分级（HIGH/MEDIUM/LOW）
- 执行审批机制
- 动态策略控制
- 已实现

---

## 技术债务与限制

### 当前限制

1. **测试覆盖不足**: 缺少端到端集成测试
2. **性能数据未验证**: 部分优化效果未实际测量
3. **Progressive Compaction**: 代码已写但未完全集成
4. **Alpha 版本**: 不推荐直接用于生产环境

### 已知问题

1. 部分 MCP servers 在 Windows 上有兼容性问题
2. 长对话场景需要更多测试
3. 错误处理需要更健壮

---

## 文档

### 核心文档
- [项目状态](PROJECT_STATUS.md) - 诚实的功能状态评估 ⭐
- [技术亮点](TECHNICAL_HIGHLIGHTS.md) - 技术设计文档
- [安装指南](INSTALLATION.md) - 详细安装步骤
- [新环境设置](NEW_ENVIRONMENT_SETUP.md) - 开发环境配置

### 功能文档
- [多租户工作区](MULTI_TENANT_WORKSPACE.md)
- [会话恢复](SESSION_RESUME.md)
- [配置优先级](CONFIG_PRIORITY.md)
- [Gateway & Web UI](GATEWAY_WEB_EVALUATION.md)

### 系统文档
- [Memory 系统集成](MEMORY_SYSTEMS_INTEGRATION.md)
- [上下文压缩机制](MEMORY_FLUSH_COMPACTION_INTERACTION.md)
- [跨平台开发](CROSS_PLATFORM_SUMMARY.md)

[完整文档索引](DOCS_INDEX.md)

---

## 适用场景

### 适合
- 学习 ReAct 架构
- 快速原型开发
- 小规模内部部署
- 需要本地化/隐私保护
- 需要自定义工具

### 不适合
- 大规模生产环境（目前）
- 需要完整功能（vs LangChain）
- 不想配置环境
- 需要开箱即用的完美体验

---

## 开发路线图

### v1.1.0 (当前 Alpha)
- [x] ReAct 核心引擎
- [x] Memory Flush
- [x] MCP 协议集成
- [x] 4 层配置优先级
- [x] 工具系统
- [ ] Progressive Compaction 集成

### v1.2.0 (规划)
- [ ] 完整的集成测试
- [ ] 性能基准测试
- [ ] 生产环境验证
- [ ] 错误处理增强

### v2.0.0 (未来)
- [ ] 多 Agent 协作
- [ ] Agent 编排
- [ ] 自动工具发现

---

## 贡献

欢迎贡献！请查看 [CLAUDE.md](CLAUDE.md) 了解开发规则。

### 开发环境

```bash
# 克隆仓库
git clone https://github.com/atom32/FastReAct.git
cd FastReAct

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
python test_config_priority.py
python test_memory_flush_logic.py
```

---

## 许可证

[MIT License](LICENSE)

---

## 致谢

- [Anthropic](https://www.anthropic.com/) - Claude 模型
- [ModelContextProtocol](https://modelcontextprotocol.io/) - MCP 协议
- [LangChain](https://github.com/langchain-ai/langchain) - 灵感来源

---

## 联系方式

- 作者: atom32
- 项目: https://github.com/atom32/FastReAct
- 问题反馈: https://github.com/atom32/FastReAct/issues

---

**最后更新**: 2025-02-05
**版本**: v1.1.0-alpha
**状态**: Alpha - 核心功能可用，持续改进中
