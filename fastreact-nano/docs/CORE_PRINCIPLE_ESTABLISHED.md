# 核心规则确立 - Platform Core Principle

**日期**: 2025-02-19
**版本**: 2.4.2
**状态**: ✅ 已确立并写入 CLAUDE.md

---

## 确立的核心规则

### 规则编号：Architecture Iron Rule #0

**规则名称**: Platform Core Principle ⚠️ FUNDAMENTAL

**核心内容**：

> **FastReAct Nano is an Agent Platform that MUST support SKILL and MCP**

---

## 规则详解

### 1. 平台定位

**FastReAct 不是什么**：
- ❌ 不是简单的聊天机器人（Chatbot）
- ❌ 不是问答系统（Q&A System）
- ❌ 不是固定功能的 AI 工具

**FastReAct 是什么**：
- ✅ **可扩展的 AI Agent 平台**（Extensible AI Agent Platform）
- ✅ 支持通过 SKILL 扩展认知能力
- ✅ 支持通过 MCP 集成外部工具

### 2. 两大核心扩展机制

#### SKILL（技能系统）
- **定义**：认知模式和任务策略
- **公式**：SKILL = 结构化提示词 + 工具策略 + 推理模式
- **位置**：
  - 全局技能：`skills/builtin/`
  - 用户技能：`{user_workspace}/skills/`（多租户）
  - 社区技能：`skills/community/`
- **特性**：可自动选择（基于查询内容）

#### MCP（Model Context Protocol）
- **定义**：外部工具集成协议
- **通信方式**：STDIO（标准输入输出）
- **协议**：JSON-RPC 2.0
- **位置**：`mcp_servers/config/`
- **隔离模式**：
  - `shared` - 全局共享
  - `per_user` - 每用户隔离
  - `lazy_per_user` - 按需创建

### 3. 部署架构

#### Gateway（单租户模式）
- **文件**：`src/fastreact/adapters/gateway.py`
- **工作区**：`workspaces/default/`
- **用户隔离**：❌ 无（所有用户共享）
- **适用场景**：
  - 个人开发助手
  - 测试环境
  - PoC（概念验证）
- **配置**：`paths.gateway_workspace`

#### Feishu（多租户模式）
- **文件**：`src/fastreact/adapters/feishu_sdk.py`
- **工作区**：`/var/fastreact/tenants/feishu/{user_key}/`
- **用户隔离**：✅ 完全隔离
- **适用场景**：
  - 企业部署（飞书机器人）
  - SaaS 应用
  - 多用户生产环境
- **配置**：`paths.feishu_workspace_base`
- **用户识别**：`user_key = "feishu:{user_id}"`

### 4. 强制性要求（MANDATORY）

**对于所有新功能**：
- ✅ **必须设计为可被 SKILL 增强**
- ✅ **必须兼容 MCP 工具**
- ✅ **必须在加载 SKILL 时正常工作**
- ✅ **必须在 MCP 工具可用时正常工作**
- ✅ **必须尊重多租户隔离（不泄漏用户数据）**

### 5. 开发规则（5 条 NEVER / ALWAYS）

1. **NEVER bypass SKILL system**
   - 永远不要绕过 SKILL 系统
   - 所有功能都应能通过 SKILL 增强

2. **NEVER hardcode tools**
   - 永远不要硬编码外部集成
   - 使用 MCP 协议

3. **ALWAYS test with skills**
   - 始终测试 SKILL 加载场景
   - 验证功能在 SKILL 可用时正常

4. **ALWAYS test with MCP**
   - 始终测试 MCP 工具场景
   - 验证功能在 MCP 可用时正常

5. **ALWAYS respect multi-tenant isolation**
   - 始终尊重多租户隔离
   - 永远不要泄漏用户数据

### 6. 禁止事项（FORBIDDEN）

- ❌ 实现无法通过 SKILL 扩展的功能
- ❌ 硬编码外部集成（应使用 MCP）
- ❌ 破坏 SKILL 自动选择
- ❌ 破坏 MCP 工具发现
- ❌ 在多租户模式下混合用户数据

---

## SKILL 和 MCP 集成示例

### 代码示例

