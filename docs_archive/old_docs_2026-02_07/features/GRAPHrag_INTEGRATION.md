# FastReAct + GraphRAG 集成指南

## 概述

FastReAct现在完全支持GraphRAG工具，提供真正的ReAct（推理-行动-观察）循环来查询和推理知识图谱。

### 核心特性

✅ **真正的ReAct实现** - Thought→Action→Observation完整循环
✅ **5个GraphRAG工具** - 查询、分析、推理、提取、检查
✅ **MCP工具系统** - 解耦合的工具注册和管理
✅ **并发执行** - 同时调用多个工具提高效率
✅ **智能缓存** - LRU缓存减少重复查询
✅ **流式输出** - 实时显示推理过程

---

## 快速开始

### 1. 安装依赖

```bash
cd D:\FastReAct
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑.env文件
nano .env
```

必需配置：
```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

HIPPO_RAG_URL=http://localhost:8080
```

### 3. 运行示例

```bash
python examples/graphrag_query_demo.py
```

---

## GraphRAG工具集

### 工具列表

| 工具名称 | 功能 | 参数 |
|---------|------|------|
| **query_graph_rag** | 自然语言查询知识图谱 | query, max_results, reasoning_depth |
| **analyze_relationships** | 分析实体间的关系 | entities[], relationship_types[], max_depth |
| **multi_hop_reasoning** | 多跳推理找实体间路径 | start_entity, end_entity, max_hops |
| **knowledge_extraction** | 从文本提取知识并添加到图谱 | text, extract_relationships, add_to_graph |
| **check_graph_rag_config** | 检查GraphRAG配置和连接 | 无 |

### 工具详细说明

#### 1. query_graph_rag

**功能**: 使用自然语言查询知识图谱

**参数**:
- `query` (str, 必需): 自然语言查询
- `max_results` (int, 可选): 最大结果数，默认10
- `reasoning_depth` (int, 可选): 推理深度(1-5)，默认3

**返回**:
```python
{
    "status": "success",
    "answer": "主要答案内容",
    "sources": ["出处1", "出处2"],
    "confidence": 0.85,
    "related_entities": ["实体1", "实体2"],
    "key_concepts": ["概念1", "概念2"],
    "execution_time": 3.2
}
```

**示例**:
```python
result = query_graph_rag(
    query="Alice的兴趣爱好是什么？",
    max_results=10,
    reasoning_depth=3
)
```

#### 2. analyze_relationships

**功能**: 分析多个实体之间的关系

**参数**:
- `entities` (list[str], 必需): 实体名称列表
- `relationship_types` (list[str], 可选): 关系类型过滤
- `max_depth` (int, 可选): 遍历深度，默认2

**返回**:
```python
{
    "status": "success",
    "entities": ["Alice", "Bob"],
    "direct_relationships": [
        {"source": "Alice", "target": "Bob", "type": "colleague", "strength": 0.8}
    ],
    "indirect_relationships": [...],
    "centrality": {"Alice": 0.8, "Bob": 0.6},
    "common_entities": ["TechCorp", "Python"]
}
```

**示例**:
```python
result = analyze_relationships(
    entities=["Alice", "Bob", "Charlie"],
    max_depth=2
)
```

#### 3. multi_hop_reasoning

**功能**: 多跳推理，查找实体间的路径

**参数**:
- `start_entity` (str, 必需): 起始实体
- `end_entity` (str, 必需): 目标实体
- `max_hops` (int, 可选): 最大跳数，默认5
- `reasoning_mode` (str, 可选): 推理模式（shortest_path, all_paths, beam_search）

**返回**:
```python
{
    "status": "success",
    "start_entity": "Alice",
    "end_entity": "Charlie",
    "reasoning_paths": [
        ["Alice", "Bob", "Charlie"],
        ["Alice", "David", "Charlie"]
    ],
    "shortest_path": ["Alice", "Bob", "Charlie"],
    "path_confidence": 0.75,
    "intermediate_entities": ["Bob"]
}
```

**示例**:
```python
result = multi_hop_reasoning(
    start_entity="Alice",
    end_entity="Charlie",
    max_hops=5
)
```

#### 4. knowledge_extraction

**功能**: 从文本提取实体和关系

**参数**:
- `text` (str, 必需): 输入文本
- `extract_relationships` (bool, 可选): 是否提取关系，默认True
- `add_to_graph` (bool, 可选): 是否添加到图谱，默认False

