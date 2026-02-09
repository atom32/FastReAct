# FastReAct Nano 设计文档 v2.0

**版本**: 2.0.0
**日期**: 2026-02-10
**定位**: 轻量级高级 ReAct 智能体核心

---

## 一、设计哲学

### 1.1 核心理念

> **"Less is More" - Nanobot 的简洁 + Moltbot 的强大**

**原则**:
1. **极简工具**: 按 Pi 哲学，只保留核心工具
2. **双层循环**: 支持 Moltbot 的转向/后续消息
3. **异步优先**: 全栈 asyncio，高性能
4. **智能体核心**: 作为基础设施，不绑定具体应用

### 1.2 参考框架分析

| 特性 | Nanobot | Moltbot | Pi | FR Nano 目标 |
|------|---------|---------|-----|--------------|
| **代码量** | 15k | 82k | - | <3k |
| **循环模式** | 单层 ReAct | 双层循环 | - | 双层循环 |
| **转向消息** | 无 | 有 | 有 | 有 |
| **后续消息** | 无 | 有 | 有 | 有 |
| **工具数量** | 适中 | 少 | 极少 (4) | 极少 (4-5) |
| **工具哲学** | 专用工具 | 专用工具 | Bash 优先 | Bash 优先 |
| **干预能力** | 无 | 实时转向 | 实时 | 实时 |

---

## 二、架构设计

### 2.1 双层循环架构（Moltbot 模式）

```python
class ReActCore:
    """
    高级 ReAct 核心引擎

    特性：
    - 双层循环（内层处理工具，外层处理后续任务）
    - 转向消息（实时干预）
    - 后续消息（异步任务）
    - 流式输出
    """

    async def run(self, context: Context) -> str:
        """
        主执行循环

        外层循环：处理后续消息队列
        内层循环：处理工具调用和转向消息
        """
        pending_messages: list[Message] = []
        followup_queue: asyncio.Queue = asyncio.Queue()

        # === 外层循环 ===
        while True:
            has_more_tool_calls = True
            steering_after_tools = None

            # === 内层循环 ===
            while has_more_tool_calls or pending_messages:
                # 1. 处理待处理消息
                if pending_messages:
                    for msg in pending_messages:
                        context.add_message(msg)
                    pending_messages = []

                # 2. 调用 LLM
                response = await self._call_llm(context)

                # 3. 检查工具调用
                has_more_tool_calls = response.has_tool_calls()

                # 4. 执行工具
                if has_more_tool_calls:
                    results = await self._execute_tools(response.tool_calls)
                    for result in results:
                        context.add_message(result)

                # 5. 检查转向消息（实时干预）
                steering = await self._get_steering_messages()
                if steering:
                    pending_messages.extend(steering)
                    # 可选：重置工具调用标志
                    has_more_tool_calls = True

            # 6. 检查后续消息队列
            followup = await self._get_followup_messages()
            if followup:
                pending_messages = followup
                continue  # 继续外层循环

            break  # 完成处理

        return response.content
```

### 2.2 消息类型扩展

```python
@dataclass
class Message:
    """统一消息类型"""
    role: str  # "user", "assistant", "tool", "steering", "followup"
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def user(cls, content: str) -> "Message":
        return cls(role="user", content=content)

    @classmethod
    def assistant(cls, content: str) -> "Message":
        return cls(role="assistant", content=content)

    @classmethod
    def tool(cls, name: str, result: str, call_id: str) -> "Message":
        return cls(
            role="tool",
            content=result,
            tool_name=name,
            tool_call_id=call_id,
        )

    @classmethod
    def steering(cls, content: str) -> "Message":
        """转向消息：实时干预"""
        return cls(role="steering", content=content)

    @classmethod
    def followup(cls, content: str) -> "Message":
        """后续消息：异步任务完成后"""
        return cls(role="followup", content=content)
```

---

## 三、工具系统设计（Pi 哲学）

### 3.1 核心工具集

