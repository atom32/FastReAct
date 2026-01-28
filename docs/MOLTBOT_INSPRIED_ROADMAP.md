# FastReAct 改进路线图（参考 Moltbot）

> **基于 Moltbot v2026.1.24 架构** - 从基础框架到生产级 AI 助手

---

## 📊 当前状态对比

### 已完成 ✅

| 特性 | Moltbot | FastReAct | 状态 |
|------|---------|-----------|------|
| WebSocket Gateway | ✅ | ✅ | **已完成** |
| 会话管理 | ✅ | ✅ | **已完成** |
| 实时进度追踪 | ✅ | ✅ | **已完成** |
| Function Calling API | ✅ | ✅ | **已完成** |
| 错误处理和重试 | ✅ | ✅ | **已完成** |
| 请求去重 | - | ✅ | **FastReAct 独有** |

### 待实现 ⏳

| 特性 | Moltbot | FastReAct | 优先级 |
|------|---------|-----------|--------|
| 持久化会话存储 | ✅ SQLite/Redis | ⚠️ 仅内存 | **P0** |
| 多智能体支持 | ✅ | ❌ | **P0** |
| Agent-to-Agent 通信 | ✅ sessions_* | ❌ | **P0** |
| 多通道支持 | ✅ 50+ | ⚠️ 仅 WebChat | P1 |
| 沙箱隔离 | ✅ Docker | ❌ | P1 |
| Canvas/A2UI | ✅ | ❌ | P2 |
| Cron + Webhooks | ✅ | ❌ | P2 |
| Companion Apps | ✅ macOS/iOS/Android | ❌ | P3 |

---

## 🎯 改进路线图

### Phase 1: 持久化和多智能体（2-3周）⭐⭐⭐

#### 目标
实现数据持久化和多智能体协作能力。

#### Week 1: 会话持久化

**1.1 存储层设计**

```python
# src/fastreact/storage/base.py

from abc import ABC, abstractmethod
from typing import Optional, Dict, List
from datetime import datetime

class SessionStorage(ABC):
    """会话存储抽象基类"""

    @abstractmethod
    async def save_session(self, session_id: str, data: Dict) -> None:
        """保存会话数据"""
        pass

    @abstractmethod
    async def load_session(self, session_id: str) -> Optional[Dict]:
        """加载会话数据"""
        pass

    @abstractmethod
    async def list_sessions(self, user_id: str = None) -> List[Dict]:
        """列出会话"""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """删除会话"""
        pass

# src/fastreact/storage/sqlite.py

import aiosqlite
import json

class SQLiteSessionStorage(SessionStorage):
    """SQLite 会话存储"""

    def __init__(self, db_path: str = "./data/sessions.db"):
        self.db_path = db_path

    async def initialize(self):
        """初始化数据库表"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    title TEXT,
                    messages TEXT,  -- JSON 格式
                    metadata TEXT,  -- JSON 格式
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id
                ON sessions(user_id)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_active
                ON sessions(last_active)
            """)
            await db.commit()

    async def save_session(self, session_id: str, data: Dict) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO sessions
                (session_id, user_id, title, messages, metadata, updated_at, last_active)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                session_id,
                data.get("user_id"),
                data.get("title"),
                json.dumps(data.get("messages", [])),
                json.dumps(data.get("metadata", {}))
            ))
            await db.commit()

    async def load_session(self, session_id: str) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "session_id": row[0],
                        "user_id": row[1],
                        "title": row[2],
                        "messages": json.loads(row[3]),
                        "metadata": json.loads(row[4]),
                        "created_at": row[5],
                        "updated_at": row[6],
                        "last_active": row[7]
                    }
                return None

    async def list_sessions(self, user_id: str = None, limit: int = 50) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            if user_id:
                async with db.execute("""
                    SELECT * FROM sessions
                    WHERE user_id = ?
                    ORDER BY last_active DESC
                    LIMIT ?
                """, (user_id, limit)) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute("""
                    SELECT * FROM sessions
                    ORDER BY last_active DESC
                    LIMIT ?
                """, (limit,)) as cursor:
                    rows = await cursor.fetchall()

            return [
                {
                    "session_id": row[0],
                    "user_id": row[1],
                    "title": row[2],
                    "created_at": row[5],
                    "last_active": row[7]
                }
                for row in rows
            ]

    async def delete_session(self, session_id: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            await db.commit()
```

**1.2 集成到 Gateway**

