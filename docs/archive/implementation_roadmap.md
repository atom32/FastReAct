# FastReAct 功能完整版 - 8周实现路线图

## 🎯 目标定位

**方案B：功能完整版（6-8周）**

从基础ReACT框架升级为具备以下能力的智能体框架：
- ✅ 可观测性（日志、追踪、可视化）
- ✅ 长期记忆（向量数据库）
- ✅ 任务规划（自动分解）
- ✅ 反思机制（质量提升）

---

## 📋 总体时间规划

| 阶段 | 时间 | 核心目标 | 交付物 |
|------|------|----------|--------|
| **Phase 1** | 第1-2周 | 可观测性基础 | 日志系统 + 进度追踪 |
| **Phase 2** | 第3-4周 | 记忆系统 | 向量数据库集成 |
| **Phase 3** | 第5-6周 | 智能规划 | 任务规划器 |
| **Phase 4** | 第7-8周 | 质量提升 | 反思机制 + 测试 |

---

## 🗓️ 详细实现计划

### Phase 1: 可观测性基础（第1-2周）

#### 目标
让Agent的执行过程完全透明，可追踪、可调试、可优化。

#### Week 1: 日志系统

**Day 1-2: 设计日志架构**
```python
# 设计目标
- 双层日志：结构化日志（JSONL）+ 人读日志（TXT）
- 多维度：时间、性能、工具调用、思考过程
- 可扩展：支持自定义日志字段
- 性能友好：异步写入，不阻塞主流程

# 文件结构
logs/
  {run_id}/
    agent_log.jsonl     # 结构化日志
    console_log.txt     # 控制台日志
    metrics.json        # 性能指标
```

**Day 3-4: 实现核心日志类**
```python
# src/fastreact/observability/logger.py

class AgentLogger:
    """Agent日志系统"""

    def __init__(self, run_id: str, log_dir: str = "logs"):
        self.run_id = run_id
        self.log_dir = log_dir
        self.log_file = f"{log_dir}/{run_id}/agent_log.jsonl"
        self.console_file = f"{log_dir}/{run_id}/console_log.txt"
        self.start_time = time.time()

        # 性能统计
        self.metrics = {
            "llm_calls": 0,
            "tool_calls": 0,
            "total_tokens": 0,
            "errors": 0
        }

    def log_start(self, config: Dict):
        """记录运行开始"""
        self._write_log({
            "type": "run_start",
            "run_id": self.run_id,
            "config": config,
            "timestamp": time.time()
        })

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

    def log_tool_call(self, tool_name: str, params: Dict, result: Any, duration: float):
        """记录工具调用"""
        self.metrics["tool_calls"] += 1
        self._write_log({
            "type": "tool_call",
            "tool": tool_name,
            "parameters": params,
            "result": str(result)[:1000],
            "duration": duration,
            "timestamp": time.time() - self.start_time
        })

    def log_llm_call(self, messages: List, response: str, duration: float, tokens: int):
        """记录LLM调用"""
        self.metrics["llm_calls"] += 1
        self.metrics["total_tokens"] += tokens
        self._write_log({
            "type": "llm_call",
            "messages": messages,
            "response": response,
            "tokens": tokens,
            "duration": duration,
            "timestamp": time.time() - self.start_time
        })

    def log_error(self, error: Exception, context: Dict):
        """记录错误"""
        self.metrics["errors"] += 1
        self._write_log({
            "type": "error",
            "error": str(error),
            "context": context,
            "timestamp": time.time() - self.start_time
        })

    def log_complete(self, result: Any):
        """记录运行完成"""
        self._write_log({
            "type": "run_complete",
            "result": str(result)[:500],
            "metrics": self.metrics,
            "total_time": time.time() - self.start_time,
            "timestamp": time.time() - self.start_time
        })

    def _write_log(self, log_entry: Dict):
        """写入日志（异步）"""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
```

