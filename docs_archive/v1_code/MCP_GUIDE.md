# FastReAct Nano - MCP Protocol Guide

**版本**: 2.1.0
**协议**: SimpleMCP-Stdio (JSON-RPC over stdio)
**状态**: Production Ready

---

## 什么是MCP？

**MCP (Model Context Protocol)** 是AI Agent与外部工具通信的标准协议。

**SimpleMCP-Stdio**特点：
- **标准输入输出通信**: stdin/stdout
- **JSON-RPC格式**: 轻量级消息格式
- **进程隔离**: 每个MCP server独立进程
- **错误隔离**: Server崩溃不影响主进程

---

## 架构

```
┌──────────────────────────────────────────────────┐
│           FastReAct Agent (Python)               │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │   MCP Client (SimpleMCPClient)           │   │
│  │                                          │   │
│  │  - Connect to server                     │   │
│  │  - List tools                            │   │
│  │  - Call tools                            │   │
│  └──────────────────────────────────────────┘   │
│           │                                        │
│           │ JSON-RPC (stdio)                      │
│           │                                        │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │   MCP Server (Subprocess)                │   │
│  │                                          │   │
│  │  - Read requests from stdin             │   │
│  │  - Execute tools                         │   │
│  │  - Write responses to stdout            │   │
│  └──────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

---

## 快速开始

### 1. 运行独立MCP Server

```bash
# 文件操作MCP server
cd fastreact-nano
python examples/file_mcp_server.py --base-path .

# 在另一个终端，测试server
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | \
    python examples/file_mcp_server.py
```

### 2. Python代码调用MCP Server

```python
import asyncio
from fastreact.mcp.client import SimpleMCPClient

async def main():
    client = SimpleMCPClient(
        server_command="python",
        server_args=["file_mcp_server.py", "--base-path", "."],
    )

    try:
        # 连接
        await client.connect()

        # 列出工具
        tools = await client.list_tools()
        for tool in tools:
            print(f"- {tool['name']}: {tool['description']}")

        # 调用工具
        result = await client.call_tool(
            "read_file",
            {"path": "README.md"}
        )
        print(result)

    finally:
        await client.close()

asyncio.run(main())
```

### 3. 一行代码调用

```python
from fastreact.mcp.client import call_mcp_tool

result = await call_mcp_tool(
    server_command="python",
    server_args=["file_mcp_server.py"],
    tool_name="list_dir",
    arguments={"path": "."},
)

print(result)
```

---

## 内置MCP Server

### File Operations Server

**文件**: `examples/file_mcp_server.py`

**工具**:
| 工具 | 功能 | 参数 |
|------|------|------|
| `read_file` | 读取文件 | `path`: 文件路径 |
| `write_file` | 写入文件 | `path`: 文件路径<br>`content`: 内容 |
| `list_dir` | 列出目录 | `path`: 目录路径（可选） |
| `file_info` | 文件信息 | `path`: 文件路径 |

**安全特性**:
- ✅ 沙箱路径（不能逃出base_path）
- ✅ 文件大小限制（1MB）
- ✅ 错误处理

**使用**:
```bash
# 启动server
python examples/file_mcp_server.py --base-path /tmp/sandbox

# 测试模式（列出工具）
python examples/file_mcp_server.py --test
```

---

## API参考

### SimpleMCPClient

```python
class SimpleMCPClient:
    def __init__(
        self,
        server_command: str,
        server_args: list[str] = None,
        timeout: float = 30.0,
    ):
        """
        初始化MCP客户端

        Args:
            server_command: 启动server的命令
            server_args: server参数
            timeout: 请求超时（秒）
        """

    async def connect(self) -> None:
        """启动并连接到MCP server"""

    async def close(self) -> None:
        """关闭连接"""

    async def list_tools(self) -> list[Dict[str, Any]]:
        """
        列出可用工具

        Returns:
            工具定义列表
        """

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
    ) -> str:
        """
        调用工具

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            工具结果（字符串）
        """
```

### SimpleMCPServer

```python
class SimpleMCPServer:
    """MCP Server基类"""

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
    ) -> None:
        """注册工具"""

    @abstractmethod
    async def handle_tool_call(
        self,
        name: str,
        arguments: Dict[str, Any],
    ) -> str:
        """处理工具调用（子类实现）"""

    async def run(self) -> None:
        """运行server主循环"""
```

---

## 创建自定义MCP Server

### 示例：计算器Server

```python
import asyncio
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastreact.mcp.server import SimpleMCPServer


class CalculatorMCPServer(SimpleMCPServer):
    """计算器MCP server"""

    def __init__(self):
        super().__init__()
        self._register_tools()

    def _register_tools(self):
        """注册计算器工具"""
        self.register_tool(
            name="add",
            description="加法运算",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            },
        )

        self.register_tool(
            name="multiply",
            description="乘法运算",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            },
        )

    async def handle_tool_call(self, name: str, arguments: dict) -> str:
        """处理工具调用"""
        if name == "add":
            a = arguments.get("a", 0)
            b = arguments.get("b", 0)
            return f"{a} + {b} = {a + b}"

        elif name == "multiply":
            a = arguments.get("a", 0)
            b = arguments.get("b", 0)
            return f"{a} * {b} = {a * b}"

        return f"[ERROR] Unknown operation: {name}"


