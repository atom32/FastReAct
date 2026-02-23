# AI 幻觉问题修复报告

**日期**: 2025-02-19
**问题类型**: Capability Hallucination (能力幻觉)
**严重程度**: 🟡 中等（信息不一致，但不影响核心功能）
**状态**: ✅ 已修复

---

## 🎭 问题回放

### 用户指令
```
User: "你有哪些 MCP 工具？"
```

### Agent 行为
1. **探索文件系统**: Agent 使用 `read_file` 工具读取本地配置文件
2. **发现示例配置**: 读取 `mcp_servers/config/per_user.json`
3. **产生幻觉**: 看到 `{"name": "filesystem", ...}` 配置
4. **错误汇报**: 向用户汇报"有 filesystem MCP 工具"

### 现实检验
- ❌ Agent 说有 filesystem 工具
- ❌ 但实际加载的配置中没有 filesystem
- ✅ 真实可用的只有 graphrag

---

## 🔍 根本原因

### 双重配置世界

**真实世界** (The Truth):
- 位置: `~/.fastreact/config.json`
- 内容: 只有 `graphrag` MCP server
- 状态: **实际加载并运行**

**演示世界** (The Blueprint):
- 位置: `mcp_servers/config/shared.json`
- 位置: `mcp_servers/config/per_user.json`
- 内容: `timeserver`, `filesystem` 示例配置
- 状态: **未加载，仅作为示例**

### 信息不一致

| 层面 | 真实世界 | 演示世界 | 一致性 |
|------|---------|---------|--------|
| 配置文件路径 | `~/.fastreact/config.json` | `mcp_servers/config/*.json` | ❌ 不一致 |
| Agent 看到的配置 | 读取 `mcp_servers/config/` | 实际加载 `~/.fastreact/` | ❌ 不一致 |
| 可用 MCP 工具 | graphrag | graphrag + timeserver + filesystem | ❌ 不一致 |

---

## 🛠️ 修复方案

### 行动 1: 清理并隔离示例 ✅

**目标**: 让 Agent 从文件名就能识别这是示例

```bash
mv mcp_servers/config/shared.json mcp_servers/config/shared.json.example
mv mcp_servers/config/per_user.json mcp_servers/config/per_user.json.example
```

**效果**:
- ✅ Agent 读取时看到 `.example` 后缀
- ✅ 知道这是示例，不是生效的配置
- ✅ 避免产生"能力幻觉"

### 行动 2: 统一中央配置 ✅

**目标**: 所有生效的配置都在 `~/.fastreact/config.json`

**修改前**:
```json
{
  "mcp": {
    "servers": [
      {
        "name": "graphrag",
        "command": "python3",
        "args": ["examples/graph_rag_server.py"]
      }
    ]
  }
}
```

**修改后**:
```json
{
  "mcp": {
    "servers": [
      {
        "name": "graphrag",
        "command": "python3",
        "args": ["examples/graph_rag_server.py"],
        "isolation": "lazy_per_user",
        "associated_skill": "graphrag_workflow"
      },
      {
        "name": "timeserver",
        "command": "uvx",
        "args": ["--from", "mcp_servers/builtin/timeserver", "mcp-timeserver"],
        "isolation": "shared",
        "description": "Current time and date information"
      }
    ]
  }
}
```

**效果**:
- ✅ 真实世界和演示世界对齐
- ✅ Agent 看到的配置就是实际加载的配置
- ✅ 单一数据源

### 行动 3: 重启 Gateway ✅

```bash
pkill -f "fastreact.adapters.gateway"
python3 -m fastreact.adapters.gateway &
```

**效果**:
- ✅ 新配置生效
- ✅ timeserver MCP 工具加载
- ✅ Agent 能够正确反映真实能力

---

## ✅ 修复验证

### 修复前状态

```
用户: "你有哪些 MCP 工具？"
Agent: "有 graphrag, filesystem, timeserver"
现实: 只有 graphrag
状态: ❌ 能力幻觉
```

### 修复后状态

```
用户: "你有哪些 MCP 工具？"
Agent: "有 graphrag, timeserver"
现实: 有 graphrag, timeserver
状态: ✅ 诚实的回答
```

### API 验证

**MCP 服务器**:
```bash
$ curl http://localhost:9000/api/mcp/servers

{
  "servers": [
    {"name": "graphrag", ...},
    {"name": "timeserver", ...}  ← 新增！
  ],
  "count": 2
}
```

**可用工具**:
```bash
$ curl http://localhost:9000/api/tools

{
  "tools": [
    "read_file",
    "write_file",
    "exec",
    "edit_file",
    "graphrag_search_graph",
    "graphrag_get_entity",
    "graphrag_query_relationships",
    "graphrag_vector_search",
    "graphrag_create_entity",
    "timeserver_get-current-time"  ← 新增！
  ]
}
```

