# 动态 Skill 选择机制设计

**Date**: 2025-02-27
**问题**: Skills 只在开始时选择一次，不够灵活

---

## 当前实现

### Skills 选择时机

```python
# ❌ 当前：只在 query 开始时选择一次
async def run_event_stream(query, skills=None):
    # 1. 选择 skills（只一次）
    if skills is None and self._auto_select_skills:
        skills = self._select_skills_auto(query)

    # 2. 构建 system prompt（固定）
    system_prompt = self._build_system_prompt_with_skills(skills)

    # 3. ReAct 循环（skills 不变）
    while True:
        thought = await self._core.generate_thought(messages)
        tool_call = await self._core.generate_tool_call(messages)
        # skills 始终不变 ❌
```

**问题**：
- ❌ Skills 无法根据中间的 THOUGHT 动态调整
- ❌ 无法适应不同阶段的不同需求
- ❌ 浪费 token（不需要的 skills 一直占用 context）

---

## 改进方案：动态 Skill 选择

### 核心思路

**每次 THOUGHT 后重新评估需要的 skills**：

```python
# ✅ 改进：每次 iteration 重新选择 skills
async def run_event_stream(query, skills=None):
    iteration_count = 0

    while iteration_count < max_iterations:
        # === 动态选择 skills ===
        if self._auto_select_skills:
            # 1. 分析当前上下文（query + history + thoughts）
            context = self._build_selection_context(
                query,      # 原始查询
                history,    # 对话历史
                thoughts,   # 之前的思考
            )

            # 2. 根据上下文重新选择 skills
            current_skills = self._select_skills_dynamic(
                context,
                self._max_auto_skills,
            )

            # 3. 重新构建 system prompt
            system_prompt = self._build_system_prompt_with_skills(current_skills)

        # === Brain: 生成 THOUGHT ===
        thought = await self._core.generate_thought(messages)

        # === Body: 执行工具 ===
        tool_call = await self._core.generate_tool_call(messages)

        iteration_count += 1
```

---

## 实现细节

### 1. 上下文构建

```python
def _build_selection_context(
    self,
    query: str,
    history: list[dict],
    thoughts: list[str],
    tool_calls: list[dict],
) -> str:
    """
    构建 skill 选择的上下文

    Args:
        query: 用户原始查询
        history: 对话历史
        thoughts: 之前的思考链
        tool_calls: 之前的工具调用

    Returns:
        上下文字符串
    """
    context_parts = []

    # 1. 原始查询
    context_parts.append(f"# Task\n{query}")

    # 2. 最近的对话历史
    if history:
        recent_history = history[-3:]  # 最近 3 轮
        context_parts.append("# Recent Conversation")
        for msg in recent_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]  # 截断
            context_parts.append(f"{role}: {content}")

    # 3. 最近的思考
    if thoughts:
        recent_thoughts = thoughts[-2:]  # 最近 2 个思考
        context_parts.append("# Recent Thoughts")
        for thought in recent_thoughts:
            context_parts.append(f"- {thought[:200]}")  # 截断

    # 4. 最近的工具调用
    if tool_calls:
        recent_calls = tool_calls[-3:]  # 最近 3 个调用
        context_parts.append("# Recent Actions")
        for call in recent_calls:
            tool = call.get("tool", "unknown")
            context_parts.append(f"- Used: {tool}")

    return "\n\n".join(context_parts)
```

---

### 2. 动态选择算法

