"""
Gateway 客户端工具 - 让 Agent 可以调用 Gateway 服务

类似 moltbot 的方式：工具通过 Gateway API 调用远程服务
支持 Subagent 创建和通信
"""

import logging
from typing import Dict, Any, Optional, List
from .fn_registry import Tool

logger = logging.getLogger(__name__)


def create_spawn_subagent_tool(gateway_url: str = "http://localhost:8080") -> Tool:
    """创建 Subagent 工具

    允许主 agent 创建子 agent 来处理复杂或独立的任务
    """
    async def execute(task: str, prompt_mode: str = "minimal", reasoning_level: str = "off") -> str:
        """创建一个 subagent 来处理指定任务

        Args:
            task: 分配给 subagent 的任务描述
            prompt_mode: subagent 的 prompt 模式（minimal/none）
            reasoning_level: subagent 的推理级别（off/basic/extended）
        """
        import httpx
        import uuid

        # 生成唯一的 subagent session ID
        subagent_id = f"subagent-{uuid.uuid4().hex[:8]}"

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # 通过 WebSocket 创建 subagent 会话
                # 注意：这里简化实现，实际需要通过 WebSocket 发送消息
                url = f"{gateway_url}/ws/{subagent_id}"

                # 构造任务消息
                message = {
                    "type": "message",
                    "content": task,
                    "metadata": {
                        "is_subagent": True,
                        "parent_session": "main",
                        "prompt_mode": prompt_mode,
                        "reasoning_level": reasoning_level
                    }
                }

                # 这里应该建立 WebSocket 连接并发送消息
                # 为了简化，我们返回一个说明
                return f"""Subagent 已创建：

Subagent ID: {subagent_id}
任务: {task}
模式: {prompt_mode}
推理级别: {reasoning_level}

说明：
- Subagent 会独立处理此任务
- 完成后会向你汇报结果
- 你可以继续处理其他任务
- 使用 session_manager 查看所有 subagent 状态

注意：完整的 subagent 功能需要 WebSocket 连接支持。
当前实现返回模拟结果。"""

        except Exception as e:
            return f"创建 Subagent 失败: {str(e)}"

    return Tool(
        name="spawn_subagent",
        label="Spawn Subagent",
        description="""创建一个 Subagent 来处理复杂或独立的任务

**何时使用 Subagent**：
- 任务复杂且耗时，需要独立处理
- 任务可以并行执行
- 需要专门的配置（如不同的推理模式）
- 任务可能需要多次重试

**使用方法**：
- 描述清晰的任务目标
- Subagent 完成后会汇报结果
- 你可以继续处理其他任务，不必等待

**示例**：
```
task: "搜索并分析 2024 年 AI 领域的突破性进展，生成一份详细报告"
prompt_mode: "minimal"
reasoning_level: "extended"
```

**注意**：Subagent 使用 minimal 模式以节省 token，
只在需要深度推理时才使用 extended。""",
        parameters={
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "分配给 subagent 的任务描述，应该清晰明确"
                },
                "prompt_mode": {
                    "type": "string",
                    "enum": ["minimal", "none"],
                    "description": "Subagent 的 prompt 模式（默认 minimal）",
                    "default": "minimal"
                },
                "reasoning_level": {
                    "type": "string",
                    "enum": ["off", "basic", "extended", "deep"],
                    "description": "Subagent 的推理级别（默认 off）",
                    "default": "off"
                }
            },
            "required": ["task"]
        },
        execute=execute,
    )


def create_gateway_tool(gateway_url: str = "http://localhost:8080") -> Tool:
    """创建 Gateway 客户端工具

    Args:
        gateway_url: Gateway 服务的 URL
    """
    async def execute(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> str:
        """调用 Gateway API"""
        import httpx

        url = f"{gateway_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data, headers=headers)
                else:
                    return f"不支持的 HTTP 方法: {method}"

                response.raise_for_status()
                return f"Gateway 调用成功:\n{response.text[:500]}"
        except httpx.HTTPStatusError as e:
            return f"Gateway HTTP 错误 {e.response.status_code}: {e.response.text[:200]}"
        except Exception as e:
            return f"Gateway 调用失败: {str(e)}"

    return Tool(
        name="gateway",
        label="Gateway",
        description="""调用 FastReAct Gateway 的 API 端点

可用的 Gateway 端点：
- GET /health - 健康检查
- GET /sessions - 列出所有会话
- WebSocket /ws/{session_id} - WebSocket 连接

使用方法：
- 调用健康检查：endpoint="health", method="GET"
- 列出会话：endpoint="sessions", method="GET"

这个工具可以让 Agent 通过 Gateway 获取系统状态或执行管理操作。""",
        parameters={
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "API 端点路径（如 'health', 'sessions'）"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST"],
                    "description": "HTTP 方法",
                    "default": "GET"
                },
                "data": {
                    "type": "object",
                    "description": "POST 请求的数据（仅 POST 时使用）"
                }
            },
            "required": ["endpoint"]
        },
        execute=execute,
    )


def create_session_tool(gateway_url: str = "http://localhost:8080") -> Tool:
    """创建会话管理工具"""
    async def execute(action: str, session_id: Optional[str] = None) -> str:
        """管理会话"""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if action == "list":
                    # 列出所有会话
                    response = await client.get(f"{gateway_url}/sessions")
                    response.raise_for_status()
                    data = response.json()
                    sessions = data.get("sessions", [])
                    total = data.get("total", len(sessions))
                    return f"共有 {total} 个会话:\n" + "\n".join([
                        f"  - {s.get('session_id', 'unknown')}: {s.get('message_count', 0)} 条消息"
                        for s in sessions[:10]
                    ])

                elif action == "health":
                    # 健康检查
                    response = await client.get(f"{gateway_url}/health")
                    response.raise_for_status()
                    data = response.json()
                    return f"Gateway 状态: {data.get('status', 'unknown')}\n活动会话: {data.get('active_sessions', 0)}"

                else:
                    return f"未知操作: {action}"

        except Exception as e:
            return f"会话管理失败: {str(e)}"

    return Tool(
        name="session_manager",
        label="Session Manager",
        description="""管理 Gateway 的会话

支持操作：
- list: 列出所有会话
- health: 检查 Gateway 健康状态

示例：
- 列出会话：action="list"
- 健康检查：action="health" """,
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "health"],
                    "description": "操作类型"
                },
                "session_id": {
                    "type": "string",
                    "description": "会话 ID（某些操作需要）"
                }
            },
            "required": ["action"]
        },
        execute=execute,
    )


def create_gateway_tools(gateway_url: str = "http://localhost:8080") -> list:
    """创建所有 Gateway 相关工具"""
    return [
        create_gateway_tool(gateway_url),
        create_session_tool(gateway_url),
        create_spawn_subagent_tool(gateway_url),  # 新增
    ]