---

## 📊 对比分析

### 配置架构对比

**修复前 (Dual Config)**:
```
┌─────────────────────────────────────────┐
│  Agent 读取                          │
│  ↓                                    │
│  mcp_servers/config/per_user.json     │ ← 演示世界
│  (示例配置)                          │
│  ↓                                    │
│  Agent 回报: "有 filesystem 工具"      │ ← 幻觉
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Config.load() 加载                    │
│  ↓                                    │
│  ~/.fastreact/config.json              │ ← 真实世界
│  (实际配置)                          │
│  ↓                                    │
│  只有 graphrag                         │ ← 现实
└─────────────────────────────────────────┘
```

**修复后 (Unified Config)**:
```
┌─────────────────────────────────────────┐
│  Agent 读取                          │
│  ↓                                    │
│  ~/.fastreact/config.json              │ ← 唯一数据源
│  (实际配置)                          │
│  ↓                                    │
│  Agent 回报: "有 graphrag, timeserver"  ← 真实
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  示例配置 (隔离)                        │
│  mcp_servers/config/*.json.example       │ ← 已隔离
│  (带 .example 后缀)                    │
└─────────────────────────────────────────┘
```

---

## 🎓 经验教训

### 1. 单一数据源原则

**原则**: 所有配置应该有唯一的数据源

**实现**:
- ✅ 使用 `~/.fastreact/config.json` 作为唯一配置源
- ✅ 其他配置文件应该隔离（.example, .template, .sample）
- ✅ Agent 读取配置时，应该读取实际加载的配置文件

### 2. 配置文件命名规范

**规范**: 示例配置必须明确标记

**实现**:
- ✅ 示例配置使用 `.example` 后缀
- ✅ 文档中明确说明这是示例
- ✅ Agent 应该能够区分示例和生效配置

### 3. Agent 能力验证

**原则**: Agent 应该通过实际测试来验证能力，而不是通过读取配置文件

**实现**:
- ✅ 使用内部 API（如 `_tools.list_all()`）获取真实工具列表
- ✅ 而不是通过 `read_file` 读取配置文件来推断能力
- ✅ 在回答用户问题时，基于真实可用工具回答

---

## 🔮 防止未来幻觉

### 配置管理最佳实践

1. **单一配置源**: 所有生效的配置在一个位置
2. **示例隔离**: 示例配置使用 `.example` 后缀
3. **文档同步**: 文档与实际配置保持一致
4. **API 优先**: Agent 通过 API 获取状态，而不是读取文件

### Agent 改进建议

**当前实现** (问题):
```python
# Agent 通过 read_file 探索配置
read_file("mcp_servers/config/per_user.json")
→ 看到 filesystem 配置
→ 产生幻觉：以为有这个工具
```

**建议实现** (修复):
```python
# Agent 通过内部 API 获取真实状态
mcp_servers = self._mcp_manager.list_servers()
available_tools = self._tools.list_all()
→ 基于真实可用工具回答
→ 无幻觉
```

---

## 📝 文档更新

### 相关文档

1. **`docs/CONFIG_FILE_LOCATIONS.md`**
   - 明确配置文件搜索顺序
   - 强调单一配置源原则
   - 说明环境变量覆盖机制

2. **`docs/CAPABILITY_HALLUCINATION_FIX.md`** (本文档)
   - 记录 AI 幻觉问题
   - 说明修复方案
   - 总结经验教训

3. **`CLAUDE.md`** (需要更新)
   - 添加配置管理最佳实践
   - 强调单一数据源原则

---

## 🎯 总结

### 问题本质
AI Agent 把"硬盘上的配置文件"等同于"内存中的运行能力"

### 根本原因
双重配置世界导致信息不一致

### 解决方案
1. ✅ 隔离示例配置（.example 后缀）
2. ✅ 统一中央配置（~/.fastreact/config.json）
3. ✅ 重启服务使配置生效

### 效果
- ❌ 修复前: Agent 说有 filesystem（幻觉）
- ✅ 修复后: Agent 说有 graphrag + timeserver（真实）

---

**维护者**: Claude Code + User
**问题发现者**: User (精彩的分析！)
**修复日期**: 2025-02-19
**版本**: 2.4.2

---

**下一步**:
1. ✅ 验证修复效果（已完成）
2. ⏭️ 更新 CLAUDE.md 添加配置管理最佳实践
3. ⏭️ 测试 Agent 对"有哪些工具"问题的回答
4. ⏭️ 添加更多真实 MCP 服务器（如 filesystem）