async def main():
    """运行server"""
    server = CalculatorMCPServer()

    print("[INFO] Calculator MCP Server starting...")
    print("[INFO] Available tools:")
    for tool_name, tool_def in server._tools.items():
        print(f"  - {tool_name}: {tool_def['description']}")

    try:
        await server.run()
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
```

**使用**:
```bash
# 保存为 calculator_server.py
python calculator_server.py

# 在另一个终端调用
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"add","arguments":{"a":5,"b":3}}}' | \
    python calculator_server.py
```

---

## 集成到FastReAct Agent

### 方式1：作为独立工具

```python
from fastreact import Agent
from fastreact.mcp.client import SimpleMCPClient

async def call_file_mcp(path: str) -> str:
    """辅助函数：调用文件MCP"""
    client = SimpleMCPClient("python", ["file_mcp_server.py"])
    async with client:
        return await client.call_tool("read_file", {"path": path})

# 使用
agent = Agent()
response = await agent.run("Read file_mcp_server.py using file MCP")
```

### 方式2：注册为FastReAct工具

```python
from fastreact.core.tools import Tool
from fastreact.mcp.client import SimpleMCPClient

class MCPTool(Tool):
    """MCP工具包装器"""

    def __init__(self, server_command: str, server_args: list[str]):
        self._client = SimpleMCPClient(server_command, server_args)

    @property
    def name(self) -> str:
        return "mcp_call"

    @property
    def description(self) -> str:
        return "Call MCP server tool"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "tool_name": {"type": "string"},
                "arguments": {"type": "object"},
            },
            "required": ["tool_name", "arguments"],
        }

    async def execute(self, **params) -> str:
        await self._client.connect()
        try:
            return await self._client.call_tool(
                params["tool_name"],
                params["arguments"],
            )
        finally:
            await self._client.close()

# 注册工具
agent = Agent()
agent._tools.register(MCPTool("python", ["file_mcp_server.py"]))
```

---

## 测试

### 运行完整测试

```bash
cd fastreact-nano
python test_mcp_integration.py
```

**测试覆盖**:
- ✅ MCP Server独立运行
- ✅ 工具发现（tools/list）
- ✅ 工具执行（tools/call）
- ✅ 安全性（路径沙箱）

**预期结果**:
```
Total Tests: 4
Passed: 4/4

[SUCCESS] All MCP tests passed!
[READY] MCP Protocol is FULLY FUNCTIONAL
```

---

## 性能特点

| 指标 | 值 | 说明 |
|------|-----|------|
| 启动延迟 | ~100ms | 子进程启动开销 |
| 通信延迟 | <10ms | stdio读写 |
| 内存隔离 | 完全 | 独立进程 |
| 错误隔离 | 完全 | Server崩溃不影响Agent |
| 并发性 | 高 | 可启动多个server |

---

## 安全考虑

### 1. 路径沙箱

File MCP Server限制操作在base_path内：

```python
# ✅ 允许
await client.call_tool("read_file", {"path": "README.md"})

# ❌ 拒绝
await client.call_tool("read_file", {"path": "../../../etc/passwd"})
# → [ERROR] Path escapes base directory
```

### 2. 文件大小限制

File MCP Server限制读取文件大小为1MB：

```python
# 超过1MB的文件会被拒绝
```

### 3. 进程隔离

```python
# Server崩溃只影响subprocess，不影响Agent
try:
    await client.call_tool(...)
except Exception:
    # Agent仍然正常运行
    pass
```

---

## 故障排查

### 问题1：Server启动失败

```
[ERROR] Failed to start MCP server
```

**解决**：
- 检查server_command路径是否正确
- 检查Python环境是否一致
- 检查server_args参数

### 问题2：工具调用超时

```
[ERROR] MCP request timeout (30s)
```

**解决**：
- 增加timeout参数
- 检查server是否卡死
- 检查是否有死循环

### 问题3：JSON解析错误

```
[ERROR] Invalid MCP response
```

**解决**：
- 确保server输出有效JSON
- 检查server是否有额外打印
- 确保每行一个JSON对象

---

## 示例代码

完整示例见：
- `examples/file_mcp_server.py` - 文件操作server
- `examples/mcp_demo.py` - 使用示例
- `test_mcp_integration.py` - 集成测试

---

## 总结

**MCP Protocol Support**:
- ✅ 完整实现Client和Server
- ✅ 独立可用的File MCP Server
- ✅ 完整测试覆盖（4/4通过）
- ✅ 安全隔离（进程沙箱）
- ✅ 易于扩展（基类+自定义）

**FastReAct Nano v2.1.0现在支持MCP协议！**

---

*文档版本: 1.0*
*最后更新: 2026-02-15*
