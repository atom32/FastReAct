# FastReAct V2.0 架构设计方案

> 基于 Moltbot 代码分析的下一代架构演进方案
> 创建时间: 2026-02-03

---

## 一、设计目标

### 1.1 核心目标

学习 Moltbot 的长处，在保持 FastReAct 简洁性的前提下，实现：

| 特性 | FastReAct V1 | Moltbot | FastReAct V2 目标 |
|------|-------------|---------|------------------|
| **响应模式** | 批量 | 流式 | ✅ 流式 + 批量可选 |
| **工具分组** | 扁平列表 | 分组（groups） | ✅ 简单分组（5-8组） |
| **沙盒执行** | 主机直接 | Docker 隔离 | ✅ Docker 必需 |
| **工具策略** | 基于列表 | 基于组 | ✅ 基于组的策略 |
| **实时输出** | ❌ | ✅ `<thinking>` | ✅ 实时思考/工具调用 |
| **设备同步** | ❌ | ✅ | ⚠️ 可选 |

### 1.2 保持的优势

- ✅ 简洁的 Python 代码
- ✅ 完善的上下文管理（渐进压缩、记忆刷新）
- ✅ 性能优化（LRU、去重、连接池）
- ✅ 本地 RAG（混合检索、向量存储）

---

## 二、流式响应架构

### 2.1 设计原则

**同时支持 SSE 和 WebSocket**，让用户根据场景选择：

```python
# API 设计示例
from fastreact import FastReAct

# 方式 1: SSE（推荐用于 Web）
agent = FastReAct(
    api_key="...",
    streaming_mode="sse",  # Server-Sent Events
)

async for chunk in agent.run_streaming("帮我写一个排序算法"):
    if chunk.type == "thinking":
        print(f"<thinking>{chunk.content}</thinking>")
    elif chunk.type == "tool_call":
        print(f"<tool>{chunk.tool_name}({chunk.params})</tool>")
    elif chunk.type == "tool_result":
        print(f"<result>{chunk.content[:100]}</result>")
    elif chunk.type == "answer":
        print(f"<answer>{chunk.content}</answer>")

# 方式 2: WebSocket（推荐用于 CLI/长连接）
agent = FastReAct(
    api_key="...",
    streaming_mode="websocket",
)

ws = await agent.connect_streaming()
await ws.send("帮我分析这个项目")
async for msg in ws:
    print(msg)  # 实时流式消息
```

### 2.2 核心组件设计

#### 2.2.1 流式上下文管理器

```python
# fastreact/core/streaming.py
from dataclasses import dataclass
from enum import Enum

class StreamChunkType(Enum):
    THINKING = "thinking"       # <thinking> 内容
    TOOL_CALL = "tool_call"     # 工具调用开始
    TOOL_RESULT = "tool_result" # 工具执行结果
    ANSWER = "answer"           # 最终答案
    ERROR = "error"             # 错误信息
    METADATA = "metadata"       # 元数据（token 使用等）

@dataclass
class StreamChunk:
    """流式响应数据块"""
    type: StreamChunkType
    content: str
    metadata: dict = None

    # 工具调用专用字段
    tool_name: str = None
    tool_params: dict = None
    tool_status: str = None  # "start" | "progress" | "complete"

class StreamingContext:
    """流式上下文管理器"""

    def __init__(self, engine: FastReAct):
        self.engine = engine
        self._buffer = ""
        self._state = "idle"

    async def stream_with_sse(self, query: str) -> AsyncIterator[StreamChunk]:
        """SSE 流式响应"""
        # 1. 发送开始事件
        yield StreamChunk(type=StreamChunkType.METADATA, content="start")

        # 2. 流式调用 LLM（使用 OpenAI Streaming API）
        async for delta in self._llm_stream(query):
            if delta.choices[0].delta.content:
                content = delta.choices[0].delta.content

                # 检测 <thinking> 标签
                if "<thinking>" in content:
                    yield StreamChunk(
                        type=StreamChunkType.THINKING,
                        content=self._extract_thinking(content)
                    )
                elif self._is_tool_call(delta):
                    # 解析工具调用
                    tool_call = self._parse_tool_call(delta)
                    yield StreamChunk(
                        type=StreamChunkType.TOOL_CALL,
                        content=tool_call.get("arguments", "{}"),
                        tool_name=tool_call.get("name", ""),
                        tool_params=tool_call.get("parameters", {}),
                        tool_status="start"
                    )

                    # 执行工具
                    result = await self._execute_tool(tool_call)
                    yield StreamChunk(
                        type=StreamChunkType.TOOL_RESULT,
                        content=str(result)[:500],  # 截断
                        tool_name=tool_call.get("name", ""),
                        tool_status="complete"
                    )
                else:
                    # 普通回答
                    yield StreamChunk(
                        type=StreamChunkType.ANSWER,
                        content=content
                    )

    async def stream_with_websocket(self, query: str, ws: WebSocket) -> AsyncIterator[StreamChunk]:
        """WebSocket 流式响应"""
        # 类似 SSE，但通过 WebSocket 发送
        while True:
            msg = await ws.recv()
            if msg == "stop":
                break

            # 处理消息...
```