**返回**:
```python
{
    "status": "success",
    "entities": ["Alice", "TechCorp"],
    "relationships": [
        {"source": "Alice", "target": "TechCorp", "type": "works_at"}
    ],
    "concepts": ["employment", "company"],
    "confidence": 0.9
}
```

**示例**:
```python
result = knowledge_extraction(
    text="Alice在TechCorp工作，她是AI研究员",
    extract_relationships=True
)
```

#### 5. check_graph_rag_config

**功能**: 检查GraphRAG配置和连接状态

**参数**: 无

**返回**:
```python
{
    "status": "success",
    "hippo_rag_url": "http://localhost:8080",
    "api_key_configured": true,
    "connection_status": "ok",
    "version": "1.0.0",
    "features": ["query", "analyze", "reasoning", "extraction"]
}
```

**示例**:
```python
result = check_graph_rag_config()
```

---

## 使用FastReAct引擎

### 基础用法

```python
import asyncio
from fastreact.core.engine import FastReAct
from fastreact.tools import export_tools_to_fastreact

async def main():
    # 创建引擎
    agent = FastReAct(
        api_key="your-openai-api-key",
        base_url="https://api.openai.com/v1",
        model="gpt-4",
        max_iterations=10,
        enable_cache=True,
    )

    # 注册GraphRAG工具
    for tool in export_tools_to_fastreact():
        agent.register_tool(tool)

    # 执行查询
    result = await agent.run_async(
        query="Alice和Bob有什么共同兴趣？",
        step_callback=lambda step: print(f"Step: {step}")
    )

    print(f"答案: {result['answer']}")
    print(f"统计: {result['stats']}")

    await agent.close()

asyncio.run(main())
```

### 流式输出

```python
async def main():
    agent = FastReAct(
        api_key="your-api-key",
        enable_streaming=True,  # 启用流式输出
        # ...其他参数
    )

    # 流式回调
    def stream_callback(text: str):
        print(text, end="", flush=True)

    # 步骤回调
    def step_callback(step: Dict):
        iteration = step.get("iteration")
        thought = step.get("thought")
        print(f"\n[Step {iteration}] {thought}")

    # 执行查询（流式）
    result = await agent.run_async(
        query="查询Alice的兴趣",
        stream_callback=stream_callback,
        step_callback=step_callback,
    )
```

### 自定义工具注册

```python
from fastreact.tools.mcp_adapter import register_mcp_tool

# 定义自定义工具
@register_mcp_tool(
    "my_custom_tool",
    description="我的自定义工具",
)
def my_custom_tool(param1: str, param2: int = 10) -> Dict:
    """工具实现"""
    result = perform_operation(param1, param2)
    return {"status": "success", "result": result}

# 注册到引擎
agent.register_tool(
    get_global_registry().get_tool("my_custom_tool")
)
```

---

## ReAct循环示例

### 示例1：简单查询

**查询**: "Alice的兴趣爱好是什么？"

**ReAct循环**:
```
Step 1:
  💭 Thought: 我需要查询Alice的兴趣信息
  🔧 Action: [TOOL_CALL] {"name": "query_graph_rag", "parameters": {"query": "Alice的兴趣爱好"}}
  👀 Observation: ✅ Alice的兴趣是Python编程、AI研究和音乐

  💭 Thought: 我已经有了完整信息，可以回答了
  🎯 Final Answer: 根据知识图谱，Alice的兴趣爱好包括Python编程、AI研究和音乐。
```

### 示例2：复杂推理

**查询**: "Alice和Bob有什么共同兴趣？他们如何认识彼此的？"

**ReAct循环**:
```
Step 1:
  💭 Thought: 我需要先了解Alice的兴趣
  🔧 Action: [TOOL_CALL] {"name": "query_graph_rag", "parameters": {"query": "Alice的兴趣"}}
  👀 Observation: ✅ Alice喜欢Python、AI和音乐

Step 2:
  💭 Thought: 现在我需要了解Bob的兴趣
  🔧 Action: [TOOL_CALL] {"name": "query_graph_rag", "parameters": {"query": "Bob的兴趣"}}
  👀 Observation: ✅ Bob喜欢Python、AI和游戏

Step 3:
  💭 Thought: 我可以分析两人的关系了
  🔧 Action: [TOOL_CALL] {"name": "analyze_relationships", "parameters": {"entities": ["Alice", "Bob"]}}
  👀 Observation: ✅ Alice和Bob是同事关系，关系强度0.8，共同兴趣包括Python和AI

  💭 Thought: 信息已经完整，可以给出最终答案了
  🎯 Final Answer: Alice和Bob的共同兴趣是Python编程和AI研究。他们在TechCorp是同事关系，通过工作相识。
```

