# Embedding 模型解决方案

> 更新日期: 2025-02-01
> 问题: SiliconFlow 不支持 embeddings API

---

## 当前限制

### 问题确认

```python
POST https://api.siliconflow.cn/v1/embeddings
400 Bad Request
```

**原因**: SiliconFlow 目前只支持聊天/补全 API，不支持 embeddings。

---

## 可选方案对比

### 方案 1: OpenAI Embeddings ⭐ 推荐

**优点**:
- ✅ 稳定可靠
- ✅ 高质量向量
- ✅ 成本低廉
- ✅ 多个模型可选

**成本**:
| 模型 | 维度 | 成本 | 性能 |
|------|------|------|------|
| text-embedding-3-small | 1536 | $0.02/1M tokens | 快速 |
| text-embedding-3-large | 3072 | $0.13/1M tokens | 高质量 |

**代码示例**:
```python
import json

# 修改 config.json
config = {
    "memory": {
        "enabled": true,
        "embedding_provider": "openai",
        "embedding_model": "text-embedding-3-small",
        # OpenAI 专用配置
        "openai_api_key": "sk-xxx",
        "openai_base_url": "https://api.openai.com/v1",
    }
}
```

**优势**: 代码已支持，只需配置 API key

---

### 方案 2: 本地模型（Sentence-Transformers）

**优点**:
- ✅ 完全免费
- ✅ 数据隐私
- ✅ 离线可用

**缺点**:
- ⚠️ 需要下载模型（~100-500MB）
- ⚠️ CPU 运行较慢
- ⚠️ 占用内存

**推荐模型**:
| 模型 | 维度 | 大小 | 性能 |
|------|------|------|------|
| all-MiniLM-L6-v2 | 384 | ~80MB | ⭐⭐⭐⭐ 快速 |
| all-mpnet-base-v2 | 768 | ~400MB | ⭐⭐⭐⭐⭐ 平衡 |
| all-mpnet-base-v2 | 768 | ~400MB | ⭐⭐⭐⭐⭐ 英文优化 |

**安装**:
```bash
pip install sentence-transformers
```

**代码示例**:
```python
from sentence_transformers import SentenceTransformer

# 下载并加载模型
model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = model.encode("Hello world")
print(embedding.shape)  # (384,)
```

**集成到 FastReAct**:
```python
# src/fastreact/memory/embeddings.py
class LocalEmbedding(EmbeddingProvider):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        import sentence_transformers
        self.model = sentence_transformers.SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

    async def embed(self, text: str):
        # 同步调用，在线程池中运行
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.model.encode, text)
```

---

### 方案 3: HuggingFace Inference API（免费）

**优点**:
- ✅ 完全免费
- ✅ 无需本地模型
- ✅ 多种模型可选

**缺点**:
- ⚠️ 网络延迟
- ⚠️ 速率限制

**安装**:
```bash
pip install requests
```

**代码示例**:
```python
import requests

API_URL = "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2"
headers = {"Authorization": f"Bearer {hf_api_key}"}

def query_embedding(text):
    response = requests.post(
        API_URL,
        headers=headers,
        json={"inputs": text}
    )
    return response.json()[0]  # 返回 384 维向量
```

**推荐模型**:
- `sentence-transformers/all-MiniLM-L6-v2` - 快速，384 维
- `sentence-transformers/all-mpnet-base-v2` - 高质量，768 维

---

### 方案 4: Jina AI Embeddings（免费层）

**优点**:
- ✅ 免费层可用
- ✅ 性能优秀
- ✅ 多语言支持

**免费额度**:
- 100K tokens/月
- 请求速率: 200 tokens/秒

**安装**:
```bash
pip install jinaplus
```

**代码示例**:
```python
from jina import Client

client = Client("jina_embedding:S7s/hP8kg")  # 免费

embedding = client.encode(["Hello world"])
# numpy array, shape: (1, 768)
```

---

### 方案 5: Cohere Embeddings

**免费额度**:
- 1000 次 API 调用/月
- 多语言支持

**模型**:
- embed-english-v3.0 (1024 维)
- embed-multilingual-v3.0 (1024 维)

**代码示例**:
```python
import cohere

co = cohere.Client(api_key="xxx")
response = co.embed(
    texts=["Hello world"],
    model="embed-english-v3.0"
)
embedding = response.embeddings[0]
```

---

## 推荐方案总结

### 开发/测试（快速开始）

**方案 2: 本地模型** - sentence-transformers

```bash
pip install sentence-transformers
```

**优点**: 完全免费，快速上手
**缺点**: 需要下载模型

---

### 生产环境（小规模）

**方案 1: OpenAI Embeddings** - text-embedding-3-small

```json
{
  "memory": {
    "embedding_provider": "openai",
    "embedding_model": "text-embedding-3-small",
    "openai_api_key": "sk-xxx"
  }
}
```