#### 2.2.2 现有引擎改造

```python
# fastreact/core/engine.py 改造

class FastReAct:
    """V2: 支持流式响应"""

    def __init__(
        self,
        ...,
        streaming_mode: str = "none",  # "none" | "sse" | "websocket"
        enable_thinking_tag: bool = True,  # 是否输出 <thinking>
    ):
        self.streaming_mode = streaming_mode
        self.enable_thinking_tag = enable_thinking_tag

    async def run_streaming(
        self,
        query: str,
    ) -> AsyncIterator[StreamChunk]:
        """流式执行（新增）"""
        if self.streaming_mode == "none":
            # 降级到批量模式
            result = await self.run_async(query)
            yield StreamChunk(
                type=StreamChunkType.ANSWER,
                content=result["answer"]
            )
            return

        # 流式模式
        stream_ctx = StreamingContext(self)

        if self.streaming_mode == "sse":
            async for chunk in stream_ctx.stream_with_sse(query):
                yield chunk
        elif self.streaming_mode == "websocket":
            async for chunk in stream_ctx.stream_with_websocket(query):
                yield chunk
```

### 2.3 Gateway 改造

```python
# fastreact/gateway/server.py

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

@app.get("/v1/chat/stream")
async def chat_stream_sse(query: str):
    """SSE 流式端点"""

    async def generate():
        agent = FastReAct(
            api_key=get_api_key(),
            streaming_mode="sse",
        )

        async for chunk in agent.run_streaming(query):
            # SSE 格式
            yield f"event: {chunk.type.value}\n"
            yield f"data: {json.dumps(chunk.to_dict())}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )

@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """WebSocket 流式端点"""
    await websocket.accept()

    agent = FastReAct(
        api_key=get_api_key(),
        streaming_mode="websocket",
    )

    async for chunk in agent.run_streaming_via_ws(websocket):
        await websocket.send_json(chunk.to_dict())
```

---

## 三、工具分组系统

### 3.1 工具组定义

参考 Moltbot，定义 **5-8 个简单分组**：

```python
# fastreact/tools/groups.py

from enum import Enum

class ToolGroup(str, Enum):
    """工具分组"""
    FILESYSTEM = "group:fs"        # 文件系统操作
    RUNTIME = "group:runtime"       # 运行时执行
    WEB = "group:web"              # 网络请求
    MEMORY = "group:memory"        # 记忆/检索
    UI = "group:ui"                # 用户界面
    COMMUNICATION = "group:msg"    # 通信/消息
    AGENT = "group:agent"          # 子代理
    SYSTEM = "group:system"        # 系统工具

# 工具组到工具的映射
TOOL_GROUP_MAP = {
    ToolGroup.FILESYSTEM: [
        "read_file",
        "write_file",
        "edit_file",
        "delete_file",  # 新增
        "list_files",   # 新增
    ],
    ToolGroup.RUNTIME: [
        "bash",
        "python_exec",  # 新增
        "exec_code",    # 新增
    ],
    ToolGroup.WEB: [
        "search",
        "http_request",
        "fetch_url",    # 新增
    ],
    ToolGroup.MEMORY: [
        "memory_search",
        "memory_save",
        "memory_get",
    ],
    ToolGroup.UI: [
        "browser_open",   # 新增
        "screenshot",     # 新增
    ],
    ToolGroup.COMMUNICATION: [
        "send_message",
        "email",         # 新增
    ],
    ToolGroup.AGENT: [
        "spawn_subagent",
        "query_agent",
    ],
    ToolGroup.SYSTEM: [
        "calculator",
        "datetime",
        "weather",
    ],
}
```

