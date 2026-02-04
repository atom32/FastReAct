# FastReAct Multi-Tenant Workspace Support

## Overview

FastReAct 现已支持**动态工作区切换**，允许多租户场景下的知识库隔离。

## 核心特性

- **运行时切换**: 无需重启，随时切换 workspace
- **租户隔离**: 不同租户使用独立的向量数据库和文档目录
- **零配置影响**: config.json 中的配置作为默认值，运行时可覆盖
- **CLI 集成**: REPL 中通过 `/workspace` 命令管理
- **Gateway 集成**: WebSocket 连接支持 session 级别 workspace

---

## API 使用

### 1. Python API

#### 切换工作区

```python
from fastreact import FastReAct

agent = FastReAct(api_key="...", model="gpt-4")

# Switch to tenant A's workspace
agent.set_workspace("./tenants/a/docs")

# Query tenant A's knowledge base
result_a = await agent.run_async("What's the vacation policy?")

# Switch to tenant B's workspace
agent.set_workspace("./tenants/b/docs")

# Query tenant B's knowledge base
result_b = await agent.run_async("What's the vacation policy?")
```

#### 自定义数据库路径

```python
# Switch workspace with custom database location
agent.set_workspace(
    "./tenant_a/docs",
    db_path="./tenant_a/memory.db"
)
```

#### 查看当前工作区

```python
current = agent.get_workspace()
print(f"Current workspace: {current}")
```

---

### 2. CLI REPL

#### 查看当前工作区

```
> /workspace
Current workspace: None
  - RAG: disabled (enable in config.json to use)
```

#### 切换工作区

```
> /workspace ./tenants/tenant_a/docs
[Success] Workspace switched to: D:\FastReAct\tenants\tenant_a\docs
  - Found 2 items in workspace
  - RAG retriever re-initialized
```

#### 多租户查询流程

```
# Tenant A
> /workspace ./data/tenant_a
> run 查询差旅政策
# Answer: 根据租户 A 的文档回答

# Tenant B
> /workspace ./data/tenant_b
> run 查询差旅政策
# Answer: 根据租户 B 的文档回答（可能与 A 不同）
```

---

### 3. Gateway (WebSocket)

#### 连接时指定工作区

```javascript
// 前端 WebSocket 连接
const ws = new WebSocket(
  `ws://localhost:8080/ws/session-123?workspace=./tenants/tenant_a/docs`
);
```

#### 完整示例

```javascript
// Tenant A connection
const wsA = new WebSocket(
  "ws://localhost:8080/ws/session-a?workspace=./tenants/a/docs"
);

wsA.send(JSON.stringify({
  type: "message",
  content: "What's our vacation policy?"
  // Will search tenant A's knowledge base
}));

// Tenant B connection
const wsB = new WebSocket(
  "ws://localhost:8080/ws/session-b?workspace=./tenants/b/docs"
);

wsB.send(JSON.stringify({
  type: "message",
  content: "What's our vacation policy?"
  // Will search tenant B's knowledge base
}));
```

---

## 配置

### config.json 默认配置

```json
{
  "context": {
    "retrieval": {
      "enabled": true,
      "db_path": "./data/memory.db",
      "workspace_paths": ["./docs"],
      "provider": "modelscope",
      "embedding_model": "Qwen/Qwen3-Embedding-0.6B"
    }
  }
}
```

### 运行时覆盖优先级

```
运行时 set_workspace() > config.json > 硬编码默认值
```

---

## 架构设计

### 数据隔离

```
tenants/
├── tenant_a/
│   ├── docs/
│   │   ├── policy.txt
│   │   └── handbook.pdf
│   └── memory.db              # 向量数据库（租户 A）
├── tenant_b/
│   ├── docs/
│   │   ├── policy.txt         # 不同内容
│   │   └── handbook.pdf
│   └── memory.db              # 向量数据库（租户 B）
└── tenant_c/
    ├── docs/
    └── memory.db              # 向量数据库（租户 C）
```

### 切换流程

```
1. agent.set_workspace(path)
       ↓
2. 更新 RetrievalConfig.workspace_paths
       ↓
3. 更新 RetrievalConfig.db_path
       ↓
4. 重新初始化 MemoryRetriever
       ↓
5. 后续查询使用新工作区
```

---

## 多租户场景

### 场景 1: SaaS 应用

```python
# 用户认证后切换到对应租户工作区
async def handle_user_request(user_id: str, query: str):
    tenant_id = get_tenant_id(user_id)
    workspace = f"./tenants/{tenant_id}/docs"

    agent.set_workspace(workspace)
    result = await agent.run_async(query)

    return result