**Day 5-6: 集成到FastReAct引擎**
```python
# src/fastreact/core/engine.py

class FastReAct:
    def __init__(
        self,
        ...,
        enable_logging: bool = True,
        log_dir: str = "logs"
    ):
        ...
        self.enable_logging = enable_logging
        self.log_dir = log_dir
        self.logger = None

    async def run_async(self, query: str, ...) -> Dict:
        # 初始化日志
        if self.enable_logging:
            run_id = f"run_{uuid.uuid4().hex[:12]}"
            self.logger = AgentLogger(run_id, self.log_dir)
            self.logger.log_start({
                "query": query,
                "model": self.model,
                "tools": list(self.tools.keys())
            })

        for iteration in range(self.max_iterations):
            # 记录步骤
            if self.logger:
                self.logger.log_step(step)

            # 记录工具调用
            if self.logger:
                for result in results:
                    self.logger.log_tool_call(
                        tool_name=result.tool_name,
                        parameters=tool_call.parameters,
                        result=result.result,
                        duration=result.execution_time
                    )

        # 记录完成
        if self.logger:
            self.logger.log_complete(result)

        return result
```

**Day 7: 单元测试**
```python
# tests/test_logger.py

def test_logger_creation():
    """测试日志创建"""
    logger = AgentLogger("test_run")
    assert logger.run_id == "test_run"

def test_log_step():
    """测试步骤日志"""
    logger = AgentLogger("test_run")
    step = ReACTStep(thought="测试思考", iteration=0)
    logger.log_step(step)

    # 读取日志文件验证
    with open(logger.log_file, 'r') as f:
        log = json.loads(f.readline())
        assert log["type"] == "step"
        assert log["thought"] == "测试思考"
```

#### Week 2: 进度追踪 + Prompt优化

**Day 1-3: 进度追踪系统**
```python
# src/fastreact/observability/progress.py

class ProgressTracker:
    """进度追踪系统"""

    def __init__(self, run_id: str, progress_dir: str = "progress"):
        self.run_id = run_id
        self.progress_file = f"{progress_dir}/{run_id}/progress.json"
        self.outputs_dir = f"{progress_dir}/{run_id}/outputs"

    def update(
        self,
        stage: str,           # planning, executing, completed
        progress: int,        # 0-100
        message: str,
        current_step: str = None,
        completed_steps: List[str] = None
    ):
        """更新进度"""
        progress_data = {
            "run_id": self.run_id,
            "stage": stage,
            "progress": progress,
            "message": message,
            "current_step": current_step,
            "completed_steps": completed_steps or [],
            "updated_at": datetime.now().isoformat()
        }

        os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)

    def save_intermediate(self, key: str, content: Any):
        """保存中间结果"""
        os.makedirs(self.outputs_dir, exist_ok=True)
        output_file = f"{self.outputs_dir}/{key}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            if isinstance(content, str):
                f.write(content)
            else:
                json.dump(content, f, ensure_ascii=False, indent=2)
```

**Day 4-7: Prompt工程优化**
```python
# src/fastreact/prompts/manager.py

class PromptManager:
    """Prompt管理系统"""

    def __init__(self):
        self.templates = self._load_templates()

    def build_system_prompt(
        self,
        task_type: str,
        tools: List[Tool],
        context: Dict = None
    ) -> str:
        """构建系统Prompt"""

        # 获取模板
        template = self.get_template(task_type)

        # 构建工具描述
        tools_desc = self._build_tools_description(tools)

        # 构建规则
        rules = self._get_rules(task_type)

        # 构建格式要求
        format_reqs = self._get_format_requirements(task_type)

        # 填充模板
        prompt = template.format(
            role=self._get_role(task_type),
            tools=tools_desc,
            rules=rules,
            format=format_reqs,
            examples=self._get_examples(task_type)
        )

        return prompt

    def _build_tools_description(self, tools: List[Tool]) -> str:
        """构建工具描述"""
        descriptions = []

        for tool in tools:
            desc = f"""
### {tool.name}

**描述**: {tool.description}

**参数**:
```json
{json.dumps(tool.parameters, ensure_ascii=False, indent=2)}
```

**使用场景**: {self._get_tool_usage_example(tool)}
"""
            descriptions.append(desc)

        return "\n\n".join(descriptions)

    def get_template(self, task_type: str) -> str:
        """获取Prompt模板"""

        templates = {
            "default": """
你是一个智能助手，可以使用以下工具来完成任务：

{tools}

## 工作流程

1. **Thought**: 思考需要什么信息来回答问题
2. **Action**: 调用工具获取信息
3. **Observation**: 分析工具返回结果
4. **循环**: 重复步骤1-3，直到收集到足够信息
5. **Final Answer**: 基于工具结果给出最终答案

## 工具调用格式

使用以下格式调用工具：
```
[TOOL_CALL] {{"name": "工具名", "parameters": {{"参数名": "参数值"}}}}
```

## 重要提示

- 一次可以调用多个工具（用多个[TOOL_CALL]标记）
- 工具调用结果会给你提供更多信息
- 最终答案必须基于工具返回的结果，不要编造
- 如果信息足够，直接给出Final Answer，不再调用工具
""",

            "planning": """
你是一个任务规划专家，负责将复杂任务分解为可执行的子任务。

{tools}

## 规划原则

1. **目标导向**: 每个子任务都有明确的目标
2. **可执行性**: 子任务应该具体且可执行
3. **逻辑顺序**: 子任务之间有合理的依赖关系
4. **完整性**: 所有子任务合起来能完成总目标

## 输出格式

请以JSON格式输出规划结果：
```json
{{
  "goal": "总目标",
  "subtasks": [
    {{
      "title": "子任务1",
      "description": "描述",
      "dependencies": [],
      "estimated_steps": 3
    }}
  ]
}}
```
"""
        }

        return templates.get(task_type, templates["default"])
```

