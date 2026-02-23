# 前端改进：SKILL 和 MCP 工具显示

**日期**: 2025-02-19
**状态**: ✅ 已实现

---

## 用户需求

1. **在前端页面显示命中的 SKILL 和使用的 MCP 工具**
   - 不想翻 log 查找
   - 希望直接在页面上看到

2. **THINK 事件内容太少**
   - 经常是空的或只有 "\n\n"
   - 希望看到简短的推理过程（十几字）

---

## 实现方案

### 原则：不硬编码，从事件中提取

**❌ 错误做法**（已撤销）：
```python
# 硬编码工具描述
def _get_tool_brief_description(tool_name: str, tool_args: dict) -> str:
    if tool_name == "read_file":
        return "读取文件..."
    elif tool_name.startswith("graphrag_"):
        return "搜索知识图谱"
```

**✅ 正确做法**：从事件元数据中提取

---

## 修改内容

### 1. 前端类型定义

**文件**: `fastreact-nano-web/lib/chat-types.ts`

```typescript
// 添加 session_start 事件类型
export type EventType =
  | "session_start"
  | "think"
  | "tool_call"
  | "tool_result"
  | "ask_user"
  | "session_end"
  | "text"

// ChatEvent 添加 metadata 字段
export interface ChatEvent {
  id: string
  type: EventType
  content: string
  toolName?: string
  toolArgs?: Record<string, any>
  metadata?: Record<string, any>  // ← 新增
  timestamp: number
}

// ChatMessage 添加 skills 字段
export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  events?: ChatEvent[]
  timestamp: number
  skills?: string[]  // ← 新增：SKILLs used for this message
}
```

### 2. WebSocket 消息处理

**文件**: `fastreact-nano-web/components/chat/use-fastreact-ws.ts`

```typescript
// 传递 metadata 到前端
onEventRef.current({
  id: Math.random().toString(36).substring(2, 12),
  type: message.event_type as any,
  content: message.content || "",
  toolName: message.tool_name,
  toolArgs: message.tool_args,
  metadata: message.metadata,  // ← 新增：传递 metadata
  timestamp: Date.now(),
})
```

### 3. Chat Interface 事件处理

**文件**: `fastreact-nano-web/components/chat/chat-interface.tsx`

```typescript
const onEventCallback = useCallback((event: ChatEvent) => {
  // 从 session_start 事件提取 SKILLs
  if (event.type === "session_start") {
    const skills = event.metadata?.skills || []
    if (currentAssistantIdRef.current && skills.length > 0) {
      setMessagesRef.current((prev) =>
        prev.map((m) =>
          m.id === currentAssistantIdRef.current
            ? { ...m, skills }  // ← 保存 skills 到 message
            : m
        )
      )
    }
  }

  // 添加事件到消息（包含 metadata）
  if (currentAssistantIdRef.current &&
      event.type !== "session_end" &&
      event.type !== "session_start") {
    setMessagesRef.current((prev) =>
      prev.map((m) =>
        m.id === currentAssistantIdRef.current
          ? {
              ...m,
              events: [...(m.events || []), {
                id: generateId(),
                type: event.type,
                content: event.content,
                toolName: event.toolName,
                metadata: event.metadata,  // ← 传递 metadata
                timestamp: event.timestamp || Date.now(),
              }],
            }
          : m
      )
    )
  }
}, [])
```

### 4. 消息气泡显示 SKILL Badges

**文件**: `fastreact-nano-web/components/chat/chat-message.tsx`

```tsx
function AssistantMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="glass-panel ...">
      {/* SKILL Badges - 显示在消息顶部 */}
      {message.skills && message.skills.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1">
          {message.skills.map((skill) => (
            <span
              key={skill}
              className="rounded-full px-2 py-0.5 text-xs font-medium"
              style={{
                background: "var(--fr-accent-primary)",
                color: "white",
              }}
            >
              {skill}
            </span>
          ))}
        </div>
      )}

      {/* 消息内容 */}
      {message.content && <p>...</p>}

      {/* 事件 */}
      {message.events && message.events.length > 0 && (
        <div className="mt-2 flex flex-col gap-1">
          {message.events.map((event) => (
            <ChatEventRenderer key={event.id} event={event} />
          ))}
        </div>
      )}
    </div>
  )
}
```