```

### 场景 2: 部门级隔离

```python
# 不同部门使用不同知识库
departments = {
    "hr": "./data/hr/knowledge",
    "engineering": "./data/engineering/docs",
    "sales": "./data/sales/materials"
}

def query_department(dept: str, question: str):
    agent.set_workspace(departments[dept])
    return await agent.run_async(question)
```

### 场景 3: 环境隔离

```python
# 开发/测试/生产环境隔离
environments = {
    "dev": "./envs/dev/docs",
    "staging": "./envs/staging/docs",
    "prod": "./envs/prod/docs"
}

agent.set_workspace(environments["dev"])
```

---

## 实现细节

### 核心改动

#### 1. RetrievalConfig 添加 workspace_paths

```python
@dataclass
class RetrievalConfig:
    workspace_paths: List[str] = field(default_factory=lambda: ["./docs"])

    @classmethod
    def from_dict(cls, config_dict: dict, workspace_paths: Optional[List[str]] = None):
        # 支持运行时覆盖
        if workspace_paths is None:
            workspace_paths = retrieval_cfg.get("workspace_paths", ["./docs"])
        return cls(workspace_paths=workspace_paths)
```

#### 2. FastReAct.set_workspace()

```python
def set_workspace(self, workspace: str, db_path: Optional[str] = None):
    # 更新配置
    self._retrieval_config.workspace_paths = [workspace_abs]
    self._retrieval_config.db_path = db_path or os.path.join(workspace_abs, "memory.db")

    # 重新初始化 retriever
    if self._retriever is not None:
        self._retriever.close()
        self._setup_retriever()
```

#### 3. Gateway 会话级别 workspace

```python
# WebSocket 端点添加 workspace 参数
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    workspace: Optional[str] = Query(None)  # Multi-tenant support
):
    # 保存到会话元数据
    session["metadata"]["workspace"] = workspace

    # 查询时动态切换
    if session_workspace:
        agent.set_workspace(session_workspace)
    result = await agent.run_async(query)
```

---

## 验证

### 运行测试

```bash
python test_multi_tenant_workspace.py
```

### 预期输出

```
======================================================================
[SUCCESS] All tests passed!
======================================================================

Multi-Tenant Workspace Test
[OK] Workspace switched successfully

CLI Workspace Command Test
[OK] Workspace switched

RetrievalConfig Runtime Override Test
[OK] Runtime workspace override successful
```

---

## 最佳实践

### 1. 目录结构

```
tenant_data/
├── {tenant_id}/
│   ├── docs/              # 文档目录
│   ├── memory.db          # 向量数据库
│   └── memory_embedding_cache.db
```

### 2. 初始化脚本

```python
def init_tenant(tenant_id: str):
    """初始化新租户工作区"""
    import os
    from pathlib import Path

    path = Path(f"./tenants/{tenant_id}")
    path.mkdir(parents=True, exist_ok=True)

    # 创建文档目录
    (path / "docs").mkdir(exist_ok=True)

    # 添加欢迎文档
    (path / "docs" / "welcome.txt").write_text(f"Welcome to {tenant_id}!")

    print(f"Tenant {tenant_id} initialized at {path}")
```

### 3. 错误处理

```python
try:
    agent.set_workspace(tenant_workspace)
    result = await agent.run_async(query)
except FileNotFoundError:
    print(f"Workspace not found: {tenant_workspace}")
    print("Please initialize the tenant first")
except Exception as e:
    print(f"Query failed: {e}")
```

---

## 限制与注意事项

1. **RAG 必须启用**: 只有启用 retrieval 时 workspace 切换才有意义
2. **数据库位置**: 每个租户应有独立的 memory.db
3. **并发安全**: 同一 agent 实例在并发切换 workspace 时需要注意
4. **内存占用**: 频繁切换可能导致多个 embedding 模型加载

---

## 未来扩展

- [ ] Workspace 模板（预定义知识库结构）
- [ ] Workspace 权限控制（RBAC）
- [ ] Workspace 热切换（无需重新初始化）
- [ ] 共享 workspace（只读访问）
- [ ] Workspace 版本控制
- [ ] Workspace 同步机制

---

**FastReAct + 多租户 Workspace = 企业级 AI Agent 平台**