**成本**: $0.02/1M tokens ≈ **$0.20/100万次查询**
**优势**: 最稳定，最可靠

---

### 生产环境（大规模）

**方案 4: Jina AI** - 免费层 + 付费扩展

```bash
pip install jinaplus
```

**成本**: 免费层 100K tokens/月

---

### 本地私有部署

**方案 2 + 优化**: sentence-transformers + 量化

```python
# 使用量化模型减小内存占用
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    'all-MiniLM-L6-v2',
    device='cpu'
)

# 量化到 8-bit
import torch
quantized_model = quantize_dynamic(model)
```

---

## 代码实现：本地 Embedding Provider

让我创建一个完整的本地实现：

```python
# src/fastreact/memory/embeddings.py
# 添加 LocalEmbedding 类

class LocalEmbedding(EmbeddingProvider):
    """Local sentence-transformers embedding provider

    Uses sentence-transformers for on-device embedding generation.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
        cache_dir: Optional[str] = None,
    ):
        """Initialize local embedding provider

        Args:
            model_name: Model name from sentence-transformers
            device: Device to use ("cpu" or "cuda")
            cache_dir: Cache directory for models
        """
        self.model_name = model_name
        self.device = device
        self.cache_dir = cache_dir
        self._model = None

    async def _get_model(self):
        """Lazy load model"""
        if self._model is None:
            import asyncio
            import sentence_transformers as st

            # 在线程池中加载模型（避免阻塞）
            loop = asyncio.get_event_loop()
            self._model = await loop.run_in_executor(
                None,
                lambda: st.SentenceTransformer(
                    self.model_name,
                    device=self.device,
                    cache_folder=self.cache_dir,
                )
            )
            logger.info(f"Loaded local embedding model: {self.model_name}")

        return self._model

    async def embed(self, text: str) -> List[float]:
        """Generate embedding

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        model = await self._get_model()

        # 在线程池中运行（CPU密集）
        import asyncio
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            model.encode,
            text
        )

        return embedding.tolist()

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        model = await self._get_model()

        # 在线程池中运行
        import asyncio
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            model.encode,
            texts
        )

        return [emb.tolist() for emb in embeddings]
```

---

## 快速开始指南

### 选项 1: 使用 OpenAI（最简单）

**步骤**:
1. 获取 OpenAI API key: https://platform.openai.com/api-keys
2. 更新 `config.json`:

```json
{
  "memory": {
    "enabled": true,
    "embedding_provider": "openai",
    "embedding_model": "text-embedding-3-small",
    "openai_api_key": "sk-proj-xxx",
    "openai_base_url": "https://api.openai.com/v1"
  }
}
```

---

### 选项 2: 使用本地模型（完全免费）

**步骤**:
1. 安装依赖:
```bash
pip install sentence-transformers
```

2. 更新 `embeddings.py` 添加 `LocalEmbedding` 类（见上面代码）

3. 更新 `EmbeddingBuilder.from_config` 支持本地模型:

```python
@staticmethod
def from_config(
    provider_name: str,
    provider_config: Dict[str, Any],
    memory_config: Dict[str, Any],
) -> EmbeddingGenerator:
    if provider_name == "openai":
        provider = OpenAIEmbedding(...)
    elif provider_name == "local":
        provider = LocalEmbedding(
            model_name=memory_config.get("embedding_model", "all-MiniLM-L6-v2"),
            device="cpu",
        )
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")

    return EmbeddingGenerator(provider=provider, ...)
```

4. 更新 `config.json`:

```json
{
  "memory": {
    "enabled": true,
    "embedding_provider": "local",
    "embedding_model": "all-MiniLM-L6-v2"
  }
}
```

---

## 性能对比

| 方案 | 延迟 | 成本 | 隐私 | 推荐度 |
|------|------|------|------|--------|
| OpenAI | ~200ms | $0.02/1M | 云端 | ⭐⭐⭐⭐⭐ 生产 |
| 本地 ST | ~500ms | 免费 | 本地 | ⭐⭐⭐⭐ 开发 |
| HuggingFace | ~1s | 免费 | 云端 | ⭐⭐⭐ 测试 |
| Jina AI | ~300ms | 免费层 | 云端 | ⭐⭐⭐⭐ 备选 |

---

## 总结

### 立即可用

1. **快速测试**: 本地 sentence-transformers
2. **生产环境**: OpenAI embeddings（最便宜）

### 推荐配置

```json
{
  "memory": {
    "enabled": true,
    "embedding_provider": "openai",
    "embedding_model": "text-embedding-3-small",
    "openai_api_key": "sk-proj-xxx"
  }
}
```

**成本**: 假设每次对话 10 次检索，每次 100 tokens：
- 每天 1000 次检索 × 100 tokens = 100K tokens
- 每月 3M tokens = **$0.06**

---

**我可以帮你实现其中任何一种方案。** 你想用哪种？
