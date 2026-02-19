# MCP-timeserver 集成指南

**版本**: 2.4.2
**更新日期**: 2025-02-19

---

## 概述

本文档说明如何集成和测试 MCP-timeserver，以验证 FastReAct 的 SKILL 和 MCP 系统正常工作。

---

## 一、MCP-timeserver 简介

### 1.1 什么是 MCP-timeserver？

MCP-timeserver 是一个简单的 MCP 服务器，提供：
- **Tool**: `get-current-time` - 获取当前系统时间
- **Resources**: `datetime://timezone/now` - 获取指定时区的当前时间

### 1.2 为什么选择 MCP-timeserver？

✅ **简单**: 代码少，易于理解
✅ **实用**: 提供真实可用的功能
✅ **稳定**: 无外部依赖，易于测试
✅ **标准**: 完全符合 MCP 协议规范

---

## 二、安装和配置

### 2.1 下载 MCP-timeserver

```bash
cd /Users/xudawei/FastReAct/fastreact-nano

# 已自动克隆到:
mcp_servers/builtin/timeserver/
```

### 2.2 配置 MCP-timeserver

配置文件: `mcp_servers/config/shared.json`

```json
{
  "schema_version": "1.0",
  "description": "Shared MCP servers (single instance for all users)",
  "servers": [
    {
      "name": "timeserver",
      "command": "uvx",
      "args": ["--from", "mcp_servers/builtin/timeserver", "mcp-timeserver"],
      "isolation": "shared",
      "description": "Current time and date information"
    }
  ]
}
```

### 2.3 安装依赖

```bash
# 确保安装了 uv (Python 包管理器)
pip install uv

# 或使用 pip 直接安装
pip install mcp-timeserver
```

---

## 三、验证 MCP-timeserver

### 3.1 运行测试脚本

```bash
cd /Users/xudawei/FastReAct/fastreact-nano

python3 test_mcp_timeserver.py
```

**预期输出**:
```
============================================================
MCP-timeserver Integration Test
============================================================

[1/4] Loading configuration...
✓ Config loaded from: mcp_servers/config/shared.json

[2/4] Checking MCP server configuration...
✓ Found 1 MCP server(s) configured:
  - timeserver: Current time and date information
✓ timeserver found: uvx --from mcp_servers/builtin/timeserver mcp-timeserver

[3/4] Creating Agent and loading MCP servers...
✓ MCP servers loaded successfully
✓ MCP manager initialized
✓ MCP servers: ['timeserver']

[4/4] Listing available tools...
✓ Total tools: 8
✓ Timeserver tools: 1
✓ timeserver_get-current-time

============================================================
Testing timeserver_get-current-time tool...
============================================================
✓ Tool executed successfully!
✓ Result: The current time is 2025-02-19 17:55:30

============================================================
Test Complete!
============================================================

Summary:
  ✓ MCP servers configured: 1
  ✓ MCP servers loaded: 1
  ✓ Timeserver tools available: 1
  ✓ Total tools available: 8

SKILL System Status:
  ✓ Skills available: 5
  ✓ Skills: code_review, file_ops, git_workflow, github_integration, graphrag_workflow
```

### 3.2 手动测试 MCP Server

```bash
# 直接运行 MCP server (测试是否能启动)
cd /Users/xudawei/FastReAct/fastreact-nano
uvx --from mcp_servers/builtin/timeserver mcp-timeserver
```

**预期**: Server 启动并等待 JSON-RPC 请求（不会返回提示符）

---

## 四、Gateway API 测试

### 4.1 启动 Gateway

```bash
cd /Users/xudawei/FastReAct/fastreact-nano

# 启动 Gateway
python3 -m fastreact.adapters.gateway

# 或使用 uvicorn
uvicorn fastreact.adapters.gateway:create_gateway_app --host 0.0.0.0 --port 9000 --reload
```

### 4.2 查看 SKILL 状态

```bash
curl http://localhost:9000/api/skills
```

**预期响应**:
```json
{
  "skills": [
    {
      "name": "code_review",
      "description": "Review code for bugs, security issues, and style",
      "version": "1.0.0",
      "author": "FastReAct",
      "mcp_servers": []
    },
    {
      "name": "git_workflow",
      "description": "Git workflow automation",
      "version": "1.0.0",
      "author": "FastReAct",
      "mcp_servers": []
    }
  ],
  "global_skills_dir": "/Users/xudawei/FastReAct/fastreact-nano/skills/builtin",
  "total_count": 5
}
```

### 4.3 查看 MCP 状态

```bash
curl http://localhost:9000/api/mcp/servers
```

**预期响应**:
```json
{
  "servers": [
    {
      "name": "timeserver",
      "command": "uvx",
      "args": ["--from", "mcp_servers/builtin/timeserver", "mcp-timeserver"],
      "description": "Current time and date information",
      "isolation": "shared",
      "associated_skill": null
    }
  ]
}
```

