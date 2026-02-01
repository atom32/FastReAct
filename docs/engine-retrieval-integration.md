# Engine 记忆检索集成方案

> 日期: 2025-02-01
> 状态: 实施中
> 硬件: RTX 5090 + CUDA
> 环境: 中国大陆 (ModelScope)

---

## 目标

在 FastReAct Engine 中集成语义检索功能，在每次查询时自动检索相关历史对话并注入上下文。

---

## 架构设计

### 1. 检索流程

```
用户查询
    ↓
生成查询嵌入 (Qwen3-Embedding-0.6B, GPU加速)
    ↓
向量检索 (Top-K 最相关 chunks)
    ↓
格式化检索结果
    ↓
注入到系统提示
    ↓
LLM 生成响应
```

### 2. 配置结构

```json
{
  "context": {
    "retrieval": {
      "enabled": true,
      "provider": "modelscope",
      "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
      "embedding_dim": 1536,
      "vector_store": "sqlite_vec",
      "chunk_size": 500,
      "chunk_overlap": 50,
      "top_k": 3,
      "min_similarity": 0.65,
      "max_context_chunks": 5,
      "inject_position": "system",  // "system" | "user"
      "template": "Related context:\n{context}"
    }
  }
}
```

### 3. Engine 集成点

**File**: `src/fastreact/core/engine.py`

**修改位置**:
1. **__init__**: 添加 `retriever` 和 `retrieval_config` 参数
2. **_build_messages_context**: 添加检索逻辑
3. **run_async**: 自动索引对话到向量存储

---

## 实施步骤

### Step 1: 扩展配置类

**File**: `src/fastreact/context/config.py`

```python
@dataclass
class RetrievalConfig:
    """Memory retrieval configuration"""

    # Enable/disable retrieval
    enabled: bool = False

    # Embedding provider
    provider: str = "modelscope"
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    embedding_dim: int = 1536
    device: str = "cuda"  # Use GPU by default

    # Vector store
    vector_store: str = "sqlite_vec"  # or "apsw" for Windows
    db_path: str = "./data/memory.db"

    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Retrieval parameters
    top_k: int = 3  # Number of results to retrieve
    min_similarity: float = 0.65  # Minimum similarity threshold
    max_context_chunks: int = 5  # Max chunks to inject

    # Injection
    inject_position: str = "system"  // "system" or "user"
    template: str = "Related context:\n{context}\n\n"

    # Auto-indexing
    auto_index: bool = True  # Automatically index conversations
    index_delay: int = 1  # Delay before indexing (iterations)
```

### Step 2: 更新 ContextConfig

```python
@dataclass
class ContextConfig:
    # ... existing fields ...

    # Memory retrieval configuration
    retrieval: Optional[RetrievalConfig] = None
```

### Step 3: Engine 初始化

**File**: `src/fastreact/core/engine.py`

```python
from ..memory import MemoryRetriever, EmbeddingGenerator, ModelScopeEmbedding
from ..context import RetrievalConfig

class FastReAct:
    def __init__(
        self,
        # ... existing parameters ...
        retrieval_config: Optional[RetrievalConfig] = None,
    ):
        # ... existing initialization ...

        # Initialize retriever
        self._retriever = None
        self._retrieval_config = retrieval_config or (
            context_config.retrieval if context_config else None
        )

        if self._retrieval_config and self._retrieval_config.enabled:
            self._setup_retriever()

    def _setup_retriever(self):
        """Setup memory retriever"""
        from ..memory import VectorStoreBuilder, EmbeddingGenerator

        # Create embedding generator
        provider = EmbeddingGenerator.create_provider(
            provider_name=self._retrieval_config.provider,
            model_id=self._retrieval_config.embedding_model,
            device=self._retrieval_config.device,
        )

        generator = EmbeddingGenerator(
            provider=provider,
            enable_cache=True,
            cache_size=10000,
        )

        # Create vector store
        vector_store = VectorStoreBuilder.create(
            backend=self._retrieval_config.vector_store,
            db_path=self._retrieval_config.db_path,
            embedding_dim=self._retrieval_config.embedding_dim,
        )

        # Create retriever
        self._retriever = MemoryRetriever(
            vector_store=vector_store,
            embedding_generator=generator,
            chunk_size=self._retrieval_config.chunk_size,
            chunk_overlap=self._retrieval_config.chunk_overlap,
            top_k=self._retrieval_config.top_k,
            min_similarity=self._retrieval_config.min_similarity,
        )

        logger.info("Memory retriever initialized")
```