### 3.2 工具注册表改造

```python
# fastreact/tools/registry_v2.py

class ToolRegistry:
    """V2: 支持分组的工具注册表"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._groups: Dict[ToolGroup, List[str]] = {}

    def register(
        self,
        tool: Tool,
        group: ToolGroup = ToolGroup.SYSTEM,
        tags: List[str] = None,
    ):
        """注册工具到分组"""
        tool.group = group
        tool.tags = tags or []

        self._tools[tool.name] = tool

        if group not in self._groups:
            self._groups[group] = []
        self._groups[group].append(tool.name)

    def get_tools_by_group(self, group: ToolGroup) -> List[Tool]:
        """获取分组内的所有工具"""
        tool_names = self._groups.get(group, [])
        return [self._tools[name] for name in tool_names]

    def get_tool_groups_for_policy(
        self,
        allowed_groups: List[ToolGroup],
    ) -> List[Tool]:
        """根据策略获取工具（用于工具策略）"""
        tools = []
        for group in allowed_groups:
            tools.extend(self.get_tools_by_group(group))
        return tools
```

---

## 四、基于组的工具策略

### 4.1 多层策略设计

```python
# fastreact/core/policy_v2.py

@dataclass
class ToolPolicy:
    """工具策略配置"""
    name: str
    allow_groups: List[ToolGroup]      # 允许的工具组
    deny_groups: List[ToolGroup]       # 拒绝的工具组
    allow_tools: List[str]             # 单独允许的工具
    deny_tools: List[str]              # 单独拒绝的工具
    require_approval: List[str]        # 需要审批的工具

class PolicyEngine:
    """策略引擎（多层检查）"""

    def __init__(self):
        self.policies = []

    def add_policy(self, policy: ToolPolicy):
        """添加策略层"""
        self.policies.append(policy)

    def check_tool_allowed(
        self,
        tool_name: str,
        tool_group: ToolGroup,
    ) -> tuple[bool, str | None]:
        """
        检查工具是否允许执行

        返回: (是否允许, 拒绝原因)
        """
        # 策略检查顺序：全局 -> 代理 -> 会话 -> 用户
        for policy in self.policies:
            # 1. 检查拒绝组
            if tool_group in policy.deny_groups:
                # 但如果单独允许，则覆盖
                if tool_name not in policy.allow_tools:
                    return False, f"工具组 {tool_group} 被策略 {policy.name} 拒绝"

            # 2. 检查允许组
            if policy.allow_groups and tool_group not in policy.allow_groups:
                return False, f"工具组 {tool_group} 不在允许列表中"

            # 3. 检查单独拒绝
            if tool_name in policy.deny_tools:
                return False, f"工具 {tool_name} 被策略 {policy.name} 拒绝"

        return True, None

    async def request_approval(
        self,
        tool_name: str,
        params: dict,
        policy: ToolPolicy,
    ) -> bool:
        """请求用户审批"""
        if tool_name not in policy.require_approval:
            return True

        # 发送审批请求（通过回调或 WebSocket）
        print(f"[APPROVAL] 需要审批: {tool_name}({params})")
        print("确认执行？(y/n)")

        # 等待用户输入（实际应该通过 WebSocket）
        response = await self._wait_for_approval()
        return response.lower() == "y"
```

### 4.2 预定义策略