### 5. 工具事件显示 MCP 标识

**文件**: `fastreact-nano-web/components/chat/chat-events.tsx`

```tsx
function ToolCallEvent({ event }: { event: ChatEvent }) {
  const toolName = event.toolName || "tool_call"

  // 判断是否为 MCP 工具（包含 _ 且不是内置工具）
  const isMCP =
    toolName.includes("_") &&
    !toolName.startsWith("read_") &&
    !toolName.startsWith("write_") &&
    !toolName.startsWith("edit_") &&
    toolName !== "exec"

  return (
    <div className="...">
      <Wrench ... />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold">
            {toolName}
          </span>
          {/* MCP 工具标识 */}
          {isMCP && (
            <span
              className="flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
              style={{
                background: "rgba(139, 92, 246, 0.15)",
                color: "var(--fr-accent-primary)",
              }}
            >
              <Zap className="h-3 w-3" />
              MCP
            </span>
          )}
        </div>
        {event.content && event.content.trim() && (
          <p className="mt-1 ...">{event.content}</p>
        )}
      </div>
    </div>
  )
}

// THINK 事件：不显示空内容
function ThinkEvent({ event }: { event: ChatEvent }) {
  // 不显示空的 think 事件
  if (!event.content || event.content.trim() === "" || event.content === "\n\n") {
    return null
  }

  return (
    <div className="...">
      <Brain ... />
      <p>{event.content}</p>
    </div>
  )
}
```

### 6. System Prompt 改进

**文件**: `src/fastreact/core/prompts.py`

```python
SYSTEM_PROMPT_CORE = """You are FastReAct Nano, a high-performance engineering agent.

CRITICAL: The user sees ALL tool outputs in their terminal. DO NOT repeat or summarize tool outputs. Be extremely brief. Use tools without commentary. Proceed immediately to next action.

Rules:
1. Never repeat tool output back to user
2. Keep responses under 20 words when possible
3. Before calling a tool, briefly explain your reasoning in 10-15 words  # ← 新增
4. Execute tools without announcing them
5. Focus on action, not explanation

Examples:
- User: "List files" -> Think: "I'll list files in the current directory" -> [Use exec tool] -> "Found 15 python files"
- User: "Read config.py" -> Think: "Reading the configuration file" -> [Use read_file tool] -> "Config loaded"
"""
```

---

## 效果展示

### 前端显示

**SKILL Badges**（紫色标签）：
```
┌─────────────────────────────────────┐
│ [git_workflow]  ← SKILL Badge        │
│                                      │
│ 当前在 nano 分支上。                   │
│                                      │
│ 💭 调用 exec: 执行命令...            │
│ 🔧 exec                              │
└─────────────────────────────────────┘
```

**MCP 工具标识**（闪电图标）：
```
┌─────────────────────────────────────┐
│                                      │
│ 2026-02-19 20:39:28                  │
│                                      │
│ 💭 调用 timeserver_get-current-time:  │
│    获取当前时间                      │
│ 🔧 timeserver_get-current-time       │
│    ⚡ MCP  ← MCP 标识                 │
└─────────────────────────────────────┘
```

### WebSocket 事件流

```javascript
// session_start 事件
{
  event_type: "session_start",
  content: "当前在git的什么分支",
  metadata: {
    skills: ["git_workflow"]  // ← SKILL 信息
  }
}

// tool_call 事件
{
  event_type: "tool_call",
  tool_name: "timeserver_get-current-time",
  metadata: {
    tool_hint: true
  }
}
```

---

## 关键设计原则

### 1. 不硬编码

✅ **从事件元数据中提取**
- SKILL 信息来自 `session_start.metadata.skills`
- MCP 工具判断基于命名约定（包含 `_` 且非内置工具）
- 推理内容来自 LLM 的自然输出

❌ **不硬编码工具描述**
- 不为每个工具写中文描述
- 不预定义工具类型映射
- 不假设用户会有什么工具