```python
# 核心工具：只有 4 个（参考 Pi）
CORE_TOOLS = {
    "read_file": ReadFileTool,
    "write_file": WriteFileTool,
    "exec": ExecTool,      # Bash/Shell 执行
    "edit_file": EditFileTool,
}

# 只读工具：用于探索阶段
READONLY_TOOLS = {
    "read_file": ReadFileTool,
    "search": SearchTool,    # 搜索文件内容
    "list_dir": ListDirTool,  # 列出目录
    "grep": GrepTool,        # 搜索文件
}

# 动态工具：根据需要启用
OPTIONAL_TOOLS = {
    "web_search": WebSearchTool,
    "web_fetch": WebFetchTool,
    "datetime": DateTimeTool,
}
```

### 3.2 Pi 哲学：不要为每个功能写新工具

**错误示例**（过度设计）:
```python
class SendEmailTool(Tool):
    """发送邮件"""
    # 每个功能都写一个工具

class CalculateDiscountTool(Tool):
    """计算折扣"""

class FormatJSONTool(Tool):
    """格式化 JSON"""
```

**正确示例**（Pi 哲学）:
```python
# 只有 Bash 工具
class ExecTool(Tool):
    """执行 Bash 命令"""
    async def execute(self, command: str) -> str:
        return await subprocess.run(command, shell=True)

# AI 自己写脚本发送邮件
# User: "发送邮件给 foo@example.com"
# AI: 调用 ExecTool("mail -s 'Subject' foo@example.com < body.txt")

# AI 自己写脚本计算
# User: "计算 8.5 折后价格"
# AI: 调用 ExecTool("python -c 'print(8.5 * 0.9)'")
```

### 3.3 工具实现

```python
class ReadFileTool(Tool):
    """读取文件"""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read file contents. Args: path (str)"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path to read",
                },
            },
            "required": ["path"],
        }

    async def execute(self, path: str) -> str:
        from pathlib import Path

        file_path = Path(path)
        if not file_path.exists():
            return f"[ERROR] File not found: {path}"

        # 限制读取大小
        MAX_SIZE = 10_000  # 10KB
        content = file_path.read_text(encoding="utf-8")

        if len(content) > MAX_SIZE:
            content = content[:MAX_SIZE] + "\n... (truncated)"

        return content


class ExecTool(Tool):
    """执行命令（Pi 哲学的核心）"""

    def __init__(self, timeout: int = 30, workspace: Optional[Path] = None):
        self._timeout = timeout
        self._workspace = workspace or Path.cwd()

    @property
    def name(self) -> str:
        return "exec"

    @property
    def description(self) -> str:
        return "Execute shell command. Use for complex operations, calculations, web requests, etc."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute",
                },
            },
            "required": ["command"],
        }

    async def execute(self, command: str) -> str:
        import subprocess
        import asyncio

        # 安全检查
        dangerous = ["rm -rf ", "format ", "mkfs", "dd if="]
        if any(d in command for d in dangerous):
            return f"[ERROR] Dangerous command blocked"

        try:
            # 在工作目录中执行
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=self._workspace,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self._timeout,
            )

            if proc.returncode != 0:
                return f"[ERROR] Command failed (code {proc.returncode}): {stderr}"

            return stdout or stderr or "[OK] Command executed"

        except asyncio.TimeoutError:
            return f"[ERROR] Command timeout after {self._timeout}s"


class WriteFileTool(Tool):
    """写入文件"""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to file. Args: path (str), content (str)"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        }

    async def execute(self, path: str, content: str) -> str:
        from pathlib import Path

        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 安全检查：不覆盖系统关键路径
        protected = ["/bin", "/sbin", "/usr/bin", "/etc"]
        if any(str(file_path).startswith(p) for p in protected):
            return f"[ERROR] Protected path: {path}"

        file_path.write_text(content, encoding="utf-8")
        return f"[OK] Wrote {len(content)} bytes to {path}"


class EditFileTool(Tool):
    """编辑文件（基于 Nanobot）"""

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return "Edit file by replacing text. Args: path, old_text, new_text"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["path", "old_text", "new_text"],
        }

    async def execute(self, path: str, old_text: str, new_text: str) -> str:
        from pathlib import Path

        file_path = Path(path)
        if not file_path.exists():
            return f"[ERROR] File not found: {path}"

        content = file_path.read_text(encoding="utf-8")

        if old_text not in content:
            return f"[ERROR] Old text not found in file"

        new_content = content.replace(old_text, new_text, 1)
        file_path.write_text(new_content, encoding="utf-8")

        return f"[OK] Edited {path}"
```