```python
# src/fastreact/gateway/server.py

from ..storage.sqlite import SQLiteSessionStorage

class GatewayServer:
    def __init__(
        self,
        agent: FastReAct,
        storage: SessionStorage = None,
        storage_path: str = "./data/sessions.db"
    ):
        self.agent = agent
        self.storage = storage or SQLiteSessionStorage(storage_path)
        self.sessions: Dict[str, Dict] = {}  # 内存缓存

    async def startup(self):
        """启动时初始化存储"""
        await self.storage.initialize()
        # 加载活跃会话（可选）
        logger.info("Gateway started with persistent storage")

    async def websocket_endpoint(self, websocket: WebSocket, session_id: str):
        await websocket.accept()

        # 尝试从存储加载会话
        stored_session = await self.storage.load_session(session_id)
        if stored_session:
            self.sessions[session_id] = stored_session
            # 发送历史消息
            for msg in stored_session.get("messages", []):
                await websocket.send_json({
                    "type": "history",
                    "message": msg
                })
        else:
            # 创建新会话
            self.sessions[session_id] = {
                "session_id": session_id,
                "messages": [],
                "created_at": datetime.now()
            }

        try:
            while True:
                data = await websocket.receive_json()
                response = await self.handle_message(session_id, data)

                # 保存到存储
                await self.storage.save_session(session_id, self.sessions[session_id])

                await websocket.send_json(response)
        finally:
            # 最后保存一次
            await self.storage.save_session(session_id, self.sessions[session_id])
```

#### Week 2-3: 多智能体系统

**2.1 智能体基类**

```python
# src/fastreact/agents/base.py

from typing import List, Dict, Optional, Callable
from ..core.engine import FastReAct
from ..core.tool import Tool

class Agent:
    """智能体基类"""

    def __init__(
        self,
        name: str,
        role: str,
        description: str,
        tools: List[Tool] = None,
        system_prompt: str = None,
        model: str = None
    ):
        self.name = name
        self.role = role
        self.description = description
        self.tools = tools or []
        self.system_prompt = system_prompt
        self.model = model

    async def execute(self, task: str, context: Dict = None) -> Dict:
        """执行任务"""
        raise NotImplementedError

# src/fastreact/agents/specialized.py

class ResearchAgent(Agent):
    """研究智能体 - 信息收集和分析"""

    def __init__(self):
        super().__init__(
            name="researcher",
            role="研究专家",
            description="擅长信息收集、搜索和数据分析",
            tools=[SearchTool(), CalculatorTool()]
        )
        self.system_prompt = """
        你是一个研究专家，擅长：
        - 信息搜索和收集
        - 数据分析和总结
        - 事实核查

        工作流程：
        1. 理解研究目标
        2. 搜索相关信息
        3. 分析和总结
        4. 提供结构化报告
        """

class CodeAgent(Agent):
    """代码智能体 - 编程和调试"""

    def __init__(self):
        super().__init__(
            name="coder",
            role="编程专家",
            description="擅长编程、调试和代码审查",
            tools=[CalculatorTool(), RunPythonCodeTool()]
        )
        self.system_prompt = """
        你是一个编程专家，擅长：
        - 编写和调试代码
        - 代码审查和优化
        - 技术问题解决

        工作流程：
        1. 理解需求
        2. 设计解决方案
        3. 编写/修改代码
        4. 测试和验证
        """

class CreativeAgent(Agent):
    """创意智能体 - 内容生成"""

    def __init__(self):
        super().__init__(
            name="creator",
            role="创意专家",
            description="擅长内容创作和创意设计"
        )
        self.system_prompt = """
        你是一个创意专家，擅长：
        - 文案创作
        - 创意设计
        - 内容策划

        工作流程：
        1. 理解目标受众
        2. 构思创意方向
        3. 生成内容草稿
        4. 优化和润色
        """

class ManagerAgent(Agent):
    """管理智能体 - 任务协调"""

    def __init__(self):
        super().__init__(
            name="manager",
            role="项目经理",
            description="负责任务分配和协调"
        )
        self.system_prompt = """
        你是一个项目经理，负责：
        - 任务分解
        - 智能体调度
        - 进度跟踪
        - 结果汇总

        工作流程：
        1. 分析任务需求
        2. 选择合适的智能体
        3. 分配子任务
        4. 汇总结果
        """
```

**2.2 智能体路由器**

