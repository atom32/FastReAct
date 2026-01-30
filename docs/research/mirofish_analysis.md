# MiroFish vs FastReAct 对比分析

## 📊 核心能力对比

| 能力维度 | FastReAct | MiroFish | 差距分析 |
|---------|-----------|----------|----------|
| **ReACT循环** | ✅ 完整实现 | ✅ 完整实现 | 相当 |
| **工具系统** | ⚠️ 简单基类 | ✅ 完善的工具生态 | MiroFish更强 |
| **记忆系统** | ❌ 仅有LRU缓存 | ✅ Zep向量数据库 + 多种检索工具 | MiroFish远超 |
| **日志系统** | ❌ 无日志 | ✅ 双层日志（JSONL + 控制台） | MiroFish远超 |
| **进度追踪** | ❌ 无进度追踪 | ✅ 实时进度 + 分章节输出 | MiroFish远超 |
| **错误处理** | ⚠️ 基础异常捕获 | ✅ 完善的错误恢复和重试 | MiroFish更强 |
| **Prompt管理** | ⚠️ 硬编码 | ✅ 结构化、多层次Prompt | MiroFish更强 |
| **规划能力** | ❌ 无规划 | ✅ 自动生成大纲 | MiroFish远超 |
| **反思机制** | ❌ 无反思 | ✅ 多轮思考与反思 | MiroFish远超 |
| **可观测性** | ⚠️ 简单统计 | ✅ 详细日志和执行追踪 | MiroFish远超 |

---

## 🎯 MiroFish的8大核心优势

### 1. 强大的工具系统（Tool Ecosystem）

**MiroFish的优势：**
```python
# 丰富的检索工具，针对不同场景优化
tools = {
    "insight_forge": "深度洞察检索 - 自动分解问题，多维度检索",
    "panorama_search": "广度搜索 - 获取全貌和演变过程",
    "quick_search": "快速检索 - 简单查询",
    "interview_agents": "深度采访 - 调用真实Agent采访"
}
```

**FastReAct的不足：**
- 只有基础工具（Calculator、Search、Weather）
- 缺少领域特定的专业工具
- 没有工具选择的智能推荐

**可借鉴的设计：**

```python
class AdvancedToolSystem(Tool):
    """
    增强的工具系统 - 借鉴MiroFish

    特点：
    1. 分层工具设计（基础层、专业层、组合层）
    2. 智能工具推荐（根据任务自动选择最合适的工具）
    3. 工具链编排（支持多工具组合完成复杂任务）
    """

    # 基础层：通用工具
    BASIC_TOOLS = ["search", "calculator", "http"]

    # 专业层：领域特定工具
    DOMAIN_TOOLS = {
        "data_analysis": ["sql_query", "pandas_analyze"],
        "content_generation": ["blog_writer", "summarizer"],
        "knowledge": ["vector_search", "graph_query"]
    }

    # 组合层：工作流工具
    WORKFLOW_TOOLS = ["research_and_write", "analyze_and_report"]

    async def recommend_tool(self, task: str) -> List[Tool]:
        """根据任务推荐最合适的工具"""
        # 使用LLM分析任务，推荐工具
        pass
```

---

### 2. 多层次记忆系统（Memory System）

**MiroFish的优势：**
```python
# 集成Zep向量数据库
class ZepToolsService:
    """专业的记忆和检索服务"""

    # 多种检索模式
    - insight_forge: 混合检索（语义 + 实体 + 关系链）
    - panorama_search: 广度搜索（包含历史信息）
    - quick_search: 快速检索（仅语义）

    # 结构化返回
    SearchResult:
        - facts: 相关事实列表
        - edges: 关系链
        - nodes: 实体信息
```

**FastReAct的不足：**
- 仅有简单的LRU缓存
- 没有向量检索
- 没有记忆分类（情景/语义）
- 没有记忆检索和排序

**可借鉴的设计：**

```python
class EnhancedMemorySystem:
    """
    增强的记忆系统 - 借鉴MiroFish

    三层记忆架构：
    1. 工作记忆（Working Memory）- 当前任务上下文
    2. 短期记忆（Short-term）- 最近的经验，向量存储
    3. 长期记忆（Long-term）- 提炼的规律和模式
    """

    def __init__(self):
        self.vector_db = ChromaDB()  # 向量数据库
        self.working_memory = {}     # 工作记忆
        self.insight_memory = {}     # 洞察记忆

    async def remember(
        self,
        query: str,
        mode: str = "hybrid",  # hybrid | semantic | exact
        limit: int = 10
    ) -> List[Memory]:
        """
        智能记忆检索

        mode选项：
        - hybrid: 语义搜索 + 实体关系（类似insight_forge）
        - semantic: 纯语义搜索（类似quick_search）
        - temporal: 包含时间维度（类似panorama_search）
        """
        pass

    async def memorize(self, experience: Experience):
        """存储新经验，自动分类和索引"""
        # 提取关键实体
        # 生成向量表示
        # 存储到向量数据库
        pass
```