**集成到FastReAct：**
```python
class FastReAct:
    def __init__(
        self,
        ...,
        prompt_manager: PromptManager = None
    ):
        ...
        self.prompt_manager = prompt_manager or PromptManager()

    def _build_system_prompt(self) -> str:
        """使用PromptManager构建系统Prompt"""
        return self.prompt_manager.build_system_prompt(
            task_type="default",
            tools=list(self.tools.values()),
            context={}
        )
```

#### Phase 1 验收标准
- [ ] 所有LLM调用都有日志记录
- [ ] 所有工具调用都有日志记录
- [ ] 可通过run_id查询完整执行轨迹
- [ ] 实时进度可通过progress.json获取
- [ ] Prompt清晰、结构化、易于理解
- [ ] 单元测试覆盖率 > 80%

---

### Phase 2: 记忆系统（第3-4周）

#### 目标
实现多层次记忆系统，支持长期记忆存储和智能检索。

#### Week 3: 向量数据库集成

**Day 1-2: 技术选型和安装**
```python
# requirements.txt 添加
chromadb>=0.4.0
sentence-transformers>=2.2.0

# 或使用 Qdrant（更轻量）
# qdrant-client>=1.6.0
```

**Day 3-5: 实现向量存储**
```python
# src/fastreact/memory/vector_store.py

import chromadb
from chromadb.config import Settings

class VectorStore:
    """向量存储"""

    def __init__(
        self,
        collection_name: str = "fastreact_memories",
        persist_dir: str = "./data/chroma",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        # 初始化ChromaDB
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name
        )

        # 初始化embedding模型
        from sentence_transformers import SentenceTransformer
        self.encoder = SentenceTransformer(embedding_model)

    def add(
        self,
        texts: List[str],
        metadatas: List[Dict],
        ids: List[str] = None
    ) -> None:
        """添加文本到向量库"""
        # 生成embeddings
        embeddings = self.encoder.encode(texts).tolist()

        # 生成IDs
        if ids is None:
            ids = [f"mem_{uuid.uuid4().hex}" for _ in texts]

        # 添加到集合
        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    def search(
        self,
        query: str,
        n_results: int = 10,
        where: Dict = None,
        where_document: Dict = None
    ) -> List[Dict]:
        """语义搜索"""
        # 生成query embedding
        query_embedding = self.encoder.encode([query]).tolist()

        # 搜索
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=where,
            where_document=where_document
        )

        # 格式化结果
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'text': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i]
            })

        return formatted_results

    def delete(self, ids: List[str]) -> None:
        """删除记忆"""
        self.collection.delete(ids=ids)

    def get(self, ids: List[str]) -> List[Dict]:
        """获取记忆"""
        results = self.collection.get(ids=ids)
        return results
```

