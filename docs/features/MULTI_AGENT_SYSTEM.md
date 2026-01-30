# 多智能体系统使用指南

> **Phase 1: 多智能体协作** - 专用智能体 + 自动路由 + 会话绑定

---

## 概述

FastReAct 现在支持多智能体系统，可以根据任务类型自动路由到合适的专用智能体，提升任务完成质量。

**核心特性**：
- ✅ **专用智能体** - ResearchAgent, CodeAgent, CreativeAgent
- ✅ **自动路由** - 根据任务类型自动选择智能体
- ✅ **会话绑定** - 会话可以绑定到特定智能体
- ✅ **灵活扩展** - 轻松添加自定义智能体

---

## 快速开始

### 1. 创建多智能体系统

```python
from fastreact import FastReAct
from fastreact.agents import (
    AgentRouter,
    create_agent_from_fastreact
)

# 创建 FastReAct 实例
fastreact = FastReAct(
    api_key="your-api-key",
    model="gpt-4",
    tools=[...]
)

# 创建路由器
router = AgentRouter()

# 创建并注册智能体
researcher = create_agent_from_fastreact(
    name="researcher",
    role="研究专家",
    description="擅长信息搜索和分析",
    fastreact=fastreact
)
router.register_agent(researcher)

coder = create_agent_from_fastreact(
    name="coder",
    role="编程专家",
    description="擅长编程和调试",
    fastreact=fastreact
)
router.register_agent(coder)

# ...
```

### 2. 使用智能体路由

```python
# 自动路由 - 根据任务类型自动选择
task1 = "帮我写一个排序算法"
agent1 = router.route(task1)
print(f"Task: {task1}")
print(f"Routed to: {agent1.name}")  # 输出: coder

task2 = "研究一下AI发展趋势"
agent2 = router.route(task2)
print(f"Routed to: {agent2.name}")  # 输出: researcher
```

### 3. 会话绑定

```python
# 绑定会话到特定智能体
session_id = "user_session_123"
router.bind_session_agent(session_id, "coder")

# 该会话的后续任务都会路由到 coder
agent = router.route("继续刚才的代码", session_id=session_id)
print(f"Agent: {agent.name}")  # 输出: coder

# 解绑会话
router.unbind_session(session_id)
```

---

## 内置智能体

### ResearchAgent（研究专家）

**擅长**：
- 信息搜索和收集
- 数据分析和总结
- 事实核查
- 结构化报告

**适用任务**：
```
- "搜索最新AI新闻"
- "分析市场数据"
- "总结研究报告"
- "查找技术资料"
```

### CodeAgent（编程专家）

**擅长**：
- 编写和优化代码
- 调试和修复 bug
- 代码审查
- 技术问题解决

**适用任务**：
```
- "写一个快速排序"
- "这个函数有bug"
- "优化这段代码"
- "解释这个算法"
```

### CreativeAgent（创意专家）

**擅长**：
- 文案创作
- 内容策划
- 品牌叙事
- 营销文案

**适用任务**：
```
- "写一个产品介绍"
- "创作广告文案"
- "设计品牌故事"
- "策划营销活动"
```

### GeneralAgent（通用助手）

**擅长**：
- 处理各类任务
- 回答通用问题
- 提供建议

**适用任务**：
```
- "今天天气怎么样"
- "推荐几本书"
- "讲个笑话"
```

---

## 高级用法

### 1. 自定义智能体

```python
from fastreact.agents import FastReActAgentWrapper

class CustomAgent(FastReActAgentWrapper):
    async def execute(self, task, context=None, **kwargs):
        # 自定义执行逻辑
        if "特殊关键词" in task:
            # 特殊处理
            return {
                "success": True,
                "result": "特殊处理结果"
            }
        else:
            # 默认使用 FastReAct
            return await super().execute(task, context, **kwargs)

# 注册自定义智能体
custom_agent = CustomAgent(
    name="custom",
    role="自定义专家",
    description="处理特殊任务",
    fastreact=fastreact
)
router.register_agent(custom_agent)
```

### 2. 智能体协作

```python
# 通用智能体将复杂任务分解
manager = router.get_agent("manager")

# 子任务1 - 研究
research_task = "研究相关技术"
research_agent = router.route(research_task)
research_result = await research_agent.execute(research_task)

# 子任务2 - 编码
code_task = "根据研究结果实现原型"
coder_agent = router.route(code_task)
code_result = await coder_agent.execute(code_task)

# 汇总结果
final_result = {
    "research": research_result,
    "code": code_result
}
```

