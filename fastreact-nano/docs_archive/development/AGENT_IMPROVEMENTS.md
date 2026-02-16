# FastReAct Nano - Agent 层改进计划

## 改进任务清单

### Task 1: Skills 集成 [P0 - Critical]

**目标**: Skills 被注入到系统提示中

**文件**: `src/fastreact/agent.py`

**实现步骤**:

1. 添加 `_build_system_prompt_with_skills()` 方法
2. 修改 `run_event_stream()` 加载并注入 skills
3. 将自定义系统提示传递给 Core 层

**代码**:
```python
def _build_system_prompt_with_skills(self, skills: list) -> str:
    """Build system prompt with skills injected"""
    from fastreact.core.prompts import get_system_prompt

    # Get base system prompt
    base_prompt = get_system_prompt("core")

    if not skills:
        return base_prompt

    # Load skill descriptions
    skill_descriptions = []
    for skill_name in skills:
        skill = self._skills.get(skill_name)
        if skill:
            skill_descriptions.append(f"## {skill.name}\n{skill.description}")

    if not skill_descriptions:
        return base_prompt

    # Inject skills into system prompt
    skills_section = "\n\n# Available Skills\n" + "\n\n".join(skill_descriptions)
    return base_prompt + skills_section
```

### Task 2: Core 层接受自定义系统提示 [P0]

**目标**: Core 层使用自定义系统提示

**文件**: `src/fastreact/core/react.py`

**修改**:
```python
async def run_step_stream(
    self,
    messages: list[dict],
    session_id: str,
    system_prompt: Optional[str] = None,  # ← 新增参数
) -> AsyncIterator["AgentEvent"]:
    # Use custom system prompt or default
    prompt = system_prompt or SYSTEM_PROMPT_CORE

    messages_for_llm = [
        {"role": "system", "content": prompt},
        *messages,
    ]
    ...
```

### Task 3: History 验证和清理 [P1]

**目标**: 确保历史记录格式正确

**文件**: `src/fastreact/agent.py`

**实现**:
```python
def _validate_history(self, history: Optional[list[dict]]) -> list[dict]:
    """Validate and clean conversation history"""
    if not history:
        return []

    # Validate each message
    clean_history = []
    for msg in history:
        if not isinstance(msg, dict):
            continue

        role = msg.get("role")
        content = msg.get("content", "")

        # Skip invalid messages
        if role not in ("user", "assistant"):
            continue

        # Ensure content exists
        if not content:
            continue

        clean_history.append({"role": role, "content": content})

    return clean_history
```

### Task 4: 增强文档 [P2]

**目标**: Adapter 层开发者清楚如何使用 API

**文件**: `src/fastreact/agent.py`

**添加详细的 docstring**，包括：
- Skills 如何工作
- History 格式要求
- Session 管理
- 事件流说明
- 上下文管理策略

## 架构分层（最终版）

```
┌─────────────────────────────────────────┐
│  Adapter Layer                         │
│  职责: 用户交互                         │
│  输入: query + history + skills        │
│  输出: 事件流                          │
└──────────────┬──────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────┐
│  Agent Layer (The Body)                │
│  职责: 管理和执行                       │
│  - ✓ 接收 history                     │
│  - ✓ 验证和清理历史                    │
│  - ✗ 注入 skills (待实现)             │
│  - ✓ 监控上下文                        │
│  - ✓ 发出事件 (不占上下文)             │
└──────────────┬──────────────────────────┘
               │
               ↓ messages + system_prompt
┌─────────────────────────────────────────┐
│  Core Layer (The Brain)                │
│  职责: 推理和意图生成                   │
│  - ✓ 调用 LLM                         │
│  - ✓ 返回事件流                       │
│  - ✗ 接受自定义系统提示 (待实现)       │
└─────────────────────────────────────────┘
```

## 关键设计原则

1. **事件不占用上下文** ✅ 已实现
   - 事件通过 yield 发出
   - 不会添加到 LLM 的 messages 中

2. **Skills 注入提示** ❌ 待实现
   - Skills 应该被添加到系统提示中
   - 不应该作为工具（避免上下文浪费）

3. **历史记录管理** ⚠️ 部分实现
   - History 被直接传递给 LLM
   - 缺少验证和压缩

4. **上下文监控** ✅ 已实现
   - ContextMonitor 截断工具输出
   - 可以扩展为历史压缩

## 实现优先级

### P0 (立即实现)
- [ ] Skills 注入到系统提示
- [ ] Core 层接受自定义系统提示
- [ ] History 验证

### P1 (下一步)
- [ ] 历史记录压缩
- [ ] 详细 API 文档
- [ ] 示例代码

### P2 (可选)
- [ ] 自动技能选择
- [ ] 滑动窗口
- [ ] 上下文使用监控 API