**Day 6-7: 实现记忆管理器**
```python
# src/fastreact/memory/manager.py

class MemoryManager:
    """记忆管理器"""

    def __init__(self, vector_store: VectorStore = None):
        self.vector_store = vector_store or VectorStore()
        self.working_memory = {}  # 工作记忆

    async def remember(
        self,
        query: str,
        memory_type: str = "all",
        limit: int = 10
    ) -> List[Memory]:
        """
        检索记忆

        Args:
            query: 查询内容
            memory_type: 记忆类型（working/episodic/semantic/all）
            limit: 返回数量
        """
        results = []

        # 1. 工作记忆（当前对话）
        if memory_type in ["working", "all"]:
            working_results = self._search_working_memory(query)
            results.extend(working_results)

        # 2. 情景记忆（向量搜索）
        if memory_type in ["episodic", "all"]:
            vector_results = self.vector_store.search(
                query=query,
                n_results=limit,
                where={"type": "episodic"}
            )
            results.extend([
                Memory(
                    content=r['text'],
                    metadata=r['metadata'],
                    relevance=1.0 - r['distance']
                )
                for r in vector_results
            ])

        # 3. 语义记忆（规律和模式）
        if memory_type in ["semantic", "all"]:
            semantic_results = self.vector_store.search(
                query=query,
                n_results=limit // 2,
                where={"type": "semantic"}
            )
            results.extend([
                Memory(
                    content=r['text'],
                    metadata=r['metadata'],
                    relevance=1.0 - r['distance']
                )
                for r in semantic_results
            ])

        # 按相关性排序
        results.sort(key=lambda x: x.relevance, reverse=True)

        return results[:limit]

    async def memorize(
        self,
        content: str,
        memory_type: str = "episodic",
        metadata: Dict = None
    ) -> str:
        """
        存储记忆

        Args:
            content: 记忆内容
            memory_type: 记忆类型（episodic/semantic）
            metadata: 元数据
        """
        metadata = metadata or {}
        metadata.update({
            "type": memory_type,
            "timestamp": datetime.now().isoformat()
        })

        # 存储到向量库
        memory_id = f"mem_{uuid.uuid4().hex}"
        self.vector_store.add(
            texts=[content],
            metadatas=[metadata],
            ids=[memory_id]
        )

        return memory_id

    def _search_working_memory(self, query: str) -> List[Memory]:
        """搜索工作记忆"""
        results = []
        for key, value in self.working_memory.items():
            # 简单的关键词匹配
            if query.lower() in str(value).lower():
                results.append(Memory(
                    content=str(value),
                    metadata={"source": "working_memory", "key": key},
                    relevance=0.8
                ))
        return results
```

#### Week 4: 智能检索

**Day 1-3: 实现多种检索模式**
```python
# src/fastreact/memory/retriever.py

class MemoryRetriever:
    """智能检索器"""

    def __init__(self, memory_manager: MemoryManager):
        self.memory = memory_manager

    async def retrieve(
        self,
        query: str,
        mode: str = "hybrid",
        **kwargs
    ) -> RetrievalResult:
        """
        智能检索

        Args:
            query: 查询内容
            mode: 检索模式
                - semantic: 纯语义搜索
                - hybrid: 语义+关键词混合
                - temporal: 时间加权
                - contextual: 上下文感知
        """
        if mode == "semantic":
            return await self._semantic_search(query, **kwargs)
        elif mode == "hybrid":
            return await self._hybrid_search(query, **kwargs)
        elif mode == "temporal":
            return await self._temporal_search(query, **kwargs)
        elif mode == "contextual":
            return await self._contextual_search(query, **kwargs)
        else:
            raise ValueError(f"Unknown mode: {mode}")

    async def _semantic_search(self, query: str, limit: int = 10):
        """纯语义搜索"""
        memories = await self.memory.remember(
            query=query,
            memory_type="all",
            limit=limit
        )

        return RetrievalResult(
            query=query,
            mode="semantic",
            memories=memories,
            total_found=len(memories)
        )

    async def _hybrid_search(self, query: str, limit: int = 10):
        """混合检索（语义+关键词）"""
        # 1. 语义搜索
        semantic_memories = await self.memory.remember(
            query=query,
            memory_type="episodic",
            limit=limit * 2
        )

        # 2. 关键词匹配
        keywords = self._extract_keywords(query)
        keyword_memories = []
        for memory in semantic_memories:
            keyword_score = self._calculate_keyword_score(
                memory.content,
                keywords
            )
            # 结合语义相关性和关键词匹配度
            memory.relevance = (
                memory.relevance * 0.7 +
                keyword_score * 0.3
            )
            keyword_memories.append(memory)

        # 3. 重新排序
        keyword_memories.sort(key=lambda x: x.relevance, reverse=True)

        return RetrievalResult(
            query=query,
            mode="hybrid",
            memories=keyword_memories[:limit],
            total_found=len(keyword_memories)
        )

    async def _temporal_search(self, query: str, limit: int = 10, recency_weight: float = 0.3):
        """时间加权检索"""
        memories = await self.memory.remember(
            query=query,
            memory_type="episodic",
            limit=limit * 2
        )

        # 计算时间权重（越新的权重越高）
        now = datetime.now()
        for memory in memories:
            timestamp = datetime.fromisoformat(memory.metadata.get("timestamp", ""))
            days_ago = (now - timestamp).days
            time_weight = 1.0 / (1.0 + days_ago / 30.0)  # 30天半衰期

            # 结合相关性和时间权重
            memory.relevance = (
                memory.relevance * (1 - recency_weight) +
                time_weight * recency_weight
            )

        memories.sort(key=lambda x: x.relevance, reverse=True)

        return RetrievalResult(
            query=query,
            mode="temporal",
            memories=memories[:limit],
            total_found=len(memories)
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单实现：提取名词
        import jieba
        import jieba.posseg as pseg

        words = pseg.cut(text)
        keywords = [word for word, flag in words if flag.startswith('n')]
        return list(set(keywords))

    def _calculate_keyword_score(self, text: str, keywords: List[str]) -> float:
        """计算关键词匹配分数"""
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        return min(matches / len(keywords), 1.0) if keywords else 0.0
```