```python
def _select_skills_dynamic(
    self,
    context: str,
    max_skills: int = 3,
    user_context: Optional[UserContext] = None,
) -> list[str]:
    """
    根据当前上下文动态选择 skills

    Args:
        context: 当前上下文字符串
        max_skills: 最大技能数
        user_context: 用户上下文

    Returns:
        选择的技能名称列表
    """
    # 1. 提取上下文关键词
    keywords = self._extract_keywords(context)

    # 2. 考虑之前使用的 skills（避免频繁切换）
    previous_skills = self._get_recently_used_skills()

    # 3. 评分所有 skills
    skill_scores = []

    for skill_name, skill in self._skills.items():
        score = 0.0

        # 基础分：关键词匹配
        score += self._score_skill_keywords(skill, keywords)

        # 加分：最近使用过的 skill（保持连贯性）
        if skill_name in previous_skills:
            score += 1.0

        # 加分：工具依赖满足
        if self._check_skill_dependencies(skill):
            score += 2.0

        if score > 0:
            skill_scores.append((skill_name, score))

    # 4. 排序并返回 top-k
    skill_scores.sort(key=lambda x: x[1], reverse=True)
    selected = [name for name, _ in skill_scores[:max_skills]]

    return selected
```

---

### 3. 智能缓存机制

**避免频繁切换 skills**：

```python
class SkillSelectionCache:
    """Skill 选择缓存"""

    def __init__(self, ttl: int = 3):
        self._cache: dict[str, list[str]] = {}
        self._timestamps: dict[str, float] = {}
        self._ttl = ttl  # 缓存 3 个 iteration

    def get(self, context_hash: str) -> Optional[list[str]]:
        """获取缓存的 skills"""
        if context_hash not in self._cache:
            return None

        age = time.time() - self._timestamps[context_hash]
        if age > self._ttl:
            # 缓存过期
            del self._cache[context_hash]
            return None

        return self._cache[context_hash]

    def set(self, context_hash: str, skills: list[str]):
        """缓存 skills"""
        self._cache[context_hash] = skills
        self._timestamps[context_hash] = time.time()
```

**使用**：
```python
# 计算上下文 hash
context_hash = hashlib.md5(context.encode()).hexdigest()[:8]

# 尝试从缓存获取
cached_skills = self._skill_cache.get(context_hash)
if cached_skills:
    current_skills = cached_skills
else:
    # 重新选择
    current_skills = self._select_skills_dynamic(context)
    self._skill_cache.set(context_hash, current_skills)
```

---

### 4. 避免重复选择

**只在必要时重新选择**：

```python
# 检测是否需要重新选择
def _should_reselect_skills(
    self,
    previous_thought: str,
    current_thought: str,
    previous_skills: list[str],
) -> bool:
    """
    判断是否需要重新选择 skills

    Returns:
        True if reselection is needed
    """
    # 1. 提取思考意图
    prev_intent = self._extract_intent(previous_thought)
    curr_intent = self._extract_intent(current_thought)

    # 2. 意图没有变化 → 不重新选择
    if prev_intent == curr_intent:
        return False

    # 3. 当前 skills 已经覆盖需要的 tools → 不重新选择
    if self._skills_cover_tools(previous_skills, curr_intent):
        return False

    # 4. 需要重新选择
    return True


def _extract_intent(self, thought: str) -> str:
    """提取思考的意图（关键词）"""
    keywords = []
    for word in thought.split():
        if len(word) > 4:  # 长词可能是意图词
            keywords.append(word.lower())
    return " ".join(keywords)


def _skills_cover_tools(self, skills: list[str], intent: str) -> bool:
    """检查当前 skills 是否覆盖需要的 tools"""
    # 例如：intent 包含 "http"，检查 http skill 是否存在
    required_tools = self._infer_required_tools(intent)

    for skill_name in skills:
        skill = self._skills.get(skill_name)
        if skill and skill.metadata.recommended_tools:
            available = set(skill.metadata.recommended_tools)
            if available & set(required_tools):
                return True

    return False
```

---

## 性能优化

### 避免频繁重新选择

```python
# ✅ 只在必要时重新选择
RESELECT_INTERVAL = 3  # 每 3 个 iteration 重新选择一次

if iteration_count % RESELECT_INTERVAL == 0:
    # 重新评估 skills
    current_skills = self._select_skills_dynamic(context)
```

### Token 开销控制

```python
# ✅ 只在 system prompt 中包含当前 skills
def _build_system_prompt_with_skills(self, skills: list[str]) -> str:
    # 只注入当前 iteration 的 skills
    # 不是所有可用 skills
    ...
```

