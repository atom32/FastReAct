# Vector Store 实现状态与替代方案

> 更新日期: 2025-02-01
> 状态: 代码已实现，Windows 兼容性待解决

---

## 已完成的实现

### 核心模块 ✅

| 模块 | 文件 | 状态 | 说明 |
|------|------|------|------|
| Embeddings | `src/fastreact/memory/embeddings.py` | ✅ 完成 | OpenAI/本地 embedding 支持 |
| Vector Store | `src/fastreact/memory/vector_store.py` | ✅ 完成 | 抽象层接口 |
| SQLite-Vec | `src/fastreact/memory/sqlite_vec.py` | ✅ 完成 | SQLite + sqlite-vec 实现 |
| Retriever | `src/fastreact/memory/retriever.py` | ✅ 完成 | 语义检索器 |
| Memory 模块 | `src/fastreact/memory/__init__.py` | ✅ 完成 | 模块导出 |

### 依赖

```
requirements.txt:
  sqlite-vec>=0.1.0  # 已添加
```

---

## Windows 兼容性问题 ⚠️

### 问题描述

在 Windows 上运行时，sqlite-vec 扩展无法加载：

```python
sqlite3.OperationalError: not authorized
```

### 尝试的解决方案

1. **直接加载**: `SELECT load_extension('sqlite_vec')` ❌
2. **路径加载**: 使用绝对路径加载 .dll 文件 ❌
3. **启用扩展**: `PRAGMA enable_load_extension=1` ❌

### 根本原因

Windows 上的 SQLite 扩展加载受限于：
- 文件系统权限
- DLL 签名要求
- SQLite 编译选项

---

## 推荐的替代方案

### 方案 1: ChromaDB ⭐ 推荐

**优点**:
- ✅ 跨平台支持（Windows/Linux/macOS）
- ✅ 纯 Python 实现
- ✅ 内置 embedding 支持
- ✅ 易于集成

**安装**:
```bash
pip install chromadb
```

**代码修改**:
```python
from chromadb import Client

class ChromaDBVectorStore(VectorStore):
    def __init__(self, persist_directory="./data/chroma"):
        self.client = Client(persist_directory=persist_directory)
        self.collection = self.client.get_or_create_collection("fastreact")

    async def add_chunks(self, chunks):
        embeddings = [c["embedding"] for c in chunks]
        documents = [c["content"] for c in chunks]
        metadatas = [{"session_id": c["session_id"]} for c in chunks]
        ids = [c["id"] for c in chunks]

        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )
```

---

### 方案 2: Weaviate

**优点**:
- ✅ 跨平台支持
- ✅ GraphQL API
- ✅ 丰富的功能

**安装**:
```bash
pip install weaviate-client
```

---

### 方案 3: FAISS + 自定义存储

**优点**:
- ✅ 跨平台支持
- ✅ 高性能
- ✅ Meta 官方支持

**安装**:
```bash
pip install faiss-cpu  # or faiss-gpu
```

**示例**:
```python
import faiss
import pickle

class FAISSVectorStore(VectorStore):
    def __init__(self, index_path="./data/faiss.index"):
        self.index_path = index_path
        self.index = faiss.IndexFlatL2(1536)  # OpenAI embedding dim

    async def add_chunks(self, chunks):
        embeddings = np.array([c["embedding"] for c in chunks])
        self.index.add(embeddings)
        # Save to disk
        faiss.write_index(self.index, self.index_path)
```

---

### 方案 4: 云服务

| 服务 | 免费层 | 优点 |
|------|--------|------|
| **Pinecone** | 有 | 易用，托管 |
| **Qdrant** | 开源 + 云端 | 灵活 |
| **Weaviate Cloud** | 有 | 全功能 |

---

## Embedding API 问题

### 问题

SiliconFlow 不支持 embeddings API：

```python
POST https://api.siliconflow.cn/v1/embeddings
400 Bad Request
```

### 解决方案

#### 选项 1: 使用 OpenAI Embeddings ✅

```python
provider_config = {
    "api_key": "sk-xxx",  # OpenAI API key
    "base_url": "https://api.openai.com/v1",
    "model": "text-embedding-3-small",
}

generator = EmbeddingBuilder.from_config(
    provider_name="openai",
    provider_config=provider_config,
    memory_config=memory_config,
)
```

**成本**:
- text-embedding-3-small: $0.02/1M tokens
- text-embedding-3-large: $0.13/1M tokens

#### 选项 2: 使用本地模型

```bash
pip install sentence-transformers
```

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = model.encode(text)
```

#### 选项 3: 使用 HuggingFace Inference API

```python
import requests

response = requests.post(
    "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2",
    headers={"Authorization": f"Bearer {hf_token}"},
    json={"inputs": text}
)
embedding = response.json()[0]
```

---

## 快速迁移指南

### 从 SQLite-Vect 迁移到 ChromaDB

**步骤 1**: 安装 chromadb
```bash
pip install chromadb
```

**步骤 2**: 创建新的 vector store 实现
```python
# src/fastreact/memory/chroma_store.py
from chromadb import Client
from .vector_store import VectorStore

class ChromaVectorStore(VectorStore):
    # 实现 VectorStore 接口
    ...
```

**步骤 3**: 更新配置
```json
{
  "memory": {
    "enabled": true,
    "vector_store": "chroma",  # 改为 chroma
    "persist_directory": "./data/chroma"
  }
}
```

**步骤 4**: 更新 VectorStoreBuilder
```python
# 在 vector_store.py 中添加
if store_type == "chroma":
    from .chroma_store import ChromaVectorStore
    return ChromaVectorStore(config.get("persist_directory"))
```

---

## 代码质量总结

### 架构设计 ✅

- **抽象层设计**: VectorStore 接口易于替换
- **模块化**: 各组件职责清晰
- **可扩展**: 支持多种 embedding provider

### 代码完整性 ✅

- 所有核心模块已实现
- 接口设计良好
- 错误处理完整
- 文档字符串完整

### 缺失的部分 ⚠️

1. Windows 平台的 sqlite-vec 扩展加载
2. SiliconFlow 的 embeddings API 支持
3. 集成测试（需要可用的 embedding API）
4. Engine 集成（需要向量存储正常工作）

---

## 建议

### 短期（立即可用）

1. **切换到 ChromaDB** - 最简单的解决方案
   - 跨平台支持
   - 安装简单
   - 接口兼容

2. **使用 OpenAI Embeddings** - 成本低
   - $0.02/1M tokens
   - 高质量 embedding

### 长期（生产级）

1. **支持多种 Vector Store** - 灵活切换
   - ChromaDB（开发/小规模）
   - Weaviate（生产环境）
   - 云服务（大规模）

2. **支持多种 Embedding Provider**
   - OpenAI
   - HuggingFace
   - 本地模型

---

## 总结

### 已完成 ✅

- 代码架构完整
- 接口设计优秀
- 易于替换实现

### 待解决 ⚠️

- Windows 兼容性
- Embedding API 配置

### 推荐行动

1. 使用 ChromaDB 替代 sqlite-vec
2. 配置 OpenAI embeddings
3. 运行完整测试

---

**最后更新**: 2025-02-01
**维护者**: FastReAct Team