```python
# fastreact/core/policies.py

# 预定义策略
POLICY_SAFE = ToolPolicy(
    name="safe",
    allow_groups=[
        ToolGroup.SYSTEM,
        ToolGroup.MEMORY,
        ToolGroup.WEB,
    ],
    deny_groups=[
        ToolGroup.RUNTIME,  # 拒绝执行
    ],
)

POLICY_CODING = ToolPolicy(
    name="coding",
    allow_groups=[
        ToolGroup.FILESYSTEM,
        ToolGroup.RUNTIME,
        ToolGroup.MEMORY,
        ToolGroup.SYSTEM,
    ],
    deny_groups=[
        ToolGroup.UI,
        ToolGroup.COMMUNICATION,
    ],
    require_approval=[
        "bash",        # 需要审批
        "python_exec", # 需要审批
    ],
)

POLICY_FULL_ACCESS = ToolPolicy(
    name="full",
    allow_groups=[g for g in ToolGroup],
    deny_groups=[],
)
```

---

## 五、Docker 沙盒执行

### 5.1 架构设计

```python
# fastreact/sandbox/docker.py

class DockerSandbox:
    """Docker 沙盒管理器"""

    def __init__(
        self,
        image: str = "python:3.11-slim",
        auto_remove: bool = True,
        memory_limit: str = "512m",
        cpu_limit: str = "0.5",
    ):
        self.image = image
        self.auto_remove = auto_remove
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self._container_id = None

    async def create(self):
        """创建沙盒容器"""
        import docker

        client = docker.from_env()

        container = client.containers.run(
            self.image,
            command="tail -f /dev/null",  # 保持运行
            detach=True,
            auto_remove=self.auto_remove,
            mem_limit=self.memory_limit,
            cpu_quota=int(float(self.cpu_limit) * 100000),
            volumes={
                # 挂载工作目录
                os.getcwd(): {
                    "bind": "/workspace",
                    "mode": "rw",
                }
            },
            working_dir="/workspace",
        )

        self._container_id = container.id
        return container

    async def exec_command(
        self,
        command: str,
        timeout: int = 30,
    ) -> SandboxResult:
        """在沙盒中执行命令"""
        import docker

        client = docker.from_env()
        container = client.containers.get(self._container_id)

        # 执行命令
        result = container.exec_run(
            command,
            workdir="/workspace",
            timeout=timeout,
        )

        return SandboxResult(
            exit_code=result.exit_code,
            output=result.output.decode('utf-8', errors='ignore'),
            error=result.stderr.decode('utf-8', errors='ignore') if result.stderr else None,
        )

    async def destroy(self):
        """销毁沙盒"""
        if self._container_id:
            import docker
            client = docker.from_env()
            container = client.containers.get(self._container_id)
            container.stop()
            container.remove()
            self._container_id = None
```

### 5.2 沙盒工具包装

```python
# fastreact/tools/sandbox_tools.py

class SandboxBashTool(Tool):
    """沙盒化的 Bash 工具"""

    def __init__(self, sandbox: DockerSandbox):
        self.sandbox = sandbox

    async def execute(
        self,
        command: str,
        timeout: int = 30,
    ) -> str:
        """在 Docker 沙盒中执行命令"""
        result = await self.sandbox.exec_command(command, timeout)

        if result.exit_code != 0:
            return f"[ERROR] Command failed (exit {result.exit_code}):\n{result.error or result.output}"

        return result.output

class SandboxPythonTool(Tool):
    """沙盒化的 Python 执行工具"""

    async def execute(
        self,
        code: str,
        timeout: int = 30,
    ) -> str:
        """在 Docker 沙盒中执行 Python 代码"""
        # 将代码写入临时文件
        with open("/tmp/sandbox_exec.py", "w") as f:
            f.write(code)

        # 在沙盒中执行
        result = await self.sandbox.exec_command(
            f"python /tmp/sandbox_exec.py",
            timeout=timeout,
        )

        return result.output
```

### 5.3 工厂函数