### 3. 动态切换智能体

```python
# 用户请求切换智能体
session_id = "user_123"
user_request = "我想用代码模式"

# 识别并切换
if "代码模式" in user_request:
    router.bind_session_agent(session_id, "coder")
    return {"message": "已切换到编程模式"}

# 后续对话自动使用 coder
```

---

## API 参考

### AgentRouter

#### `register_agent(agent: Agent) -> None`
注册智能体到路由器。

#### `route(task: str, session_id: str = None, force_agent: str = None) -> Agent`
路由任务到合适的智能体。

**参数**：
- `task`: 任务描述
- `session_id`: 会话 ID（用于绑定）
- `force_agent`: 强制使用的智能体

**返回**：选定的智能体

#### `bind_session_agent(session_id: str, agent_name: str) -> bool`
绑定会话到智能体。

#### `unbind_session(session_id: str) -> bool`
解绑会话。

#### `get_session_agent(session_id: str) -> Optional[str]`
获取会话绑定的智能体名称。

#### `list_agents() -> List[Dict]`
列出所有智能体信息。

#### `get_stats() -> Dict`
获取路由器统计信息。

---

## 路由规则

### 优先级

1. **强制指定** - `force_agent` 参数
2. **会话绑定** - `session_id` 已绑定
3. **自动分类** - 基于任务关键词

### 关键词匹配

| 智能体 | 关键词 |
|--------|--------|
| **coder** | 代码、编程、debug、算法、函数、API |
| **researcher** | 搜索、研究、分析、数据、报告、统计 |
| **creator** | 写、创作、文案、内容、设计、创意 |

---

## 实际示例

### 示例 1：代码问答

```python
task = "帮我写一个二分查找算法"

# 自动路由到 CodeAgent
agent = router.route(task)
result = await agent.execute(task)

print(result["result"])
# 输出: Python 代码实现二分查找
```

### 示例 2：跨智能体协作

```python
# 用户问题："帮我开发一个功能"

# Manager 分解任务
subtasks = [
    ("研究现有方案", "researcher"),
    ("设计架构", "general"),
    ("编写代码", "coder"),
    ("编写文档", "creator")
]

results = {}
for task, agent_name in subtasks:
    agent = router.get_agent(agent_name)
    result = await agent.execute(task)
    results[agent_name] = result

print("协作完成:", results)
```

### 示例 3：渐进式任务

```python
session_id = "progressive_task"

# 步骤1：研究
router.bind_session_agent(session_id, "researcher")
agent1 = router.route("研究最佳实践", session_id=session_id)

# 步骤2：实现
router.bind_session_agent(session_id, "coder")
agent2 = router.route("根据研究结果实现", session_id=session_id)

# 步骤3：文档
router.bind_session_agent(session_id, "creator")
agent3 = router.route("编写使用文档", session_id=session_id)

# 完成
router.unbind_session(session_id)
```

---

## 最佳实践

### 1. 智能体命名

- 使用清晰的英文名称（小写）
- 体现智能体的主要功能
- 避免使用通用名称（如 `agent1`, `helper`）

**推荐**：
```python
✅ researcher, coder, creator, analyzer
❌ agent1, assistant, helper, bot
```

### 2. 角色定位

- 每个智能体有明确的专长领域
- 避免功能重叠过多
- 保持专注和精简

### 3. 会话管理

- 长时间任务建议绑定智能体
- 通用任务使用自动路由
- 完成后及时解绑

### 4. 错误处理

```python
try:
    agent = router.route(task)
    result = await agent.execute(task)

    if not result["success"]:
        # 降级到通用智能体
        general_agent = router.get_agent("general")
        result = await general_agent.execute(task)

except Exception as e:
    logger.error(f"Agent execution failed: {e}")
    # 返回错误信息
```

---

## 后续计划

### Phase 1 完成项 ✅

- ✅ 多智能体基础框架
- ✅ 专用智能体实现
- ✅ 智能体路由器
- ✅ 会话绑定

### Phase 1 待完成项 ⏳

- [ ] Agent-to-Agent 通信工具
- [ ] Gateway 集成
- [ ] 完整测试覆盖

### Phase 2 计划

- [ ] WebSocket 通道集成
- [ ] Telegram/Slack 集成
- [ ] Docker 沙箱

---

**完成时间**: 2026-01-28
**测试状态**: ✅ 基础功能测试通过
**向后兼容**: ✅ 完全兼容