```python
# src/fastreact/agents/router.py

from typing import Dict, List
from .base import Agent

class AgentRouter:
    """智能体路由器"""

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.session_agent_map: Dict[str, str] = {}  # session_id -> agent_name

    def register_agent(self, agent: Agent) -> None:
        """注册智能体"""
        self.agents[agent.name] = agent

    def route(
        self,
        task: str,
        session_id: str = None,
        force_agent: str = None
    ) -> Agent:
        """路由到合适的智能体"""

        # 强制指定智能体
        if force_agent and force_agent in self.agents:
            return self.agents[force_agent]

        # 使用会话绑定的智能体
        if session_id and session_id in self.session_agent_map:
            agent_name = self.session_agent_map[session_id]
            if agent_name in self.agents:
                return self.agents[agent_name]

        # 基于任务类型自动路由
        task_lower = task.lower()

        # 关键词匹配
        if any(kw in task_lower for kw in ["代码", "编程", "debug", "函数", "api"]):
            return self.agents.get("coder", self.agents.get("default"))

        if any(kw in task_lower for kw in ["搜索", "研究", "分析", "数据", "报告"]):
            return self.agents.get("researcher", self.agents.get("default"))

        if any(kw in task_lower for kw in ["写", "创作", "文案", "内容", "设计"]):
            return self.agents.get("creator", self.agents.get("default"))

        # 默认智能体
        return self.agents.get("default")

    def bind_session_agent(self, session_id: str, agent_name: str) -> None:
        """绑定会话到特定智能体"""
        self.session_agent_map[session_id] = agent_name

    def unbind_session(self, session_id: str) -> None:
        """解绑会话"""
        if session_id in self.session_agent_map:
            del self.session_agent_map[session_id]
```

**2.3 Agent-to-Agent 通信工具**

```python
# src/fastreact/agents/communication.py

from ..core.tool import Tool

class SessionsListTool(Tool):
    """列出活跃的智能体会话"""

    def __init__(self, router: AgentRouter):
        self.router = router
        super().__init__()

    def _get_description(self):
        return "列出所有活跃的智能体会话"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": False
        }

    async def execute_async(self) -> str:
        sessions = {}
        for agent_name, agent in self.router.agents.items():
            sessions[agent_name] = {
                "name": agent.name,
                "role": agent.role,
                "description": agent.description
            }
        return json.dumps({
            "sessions": sessions,
            "count": len(sessions)
        }, ensure_ascii=False, indent=2)

class SessionsSendTool(Tool):
    """向其他智能体发送消息"""

    def __init__(self, router: AgentRouter, gateway):
        self.router = router
        self.gateway = gateway
        super().__init__()

    def _get_description(self):
        return "向另一个智能体发送消息并获取回复"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "description": "目标智能体名称（如: researcher, coder, creator）"
                },
                "message": {
                    "type": "string",
                    "description": "要发送的消息"
                },
                "reply_back": {
                    "type": "boolean",
                    "description": "是否需要回复",
                    "default": True
                }
            },
            "required": ["agent", "message"]
        }

    async def execute_async(
        self,
        agent: str,
        message: str,
        reply_back: bool = True
    ) -> str:
        # 获取目标智能体
        target_agent = self.router.agents.get(agent)
        if not target_agent:
            return f"错误：找不到智能体 '{agent}'"

        # 执行任务
        try:
            result = await target_agent.execute(message)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"错误：{str(e)}"

class SessionsHistoryTool(Tool):
    """获取会话历史"""

    def __init__(self, gateway):
        self.gateway = gateway
        super().__init__()

    def _get_description(self):
        return "获取指定会话的历史记录"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "会话ID"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回消息数量限制",
                    "default": 10
                }
            },
            "required": ["session_id"]
        }

    async def execute_async(self, session_id: str, limit: int = 10) -> str:
        session = self.gateway.sessions.get(session_id)
        if not session:
            return f"错误：找不到会话 '{session_id}'"

        messages = session.get("messages", [])[-limit:]
        return json.dumps({
            "session_id": session_id,
            "messages": messages,
            "count": len(messages)
        }, ensure_ascii=False, indent=2)
```

**2.4 集成到 Gateway**