---

## 四、高级 ReAct 特性

### 4.1 转向消息（实时干预）

```python
class SteeringCallback:
    """转向消息回调：允许外部干预

    用途：
    - 用户实时纠错
    - 管理员介入
    - 测试和调试
    """

    async def __call__(self) -> Optional[list[Message]]:
        """
        获取转向消息

        Returns:
            消息列表或 None
        """
        # 从文件读取
        steering_file = self._workspace / ".steering.jsonl"
        if not steering_file.exists():
            return None

        messages = []
        async with aiofiles.open(steering_file, "r") as f:
            async for line in f:
                if line.strip():
                    msg = json.loads(line)
                    messages.append(Message(**msg))

        # 清空文件
        steering_file.unlink()

        return messages if messages else None


class ReActCore:
    def __init__(
        self,
        llm,
        tools,
        steering_callback: Optional[Callable] = None,
        followup_callback: Optional[Callable] = None,
    ):
        self._steering_callback = steering_callback
        self._followup_callback = followup_callback

    async def _get_steering_messages(self) -> Optional[list[Message]]:
        """获取转向消息"""
        if self._steering_callback:
            return await self._steering_callback()
        return None
```

### 4.2 后续消息（异步任务）

```python
class FollowUpCallback:
    """后续消息回调：异步任务完成后继续

    用途：
    - 后台搜索完成
    - 定时任务触发
    - Webhook 回调
    """

    def __init__(self, queue: asyncio.Queue):
        self._queue = queue
        self._tasks: dict[str, asyncio.Task] = {}

    async def schedule_followup(
        self,
        delay: float,
        message: Message,
    ):
        """安排后续消息"""
        async def delayed():
            await asyncio.sleep(delay)
            await self._queue.put(message)

        task = asyncio.create_task(delayed())
        self._tasks[task.get_name()] = task


class ReActCore:
    async def _get_followup_messages(self) -> Optional[list[Message]]:
        """获取后续消息"""
        # 检查队列
        try:
            messages = []
            while not self._followup_queue.empty():
                msg = self._followup_queue.get_nowait()
                messages.append(msg)
            return messages if messages else None
        except asyncio.QueueEmpty:
            return None
```

### 4.3 流式输出

```python
class ReActCore:
    async def run_stream(
        self,
        context: Context,
        stream_callback: Callable[[str], Awaitable[None]],
    ) -> AsyncIterator[str]:
        """流式运行 ReAct 循环"""

        pending_messages = []

        while True:
            # 1. 处理待处理消息
            if pending_messages:
                for msg in pending_messages:
                    context.add_message(msg)
                pending_messages = []

            # 2. 调用 LLM（流式）
            response = await self._llm.chat_stream(
                context.messages,
                tools=self._tools.schemas(),
            )

            # 3. 流式输出
            content = ""
            async for chunk in response.content:
                content += chunk
                await stream_callback(chunk)

            # 4. 检查工具
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    result = await self._tools.execute(tool_call)
                    context.add_message(tool_call.to_message(result))
            else:
                # 5. 检查后续消息
                followup = await self._get_followup_messages()
                if followup:
                    pending_messages.extend(followup)
                    continue
                break

        yield content
```

---

## 五、配置和扩展

### 5.1 模式配置（Nanobot 风格）

```python
@dataclass
class ReActConfig:
    """ReAct 配置"""
    # 基础配置
    max_iterations: int = 20
    timeout: int = 60

    # 工具模式
    tool_mode: str = "core"  # "core", "readonly", "all"

    # 安全配置
    enable_exec: bool = True
    exec_timeout: int = 30
    restrict_to_workspace: bool = True
    workspace: Path = Path.cwd()

    # 干预配置
    enable_steering: bool = True
    steering_file: str = ".steering.jsonl"

    # 流式配置
    enable_streaming: bool = False

    # 后续任务配置
    enable_followup: bool = False


class ReActCore:
    @classmethod
    def create(cls, llm, config: ReactConfig) -> "ReActCore":
        """工厂方法：根据配置创建"""
        # 根据配置选择工具
        tools = cls._select_tools(config)

        # 创建回调
        callbacks = {}
        if config.enable_steering:
            callbacks['steering'] = SteeringCallback(config.workspace)
        if config.enable_followup:
            callbacks['followup'] = FollowUpCallback(asyncio.Queue())

        return cls(llm, tools, config, **callbacks)
```