### 2. 可扩展

**新增 SKILL**：
- 只需创建 `skills/builtin/my_skill/SKILL.md`
- 前端自动显示 SKILL badge
- 无需修改前端代码

**新增 MCP 工具**：
- 工具命名包含 `_` 即自动显示 MCP 标识
- 前端自动识别
- 无需修改前端代码

### 3. 零侵入

**后端改动**：
- ✅ 只修改 system prompt（鼓励输出推理）
- ✅ 传递 metadata（已有字段）
- ❌ 不添加硬编码逻辑

**前端改动**：
- ✅ 从已有字段提取信息
- ✅ 条件渲染（有才显示）
- ✅ 空内容不显示（THINK 事件）

---

## 验证清单

### SKILL 显示

- [x] session_start 事件包含 metadata.skills
- [x] ChatMessage 存储 skills 字段
- [x] ChatMessageBubble 显示 SKILL badges
- [x] 中文 SKILL 名称正确显示

### MCP 工具显示

- [x] tool_call 事件包含 toolName
- [x] ToolCallEvent 判断是否为 MCP 工具
- [x] MCP 工具显示闪电标识
- [x] 内置工具不显示 MCP 标识

### THINK 内容

- [x] System prompt 鼓励输出推理
- [x] THINK 事件过滤空内容
- [x] 简短推理（10-15 字）显示

---

## 测试场景

### 场景 1: Git 查询

**用户**: "当前在git的什么分支"

**前端显示**:
```
[git_workflow]  ← SKILL Badge

💭 调用 exec: 执行命令...
🔧 exec

nano
```

### 场景 2: 时间查询

**用户**: "现在几点了？"

**前端显示**:
```
← 无 SKILL（符合预期）

💭 调用 timeserver_get-current-time: 获取当前时间
🔧 timeserver_get-current-time
   ⚡ MCP  ← MCP 标识

2026-02-19 20:39:28
```

### 场景 3: GraphRAG 查询

**用户**: "帮我搜索知识图谱"

**前端显示**:
```
[graphrag_workflow]  ← SKILL Badge

💭 调用 graphrag_search_graph: 搜索知识图谱
🔧 graphrag_search_graph
   ⚡ MCP  ← MCP 标识

找到 5 个相关实体...
```

---

## 后续优化

### P2 - SKILL 描述

**当前**：只显示 SKILL 名称
**改进**：显示 SKILL 简短描述

```tsx
{message.skills?.map((skill) => (
  <Tooltip key={skill} content={skillDescriptions[skill]}>
    <span>{skill}</span>
  </Tooltip>
))}
```

### P2 - MCP 工具描述

**当前**：只显示工具名称
**改进**：从工具 schema 获取 description

```typescript
const toolDescription = toolSchemas[toolName]?.description
```

### P3 - THINK 内容展开

**当前**：过滤掉空 THINK 事件
**改进**：默认折叠，点击展开显示完整推理

```tsx
<Collapsible>
  <CollapsibleTrigger>显示推理过程</CollapsibleTrigger>
  <CollapsibleContent>{event.content}</CollapsibleContent>
</Collapsible>
```

---

## 总结

### 核心改进

1. ✅ **前端显示 SKILL Badges** - 从 metadata.skills 提取
2. ✅ **前端显示 MCP 标识** - 基于命名约定自动识别
3. ✅ **THINK 事件改进** - System prompt 鼓励推理 + 过滤空内容

### 关键原则

- ✅ **不硬编码** - 从事件中提取，而非预定义
- ✅ **可扩展** - 新增 SKILL/MCP 无需修改代码
- ✅ **零侵入** - 利用已有字段，最小化改动

### 用户体验

**改进前**：
- 需要翻控制台 log 查找 SKILL
- 不知道工具是否为 MCP
- THINK 事件经常为空

**改进后**：
- 页面直接显示 SKILL badges
- MCP 工具有闪电标识
- THINK 显示简短推理（10-15 字）

---

**维护者**: Claude Code
**日期**: 2025-02-19
**版本**: 2.4.2