### Step 4: 检索逻辑集成

**File**: `src/fastreact/core/engine.py`

```python
async def _build_messages_context(
    self,
    query: str,
    session_context: Optional[Dict[str, Any]] = None,
    iteration: int = 0,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """构建带上下文的消息列表（包含检索）"""

    system_prompt = self._build_system_prompt()
    history = list(session_context.get("history", [])) if session_context else None

    # ========== 新增：记忆检索 ==========
    retrieved_context = ""
    if self._retriever and self._retrieval_config.enabled:
        try:
            # 检索相关历史
            results = await self._retriever.retrieve(
                query=query,
                session_id=session_context.get("session_id") if session_context else None,
                top_k=self._retrieval_config.top_k,
                min_similarity=self._retrieval_config.min_similarity,
            )

            if results:
                # 格式化检索结果
                context_chunks = []
                for i, result in enumerate(results[:self._retrieval_config.max_context_chunks]):
                    chunk_text = result.get("content", "")[:500]  # Limit chunk length
                    similarity = result.get("similarity", 0)
                    context_chunks.append(f"[{i+1}] {chunk_text}... (similarity: {similarity:.2f})")

                retrieved_context = self._retrieval_config.template.format(
                    context="\n".join(context_chunks)
                )

                logger.debug(f"Retrieved {len(results)} chunks for query")

        except Exception as e:
            logger.error(f"Memory retrieval failed: {e}")

    # 注入检索结果到系统提示
    if retrieved_context:
        if self._retrieval_config.inject_position == "system":
            system_prompt = f"{retrieved_context}\n\n{system_prompt}"
        # user position injection happens later
    # ========== 检索结束 ==========

    # ... existing Memory Flush logic ...

    # Build messages
    messages, metadata = context_builder.build_context(
        system_prompt=system_prompt,
        user_query=query,
        history=history,
    )

    # Inject retrieved context at user position if configured
    if retrieved_context and self._retrieval_config.inject_position == "user":
        messages.insert(-1, {  # Insert before last user message
            "role": "system",
            "content": retrieved_context
        })

    return messages, metadata
```

### Step 5: 自动索引对话

**File**: `src/fastreact/core/engine.py`

```python
async def run_async(
    self,
    query: str,
    session_context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Run ReACT loop with auto-indexing"""

    # ... existing logic ...

    try:
        # ... ReACT loop ...

        for iteration in range(self.max_iterations):
            # ... existing iteration logic ...

            response = await self._call_llm(messages, tools)

            # ... tool calls ...

            final_response = response.get("content", "")

    finally:
        # ========== 新增：自动索引 ==========
        # Index conversation after completion
        if (self._retriever
            and self._retrieval_config.enabled
            and self._retrieval_config.auto_index
            and iteration >= self._retrieval_config.index_delay):

            try:
                session_id = session_context.get("session_id", "unknown") if session_context else "unknown"
                history = list(session_context.get("history", [])) if session_context else []

                if len(history) > 0:
                    await self._retriever.index_session(
                        session_id=session_id,
                        messages=history,
                    )

                    logger.debug(f"Indexed {len(history)} messages for session {session_id}")

            except Exception as e:
                logger.error(f"Session indexing failed: {e}")
        # ========== 索引结束 ==========

    return final_response
```

---

## 配置示例

### 开发环境 (RTX 5090)