### 示例3：多跳推理

**查询**: "Alice如何间接认识Charlie的？"

**ReAct循环**:
```
Step 1:
  💭 Thought: 我需要找到Alice到Charlie的路径
  🔧 Action: [TOOL_CALL] {"name": "multi_hop_reasoning", "parameters": {"start_entity": "Alice", "end_entity": "Charlie", "max_hops": 5}}
  👀 Observation: ✅ 找到路径：Alice -> Bob -> Charlie，置信度0.75

Step 2:
  💭 Thought: 我需要了解更多关于Bob在这条路径中的角色
  🔧 Action: [TOOL_CALL] {"name": "query_graph_rag", "parameters": {"query": "Bob与Alice和Charlie的关系"}}
  👀 Observation: ✅ Bob是Alice的同事，也是Charlie的大学同学

  💭 Thought: 现在可以完整回答了
  🎯 Final Answer: Alice通过Bob间接认识Charlie。具体路径是：Alice在TechCorp与Bob共事，Bob在大学时与Charlie是同学，因此形成了Alice->Bob->Charlie的连接链。
```

---

## 性能优化

### 1. 缓存

FastReAct内置LRU缓存，自动缓存工具执行结果：

```python
agent = FastReAct(
    enable_cache=True,  # 启用缓存（默认）
    cache_size=1000,    # 缓存大小
)

# 查看缓存统计
stats = agent.get_stats()
print(f"缓存命中率: {stats['cache_hit_rate']:.2%}")
```

### 2. 并发工具执行

FastReAct支持并发执行多个工具：

```python
agent = FastReAct(
    max_concurrent_tools=3,  # 最多3个工具并发执行
)
```

当LLM决定调用多个独立工具时，它们会并发执行。

### 3. 超时控制

GraphRAG工具内置超时控制：

```python
result = query_graph_rag(
    query="...",
    timeout=10  # 10秒超时
)
```

---

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|-------|------|--------|
| `OPENAI_API_KEY` | OpenAI API密钥 | *必需* |
| `OPENAI_BASE_URL` | OpenAI API基础URL | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 使用的模型 | `gpt-4` |
| `HIPPO_RAG_URL` | HippoRAG服务地址 | `http://localhost:8080` |
| `HIPPO_RAG_API_KEY` | HippoRAG API密钥 | 可选 |
| `HIPPO_RAG_TIMEOUT` | HippoRAG请求超时（秒） | `10` |
| `MAX_ITERATIONS` | 最大迭代次数 | `10` |
| `ENABLE_CACHE` | 启用缓存 | `true` |
| `ENABLE_STREAMING` | 启用流式输出 | `false` |
| `MAX_CONCURRENT_TOOLS` | 最大并发工具数 | `3` |

### FastReAct引擎参数

```python
FastReAct(
    api_key: str,                    # OpenAI API密钥
    base_url: str = "https://api.openai.com/v1",  # API基础URL
    model: str = "gpt-4",            # 模型名称
    tools: Optional[List[Tool]] = None,  # 工具列表
    max_iterations: int = 5,          # 最大迭代次数
    max_concurrent_tools: int = 3,    # 最大并发工具数
    enable_streaming: bool = False,   # 启用流式响应
    enable_cache: bool = True,        # 启用缓存
    cache_size: int = 1000,           # 缓存大小
    temperature: float = 0.5,         # 温度参数
    max_tokens: int = 2048,           # 最大token数
)
```

---

## 架构说明

### 系统架构

```
┌─────────────────────────────────────────┐
│         FastReAct Engine                │
│  - ReAct循环控制                        │
│  - LLM交互                              │
│  - 并发工具执行                         │
│  - LRU缓存                              │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│      MCP Tool Registry                  │
│  - 工具注册和管理                       │
│  - 自动类型推断                         │
│  - 同步/异步适配                        │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│      GraphRAG Tools                     │
│  - query_graph_rag                      │
│  - analyze_relationships                │
│  - multi_hop_reasoning                  │
│  - knowledge_extraction                 │
│  - check_graph_rag_config               │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│      HippoRAG Backend                   │
│  - 知识图谱存储                         │
│  - 查询和推理引擎                       │
└─────────────────────────────────────────┘
```