```python
# src/fastreact/gateway/server.py

from ..agents.router import AgentRouter
from ..agents.specialized import (
    ResearchAgent, CodeAgent, CreativeAgent, ManagerAgent
)
from ..agents.communication import (
    SessionsListTool, SessionsSendTool, SessionsHistoryTool
)

class GatewayServer:
    def __init__(self, config: Dict):
        # 创建智能体路由器
        self.agent_router = AgentRouter()

        # 注册专用智能体
        self.agent_router.register_agent(ResearchAgent())
        self.agent_router.register_agent(CodeAgent())
        self.agent_router.register_agent(CreativeAgent())
        self.agent_router.register_agent(ManagerAgent())

        # 创建默认智能体（使用所有工具）
        default_agent = FastReAct(...)
        self.agent_router.register_agent(Agent(
            name="default",
            role="通用助手",
            description="处理各类任务",
            tools=all_tools
        ))

        # 添加智能体通信工具
        default_agent.register_tool(SessionsListTool(self.agent_router))
        default_agent.register_tool(SessionsSendTool(self.agent_router, self))
        default_agent.register_tool(SessionsHistoryTool(self))

    async def handle_message(self, session_id: str, data: Dict) -> Dict:
        query = data.get("query")
        agent_name = data.get("agent")  # 可选：指定智能体

        # 路由到合适的智能体
        agent = self.agent_router.route(query, session_id, agent_name)

        # 执行任务
        result = await agent.run_async(query)

        # 绑定会话到智能体（后续对话使用同一智能体）
        if agent_name:
            self.agent_router.bind_session_agent(session_id, agent_name)

        return {
            "type": "answer",
            "agent": agent.name,
            "answer": result["answer"],
            "stats": result["stats"]
        }
```

### Phase 2: 通道集成（1-2周）⭐⭐

#### 目标
添加主流消息平台支持，让用户可以在日常应用中使用 FastReAct。

#### Week 1: Telegram 集成

```python
# src/fastreact/channels/telegram.py

import asyncio
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

class TelegramChannel:
    """Telegram 通道"""

    def __init__(
        self,
        bot_token: str,
        gateway_url: str = "ws://localhost:8080"
    ):
        self.bot_token = bot_token
        self.gateway_url = gateway_url
        self.bot = Bot(token=bot_token)
        self.application = None

    async def start(self):
        """启动 Telegram bot"""
        self.application = Application.builder().token(self.bot_token).build()

        # 添加处理器
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("new", self.cmd_new))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

    async def cmd_start(self, update: Update, context):
        """/start 命令"""
        await update.message.reply_text(
            "👋 欢迎使用 FastReAct！\n\n"
            "我可以帮助你处理各种任务。\n"
            "命令列表：\n"
            "/start - 开始使用\n"
            "/status - 查看状态\n"
            "/new - 开始新对话\n\n"
            "直接发送消息即可开始对话！"
        )

    async def cmd_status(self, update: Update, context):
        """/status 命令"""
        user_id = update.effective_user.id
        # 从 Gateway 获取状态
        status = await self.get_session_status(user_id)
        await update.message.reply_text(f"📊 {status}")

    async def cmd_new(self, update: Update, context):
        """/new 命令"""
        user_id = update.effective_user.id
        session_id = f"telegram_{user_id}_{int(time.time())}"
        await update.message.reply_text(f"✅ 新对话已创建: {session_id}")

    async def handle_message(self, update: Update, context):
        """处理用户消息"""
        user_id = update.effective_user.id
        query = update.message.text

        # 发送到 Gateway
        response = await self.send_to_gateway(user_id, query)

        # 回复用户
        await update.message.reply_text(response)

    async def send_to_gateway(self, user_id: str, query: str) -> str:
        """发送消息到 Gateway"""
        # 实现 WebSocket 通信
        pass

# 启动脚本
# scripts/run_telegram_channel.py

import asyncio
from fastreact.channels.telegram import TelegramChannel

async def main():
    channel = TelegramChannel(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        gateway_url="ws://localhost:8080"
    )
    await channel.start()

    # 保持运行
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

#### Week 2: Slack/Discord 集成

类似 Telegram 的实现，创建 `SlackChannel` 和 `DiscordChannel`。

### Phase 3: 高级特性（2-3周）⭐

#### 3.1 沙箱隔离（Docker）

```python
# src/fastreact/sandbox/docker.py

import docker