---

### 3. 详细的日志和追踪系统（Logging & Tracing）

**MiroFish的优势：**
```python
class ReportLogger:
    """
    双层日志系统

    1. agent_log.jsonl - 结构化日志
       - 每行一个JSON对象
       - 记录每个步骤的完整信息
       - 便于程序化分析和可视化

    2. console_log.txt - 控制台日志
       - 人可读的格式
       - 便于调试和问题排查
    """

    def log(self, action, stage, details):
        """记录每个动作"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": self._get_elapsed_time(),
            "action": action,  # tool_call, llm_response, section_complete
            "stage": stage,    # planning, generating, completed
            "details": details  # 完整内容，不截断
        }
```

**FastReAct的不足：**
- 没有日志系统
- 只有简单的统计
- 无法追踪执行过程
- 无法调试和复现

**可借鉴的设计：**

```python
class AgentLogger:
    """
    Agent日志系统 - 借鉴MiroFish

    特点：
    1. 结构化日志（JSONL格式）
    2. 多维度追踪（时间、性能、工具、思考）
    3. 可视化友好（便于前端展示）
    4. 调试友好（便于问题排查）
    """

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.log_file = f"logs/{run_id}.jsonl"
        self.start_time = time.time()

    def log_step(self, step: ReACTStep):
        """记录ReACT步骤"""
        self._write_log({
            "type": "step",
            "iteration": step.iteration,
            "thought": step.thought,
            "tool_calls": [tc.to_dict() for tc in step.tool_calls],
            "observation": step.observation,
            "timestamp": time.time() - self.start_time
        })

    def log_tool_call(self, tool_name: str, params: Dict, result: Any):
        """记录工具调用"""
        self._write_log({
            "type": "tool_call",
            "tool": tool_name,
            "parameters": params,
            "result": str(result)[:1000],  # 限制长度
            "timestamp": time.time() - self.start_time
        })

    def get_execution_trace(self) -> List[Dict]:
        """获取完整执行轨迹（用于可视化）"""
        trace = []
        with open(self.log_file, 'r') as f:
            for line in f:
                trace.append(json.loads(line))
        return trace
```

---

### 4. 实时进度追踪（Progress Tracking）

**MiroFish的优势：**
```python
class ReportManager:
    """
    分章节输出 + 实时进度

    文件结构：
    reports/{report_id}/
        meta.json       # 报告元信息
        outline.json    # 报告大纲
        progress.json   # 实时进度
        section_01.md   # 第1章节（生成完立即保存）
        section_02.md   # 第2章节
        ...
        full_report.md  # 完整报告
    """

    def update_progress(self, status, progress, message, current_section):
        """更新进度，前端可实时读取"""
        progress_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "current_section": current_section,
            "completed_sections": completed_sections,
            "updated_at": datetime.now().isoformat()
        }
```

**FastReAct的不足：**
- 没有进度追踪
- 必须等待全部完成
- 无法知道执行状态

**可借鉴的设计：**

```python
class ProgressTracker:
    """
    进度追踪系统 - 借鉴MiroFish

    特点：
    1. 实时进度更新
    2. 分阶段输出（边生成边保存）
    3. 前端可轮询获取
    4. 支持断点续传
    """

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.progress_file = f"progress/{task_id}.json"
        self.outputs = {}

    def update(self, stage: str, progress: int, message: str):
        """更新进度"""
        self._write_progress({
            "stage": stage,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

    def save_intermediate(self, key: str, content: Any):
        """保存中间结果"""
        self.outputs[key] = content
        # 立即写入文件
        self._write_output(key, content)
```

---

### 5. 高级Prompt工程（Advanced Prompting）