```python
# fastreact/tools/fn_registry.py 更新

def create_sandbox_bash_tool(sandbox: DockerSandbox) -> Tool:
    """创建沙盒 Bash 工具"""
    return Tool(
        name="bash",
        label="Shell (Sandboxed)",
        description="在 Docker 沙盒中执行 Shell 命令。安全隔离，不影响主机。",
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout": {"type": "integer", "default": 30},
            },
            "required": ["command"],
        },
        execute=SandboxBashTool(sandbox).execute,
    )

def create_sandbox_tools(sandbox: DockerSandbox) -> List[Tool]:
    """创建所有沙盒工具"""
    return [
        create_sandbox_bash_tool(sandbox),
        SandboxPythonTool(sandbox),
        # ... 更多沙盒工具
    ]
```

---

## 六、工具丰富计划

### 6.1 新增工具列表

基于 Moltbot 和实际需求，新增以下工具：

| 分组 | 工具名 | 功能 | 优先级 |
|------|--------|------|--------|
| **fs** | `delete_file` | 删除文件 | P0 |
| **fs** | `list_files` | 列出目录 | P0 |
| **fs** | `copy_file` | 复制文件 | P1 |
| **fs** | `move_file` | 移动文件 | P1 |
| **runtime** | `python_exec` | 执行 Python 代码 | P0 |
| **runtime** | `exec_code` | 执行任意代码（沙盒） | P1 |
| **web** | `fetch_url` | 获取 URL 内容 | P1 |
| **web** | `api_call` | 调用 REST API | P2 |
| **memory** | `memory_save` | 保存记忆 | P1 |
| **memory** | `memory_get` | 获取记忆 | P1 |
| **ui** | `browser_open` | 打开浏览器（测试用） | P2 |
| **ui** | `screenshot` | 截图 | P2 |
| **msg** | `send_message` | 发送消息（多渠道） | P2 |
| **agent** | `spawn_subagent` | 启动子代理 | P1 |
| **agent** | `query_agent` | 查询子代理 | P1 |

### 6.2 工具实现示例

```python
# fastreact/tools/filesystem_tools.py

async def delete_file(path: str) -> str:
    """删除文件"""
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return f"[ERROR] File not found: {path}"
    p.unlink()
    return f"[OK] Deleted: {path}"

async def list_files(
    path: str = ".",
    recursive: bool = False,
    pattern: str = "*",
) -> str:
    """列出目录文件"""
    from pathlib import Path
    p = Path(path)

    if recursive:
        files = list(p.rglob(pattern))
    else:
        files = list(p.glob(pattern))

    result = "\n".join(
        f"{'[DIR] ' if f.is_dir() else '[FILE]'}{f.relative_to(p)}"
        for f in sorted(files)
    )
    return result

# fastreact/tools/runtime_tools.py

async def python_exec(code: str) -> str:
    """执行 Python 代码（在沙盒中）"""
    # 使用沙盒执行
    pass

async def exec_code(
    code: str,
    language: str = "python",
) -> str:
    """执行代码（多语言支持）"""
    # 根据语言选择执行器
    pass
```

---

## 七、设备同步（可选）

### 7.1 设计思路

参考 Moltbot 的"设备同步"功能，实现：

```python
# fastreact/sync/device_sync.py

class DeviceSyncManager:
    """设备同步管理器"""

    def __init__(self, storage_path: str = "./sync"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def sync_state(self, state: dict) -> str:
        """同步状态到其他设备"""
        import json

        state_file = self.storage_path / f"state_{int(time.time())}.json"
        state_file.write_text(json.dumps(state, indent=2))

        # 上传到云存储（可选）
        # await self._upload_to_cloud(state_file)

        return f"[OK] State synced: {state_file.name}"

    async def load_latest_state(self) -> dict:
        """加载最新的状态"""
        state_files = sorted(self.storage_path.glob("state_*.json"))
        if not state_files:
            return {}

        latest = state_files[-1]
        import json
        return json.loads(latest.read_text())
```

---

## 八、分布式架构（长期）

### 8.1 微服务拆分