### MCP适配器

FastReAct使用MCP适配器将Biro的工具函数转换为Tool对象：

```python
# Biro风格的工具定义
@register_mcp_tool("tool_name")
def my_tool(param1: str, param2: int = 10):
    """工具描述"""
    return {"result": "..."}

# 自动转换为FastReAct的Tool对象
# - 自动推断参数schema
# - 支持同步和异步函数
# - 统一错误处理
```

---

## 常见问题

### Q: 如何添加自定义工具？

A: 使用`@register_mcp_tool`装饰器：

```python
from fastreact.tools.mcp_adapter import register_mcp_tool

@register_mcp_tool("my_tool")
def my_tool(param: str) -> Dict:
    """工具描述"""
    return {"status": "success", "result": param}

# 自动注册到全局注册表
# 导出时: export_tools_to_fastreact()
```

### Q: 如何处理工具执行错误？

A: 工具执行错误会自动捕获并返回：

```python
result = await agent.run_async(query="...")

for step in result['steps']:
    for tool_call in step.get('tool_calls', []):
        if tool_call.get('error'):
            print(f"工具错误: {tool_call['error']}")
```

### Q: 如何查看详细执行过程？

A: 使用`step_callback`:

```python
def detailed_step_callback(step: Dict):
    print(f"\n=== Step {step['iteration']} ===")
    print(f"Thought: {step['thought']}")
    if 'tool_calls' in step:
        print(f"Actions: {step['tool_calls']}")
    if 'observation' in step:
        print(f"Observation: {step['observation']}")

result = await agent.run_async(
    query="...",
    step_callback=detailed_step_callback
)
```

### Q: 如何提高性能？

A: 几个优化建议：

1. **启用缓存**: `enable_cache=True`
2. **增加并发**: `max_concurrent_tools=5`
3. **调整迭代次数**: `max_iterations=5`（简单查询）
4. **使用更快的模型**: `model="gpt-3.5-turbo"`

### Q: GraphRAG服务不可用时怎么办？

A: 工具会返回错误，ReAct循环会继续：

```python
result = query_graph_rag(...)
# 返回: {"status": "failed", "error": "Failed to query GraphRAG: ..."}

# FastReAct会看到错误并在下一步思考中决定如何处理
```

---

## 迁移指南（从Biro）

### 主要差异

| 特性 | Biro | FastReAct |
|------|------|-----------|
| 架构模式 | Plan-and-Execute | True ReAct |
| 核心代码量 | ~2000行 | ~600行 |
| 工具注册 | MCP装饰器 | MCP装饰器（兼容） |
| 执行方式 | 同步 | 异步（原生） |
| 推理可见性 | 无 | 完全可见 |
| 并发工具 | 无 | 支持（3个并发） |

### 迁移步骤

1. **保留的工具**: 所有GraphRAG工具无需修改，直接复用
2. **需要修改的**: 任务执行逻辑（从同步改为异步）
3. **删除的**: Planner、Executor、Reflector（ReAct天然替代）

### 代码对比

**Biro**:
```python
from tasks import agent_workflow_task

result = agent_workflow_task(
    task_id="123",
    prompt="查询Alice的兴趣"
)

# 用户只看到最终结果，看不到推理过程
print(result['results'])
```

**FastReAct**:
```python
from fastreact.core.engine import FastReAct

agent = FastReAct(api_key="...")
for tool in export_tools_to_fastreact():
    agent.register_tool(tool)

result = await agent.run_async(
    query="查询Alice的兴趣",
    step_callback=lambda step: print(f"Thought: {step['thought']}")
)

# 用户看到完整的推理过程
# Step 1: Thought -> Action -> Observation
# Step 2: Thought -> Final Answer
```

---

## 下一步

- 查看 `examples/graphrag_query_demo.py` 了解更多示例
- 阅读 `docs/` 目录下的详细文档
- 运行测试: `pytest tests/`

---

## 参考资源

- **FastReAct文档**: `docs/agent_architecture.md`
- **GraphRAG论文**: GraphRAG: Knowledge Graph-Enhanced RAG
- **ReAct论文**: ReAct: Synergizing Reasoning and Acting in Language Models

---

**更新时间**: 2026-01-22
**版本**: 1.0.0