**MiroFish的优势：**
```python
# 多层次、结构化的Prompt设计

system_prompt = f"""
你是一个「未来预测报告」的撰写专家，拥有对模拟世界的「上帝视角」。

═══════════════════════════════════════════════════════════════
【核心理念】
═══════════════════════════════════════════════════════════════
模拟世界是对未来的预演...

═══════════════════════════════════════════════════════════════
【最重要的规则 - 必须遵守】
═══════════════════════════════════════════════════════════════
1. 【必须调用工具观察模拟世界】
2. 【必须引用Agent的原始言行】
3. 【忠实呈现预测结果】

═══════════════════════════════════════════════════════════════
【⚠️ 格式规范 - 极其重要！】
═══════════════════════════════════════════════════════════════
【一个章节 = 最小内容单位】
- ❌ 禁止在章节内使用任何 Markdown 标题
- ✅ 使用**粗体**、段落分隔、引用、列表来组织内容
"""
```

**FastReAct的不足：**
- Prompt简短
- 没有强调关键规则
- 没有格式规范

**可借鉴的设计：**

```python
class PromptManager:
    """
    Prompt管理系统 - 借鉴MiroFish

    特点：
    1. 模板化Prompt
    2. 分层设计（理念→规则→格式→示例）
    3. 上下文感知（根据任务动态调整）
    """

    def build_system_prompt(
        self,
        task_type: str,
        tools: List[Tool],
        context: Dict
    ) -> str:
        """构建系统Prompt"""

        # 模板选择
        template = self.get_template(task_type)

        # 动态填充
        prompt = template.format(
            role=self._get_role_description(task_type),
            rules=self._get_rules(task_type),
            tools=self._get_tools_description(tools),
            format=self._get_format_requirements(task_type),
            examples=self._get_examples(task_type)
        )

        return prompt

    def get_template(self, task_type: str) -> str:
        """获取Prompt模板"""
        templates = {
            "analysis": ANALYSIS_TEMPLATE,
            "generation": GENERATION_TEMPLATE,
            "planning": PLANNING_TEMPLATE
        }
        return templates.get(task_type, DEFAULT_TEMPLATE)
```

---

### 6. 任务规划能力（Task Planning）

**MiroFish的优势：**
```python
class ReportAgent:
    """
    先规划，再执行

    阶段1：规划大纲
    - 分析模拟需求
    - 生成报告结构
    - 返回章节列表

    阶段2：逐章节生成
    - 每个章节独立ReACT循环
    - 支持工具调用和信息检索
    - 上下文连贯性管理
    """

    def plan_outline(self) -> ReportOutline:
        """使用LLM规划报告大纲"""
        # 1. 获取模拟上下文
        context = self.zep_tools.get_simulation_context(...)

        # 2. 调用LLM生成大纲
        outline = self.llm.chat_json(
            system_prompt=OUTLINE_PROMPT,
            user_prompt=f"模拟需求：{self.simulation_requirement}"
        )

        # 3. 解析并返回结构化大纲
        return ReportOutline.from_dict(outline)
```

**FastReAct的不足：**
- 没有规划能力
- 直接开始ReACT循环
- 无法分解复杂任务

**可借鉴的设计：**

```python
class TaskPlanner:
    """
    任务规划器 - 借鉴MiroFish

    特点：
    1. 自动任务分解
    2. 生成执行计划
    3. 支持计划调整
    """

    async def plan(self, goal: str, context: Context) -> Plan:
        """规划执行计划"""
        # 1. 分析任务
        analysis = await self._analyze_task(goal, context)

        # 2. 分解子任务
        subtasks = await self._decompose_task(analysis)

        # 3. 生成依赖关系
        dependencies = self._build_dependencies(subtasks)

        # 4. 生成执行计划
        plan = Plan(
            goal=goal,
            subtasks=subtasks,
            dependencies=dependencies
        )

        return plan

    async def adjust_plan(
        self,
        plan: Plan,
        feedback: Feedback
    ) -> Plan:
        """根据反馈调整计划"""
        # 重新规划未完成的任务
        pass
```

---

### 7. 多轮反思机制（Multi-round Reflection）

**MiroFish的优势：**
```python
class ReportAgent:
    """
    多轮思考与反思

    每个章节的生成过程：
    1. Thought: 思考需要什么信息
    2. Action: 调用工具获取信息
    3. Observation: 分析工具返回结果
    4. Reflection: 评估是否足够
    5. 重复或Final Answer
    """

    MAX_TOOL_CALLS_PER_SECTION = 5  # 最多5轮
    MIN_TOOL_CALLS_PER_SECTION = 2  # 至少2轮

    # 如果工具调用不足，强制继续
    if tool_calls_count < self.MIN_TOOL_CALLS_PER_SECTION:
        messages.append({
            "role": "user",
            "content": f"【注意】你只调用了{tool_calls_count}次工具，信息可能不够充分。请再调用1-2次工具..."
        })
        continue
```