---

## 完整流程

```python
async def run_event_stream(query, skills=None):
    iteration_count = 0
    current_skills = skills or []

    # 初始选择
    if self._auto_select_skills and not current_skills:
        current_skills = self._select_skills_auto(query)

    while iteration_count < max_iterations:
        # === 动态调整 skills ===
        if iteration_count > 0 and self._auto_select_skills:
            # 1. 构建上下文
            context = self._build_selection_context(
                query,
                history,
                thoughts,
                tool_calls,
            )

            # 2. 判断是否需要重新选择
            if self._should_reselect_skills(
                thoughts[-2] if len(thoughts) >= 2 else "",
                thoughts[-1] if thoughts else "",
                current_skills,
            ):
                # 3. 重新选择
                new_skills = self._select_skills_dynamic(context)

                # 4. 检查是否有变化
                if set(new_skills) != set(current_skills):
                    current_skills = new_skills
                    # emit event: skills changed
                    yield AgentEvent.skills_changed(current_skills)

        # === 重新构建 system prompt ===
        system_prompt = self._build_system_prompt_with_skills(current_skills)

        # === Brain: 生成 THOUGHT ===
        thought = await self._core.generate_thought(messages)
        thoughts.append(thought)
        yield AgentEvent.think(session_id, thought)

        # === Body: 执行工具 ===
        tool_call = await self._core.generate_tool_call(messages)
        tool_calls.append(tool_call)
        yield AgentEvent.tool_call(session_id, tool_call)

        # === 执行并返回结果 ===
        result = await self._tools.execute(...)
        yield AgentEvent.tool_result(session_id, result)

        iteration_count += 1
```

---

## 优势

### 1️⃣ **更灵活**

- ✅ 根据当前状态动态调整 skills
- ✅ 不同阶段使用不同的 skills
- ✅ 更好的适应性

### 2️⃣ **更智能**

- ✅ Agent 可以"意识到"需要不同的 skills
- ✅ 避免一开始就加载所有 skills
- ✅ 减少 token 消耗

### 3️⃣ **更高效**

- ✅ 只加载当前需要的 skills
- ✅ 避免不必要的 skills 占用 context
- ✅ 减少 token 开销

---

## 注意事项

### ⚠️ **性能考虑**

1. **避免频繁重新选择**
   - 使用缓存机制
   - 设置重新选择间隔（如每 3 个 iteration）
   - 只在必要时重新选择

2. **控制 Token 开销**
   - System prompt 重建会增加 token
   - 但动态 skills 减少不必要的 skills，总体可能更省

3. **连贯性**
   - 避免频繁切换 skills
   - 给最近使用的 skills 加分
   - 保持 skills 的稳定性

---

## 实施优先级

### Phase 1: 基础实现（1 周）

1. ✅ 添加 `_build_selection_context()` 方法
2. ✅ 添加 `_select_skills_dynamic()` 方法
3. ✅ 在 ReAct 循环中集成动态选择

### Phase 2: 优化（1 周）

1. ✅ 添加缓存机制（`SkillSelectionCache`）
2. ✅ 添加智能重新选择判断（`_should_reselect_skills()`）
3. ✅ 添加连贯性保持（给 recent skills 加分）

### Phase 3: 完善（1 周）

1. ✅ 添加 `skills_changed` event
2. ✅ 性能监控和调优
3. ✅ 文档和测试

---

## 总结

**当前问题**：
- ❌ Skills 只在开始时选择一次
- ❌ 无法根据中间思考调整
- ❌ 不够灵活和智能

**改进方案**：
- ✅ 每次 THOUGHT 后重新评估
- ✅ 根据当前上下文动态选择
- ✅ 智能缓存避免频繁切换
- ✅ 更灵活、更智能、更高效

**这才是真正的"思考"机制！**

---

**作者**: FastReAct Team
**设计原则**: 动态适应，智能选择
**状态**: 设计完成，待实施