```python
# Agent 自动加载 SKILL 和 MCP 工具
agent = Agent(
    multitenant=False,  # Gateway: 单租户
    # 或
    multitenant=True,   # Feishu: 多租户
    base_workspace="..."
)

# SKILL 从以下位置加载：
# 1. 用户工作区技能（仅多租户）
# 2. 全局技能：skills/builtin/
# 3. 社区技能：skills/community/

# MCP 服务器从以下位置加载：
# 1. 用户 mcp_config.json（仅多租户）
# 2. mcp_servers/config/per_user.json（用户特定）
# 3. mcp_servers/config/shared.json（全局共享）
```

### 技能加载优先级

**单租户（Gateway）**：
```
1. 全局技能（skills/builtin/）
   ↓
2. 社区技能（skills/community/）
```

**多租户（Feishu）**：
```
1. 用户特定技能（{user_workspace}/skills/）← 最高优先级
   ↓
2. 全局技能（skills/builtin/）
   ↓
3. 社区技能（skills/community/）
```

### MCP 服务器加载优先级

**单租户（Gateway）**：
```
1. 全局共享服务器（mcp_servers/config/shared.json）
```

**多租户（Feishu）**：
```
1. 用户特定服务器（{user_workspace}/mcp_config.json）← 最高优先级
   ↓
2. 每用户服务器（mcp_servers/config/per_user.json）
   ↓
3. 全局共享服务器（mcp_servers/config/shared.json）
```

---

## 文档引用

核心规则已写入 `CLAUDE.md`，相关文档：

1. **SKILL 系统**：`docs/SKILLS_AND_MCP.md`
   - SKILL vs MCP 工具的详细说明
   - SKILL 开发指南
   - MCP 集成指南

2. **MCP 调用机制**：`docs/MCP_CALLING_MECHANISM.md`
   - MCP 通信协议（STDIO）
   - MCP Server 开发指南
   - 可用的 MCP Servers

3. **多租户指南**：`docs/MULTITENANT_GUIDE.md`
   - 单租户 vs 多租户架构
   - User Key 机制
   - 配置和部署指南

4. **目录结构**：`docs/DIRECTORY_STRUCTURE.md`
   - 标准目录结构
   - SKILL 和 MCP 位置
   - 配置优先级

---

## 影响范围

### 对现有功能的要求

所有现有功能必须验证：
- ✅ 是否兼容 SKILL 系统？
- ✅ 是否兼容 MCP 工具？
- ✅ 在多租户模式下是否正确隔离？

### 对新功能的要求

所有新功能开发必须：
1. **设计阶段**：考虑如何通过 SKILL 增强
2. **开发阶段**：实现 MCP 集成接口
3. **测试阶段**：
   - 测试无 SKILL 场景
   - 测试有 SKILL 场景
   - 测试无 MCP 场景
   - 测试有 MCP 场景
   - 测试单租户模式
   - 测试多租户模式

### 对代码审查的要求

代码审查必须检查：
- [ ] 是否绕过了 SKILL 系统？
- [ ] 是否硬编码了外部集成？
- [ ] 是否破坏了多租户隔离？
- [ ] 是否添加了相应的测试？

---

## 例外情况

**无例外**。这是平台的**核心原则（FUNDAMENTAL）**。

如果某个功能无法通过 SKILL 或 MCP 实现：
1. **首先**：扩展 SKILL 系统能力
2. **其次**：扩展 MCP 协议支持
3. **最后**：重新评估功能设计

**永远不要**为了功能方便而绕过 SKILL 或 MCP 系统。

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 2.4.2 | 2025-02-19 | 确立核心原则：Platform Core Principle |

---

## 维护者

- **规则制定**: Claude Code + User
- **文档位置**: `CLAUDE.md` (Architecture Iron Rule #0)
- **最后更新**: 2025-02-19

---

## 总结

**核心原则**：
> FastReAct Nano is an Agent Platform that MUST support SKILL and MCP

**三大支柱**：
1. **SKILL 系统** - 扩展认知能力
2. **MCP 协议** - 集成外部工具
3. **多租户架构** - Gateway（单租户）+ Feishu（多租户）

**开发铁律**：
- 永远不要绕过 SKILL 系统
- 永远不要硬编码外部集成
- 始终尊重多租户隔离

**文档支持**：
- `docs/SKILLS_AND_MCP.md` - SKILL 和 MCP 详细说明
- `docs/MCP_CALLING_MECHANISM.md` - MCP 调用机制
- `docs/MULTITENANT_GUIDE.md` - 多租户指南
- `docs/DIRECTORY_STRUCTURE.md` - 目录结构