**FastReAct的不足：**
- 简单的ReACT循环
- 没有强制反思
- 没有质量检查

**可借鉴的设计：**

```python
class ReflectionEngine:
    """
    反思引擎 - 借鉴MiroFish

    特点：
    1. 评估答案质量
    2. 识别信息缺口
    3. 决定是否继续检索
    """

    async def reflect(
        self,
        current_answer: str,
        tool_calls_made: int,
        context: Context
    ) -> Reflection:
        """反思当前答案"""
        reflection = await self.llm.chat(
            system_prompt=REFLECTION_PROMPT,
            user_prompt=f"""
            当前答案：{current_answer}
            已调用工具次数：{tool_calls_made}

            请评估：
            1. 答案是否完整？
            2. 是否有重要信息缺失？
            3. 是否需要更多信息？

            返回JSON：{{"complete": true/false, "missing": [...], "suggestions": [...]}}
            """
        )

        return Reflection.from_dict(reflection)
```

---

### 8. 优雅的错误处理（Error Handling）

**MiroFish的优势：**
```python
class ZepToolsService:
    """完善的错误处理和重试"""

    async def insight_forge(self, ...):
        """指数退避重试"""
        for attempt in range(MAX_RETRIES):
            try:
                result = await self._call_zep_api(...)
                return result
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    logger.warning(f"重试 {attempt + 1}/{MAX_RETRIES}")
                    await asyncio.sleep(wait_time)
                else:
                    # 最终失败，返回降级结果
                    return self._get_fallback_result()
```

**FastReAct的不足：**
- 简单的try-except
- 没有重试机制
- 没有降级策略

**可借鉴的设计：**

```python
class RetryHandler:
    """
    重试处理器 - 借鉴MiroFish

    特点：
    1. 指数退避重试
    2. 最大重试次数限制
    3. 降级策略
    """

    async def execute_with_retry(
        self,
        func: Callable,
        max_retries: int = 3,
        backoff_base: float = 2.0,
        fallback: Any = None
    ):
        """带重试的执行"""
        last_error = None

        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = backoff_base ** attempt
                    logger.warning(f"重试 {attempt + 1}/{max_retries}")
                    await asyncio.sleep(wait_time)

        # 所有重试都失败，返回降级结果
        if fallback is not None:
            return fallback
        raise last_error
```

---

## 🚀 FastReAct改进路线图

基于MiroFish的优势，FastReAct可以按以下优先级改进：

### Phase 1: 可观测性（2周）- 最高优先级
- [x] ✅ 基础ReACT循环
- [ ] 添加双层日志系统（JSONL + 控制台）
- [ ] 添加进度追踪和中间输出
- [ ] 添加执行轨迹可视化

### Phase 2: 记忆系统（3-4周）- 高优先级
- [ ] 集成向量数据库（Chroma）
- [ ] 实现多层次记忆（工作/短期/长期）
- [ ] 添加智能记忆检索
- [ ] 实现记忆巩固机制

### Phase 3: 工具生态（2-3周）- 中优先级
- [ ] 完善基础工具库
- [ ] 添加领域特定工具
- [ ] 实现工具推荐系统
- [ ] 支持工具链编排

### Phase 4: 高级能力（4-6周）- 中优先级
- [ ] 实现任务规划器
- [ ] 添加反思机制
- [ ] 改进Prompt工程
- [ ] 添加错误重试

### Phase 5: 生产就绪（2-3周）- 低优先级
- [ ] 添加测试覆盖
- [ ] 性能优化
- [ ] 部署方案
- [ ] 文档完善

---

## 💡 关键设计模式

从MiroFish中学到的关键设计模式：

### 1. 分层架构
```
应用层    - ReportAgent（业务逻辑）
  ↓
服务层    - ZepToolsService（专业服务）
  ↓
框架层    - HighPerformanceReACT（通用框架）
  ↓
基础设施  - LLMClient, 向量数据库
```

### 2. 关注点分离
- 日志与逻辑分离（ReportLogger）
- 进度与执行分离（ProgressManager）
- 存储与业务分离（ReportManager）

### 3. 可观测性优先
- 每个动作都有日志
- 每个阶段都有进度
- 每个结果都可追溯

### 4. 渐进式输出
- 边生成边保存
- 分章节实时输出
- 前端可轮询获取

---

这个对比分析为FastReAct的改进提供了明确的方向和具体的实现参考。
