# 如何证明 Agent 使用了 SKILL 而非模型自带知识

**问题**: "我怎么证明是这个问题在流程中命中了skill还是用模型自己的知识做的？"

---

## 方法 1: 查看 session_start 事件的 metadata.skills 字段

### 前端日志中查找

在前端 WebSocket 日志中找到 `session_start` 事件：

```javascript
// 修复后的日志（应该包含 skills 字段）
{
  event_type: "session_start",
  content: "当前在git的什么分支上？",
  session_id: "a3534c71-cca4-4edf-8669-e51924f673e5",
  metadata: {
    skills: ["git_workflow"]  // ← 这就是证明！
  }
}
```

**如果看到 `metadata.skills` 字段包含 SKILL 名称**：
- ✅ Agent 自动选择了这个 SKILL
- ✅ SKILL 的内容被注入到系统提示词
- ✅ 不是模型自带知识，而是 SKILL 系统

### 前端代码：显示 SKILL

在 `chat-interface.tsx` 中添加 SKILL 显示：

```typescript
// 在 WebSocket 消息处理中
useEffect(() => {
  if (lastMessage) {
    const event = JSON.parse(lastMessage.data);

    // 检测 session_start 事件
    if (event.event_type === "session_start") {
      const skills = event.metadata?.skills || [];

      if (skills.length > 0) {
        console.log(`[SKILL] Auto-selected: ${skills.join(", ")}`);

        // 显示在 UI 上
        setSkills(skills);  // 添加到组件状态

        // 或者显示在消息中
        addSystemMessage(`Using SKILLs: ${skills.join(", ")}`);
      }
    }
  }
}, [lastMessage]);
```

---

## 方法 2: 对比系统提示词长度

### 验证原理

**无 SKILL**:
```python
system_prompt = agent._build_system_prompt_with_skills([])
# 长度: ~569 字符
```

**有 git_workflow SKILL**:
```python
system_prompt = agent._build_system_prompt_with_skills(["git_workflow"])
# 长度: ~796 字符 (+227 字符)
```

**有 graphrag_workflow SKILL**:
```python
system_prompt = agent._build_system_prompt_with_skills(["graphrag_workflow"])
# 长度: ~1734 字符 (+1165 字符)
```

### 证明 SKILL 注入

如果提示词变长了，说明 SKILL 内容被注入了！

差异内容包括：
- SKILL 名称和描述
- 推荐的工具列表
- MCP 服务器关联
- 使用示例和最佳实践

---

## 方法 3: 检查推荐工具是否被调用

### GraphRAG 示例

**SKILL 定义** (`skills/builtin/graphrag_workflow/SKILL.md`):
```yaml
recommended_tools:
  - graphrag_search_graph
  - graphrag_get_entity
  - graphrag_query_relationships
  - graphrag_vector_search
```

**验证**: 如果 Agent 调用了这些工具，证明 SKILL 生效

```javascript
// 前端日志中的 tool_call 事件
{
  event_type: "tool_call",
  tool_name: "graphrag_search_graph",  // ← 推荐工具被调用！
  tool_args: { query: "Artificial Intelligence", limit: 10 }
}
```

### Git 示例

**SKILL 定义** (`skills/builtin/git_workflow/SKILL.md`):
```yaml
recommended_tools:
  - exec  # 执行 git 命令
```

**验证**: Agent 使用 `exec` 工具执行 git 命令

```javascript
// 前端日志
{
  event_type: "tool_call",
  tool_name: "exec",
  tool_args: { command: "git branch --show-current" }
}
```

虽然 `exec` 是内置工具，但 Agent 知道要用它执行 git 命令，是因为 `git_workflow` SKILL 的指导。

---

## 方法 4: 禁用 SKILL 选择后行为对比

### 测试脚本

```python
from fastreact import Agent

# 创建 Agent
agent = Agent(config=config, multitenant=False)

# 禁用 SKILL 自动选择
agent.disable_auto_skill_selection()

# 运行同样的查询
async for event in agent.run_event_stream("当前在git的什么分支？"):
    print(event)
```

**预期差异**：
- **启用 SKILL**: Agent 可能直接调用 `exec` 执行 `git branch`
- **禁用 SKILL**: Agent 可能先探索文件系统，或不知道如何查询 git

---

## 方法 5: 独特的工具名称