class DockerSandbox:
    """Docker 沙箱"""

    def __init__(self):
        self.client = docker.from_env()

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30
    ) -> Dict:
        """在沙箱中执行代码"""

        # 选择镜像
        image_map = {
            "python": "python:3.11-slim",
            "javascript": "node:18-alpine",
            "bash": "bash:5.2"
        }
        image = image_map.get(language, "python:3.11-slim")

        # 运行容器
        container = self.client.containers.run(
            image,
            command=f"python -c '{code}'" if language == "python" else code,
            mem_limit="512m",
            cpu_period=100000,
            cpu_quota=50000,  # 0.5 CPU
            network_disabled=True,  # 禁用网络
            timeout=timeout,
            remove=True,
            stdout=True,
            stderr=True
        )

        return {
            "output": container.decode("utf-8"),
            "language": language
        }
```

#### 3.2 Cron + Webhooks

```python
# src/fastreact/scheduler/cron.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler

class CronScheduler:
    """定时任务调度器"""

    def __init__(self, gateway):
        self.scheduler = AsyncIOScheduler()
        self.gateway = gateway
        self.jobs = {}

    def start(self):
        """启动调度器"""
        self.scheduler.start()

    async def add_job(
        self,
        job_id: str,
        trigger: str,  # "interval", "cron", "date"
        **kwargs
    ):
        """添加定时任务"""

        async def job_func():
            # 执行任务
            await self.gateway.handle_message(
                job_id,
                {"query": kwargs.get("task")}
            )

        if trigger == "interval":
            self.scheduler.add_job(
                job_func,
                'interval',
                seconds=kwargs.get("seconds", 3600),
                id=job_id
            )
        elif trigger == "cron":
            self.scheduler.add_job(
                job_func,
                'cron',
                hour=kwargs.get("hour", 0),
                minute=kwargs.get("minute", 0),
                id=job_id
            )

        self.jobs[job_id] = kwargs

    def remove_job(self, job_id: str):
        """删除任务"""
        self.scheduler.remove_job(job_id)
        if job_id in self.jobs:
            del self.jobs[job_id]
```

#### 3.3 Webhook 支持

```python
# src/fastreact/gateway/webhooks.py

from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook/{webhook_id}")
async def webhook_endpoint(webhook_id: str, request: Request):
    """Webhook 端点"""
    data = await request.json()

    # 验证 webhook ID
    # ...

    # 处理事件
    # ...

    return {"status": "ok"}
```

---

## 📦 依赖更新

```txt
# requirements.txt 新增

# 持久化
aiosqlite>=0.19.0
redis>=5.0.0  # 可选：Redis 缓存

# 多智能体
pydantic>=2.0.0

# 通道集成
python-telegram-bot>=20.0
slack-sdk>=3.0
discord.py>=2.0

# 沙箱
docker>=6.0.0

# 调度
apscheduler>=3.10.0
```

---

## 🎯 优先级总结

| Phase | 功能 | 优先级 | 预计时间 | 价值 |
|-------|------|--------|----------|------|
| **1** | 持久化存储 | P0 | 1周 | 数据安全 |
| **1** | 多智能体系统 | P0 | 2周 | 协作能力 |
| **1** | Agent-to-Agent 通信 | P0 | 1周 | 协作效率 |
| **2** | Telegram 集成 | P1 | 1周 | 用户便利 |
| **2** | Slack/Discord 集成 | P1 | 1周 | 用户便利 |
| **3** | Docker 沙箱 | P1 | 1周 | 安全性 |
| **3** | Cron + Webhooks | P2 | 1周 | 自动化 |
| **4** | Canvas/A2UI | P2 | 2周 | 可视化 |
| **5** | Companion Apps | P3 | 4周+ | 移动端 |

---

## 🚀 快速启动（Phase 1）

```bash
# 1. 更新依赖
pip install -r requirements.txt

# 2. 初始化数据库
python -m fastreact.storage init

# 3. 启动 Gateway（带持久化）
python scripts/run_gateway.py --storage ./data/sessions.db

# 4. 测试多智能体
python scripts/test_multi_agent.py
```

---

## 📊 预期收益

完成 Phase 1 后：

- **数据持久化** ✅ - 重启不丢失数据
- **多智能体协作** ✅ - 复杂任务自动分工
- **Agent-to-Agent 通信** ✅ - 智能体间信息共享

完成 Phase 2 后：

- **多通道支持** ✅ - Telegram/Slack/Discord
- **用户体验** ✅ - 在日常应用中使用

完成 Phase 3 后：

- **安全性** ✅ - Docker 沙箱隔离
- **自动化** ✅ - 定时任务和 Webhook

---

**总结**: 参考 Moltbot 的架构，FastReAct 可以在 2-3 个月内达到生产级水平。