**Day 4-7: 集成到FastReAct**
```python
# src/fastreact/core/engine.py

class FastReAct:
    def __init__(
        self,
        ...,
        enable_memory: bool = True,
        memory_manager: MemoryManager = None
    ):
        ...
        self.enable_memory = enable_memory
        self.memory = memory_manager or MemoryManager()
        self.retriever = MemoryRetriever(self.memory)

    async def run_async(self, query: str, ...) -> Dict:
        # 1. 检索相关记忆
        if self.enable_memory:
            memories = await self.retriever.retrieve(
                query=query,
                mode="hybrid",
                limit=5
            )

            # 将记忆作为上下文
            if memories.memories:
                memory_context = "\n\n".join([
                    f"- {m.content}" for m in memories.memories
                ])
                query = f"相关记忆:\n{memory_context}\n\n当前问题:\n{query}"

        # 2. 正常执行ReACT循环
        ...

        # 3. 存储新经验
        if self.enable_memory and result:
            await self.memory.memorize(
                content=f"问题: {query}\n答案: {result['answer']}",
                memory_type="episodic",
                metadata={
                    "run_id": self.logger.run_id if self.logger else None,
                    "tool_calls": result['stats']['tool_calls']
                }
            )

        return result
```

#### Phase 2 验收标准
- [ ] 向量数据库正常工作
- [ ] 可存储和检索记忆
- [ ] 支持多种检索模式
- [ ] 记忆检索相关性 > 0.7（人工评估）
- [ ] 记忆存储不影响性能（< 100ms）

---

### Phase 3: 任务规划（第5-6周）

#### 目标
实现任务自动分解和规划能力。

#### Week 5: 规划器核心

