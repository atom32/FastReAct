# FastReAct Nano - 渐进式学习示例

本目录包含从简单到复杂的示例，帮助你逐步理解 FastReAct Nano 的核心概念和功能。

## 📚 学习路径

### v0: Minimal Core Concept（极简核心）
**文件**: `v0_minimal.py`
**代码行数**: ~15 行
**学习目标**: 理解 Brain-Body 分离架构
**核心概念**:
- Agent 创建和配置自动加载
- 事件驱动的异步调用
- 简单的 `ask()` API

```bash
python3 examples/v0_minimal.py
```

---

### v1: Event-Driven Architecture（事件驱动架构）
**文件**: `v1_event_stream.py`
**代码行数**: ~40 行
**学习目标**: 掌握事件流协议
**核心概念**:
- `run_event_stream()` 实时监听
- 事件类型: session_start, think, tool_call, tool_result, session_end
- 异步迭代器模式

```bash
python3 examples/v1_event_stream.py
```

---

### v2: MCP Server Integration（MCP 集成）
**文件**: `v2_mcp_integration.py`
**代码行数**: ~30 行
**学习目标**: 理解 MCP 工具扩展
**核心概念**:
- MCP 服务器自动发现和加载
- 工具调用抽象（filesystem, fetch, graphrag）
- Skill 与 MCP 的协同

```bash
python3 examples/v2_mcp_integration.py
```

---

### v3: Multi-Tenant Session Management（多租户会话管理）
**文件**: `v3_multi_tenant.py`
**代码行数**: ~45 行
**学习目标**: 理解会话隔离
**核心概念**:
- 每个用户独立的会话空间
- 内存管理（MemoryManager）
- 多用户并发支持

```bash
python3 examples/v3_multi_tenant.py
```

---

### v4: Production-Ready Features（生产级功能）
**文件**: `v4_production.py`
**代码行数**: ~60 行
**学习目标**: 掌握完整功能
**核心概念**:
- Skills 自动选择
- 错误处理和重试
- 无限循环防护
- 多轮对话记忆

```bash
python3 examples/v4_production.py
```

---

## 🎯 如何使用这些示例

### 前置要求

```bash
# 1. 安装 FastReAct Nano
cd /path/to/fastreact-nano
pip install -e ".[all]"

# 2. 配置 API Key
export ANTHROPIC_API_KEY="sk-xxx"
# 或
export OPENAI_API_KEY="sk-xxx"

# 3. 配置用户技能目录（可选）
mkdir -p ~/.fastreact/skills
# 添加自定义技能到 ~/.fastreact/skills/
```

### 运行示例

```bash
# 从简单开始
python3 examples/v0_minimal.py

# 逐步学习
python3 examples/v1_event_stream.py
python3 examples/v2_mcp_integration.py
python3 examples/v3_multi_tenant.py
python3 examples/v4_production.py
```

---

## 📖 核心概念速查表

| 版本 | 核心概念 | 关键方法 | 适用场景 |
|------|---------|---------|---------|
| v0 | Agent 创建 | `Agent()` | 快速测试 |
| v1 | 事件监听 | `run_event_stream()` | 实时 UI |
| v2 | 工具扩展 | MCP servers | 集成外部服务 |
| v3 | 会话管理 | MemoryManager | 多用户应用 |
| v4 | 完整功能 | 所有特性 | 生产环境 |

---

## 💡 学习建议

1. **循序渐进**: 按 v0 → v1 → v2 → v3 → v4 顺序学习
2. **动手实践**: 运行每个示例，观察输出
3. **阅读源码**: 理解示例背后的实现原理
4. **修改实验**: 在示例基础上添加自己的功能

---

## 🔗 相关文档

- [架构设计](../docs/ARCHITECTURE/) - Brain-Body 分离详解
- [事件协议](../docs/EVENTS.md) - 事件类型规范
- [Skills 系统](../docs/SKILLS_AND_MCP.md) - 技能使用指南
- [MCP 集成](../docs/MCP_CALLING_MECHANISM.md) - MCP 服务器配置

---

## 🚀 下一步

掌握这些示例后，你可以：

1. **集成到你的应用**: 参考 Gateway 或 HTTP Adapter
2. **添加自定义 Skills**: 创建 `~/.fastreact/skills/your_skill/SKILL.md`
3. **开发 MCP 服务器**: 扩展更多工具能力
4. **部署生产环境**: 参考 `deploy/README.md`

---

**开始你的 FastReAct Nano 之旅！** 🎉