```
FastReAct V2 (分布式架构):

┌─────────────────────────────────────────────────────┐
│                  API Gateway / Load Balancer          │
└──────────────┬───────────────────────────────────────┘
               │
       ┌───────┴───────┬───────────────┬────────────┐
       │               │               │            │
┌──────▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐ ┌───▼────────┐
│ Engine Svc  │ │ Memory Svc│ │ Sandbox Svc│ │ Tool Svc   │
│ (ReACT核心) │ │ (向量记忆) │ │ (Docker)   │ │ (工具注册) │
└─────────────┘ └───────────┘ └───────────┘ └────────────┘
```

### 8.2 服务间通信

```python
# 使用 gRPC 或 HTTP/REST

# engine/memory.proto
service MemoryService {
    rpc Search(SearchRequest) returns (SearchResponse);
    rpc Save(SaveRequest) returns (SaveResponse);
}

# engine/sandbox.proto
service SandboxService {
    rpc ExecCommand(ExecRequest) returns (ExecResponse);
    rpc CreateContainer(CreateRequest) returns (CreateResponse);
}
```

---

## 九、实现路线图

### 阶段 1: 流式响应 (1-2 周)

- [ ] 实现 `StreamingContext` 类
- [ ] 改造 `FastReAct.run_streaming()` 方法
- [ ] 实现 SSE 端点
- [ ] 实现 WebSocket 端点
- [ ] CLI 集成流式输出
- [ ] 测试和文档

### 阶段 2: 工具分组 (1 周)

- [ ] 定义 `ToolGroup` 枚举
- [ ] 创建 `TOOL_GROUP_MAP`
- [ ] 改造 `ToolRegistry`
- [ ] 更新工具注册
- [ ] 文档更新

### 阶段 3: 工具策略 (1 周)

- [ ] 实现 `PolicyEngine`
- [ ] 定义预定义策略
- [ ] 实现审批流程
- [ ] 集成到引擎
- [ ] 测试和文档

### 阶段 4: Docker 沙盒 (2-3 周)

- [ ] 实现 `DockerSandbox` 类
- [ ] 创建沙盒工具
- [ ] 配置管理
- [ ] 错误处理
- [ ] 测试和文档

### 阶段 5: 工具丰富 (持续)

- [ ] 实现新工具（按优先级）
- [ ] 工具测试
- [ ] 工具文档

### 阶段 6: 分布式架构（长期）

- [ ] 服务拆分
- [ ] API 设计
- [ ] 服务发现
- [ ] 部署方案

---

## 十、向后兼容性

### 10.1 API 兼容

```python
# V1 API 仍然可用
agent = FastReAct(api_key="...")
result = await agent.run_async("query")  # 批量模式

# V2 API（新功能）
agent = FastReAct(
    api_key="...",
    streaming_mode="sse",  # 新参数
)
async for chunk in agent.run_streaming("query"):
    print(chunk)
```

### 10.2 配置兼容

```json
// config.json V1
{
  "tools": {
    "builtin_enabled": true
  }
}

// config.json V2（扩展）
{
  "tools": {
    "builtin_enabled": true,
    "groups": ["fs", "runtime", "web"],  // 新增
    "policy": "coding",  // 新增
    "sandbox": {
      "enabled": true,
      "image": "python:3.11-slim"
    }
  },
  "streaming": {
    "mode": "sse",  // 新增
    "enable_thinking": true
  }
}
```

---

## 十一、总结

### 核心改进

1. **流式响应** - 实时输出 `<thinking>` 和工具调用
2. **工具分组** - 5-8 个简单分组，便于管理
3. **沙盒执行** - Docker 必需，安全隔离
4. **工具策略** - 基于组的权限控制
5. **工具丰富** - 新增 15+ 实用工具

### 实现优先级

**高优先级** (P0):
- 流式响应
- 工具分组
- Docker 沙盒
- 基础工具丰富

**中优先级** (P1):
- 工具策略
- 设备同步

**低优先级** (P2):
- UI 工具
- 分布式架构

### 预期效果

实现后，FastReAct 将：
- ✅ 接近 Moltbot 的核心能力
- ✅ 保持 Python 简洁性
- ✅ 适合生产环境部署
- ✅ 更好的用户体验（流式输出）
- ✅ 更高的安全性（Docker 沙盒）