### 创建测试 SKILL

**文件**: `skills/builtin/test_unique/SKILL.md`

```yaml
---
name: test_unique
description: Test SKILL with unique tool name
tags: [test, unique, 测试]
recommended_tools: [very_unique_tool_name_xyz123]
---

# Test SKILL

This SKILL recommends using very_unique_tool_name_xyz123
```

**验证**: 如果 Agent 尝试调用 `very_unique_tool_name_xyz123`，证明 SKILL 被加载了

（即使工具不存在，Agent 的尝试也证明它看到了 SKILL 的推荐）

---

## 方法 6: 检查系统提示词内容（调试模式）

### 添加调试日志

在 `src/fastreact/agent.py` 中添加：

```python
async def run_event_stream(self, query, skills=None, ...):
    # ... SKILL 自动选择 ...

    if skills:
        print(f"[DEBUG] Selected SKILLs: {skills}")
        system_prompt = self._build_system_prompt_with_skills(skills)
        print(f"[DEBUG] System prompt length: {len(system_prompt)}")
        print(f"[DEBUG] System prompt preview:")
        print(system_prompt[:500])  # 前 500 字符

    # ... 继续执行 ...
```

### 重启 Gateway 后查看日志

```bash
# 查询: "当前在git的什么分支？"

[DEBUG] Selected SKILLs: ['git_workflow']
[DEBUG] System prompt length: 796
[DEBUG] System prompt preview:
You are FastReAct...
...
## git_workflow
Git workflow and version control operations
Recommended Tools: `exec`
...
```

---

## 快速验证清单

- [ ] **session_start 事件包含 `metadata.skills`**
  - 如果有 → SKILL 被自动选择 ✅

- [ ] **系统提示词长度增加**
  - +200-1200 字符 → SKILL 内容被注入 ✅

- [ ] **推荐工具被调用**
  - `graphrag_*` 工具被调用 → GraphRAG SKILL 生效 ✅

- [ ] **THINK 内容提到 SKILL 指导**
  - "使用 git 命令查询..." → SKILL 指导生效 ✅

---

## 实际案例：你的查询日志

### 你的查询
```
用户: "当前项目在git的什么分支上？"
```

### 预期的完整日志（修复后）

```javascript
// 1. SESSION_START - 包含 SKILL 信息
{
  event_type: "session_start",
  content: "当前项目在git的什么分支上？",
  metadata: {
    skills: ["git_workflow"]  // ← 自动选择的 SKILL
  }
}

// 2. THINK - Agent 思考
{
  event_type: "think",
  content: "要查询当前 git 分支，我应该使用 git branch --show-current 命令"
}

// 3. TOOL_CALL - 调用工具
{
  event_type: "tool_call",
  tool_name: "exec",
  tool_args: { command: "git branch --show-current" }
}

// 4. TOOL_RESULT - 工具结果
{
  event_type: "tool_result",
  content: "nano"
}

// 5. SESSION_END - 最终答案
{
  event_type: "session_end",
  content: "当前在 nano 分支上。"
}
```

### 证明点

1. ✅ `metadata.skills: ["git_workflow"]` → SKILL 被自动选择
2. ✅ THINK 内容提到 git 命令 → SKILL 指导生效
3. ✅ TOOL_CALL 使用 exec 执行 git → SKILL 推荐工具被使用
4. ✅ 整个流程 3-5 秒完成 → 不是探索文件系统，而是直接 SKILL 指导

---

## 总结

### 最简单的证明方法

**在前端查看 session_start 事件的 metadata.skills 字段**

如果有：
```json
{"skills": ["git_workflow"]}
```

证明：
- ✅ SKILL 被自动选择
- ✅ SKILL 内容注入到系统提示词
- ✅ Agent 行为受 SKILL 指导
- ❌ 不是模型自带知识

### 代码示例

```typescript
// chat-interface.tsx
if (event.event_type === "session_start") {
  const skills = event.metadata?.skills;

  if (skills && skills.length > 0) {
    console.log(`🎯 SKILLs used: ${skills.join(", ")}`);

    // 显示在 UI 上
    return (
      <div className="skill-badge">
        Using: {skills.map(s => <span key={s}>{s}</span>)}
      </div>
    );
  }
}
```

---

**维护者**: Claude Code
**日期**: 2025-02-19
**版本**: 2.4.2