```json
{
  "context": {
    "retrieval": {
      "enabled": true,
      "provider": "modelscope",
      "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
      "embedding_dim": 1536,
      "device": "cuda",
      "vector_store": "sqlite_vec",
      "db_path": "./data/memory.db",
      "chunk_size": 500,
      "chunk_overlap": 50,
      "top_k": 5,
      "min_similarity": 0.65,
      "max_context_chunks": 5,
      "inject_position": "system",
      "template": "以下是相关的历史对话上下文，请参考这些信息来回答问题：\n\n{context}\n\n---\n\n",
      "auto_index": true,
      "index_delay": 1
    }
  }
}
```

### CPU 环境

```json
{
  "context": {
    "retrieval": {
      "enabled": true,
      "device": "cpu",
      "top_k": 3,  // 降低以加快速度
      "max_context_chunks": 3
    }
  }
}
```

---

## 性能预期

### RTX 5090 (CUDA)

| 操作 | 延迟 | 说明 |
|------|------|------|
| **嵌入生成** | ~5-10ms | Qwen3-Embedding-0.6B on GPU |
| **向量检索** | ~10-20ms | sqlite-vec KNN search |
| **总开销** | ~15-30ms | 对响应时间影响 <5% |
| **吞吐量** | ~100-200 queries/sec | 批量处理 |

### 内存占用

| 组件 | 大小 |
|------|------|
| **Qwen3 模型** | ~1.2GB (GPU) |
| **向量存储** | ~10MB per 1000 chunks |
| **嵌入缓存** | ~100MB (10000 entries) |
| **总额外内存** | ~1.3GB GPU + ~110MB RAM |

---

## 测试计划

### 1. 单元测试

```python
# tests/core/test_engine_retrieval.py

async def test_retrieval_integration():
    """Test Engine with retrieval"""
    engine = FastReAct(
        api_key="test",
        retrieval_config=RetrievalConfig(
            enabled=True,
            device="cuda",
            top_k=3,
        )
    )

    # Index some conversations
    await engine._retriever.index_session(
        session_id="test",
        messages=[
            {"role": "user", "content": "我喜欢吃苹果"},
            {"role": "assistant", "content": "了解，你喜欢吃苹果"},
        ]
    )

    # Query with retrieval
    response = await engine.run_async(
        query="我喜欢吃什么水果？",
        session_context={"session_id": "test"}
    )

    # Verify retrieval was used
    assert "苹果" in response.get("content", "")
```

### 2. 性能测试

```python
async def test_retrieval_performance():
    """Test retrieval performance"""
    import time

    # Index 1000 conversations
    for i in range(1000):
        await engine._retriever.index_session(...)

    # Measure retrieval time
    start = time.time()
    for i in range(100):
        await engine.run_async(query=f"测试查询 {i}")
    elapsed = time.time() - start

    print(f"Average query time: {elapsed/100*1000:.2f}ms")
    # Expected: <50ms per query with GPU
```

### 3. 端到端测试

```bash
# Manual testing script
python tests/integration/test_retrieval_e2e.py
```

---

## 已知限制

1. **首次查询延迟**: 模型加载需要 ~20-30 秒
   - **解决方案**: 预加载模型到 GPU

2. **冷启动缓存**: 嵌入缓存为空时较慢
   - **解决方案**: 运行时自动预热

3. **维度不匹配**: 旧嵌入 (768维) 无法使用
   - **解决方案**: 重新生成所有嵌入

4. **并发限制**: 单个检索可能阻塞
   - **解决方案**: 后台预检索下一轮查询

---

## 后续优化

1. **批量索引**: 并发索引多个会话
2. **增量更新**: 只索引新消息
3. **混合检索**: Vector + BM25 (参考 Moltbot)
4. **持久化缓存**: SQLite 缓存跨重启保存
5. **自适应阈值**: 根据查询复杂度调整

---

## 参考资料

- **Moltbot 对比**: `docs/verification-moltbot-comparison.md`
- **Qwen3 指南**: `docs/qwen3-embedding-guide.md`
- **Windows 解决方案**: `docs/windows-sqlite-vec-solution.md`

---

**状态**: 准备实施
**优先级**: 高 (短期)
**预计工时**: 2-3 小时