**Day 1-2: 设计规划器接口**
```python
# src/fastreact/planning/planner.py

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SubTask:
    """子任务"""
    title: str
    description: str
    dependencies: List[str]  # 依赖的子任务ID
    estimated_steps: int
    status: str = "pending"  # pending, in_progress, completed

@dataclass
class Plan:
    """执行计划"""
    goal: str
    subtasks: List[SubTask]
    execution_order: List[List[str]]  # 可并行执行的批次

    def get_next_tasks(self) -> List[SubTask]:
        """获取下一个可执行的任务"""
        pass

class TaskPlanner:
    """任务规划器"""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def plan(
        self,
        goal: str,
        context: Dict = None,
        max_subtasks: int = 5
    ) -> Plan:
        """
        生成执行计划

        Args:
            goal: 总目标
            context: 上下文信息
            max_subtasks: 最大子任务数
        """
        # 1. 分析任务
        analysis = await self._analyze_task(goal, context)

        # 2. 分解子任务
        subtasks = await self._decompose_task(
            goal=goal,
            analysis=analysis,
            max_subtasks=max_subtasks
        )

        # 3. 构建依赖关系
        dependencies = await self._build_dependencies(subtasks)

        # 4. 生成执行顺序
        execution_order = self._topological_sort(subtasks, dependencies)

        return Plan(
            goal=goal,
            subtasks=subtasks,
            execution_order=execution_order
        )

    async def _analyze_task(self, goal: str, context: Dict) -> Dict:
        """分析任务"""
        prompt = f"""
分析以下任务：

任务目标：{goal}

上下文：{context or '无'}

请分析：
1. 任务类型（研究/创作/分析/计算等）
2. 主要难点
3. 需要的信息类型
4. 预估复杂度（简单/中等/复杂）

返回JSON格式。
"""

        response = await self.llm.chat_json(prompt)
        return response

    async def _decompose_task(
        self,
        goal: str,
        analysis: Dict,
        max_subtasks: int
    ) -> List[SubTask]:
        """分解任务"""
        prompt = f"""
将以下任务分解为{max_subtasks}个子任务：

总目标：{goal}
任务分析：{json.dumps(analysis, ensure_ascii=False)}

要求：
1. 每个子任务都有明确目标
2. 子任务之间逻辑清晰
3. 子任务可独立执行
4. 最多{max_subtasks}个子任务

返回JSON格式：
{{
  "subtasks": [
    {{
      "title": "子任务标题",
      "description": "详细描述",
      "estimated_steps": 预估步数
    }}
  ]
}}
"""

        response = await self.llm.chat_json(prompt)

        subtasks = []
        for i, st in enumerate(response['subtasks']):
            subtasks.append(SubTask(
                title=st['title'],
                description=st['description'],
                dependencies=[],
                estimated_steps=st.get('estimated_steps', 3),
                status="pending"
            ))

        return subtasks

    async def _build_dependencies(self, subtasks: List[SubTask]) -> Dict[str, List[str]]:
        """构建依赖关系"""
        # 使用LLM分析依赖关系
        subtask_list = "\n".join([
            f"{i}. {st.title}: {st.description}"
            for i, st in enumerate(subtasks)
        ])

        prompt = f"""
分析以下子任务之间的依赖关系：

{subtask_list}

请判断哪些子任务依赖于其他子任务。

返回JSON格式：
{{
  "dependencies": {{
    "子任务1标题": ["依赖的任务1", "依赖的任务2"],
    ...
  }}
}}
"""

        response = await self.llm.chat_json(prompt)

        # 更新subtasks的dependencies
        dependencies = {}
        for st in subtasks:
            deps = response['dependencies'].get(st.title, [])
            st.dependencies = deps
            dependencies[st.title] = deps

        return dependencies

    def _topological_sort(
        self,
        subtasks: List[SubTask],
        dependencies: Dict[str, List[str]]
    ) -> List[List[str]]:
        """拓扑排序，返回可并行执行的批次"""
        # 构建依赖图
        graph = {st.title: st.dependencies for st in subtasks}
        in_degree = {st.title: 0 for st in subtasks}

        for st in subtasks:
            for dep in st.dependencies:
                if dep in in_degree:
                    in_degree[st.title] += 1

        # 拓扑排序
        queue = [title for title, degree in in_degree.items() if degree == 0]
        batches = []

        while queue:
            batches.append(queue.copy())

            next_queue = []
            for title in queue:
                for st in subtasks:
                    if title in st.dependencies:
                        in_degree[st.title] -= 1
                        if in_degree[st.title] == 0:
                            next_queue.append(st.title)

            queue = next_queue

        return batches
```

