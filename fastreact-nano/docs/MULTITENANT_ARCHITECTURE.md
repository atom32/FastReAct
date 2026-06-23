# FastReAct 多租户架构实现指南

> Reference guide: this document includes historical version labels and
> integration guidance. For current FastReAct Nano `2.4.2` service behavior, use
> [HEADLESS_SERVICE.md](HEADLESS_SERVICE.md), [security.md](security.md), and
> [CONFIG_FILE_LOCATIONS.md](CONFIG_FILE_LOCATIONS.md).

**版本**: v2.5.0
**日期**: 2025-03-04
**目标**: 为集成 PageIndex、OpenViking 等系统提供多租户隔离指导

---

## 目录

1. [核心概念](#核心概念)
2. [用户识别机制](#用户识别机制)
3. [Workspace 隔离](#workspace-隔离)
4. [会话管理](#会话管理)
5. [数据隔离](#数据隔离)
6. [安全机制](#安全机制)
7. [实现细节](#实现细节)
8. [扩展指南](#扩展指南)
9. [最佳实践](#最佳实践)

---

## 核心概念

### 什么是多租户

**多租户（Multi-tenancy）**: 单一系统实例为多个租户（用户/组织）提供服务，每个租户的数据完全隔离。

**FastReAct 的多租户模型**:
```
┌─────────────────────────────────────────────────┐
│              FastReAct Platform                 │
│  - 单一 Agent 实例                              │
│  - 统一的工具和技能管理                          │
│  - 统一的 API 接口                              │
└─────────────────┬───────────────────────────────┘
                  │
     ┌────────────┼────────────┐
     │            │            │
     ↓            ↓            ↓
┌─────────┐ ┌─────────┐ ┌─────────┐
│ User A  │ │ User B  │ │ User C  │
│ Workspace│ │ Workspace│ │ Workspace│
│ /var/... │ │ /var/... │ │ /var/... │
└─────────┘ └─────────┘ └─────────┘
```

### 核心原则

1. **数据隔离**: 每个用户的数据（文件、配置、会话历史）完全隔离
2. **资源隔离**: 每个用户的 workspace 独立，避免互相干扰
3. **身份识别**: 通过 `user_key` 唯一标识用户
4. **透明性**: 对上层应用透明，只需传递 `user_key`
5. **安全性**: 防止路径遍历、跨用户访问

---

## 用户识别机制

### User Key 格式

**格式**: `{channel}:{user_id}`

**组成部分**:
- `channel`: 接入渠道（web, feishu, api, pageindex, openviking）
- `user_id`: 用户唯一标识（email, UUID, 用户名等）

**示例**:
```python
# Web 用户
"web:user@example.com"

# 飞书用户
"feishu:ou_7d8a8f6c3b4c4d5f"

# API 客户端
"api:client_abc123"

# PageIndex (未来)
"pageindex:user_12345"

# OpenViking (未来)
"openviking:org_67890:user_abc"
```

### User Key 设计原则

#### 1. Channel 命名规范

| Channel | 用途 | 示例 |
|---------|------|------|
| `web` | Web UI 用户 | `web:user@example.com` |
| `feishu` | 飞书集成 | `feishu:ou_xxx` |
| `api` | REST API | `api:client_xxx` |
| `gateway` | WebSocket Gateway | `gateway:session_xxx` |
| `pageindex` | PageIndex 集成 | `pageindex:user_xxx` |
| `openviking` | OpenViking 集成 | `openviking:user_xxx` |

#### 2. User ID 选择

**推荐格式**:
- **Email**: `user@example.com`（人类用户）
- **UUID**: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`（系统用户）
- **平台 ID**: 使用原始平台的 user_id（如飞书 `ou_xxx`）

**避免**:
- ❌ 纯数字（容易冲突）
- ❌ 特殊字符（`/`, `\`, `..`）
- ❌ 过长的 ID（超过 256 字符）

#### 3. 验证规则

**文件**: `src/fastreact/core/multitenant.py`

```python
import re

# 安全模式：只允许字母、数字、下划线、@、.、=、+、-
SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9_@.=+-]+$')

def validate_user_key(user_key: str) -> tuple[bool, str]:
    """
    验证 user_key 格式

    Returns:
        (is_valid, error_message)
    """
    if not user_key:
        return False, "user_key cannot be empty"

    # 检查格式 {channel}:{user_id}
    if ":" not in user_key:
        return False, "user_key must be in format {channel}:{user_id}"

    parts = user_key.split(":", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return False, "channel and user_id cannot be empty"

    channel, user_id = parts

    # 检查安全字符（防止路径遍历）
    if not SAFE_PATTERN.match(channel) or not SAFE_PATTERN.match(user_id):
        return False, f"unsafe characters in user_key: {user_key}"

    # 检查长度
    if len(user_key) > 256:
        return False, f"user_key too long (max 256 chars): {len(user_key)}"

    return True, ""
```

### 默认 User Key

**向后兼容**: 如果未提供 `user_key`，使用默认值

```python
DEFAULT_USER_KEY = "web:default"

# 使用场景
- 临时用户（未登录）
- 开发测试
- 单租户模式降级
```

**注意**: 默认 user_key 的数据不持久化，重启后丢失。

---

## Workspace 隔离

### Workspace 结构

**单租户模式**（已废弃）:
```
./workspaces/
└── default/
    ├── config.json
    ├── memory.json
    ├── skills/
    └── files/
```

**多租户模式**（当前）:
```
/var/fastreact/tenants/
├── gateway/
│   ├── web:user1@example.com/
│   │   ├── config.json
│   │   ├── memory.json
│   │   ├── skills/
│   │   └── files/
│   ├── web:user2@example.com/
│   └── admin:admin/
├── feishu/
│   ├── feishu:ou_7d8a8f6c3b4c4d5f/
│   └── feishu:ou_8e9b0f7d4c5d5e6a/
├── pageindex/           # 未来
│   └── pageindex:user_123/
└── openviking/          # 未来
    └── openviking:user_456/
```

### Workspace 路径生成

**核心逻辑**: `src/fastreact/core/multitenant.py`

```python
from pathlib import Path
import re

class MultiTenantManager:
    """
    多租户 Workspace 管理器

    功能：
    - 自动创建 workspace 目录
    - 路径安全验证
    - 目录结构初始化
    """

    def __init__(self, base_workspace: Path, channel: str = "gateway"):
        """
        初始化管理器

        Args:
            base_workspace: 基础路径（如 /var/fastreact/tenants）
            channel: 渠道名称（gateway, feishu, pageindex 等）
        """
        self.base_workspace = base_workspace
        self.channel = channel

        # 创建基础目录
        self.base_workspace.mkdir(parents=True, exist_ok=True)

    def get_user_workspace(self, user_key: str) -> Path:
        """
        获取用户 workspace 路径

        流程：
        1. 验证 user_key 格式
        2. 提取 channel 和 user_id
        3. 安全检查（路径遍历防护）
        4. 构建 workspace 路径
        5. 自动创建目录结构

        Args:
            user_key: 用户标识（如 "web:user@example.com"）

        Returns:
            Path: 用户 workspace 路径

        Raises:
            ValueError: user_key 格式错误或包含不安全字符
        """
        # 1. 验证格式
        if ":" not in user_key:
            raise ValueError(f"Invalid user_key format: {user_key}")

        # 2. 提取 channel 和 user_id
        channel, user_id = user_key.split(":", 1)

        # 3. 安全检查
        SAFE_PATTERN = re.compile(r'^[a-zA-Z0-9_@.=+-]+$')
        if not SAFE_PATTERN.match(channel) or not SAFE_PATTERN.match(user_id):
            raise ValueError(f"Unsafe characters in user_key: {user_key}")

        # 4. 构建路径（将 : 替换为 _）
        safe_user_key = f"{channel}_{user_id}"
        workspace = self.base_workspace / safe_user_key

        # 5. 路径遍历防护
        workspace = workspace.resolve()
        base_resolved = self.base_workspace.resolve()

        if not workspace.is_relative_to(base_resolved):
            raise ValueError(f"Workspace escape detected: {user_key}")

        # 6. 自动创建目录
        self._create_workspace_structure(workspace)

        return workspace

    def _create_workspace_structure(self, workspace: Path):
        """
        创建 workspace 目录结构

        结构：
        {workspace}/
        ├── config.json      # 用户配置（可选）
        ├── memory.json      # 长期记忆（可选）
        ├── skills/          # 用户自定义技能
        └── files/           # 用户文件
        """
        # 创建子目录
        (workspace / "skills").mkdir(exist_ok=True)
        (workspace / "files").mkdir(exist_ok=True)

        # 创建默认配置（如果不存在）
        config_path = workspace / "config.json"
        if not config_path.exists():
            self._create_default_config(config_path)
```

### 安全机制

#### 1. 路径遍历防护

**攻击示例**:
```python
# 恶意 user_key
"web:../../../etc/passwd"

# 防护
workspace = workspace.resolve()
if not workspace.is_relative_to(base_resolved):
    raise ValueError("Workspace escape detected")
```

#### 2. 字符白名单

**只允许安全字符**: `a-zA-Z0-9_@.=+-`

**禁止字符**:
- `/`, `\` (路径分隔符)
- `..` (父目录引用)
- `*`, `?` (通配符)
- `<`, `>`, `|`, `&` (Shell 元字符)

#### 3. 长度限制

```python
MAX_USER_KEY_LENGTH = 256

if len(user_key) > MAX_USER_KEY_LENGTH:
    raise ValueError(f"user_key too long: {len(user_key)}")
```

---

## 会话管理

### 会话创建

**API**: `Agent.run_or_inject()`

```python
from fastreact import Agent, Config

async def main():
    config = Config.load()
    agent = Agent(config=config, multitenant=True)

    # 第一次调用：自动创建 workspace 和会话
    async for event in agent.run_or_inject(
        query="你好",
        user_key="web:user@example.com",  # ← 关键参数
    ):
        print(f"{event.type}: {event.content}")

    # 第二次调用：复用同一个会话（如果在上一次的 30 秒内）
    async for event in agent.run_or_inject(
        query="帮我查文件",
        user_key="web:user@example.com",  # ← 相同 user_key
    ):
        print(f"{event.type}: {event.content}")
```

### 会话生命周期

**流程**:
```
1. 创建/获取会话
   ├─ 检查是否存在活跃会话
   ├─ 不存在 → 创建新会话
   │   ├─ 调用 MultiTenantManager.get_user_workspace()
   │   ├─ 自动创建 workspace 目录
   │   ├─ 加载用户配置（config.json）
   │   └─ 初始化 MemoryManager
   └─ 存在 → 复用现有会话

2. 执行查询
   ├─ ReAct 循环
   ├─ 工具执行（在用户 workspace 中操作）
   └─ 事件流返回

3. 会话保持
   ├─ 会话缓存（Agent._sessions）
   ├─ 跟随窗口（30 秒内自动关联）
   └─ 会话历史自动管理

4. 会话清理
   ├─ 超时清理（可配置）
   ├─ 手动清理（agent.cleanup_sessions()）
   └─ 内存释放
```

### 会话隔离

**每个 user_key 独立的会话**:

```python
# 用户 A 的会话
session_a = agent.get_or_create_session(
    session_id="session-1",
    user_key="web:user@example.com"
)
# Workspace: /var/fastreact/tenants/gateway/web_user@example.com/

# 用户 B 的会话
session_b = agent.get_or_create_session(
    session_id="session-2",
    user_key="feishu:ou_7d8a8f6c3b4c4d5f"
)
# Workspace: /var/fastreact/tenants/feishu/feishu_ou_7d8a8f6c3b4c4d5f/

# 完全隔离，互不影响
```

**会话队列隔离**:

```python
# 每个 session_id 独立的队列
agent._session_queues = {
    "session-1": MessageQueue(),  # 用户 A 的队列
    "session-2": MessageQueue(),  # 用户 B 的队列
    # 互不干扰
}
```

---

## 数据隔离

### 文件系统隔离

**工具执行在用户 workspace 中**:

```python
# 用户 A: web:user1@example.com
query = "创建文件 test.txt，内容为 Hello"
# 文件创建在: /var/fastreact/tenants/gateway/web_user1@example.com/files/test.txt

# 用户 B: web:user2@example.com
query = "创建文件 test.txt，内容为 World"
# 文件创建在: /var/fastreact/tenants/gateway/web_user2@example.com/files/test.txt

# 两个文件完全独立，互不干扰
```

### 配置隔离

**每个用户独立的配置**:

```python
# 用户 A 的配置
/var/fastreact/tenants/gateway/web_user1@example.com/config.json
{
  "llm": {
    "model": "gpt-4o",
    "temperature": 0.7
  },
  "tools": {
    "enable_exec": true
  }
}

# 用户 B 的配置
/var/fastreact/tenants/gateway/web_user2@example.com/config.json
{
  "llm": {
    "model": "gpt-4o-mini",
    "temperature": 0.5
  },
  "tools": {
    "enable_exec": false
  }
}
```

### 会话历史隔离

**每个用户的对话历史独立**:

```python
# 用户 A 的历史
session_a._history = [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！有什么可以帮助你？"},
    # ... 用户 A 的对话
]

# 用户 B 的历史
session_b._history = [
    {"role": "user", "content": "帮我分析数据"},
    {"role": "assistant", "content": "好的，请提供数据"},
    # ... 用户 B 的对话（完全独立）
]
```

### 记忆隔离

**MemoryManager 的多租户支持**:

```python
# 用户 A 的记忆
/var/fastreact/tenants/gateway/web_user1@example.com/memory.json
{
  "consolidated": [
    "用户 A 偏好使用 Python 进行数据分析",
    "用户 A 经常查询金融数据",
    # ... 用户 A 的长期记忆
  ]
}

# 用户 B 的记忆
/var/fastreact/tenants/gateway/web_user2@example.com/memory.json
{
  "consolidated": [
    "用户 B 是前端开发工程师",
    "用户 B 关注 JavaScript 框架",
    # ... 用户 B 的长期记忆（完全独立）
  ]
}
```

---

## 安全机制

### 1. 身份验证

**应用层负责**（FastReAct 不处理）:

```python
# 示例：Gateway 的用户识别
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # 从 query 参数获取 user_key（应用层已验证）
    user_key = websocket.query_params.get("user_key", "web:default")

    # 格式验证
    if ":" not in user_key:
        await websocket.close(code=1008, reason="Invalid user_key format")
        return

    # 创建会话（FastReAct 层）
    session = Session(
        session_id=str(uuid.uuid4()),
        websocket=websocket,
        user_key=user_key,  # ← 传递到 FastReAct
    )
```

### 2. 授权

**FastReAct 层面**:

```python
# 每次操作都检查 user_key
async def read_file(file_path: str):
    # 1. 获取当前会话的 user_key
    user_key = session.user_key  # "web:user@example.com"

    # 2. 构建受限制的路径
    workspace = multitenant_manager.get_user_workspace(user_key)
    safe_path = workspace / "files" / file_path

    # 3. 解析路径（防止 ../）
    safe_path = safe_path.resolve()

    # 4. 验证路径在 workspace 内
    if not safe_path.is_relative_to(workspace):
        raise PermissionError("Path traversal detected")

    # 5. 读取文件
    return safe_path.read_text(encoding='utf-8')
```

### 3. 审计日志

**记录关键操作**（可扩展）:

```python
import logging

audit_logger = logging.getLogger("fastreact.audit")

class MultiTenantManager:
    def get_user_workspace(self, user_key: str) -> Path:
        # 记录 workspace 访问
        audit_logger.info(f"Workspace access: {user_key}")

        workspace = self._create_workspace(user_key)

        # 记录 workspace 创建
        if not workspace.exists():
            audit_logger.info(f"Workspace created: {user_key} -> {workspace}")

        return workspace
```

### 4. 资源配额

**防止资源滥用**（未来扩展）:

```python
class MultiTenantManager:
    def __init__(self):
        # 每个用户的 workspace 大小限制
        self.quota = {
            "max_workspace_size": 1_000_000_000,  # 1GB
            "max_file_count": 10_000,
        }

    def check_quota(self, user_key: str) -> bool:
        """检查用户是否超出配额"""
        workspace = self.get_user_workspace(user_key)

        # 计算总大小
        total_size = sum(
            f.stat().st_size
            for f in workspace.rglob('*')
            if f.is_file()
        )

        if total_size > self.quota["max_workspace_size"]:
            raise QuotaExceededError(
                f"User {user_key} exceeded quota: "
                f"{total_size} > {self.quota['max_workspace_size']}"
            )

        return True
```

---

## 实现细节

### Agent 多租户初始化

**文件**: `src/fastreact/agent.py`

```python
class Agent:
    def __init__(
        self,
        config: Config,
        multitenant: bool = False,  # ← 关键参数
        base_workspace: Path = Path("/var/fastreact/tenants"),
    ):
        self._multitenant = multitenant
        self._base_workspace = base_workspace

        # 多租户管理器
        if multitenant:
            self._multitenant_manager = MultiTenantManager(
                base_workspace=base_workspace,
                channel="gateway"  # 可配置
            )
        else:
            self._multitenant_manager = None

    def create_session(
        self,
        session_id: str,
        user_key: Optional[str] = None,
    ) -> AgentSession:
        """
        创建会话（多租户支持）

        如果 multitenant=True 且 user_key 提供：
        - 自动创建用户 workspace
        - 加载用户配置
        - 隔离用户数据
        """
        session = AgentSession(
            session_id=session_id,
            agent=self,
        )

        # 设置 user_key
        session.user_key = user_key

        # 多租户：自动创建 workspace
        if self._multitenant and user_key:
            workspace = self._multitenant_manager.get_user_workspace(user_key)
            session._workspace_path = workspace

            # 初始化 MemoryManager（使用用户 workspace）
            session._memory_manager = MemoryManager(
                workspace_path=workspace,
                agent=self,
            )

        return session
```

### run_or_inject API

**文件**: `src/fastreact/agent.py`

```python
async def run_or_inject(
    self,
    query: str,
    user_key: str,  # ← 关键参数
    session_id: Optional[str] = None,
    force_new: bool = False,
) -> AsyncIterator[AgentEvent]:
    """
    运行或注入到会话（多租户支持）

    Args:
        query: 用户查询
        user_key: 用户标识（必需）
        session_id: 会话 ID（可选）
        force_new: 强制创建新会话

    Yields:
        AgentEvent: 执行事件流
    """
    # 1. 验证 user_key
    is_valid, error = validate_user_key(user_key)
    if not is_valid:
        yield AgentEvent.error(session_id, error)
        return

    # 2. 获取或创建会话
    if force_new:
        session = self.create_session(
            session_id=session_id or str(uuid.uuid4()),
            user_key=user_key,
        )
    else:
        # 查找活跃会话
        session = self.find_active_session(user_key)
        if not session:
            session = self.create_session(
                session_id=session_id or str(uuid.uuid4()),
                user_key=user_key,
            )

    # 3. 执行查询
    async for event in self._run_react_loop(session, query):
        yield event
```

### Workspace 自动创建

**文件**: `src/fastreact/core/multitenant.py`

```python
def get_user_workspace(self, user_key: str) -> Path:
    """
    获取用户 workspace 路径（自动创建）

    流程：
    1. 验证 user_key 格式
    2. 构建安全路径
    3. 路径遍历检查
    4. 自动创建目录结构
    5. 初始化默认配置
    """
    # 验证格式
    channel, user_id = self._parse_user_key(user_key)

    # 构建路径
    safe_user_key = f"{channel}_{user_id}"
    workspace = self.base_workspace / safe_user_key

    # 安全检查
    workspace = workspace.resolve()
    if not workspace.is_relative_to(self.base_workspace.resolve()):
        raise ValueError(f"Workspace escape detected: {user_key}")

    # 自动创建
    if not workspace.exists():
        self._create_workspace_structure(workspace)

    return workspace
```

---

## 扩展指南

### 集成 PageIndex

#### 1. User Key 设计

```python
# PageIndex 用户
PAGEINDEX_USER_KEY = f"pageindex:{pageindex_user_id}"

# 示例
"pageindex:user_12345"
"pageindex:org_67890:user_abc"
```

#### 2. Workspace 配置

```python
# PageIndex 专用 workspace 路径
manager = MultiTenantManager(
    base_workspace=Path("/var/fastreact/tenants"),
    channel="pageindex"  # ← 指定 channel
)

# 生成的路径
/var/fastreact/tenants/pageindex/
├── pageindex_user_12345/
└── pageindex_org_67890_user_abc/
```

#### 3. 集成示例

```python
# PageIndex → FastReAct
from fastreact import Agent

agent = Agent(config=config, multitenant=True)

async def handle_pageindex_request(request):
    # 从 PageIndex 请求中提取 user_id
    pageindex_user_id = request.headers.get("X-PageIndex-User-Id")

    # 构建 user_key
    user_key = f"pageindex:{pageindex_user_id}"

    # 调用 FastReAct
    async for event in agent.run_or_inject(
        query=request.json["query"],
        user_key=user_key,
    ):
        # 返回事件到 PageIndex
        await send_to_pageindex(event)
```

### 集成 OpenViking

#### 1. User Key 设计

```python
# OpenViking 用户（支持多级组织）
OPENVIKING_USER_KEY = f"openviking:{org_id}:{user_id}"

# 示例
"openviking:org_67890:user_abc"
"openviking:org_12345:team_xyz:user_def"
```

#### 2. Workspace 配置

```python
# OpenViking 专用 workspace
manager = MultiTenantManager(
    base_workspace=Path("/var/fastreact/tenants"),
    channel="openviking"
)

# 生成的路径
/var/fastreact/tenants/openviking/
├── openviking_org_67890_user_abc/
└── openviking_org_12345_team_xyz_user_def/
```

#### 3. 集成示例

```python
# OpenViking → FastReAct
from fastreact import Agent

agent = Agent(config=config, multitenant=True)

async def handle_openviking_request(request):
    # 从 OpenViking 请求中提取信息
    org_id = request.json["organization_id"]
    user_id = request.json["user_id"]

    # 构建 user_key（多级）
    user_key = f"openviking:{org_id}:{user_id}"

    # 调用 FastReAct
    async for event in agent.run_or_inject(
        query=request.json["query"],
        user_key=user_key,
    ):
        # 返回事件到 OpenViking
        await send_to_openviking(event)
```

### 通用集成模式

#### 步骤 1: 定义 User Key 格式

```python
# 你的系统
YOUR_SYSTEM_USER_KEY = f"{YOUR_SYSTEM_CHANNEL}:{user_id}"

# 示例
"mysystem:user_123"
```

#### 步骤 2: 初始化 Agent

```python
from fastreact import Agent, Config

config = Config.load()
agent = Agent(
    config=config,
    multitenant=True,  # ← 启用多租户
    base_workspace=Path("/var/fastreact/tenants"),
)
```

#### 步骤 3: 请求处理

```python
async def handle_request(request):
    # 1. 从你的系统提取 user_id
    user_id = extract_user_id_from_request(request)

    # 2. 构建 user_key
    user_key = f"mysystem:{user_id}"

    # 3. 调用 FastReAct
    async for event in agent.run_or_inject(
        query=request.query,
        user_key=user_key,
    ):
        # 4. 处理事件
        await send_event_to_client(event)
```

#### 步骤 4: 可选 - 自定义 Workspace

```python
from fastreact.core.multitenant import MultiTenantManager

# 创建专用管理器
manager = MultiTenantManager(
    base_workspace=Path("/var/fastreact/tenants"),
    channel="mysystem"  # 你的系统名称
)

# 手动管理 workspace
workspace = manager.get_user_workspace(user_key)
```

---

## 最佳实践

### 1. User Key 管理

**DO ✅**:
```python
# 使用有意义的 channel
user_key = f"web:{user_email}"

# 使用平台原生 user_id
user_key = f"feishu:{feishu_open_id}"

# 多级组织（如果有）
user_key = f"openviking:{org_id}:{user_id}"
```

**DON'T ❌**:
```python
# 不要使用纯数字
user_key = "12345"  # 容易冲突

# 不要使用特殊字符
user_key = "web:../etc/passwd"  # 安全风险

# 不要硬编码
user_key = "web:admin"  # 所有用户共享
```

### 2. Workspace 路径

**DO ✅**:
```python
# 使用标准路径
/var/fastreact/tenants/{channel}/{user_key}/

# 按环境分离
/dev/fastreact/tenants/
/prod/fastreact/tenants/
```

**DON'T ❌**:
```python
# 不要放在用户目录
~/fastreact/workspaces/  # 难以管理

# 不要使用相对路径
./workspaces/  # 可能导致混乱
```

### 3. 会话管理

**DO ✅**:
```python
# 复用会话（同一用户）
async for event in agent.run_or_inject(
    query="第二个问题",
    user_key="web:user@example.com",  # ← 相同 user_key
):
    # 自动关联到上一个会话（30 秒内）
    pass
```

**DON'T ❌**:
```python
# 不要每次都创建新会话
force_new=True  # 浪费资源

# 不要共享 user_key
user_key = "web:shared"  # 数据混淆
```

### 4. 错误处理

**DO ✅**:
```python
# 验证 user_key
is_valid, error = validate_user_key(user_key)
if not is_valid:
    return {"error": error}

# 捕获路径异常
try:
    workspace = manager.get_user_workspace(user_key)
except ValueError as e:
    return {"error": str(e)}
```

**DON'T ❌**:
```python
# 不要忽略错误
workspace = manager.get_user_workspace(user_key)  # 可能抛异常

# 不要信任用户输入
user_key = user_input  # 未验证
```

### 5. 性能优化

**DO ✅**:
```python
# 缓存会话
session = agent.get_or_create_session(user_key)

# 批量操作
for query in queries:
    async for event in agent.run_or_inject(query, user_key):
        await process_event(event)
```

**DON'T ❌**:
```python
# 不要频繁创建会话
for query in queries:
    agent.create_session(user_key)  # 每次都创建

# 不要阻塞主线程
sync_operation()  # 使用 async
```

---

## 监控与调试

### 查看用户 Workspace

```bash
# 列出所有 gateway 用户
ls /var/fastreact/tenants/gateway/

# 查看特定用户的文件
ls /var/fastreact/tenants/gateway/web_user@example.com/files/

# 查看用户配置
cat /var/fastreact/tenants/gateway/web_user@example.com/config.json
```

### 日志调试

```python
import logging

# 启用多租户日志
logging.getLogger("fastreact.multitenant").setLevel(logging.DEBUG)

# 查看日志
tail -f /var/log/fastreact/multitenant.log
```

### 性能监控

```python
# 统计活跃用户
active_users = len(agent._sessions)

# 统计 workspace 数量
import os
workspace_count = len(os.listdir("/var/fastreact/tenants/gateway/"))

# 磁盘使用
du -sh /var/fastreact/tenants/
```

---

## 常见问题

### Q1: 如何迁移现有用户到多租户？

```bash
#!/bin/bash
# 迁移脚本

# 旧路径
OLD_WORKSPACE="./workspaces/default"

# 新路径
NEW_BASE="/var/fastreact/tenants/gateway"

# 获取用户列表（假设有用户映射文件）
cat users_mapping.txt | while read old_id new_user_key; do
    # 创建新 workspace
    NEW_WORKSPACE="$NEW_BASE/${new_user_key//:/_}"

    # 复制数据
    cp -r "$OLD_WORKSPACE" "$NEW_WORKSPACE"

    # 更新权限
    chown -R fastreact:fastreact "$NEW_WORKSPACE"
done
```

### Q2: 如何备份用户数据？

```bash
# 备份脚本
#!/bin/bash

BACKUP_DIR="/backup/fastreact/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# 备份所有用户 workspace
tar -czf "$BACKUP_DIR/tenants.tar.gz" /var/fastreact/tenants/

# 备份元数据
cp -r /var/fastreact/meta "$BACKUP_DIR/"

echo "Backup completed: $BACKUP_DIR"
```

### Q3: 如何清理不活跃用户？

```python
import os
import time
from pathlib import Path

def cleanup_inactive_users(base_path: Path, days: int = 30):
    """清理 N 天未活跃的用户"""
    now = time.time()
    cutoff = now - (days * 86400)

    for user_workspace in base_path.iterdir():
        if not user_workspace.is_dir():
            continue

        # 检查最后修改时间
        mtime = user_workspace.stat().st_mtime

        if mtime < cutoff:
            print(f"Removing inactive user: {user_workspace.name}")
            shutil.rmtree(user_workspace)

# 使用
cleanup_inactive_users(Path("/var/fastreact/tenants/gateway"), days=90)
```

---

## 总结

### 核心要点

1. **User Key**: `{channel}:{user_id}` 唯一标识用户
2. **Workspace**: 自动创建，完全隔离
3. **安全机制**: 路径验证、字符白名单、遍历防护
4. **API 统一**: `run_or_inject(user_key=...)`
5. **扩展简单**: 只需定义 channel 和 user_id

### 集成检查清单

集成 PageIndex/OpenViking 时：

- [ ] 定义 User Key 格式
- [ ] 初始化 Agent（multitenant=True）
- [ ] 请求处理中提取 user_id
- [ ] 调用 `run_or_inject(user_key=...)`
- [ ] 测试数据隔离
- [ ] 配置备份策略
- [ ] 设置资源配额
- [ ] 启用审计日志

### 参考资源

**代码**:
- `src/fastreact/agent.py` - Agent 多租户初始化
- `src/fastreact/core/multitenant.py` - Workspace 管理
- `src/fastreact/core/session.py` - 会话管理

**文档**:
- `docs/MULTITENANT_GUIDE.md` - 多租户部署指南
- `docs_archive/MULTITENANT_IMPLEMENTATION_SUMMARY.md` - 实施总结

**测试**:
- `tests/unit/test_multitenant.py` - 单元测试
- `tests/unit/test_gateway_multitenant.py` - Gateway 集成测试
- `tests/unit/test_multitenant_security.py` - 安全测试

---

**文档作者**: FastReAct Team
**创建日期**: 2025-03-04
**版本**: v2.5.0
**状态**: 生产就绪