### 5.2 插件系统（简化版）

```python
class SimplePluginManager:
    """简化插件管理器

    参考 Nanobot 的 skills 系统
    """

    def __init__(self, skills_dir: Path):
        self._skills_dir = skills_dir
        self._skills: dict[str, Skill] = {}

    async def load_all(self):
        """加载所有技能（Markdown 文件）"""
        for skill_file in self._skills_dir.glob("**/*.md"):
            skill = await self._parse_skill(skill_file)
            self._skills[skill.name] = skill

    async def _parse_skill(self, path: Path) -> Skill:
        """解析技能文件"""
        content = path.read_text(encoding="utf-8")

        # 解析 frontmatter
        frontmatter, body = split_frontmatter(content)
        metadata = yaml.safe_load(frontmatter)

        return Skill(
            name=metadata['name'],
            description=metadata['description'],
            content=body,
            metadata=metadata.get('metadata', {}),
        )

    def build_prompt(self) -> str:
        """构建技能提示词"""
        parts = []
        for skill in self._skills.values():
            if skill.metadata.get('always_load', False):
                parts.append(f"## {skill.name}\n\n{skill.content}")

        # 可用技能列表
        available = [s for s in self._skills.values()
                     if not s.metadata.get('always_load', False)]
        if available:
            parts.append(f"\nAvailable skills: {', '.join(s.name for s in available)}")

        return "\n\n".join(parts)
```

---

## 六、实现路线图

### Phase 1: 双层循环（2-3 小时）

**目标**: 实现 Moltbot 风格的双层循环

- [ ] 重构 ReActCore 为双层循环
- [ ] 添加转向消息支持
- [ ] 添加后续消息支持
- [ ] 更新消息类型
- [ ] 单元测试

### Phase 2: 极简工具集（2-3 小时）

**目标**: 实现 Pi 哲学的 4 个核心工具

- [ ] ReadFileTool
- [ ] WriteFileTool
- [ ] ExecTool（Bash）
- [ ] EditFileTool
- [ ] 工具安全检查
- [ ] 工具测试

### Phase 3: 高级特性（3-4 小时）

**目标**: 添加企业级特性

- [ ] 流式输出
- [ ] 转向消息回调
- [ ] 后续消息队列
- [ ] 配置管理
- [ ] 简化插件系统

### Phase 4: 测试与文档（2-3 小时）

**目标**: 验证和文档

- [ ] 单元测试（>80% 覆盖）
- [ ] 集成测试
- [ ] 使用文档
- [ ] API 文档

---

## 七、与现有框架对比

### 7.1 代码量对比（预期）

| 框架 | 行数 | 功能 |
|------|------|------|
| Nanobot | 15,000 | 轻量级 |
| **FastReAct Nano** | **~3,500** | **轻量 + 高级** |
| FastReAct v1 | 101,584 | 企业级 |
| Moltbot | 82,168 | 企业级 |

**目标**: 用 Nanobot 的代码量，实现接近 Moltbot 的功能

### 7.2 功能对比（预期完成）

| 功能 | Nanobot | FR Nano | Moltbot |
|------|---------|---------|---------|
| ReAct 循环 | 单层 | **双层** | 双层 |
| 转向消息 | 无 | **有** | 有 |
| 后续消息 | 无 | **有** | 有 |
| 工具数量 | 适中 | **极简(4)** | 少 |
| Bash 工具 | 有 | **有** | 无 |
| 流式输出 | 有 | **有** | 有 |
| 插件系统 | 有 | **简化** | 有 |

---

## 八、设计原则总结

1. **简洁优先**: <3,500 行代码
2. **双层循环**: 支持 Moltbot 高级特性
3. **极简工具**: 只保留 4-5 个核心工具
4. **Bash 优先**: 按 Pi 哲学，用 Bash 替代专用工具
5. **异步优先**: 全栈 asyncio
6. **智能体核心**: 作为基础设施，易于扩展

---

**最后更新**: 2026-02-10
**版本**: 2.0.0-alpha
**状态**: 设计阶段