**Day 3-5: 实现计划执行器**
```python
# src/fastreact/planning/executor.py

class PlanExecutor:
    """计划执行器"""

    def __init__(self, agent: FastReAct):
        self.agent = agent

    async def execute(
        self,
        plan: Plan,
        progress_callback: Callable = None
    ) -> Dict:
        """
        执行计划

        Args:
            plan: 执行计划
            progress_callback: 进度回调
        """
        results = {
            "goal": plan.goal,
            "subtask_results": [],
            "final_answer": None
        }

        # 按批次执行
        for batch_idx, batch in enumerate(plan.execution_order):
            # 并发执行当前批次的所有任务
            tasks = []
            for title in batch:
                subtask = next(st for st in plan.subtasks if st.title == title)
                task = self._execute_subtask(subtask, progress_callback)
                tasks.append(task)

            batch_results = await asyncio.gather(*tasks)

            # 更新状态
            for subtask, result in zip(batch, batch_results):
                subtask.status = "completed"
                results["subtask_results"].append({
                    "title": subtask.title,
                    "result": result
                })

            if progress_callback:
                progress_callback(
                    stage="executing",
                    progress=int((batch_idx + 1) / len(plan.execution_order) * 100),
                    message=f"完成批次 {batch_idx + 1}/{len(plan.execution_order)}"
                )

        # 汇总最终答案
        results["final_answer"] = self._synthesize_answer(results)

        return results

    async def _execute_subtask(
        self,
        subtask: SubTask,
        progress_callback: Callable
    ) -> str:
        """执行单个子任务"""
        subtask.status = "in_progress"

        if progress_callback:
            progress_callback(
                stage="executing",
                message=f"执行子任务: {subtask.title}"
            )

        # 使用FastReAct执行子任务
        result = await self.agent.run_async(
            query=f"""
任务：{subtask.title}
描述：{subtask.description}

请完成这个子任务。
""",
            step_callback=lambda step: None  # 可添加日志
        )

        return result["answer"]

    def _synthesize_answer(self, results: Dict) -> str:
        """综合最终答案"""
        # 使用LLM综合所有子任务的结果
        subtask_summaries = "\n\n".join([
            f"## {r['title']}\n{r['result']}"
            for r in results["subtask_results"]
        ])

        prompt = f"""
综合以下子任务的执行结果，生成最终答案：

总目标：{results["goal"]}

子任务结果：
{subtask_summaries}

请综合以上结果，给出完整的最终答案。
"""

        final_answer = asyncio.run(self.agent.llm.chat(prompt))
        return final_answer
```

**Day 6-7: 集成和测试**
```python
# src/fastreact/core/engine.py

class FastReAct:
    async def run_with_plan(
        self,
        goal: str,
        enable_planning: bool = True,
        progress_callback: Callable = None
    ) -> Dict:
        """
        带规划的执行

        Args:
            goal: 目标描述
            enable_planning: 是否启用规划
            progress_callback: 进度回调
        """
        if not enable_planning:
            # 直接执行
            return await self.run_async(goal)

        # 1. 规划
        planner = TaskPlanner(self._get_client())
        plan = await planner.plan(goal)

        # 2. 执行计划
        executor = PlanExecutor(self)
        results = await executor.execute(plan, progress_callback)

        return results
```

#### Week 6: 计划调整和优化

**Day 1-3: 动态计划调整**
```python
# src/fastreact/planning/adjuster.py

class PlanAdjuster:
    """计划调整器"""

    async def adjust_plan(
        self,
        plan: Plan,
        feedback: Dict,
        failed_tasks: List[str] = None
    ) -> Plan:
        """
        根据反馈调整计划

        Args:
            plan: 原计划
            feedback: 执行反馈
            failed_tasks: 失败的任务列表
        """
        if not failed_tasks:
            return plan  # 无需调整

        # 分析失败原因
        failed_analysis = await self._analyze_failures(
            plan,
            failed_tasks,
            feedback
        )

        # 重新规划失败的任务
        new_plan = await self._replan_failed_tasks(
            plan,
            failed_tasks,
            failed_analysis
        )

        return new_plan
```

**Day 4-7: 优化和测试**
- 添加更多测试用例
- 性能优化
- 边界情况处理

#### Phase 3 验收标准
- [ ] 可自动分解复杂任务
- [ ] 生成的计划逻辑合理
- [ ] 支持并行执行独立任务
- [ ] 支持计划调整
- [ ] 规划时间 < 5秒

---

### Phase 4: 反思机制（第7-8周）

#### 目标
实现多轮反思，提升答案质量。

#### Week 7: 反思引擎

**Day 1-3: 实现反思器**
```python
# src/fastreact/reflection/reflector.py

class Reflector:
    """反思引擎"""

    def __init__(self, llm_client):
        self.llm = llm_client

    async def reflect(
        self,
        question: str,
        current_answer: str,
        tool_calls_made: int,
        context: Dict
    ) -> Reflection:
        """
        反思当前答案

        Returns:
            Reflection: {
                "complete": bool,        # 是否完整
                "quality": float,        # 质量分数 0-1
                "missing_info": List[str],  # 缺失的信息
                "suggestions": List[str]    # 改进建议
            }
        """
        prompt = f"""
请反思以下回答：

**问题**：{question}

**当前回答**：{current_answer}

**已调用工具次数**：{tool_calls_made}

**上下文**：{context}

请评估：
1. 回答是否完整？（是否回答了问题的所有方面）
2. 回答质量如何？（0-1分）
3. 是否有重要信息缺失？
4. 如何改进？

返回JSON格式：
{{
  "complete": true/false,
  "quality": 0.8,
  "missing_info": ["信息1", "信息2"],
  "suggestions": ["建议1", "建议2"]
}}
"""

        response = await self.llm.chat_json(prompt)
        return Reflection(**response)
```