### 4.4 查看系统状态（新端点）

```bash
curl http://localhost:9000/api/status
```

**预期响应**:
```json
{
  "status": "healthy",
  "version": "2.4.2",
  "features": {
    "skill_system": {
      "enabled": true,
      "total_skills": 5,
      "global_skills_dir": "/Users/xudawei/FastReAct/fastreact-nano/skills/builtin",
      "skills": ["code_review", "file_ops", "git_workflow", "github_integration", "graphrag_workflow"]
    },
    "mcp_system": {
      "enabled": true,
      "loaded": true,
      "total_servers": 1,
      "servers": [
        {
          "name": "timeserver",
          "status": "running",
          "isolation": "shared"
        }
      ]
    },
    "multi_tenant": {
      "enabled": false,
      "mode": "single-tenant (Gateway)"
    }
  }
}
```

### 4.5 查看所有工具（包括 MCP 工具）

```bash
curl http://localhost:9000/api/tools
```

**预期响应**:
```json
{
  "tools": [
    "read_file",
    "write_file",
    "exec_tool",
    "edit_file",
    "echo",
    "add",
    "timeserver_get-current-time"
  ],
  "mcp_tools": [
    {
      "server": "timeserver",
      "tool": "get-current-time",
      "full_name": "timeserver_get-current-time"
    }
  ]
}
```

---

## 五、前端集成测试

### 5.1 通过前端测试

1. 打开前端: http://localhost:3000

2. 发送查询:
   ```
   现在几点了？
   ```

3. 预期行为:
   - Agent 会调用 `timeserver_get-current-time` 工具
   - 返回当前时间

**示例对话**:
```
User: 现在几点了？

Agent: [THINK] 用户想知道当前时间，我需要使用时间工具
      [TOOL_CALL] timeserver_get-current-time
      [TOOL_RESULT] The current time is 2025-02-19 17:55:30

      现在是 2025年2月19日 17:55:30。
```

---

## 六、故障排查

### 6.1 MCP Server 无法启动

**症状**: 测试脚本显示 "ERROR loading MCP servers"

**检查**:
```bash
# 1. 检查 uv 是否安装
which uv

# 2. 手动测试 MCP server
uvx --from mcp_servers/builtin/timeserver mcp-timeserver

# 3. 检查 Python 路径
python3 -c "import sys; print(sys.path)"
```

**解决**:
```bash
# 安装 uv
pip install uv

# 或使用 pip 直接安装
pip install mcp-timeserver

# 更新配置使用 pip
{
  "command": "python3",
  "args": ["-m", "mcp_timeserver"]
}
```

### 6.2 工具未找到

**症状**: `timeserver_get-current-time` 工具不在列表中

**检查**:
```bash
# 1. 检查 MCP manager 是否初始化
curl http://localhost:9000/api/status | jq .features.mcp_system

# 2. 检查 MCP server 是否运行
curl http://localhost:9000/api/status | jq .features.mcp_system.servers
```

**解决**:
- 确保 MCP server 配置正确
- 等待 MCP server 完全启动（可能需要几秒）
- 检查防火墙是否阻止子进程

### 6.3 SKILL 未加载

**症状**: `/api/skills` 返回空列表

**检查**:
```bash
# 1. 检查 skills 目录
ls -la skills/builtin/

# 2. 检查配置
cat ~/.fastreact/config.json | grep skills_dir
```

**解决**:
```bash
# 确保 skills 目录存在
ls skills/builtin/

# 应该看到:
# code_review/
# file_ops/
# git_workflow/
# github_integration/
# graphrag_workflow/
```

---

## 七、扩展：添加更多 MCP Servers

### 7.1 官方 MCP Servers

```json
{
  "servers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"],
      "isolation": "per_user",
      "description": "Filesystem operations"
    },
    {
      "name": "github",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"
      },
      "isolation": "shared",
      "description": "GitHub integration"
    }
  ]
}
```

### 7.2 自定义 MCP Server

参考 `examples/file_mcp_server.py` 创建自己的 MCP server。

---

## 八、总结

### 验证清单

- [x] MCP-timeserver 已下载
- [x] MCP-timeserver 已配置
- [x] `/api/skills` 端点可用
- [x] `/api/mcp/servers` 端点可用
- [x] `/api/status` 端点可用（新增）
- [x] `/api/tools` 端点包含 MCP 工具
- [x] 测试脚本可用

### 下一步

1. ✅ 测试 MCP-timeserver 集成
2. ✅ 验证 SKILL 系统正常工作
3. ⏭️ 添加更多 MCP Servers
4. ⏭️ 创建自定义 SKILL
5. ⏭️ 测试 SKILL + MCP 联合使用

---

**维护者**: Claude Code
**最后更新**: 2025-02-19
**版本**: 2.4.2