**Day 4-5: 集成到ReACT循环**
```python
# src/fastreact/core/engine.py

class FastReAct:
    async def run_async_with_reflection(
        self,
        query: str,
        min_tool_calls: int = 2,
        max_reflections: int = 3
    ) -> Dict:
        """
        带反思的ReACT循环
        """
        tool_calls_count = 0
        reflection_count = 0

        for iteration in range(self.max_iterations):
            # 正常ReACT循环
            response = await self._chat(messages)
            tool_calls = self._parse_tool_calls(response)

            if not tool_calls:
                # 没有工具调用，进行反思
                if tool_calls_count < min_tool_calls:
                    # 强制继续
                    messages.append({
                        "role": "user",
                        "content": f"信息不足，请继续调用工具检索（已调用{tool_calls_count}次）"
                    })
                    continue

                # 反思当前答案
                reflection = await self.reflector.reflect(
                    question=query,
                    current_answer=response,
                    tool_calls_made=tool_calls_count,
                    context={"iteration": iteration}
                )

                if not reflection.complete and reflection_count < max_reflections:
                    # 反思认为需要更多信息
                    reflection_count += 1
                    messages.append({
                        "role": "user",
                        "content": f"""
反思结果：
- 完整性：{reflection.complete}
- 质量：{reflection.quality}
- 缺失信息：{reflection.missing_info}
- 建议：{reflection.suggestions}

请根据反思结果继续改进。
"""
                    })
                    continue

                # 反思通过，返回最终答案
                return {"answer": response, ...}

            # 执行工具调用
            ...
            tool_calls_count += len(tool_calls)
```

**Day 6-7: 测试和优化**

#### Week 8: 全面测试和文档

**Day 1-3: 完整测试**
- 单元测试
- 集成测试
- 端到端测试

**Day 4-5: 性能优化**
- Profile热点代码
- 优化关键路径
- 内存优化

**Day 6-7: 文档完善**
- API文档
- 使用示例
- 最佳实践

#### Phase 4 验收标准
- [ ] 反思准确率 > 80%
- [ ] 反思后答案质量明显提升
- [ ] 反思不影响性能（< 200ms）
- [ ] 测试覆盖率 > 80%

---

## 🎯 关键里程碑

| 里程碑 | 时间 | 标志 |
|--------|------|------|
| **M1: 可观测性** | 第2周末 | 日志和进度追踪完成 |
| **M2: 记忆系统** | 第4周末 | 向量数据库集成完成 |
| **M3: 任务规划** | 第6周末 | 规划器可用 |
| **M4: 功能完整** | 第8周末 | 所有功能集成，测试通过 |

---

## 📦 交付物清单

### Phase 1
- [ ] `AgentLogger` 类
- [ ] `ProgressTracker` 类
- [ ] `PromptManager` 类
- [ ] 单元测试

### Phase 2
- [ ] `VectorStore` 类
- [ ] `MemoryManager` 类
- [ ] `MemoryRetriever` 类
- [ ] 集成测试

### Phase 3
- [ ] `TaskPlanner` 类
- [ ] `PlanExecutor` 类
- [ ] `PlanAdjuster` 类
- [ ] 端到端测试

### Phase 4
- [ ] `Reflector` 类
- [ ] 反思集成
- [ ] 性能测试
- [ ] 完整文档

---

## 🔧 技术栈

```python
# 核心依赖
openai>=1.0.0
httpx>=0.25.0
pydantic>=2.0.0

# 记忆系统
chromadb>=0.4.0
sentence-transformers>=2.2.0

# 测试
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0

# 开发工具
black>=23.0.0
ruff>=0.1.0
mypy>=1.0.0
```

---

这个8周计划将FastReAct从基础框架升级为功能完整的智能体系统。
