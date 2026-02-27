# MCP能力添加改进方案

**日期**: 2025-02-24
**状态**: 提案 (部分已实现 v2.4.2)
**最后更新**: 2025-02-24

---

## 实现状态 (v2.4.2)

### ✅ 已实现

| 方案 | 状态 | 说明 |
|------|------|------|
| **方案D: 统一配置管理** | ✅ 完成 | 标准目录结构 + 魔法路径 |
| **魔法路径支持** | ✅ 完成 | `@builtin/` 自动解析 |
| **HTTP 传输** | ✅ 完成 | stdio + HTTP 双传输 |
| **凭证管理** | ✅ 完成 | 环境变量优先级 |

### ⏳ 待实现

| 方案 | 优先级 | 工作量 | 状态 |
|------|--------|--------|------|
| **方案A: MCP模板生成器** | P1 | 1-2天 | 待实现 |
| **方案B: 配置验证工具** | P1 | 1天 | 待实现 |
| **方案C: 热重载支持** | P2 | 3-5天 | 待实现 |
| **方案E: Marketplace集成** | P3 | 1周 | 待实现 |

---

## 当前流程

### 现状 (v2.4.2 改进后)

添加MCP能力现在需要以下步骤：
1. 创建MCP server目录（标准结构）
2. 编写server代码（继承SimpleMCPServer）
3. （可选）编辑`~/.fastreact/config.json`（支持魔法路径）
4. （可选）创建对应的SKILL
5. 重启Gateway服务

**改进点**：
- ✅ 标准目录结构：`mcp_servers/builtin/{name}/server.py`
- ✅ 魔法路径简化配置：`@builtin/{name}/server.py`
- ✅ 凭证安全分离：`credentials.json` + 环境变量

### 剩余问题

| 问题 | 影响 | 严重性 | 优先级 |
|------|------|--------|--------|
| **手动编写代码** | 每次都要从头写server代码 | 中 | P1 |
| **无验证工具** | 配置错误只能在运行时发现 | 高 | P1 |
| **无模板生成** | 没有脚手架代码生成 | 中 | P1 |
| **需要重启** | 添加server需要重启Gateway | 低 | P2 |

---

## 改进方案

### 方案A: MCP Server模板生成器 (P1, 高价值)

**目标**: 提供MCP server脚手架生成工具

**实现**: CLI命令 `fastreact add-mcp`

```bash
# 使用方式
fastreact add-mcp my_server --description "My custom MCP server"

# 自动生成：
# - mcp_servers/builtin/my_server/server.py (模板代码)
# - mcp_servers/builtin/my_server/config.json (元数据)
# - mcp_servers/builtin/my_server/README.md (文档)
# - skills/builtin/my_server_workflow/SKILL.md (SKILL模板，可选)
```

**生成代码模板**:
```python
# mcp_servers/builtin/my_server/server.py
"""
FastReAct Nano - My Server MCP Server

MCP server for custom functionality.
"""

from fastreact.mcp.server import SimpleMCPServer
from typing import Any, Dict

class MyMCPServer(SimpleMCPServer):
    """My custom MCP server"""

    def __init__(self):
        super().__init__()
        self._register_tools()

    def _register_tools(self):
        """Register MCP tools"""
        self.register_tool(
            name="my_tool",
            description="Description of what this tool does",
            input_schema={
                "type": "object",
                "properties": {
                    "param": {
                        "type": "string",
                        "description": "Parameter description"
                    }
                },
                "required": ["param"]
            }
        )

    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> str:
        """Handle tool execution"""
        if name == "my_tool":
            return f"Result: {arguments.get('param', '')}"
        return f"[ERROR] Unknown tool: {name}"

if __name__ == "__main__":
    import asyncio
    server = MyMCPServer()
    asyncio.run(server.run())
```

---

### 方案B: 配置验证工具 (P1, 高价值)

**目标**: 在启动前验证MCP配置

**实现**: CLI命令 `fastreact validate-mcp`

```bash
# 验证配置
fastreact validate-mcp

# 输出示例：
# [OK] MCP config loaded from ~/.fastreact/config.json
# [OK] graphrag: Server file exists
# [OK] graphrag: Python syntax valid
# [OK] graphrag: Transport = stdio
# [WARNING] timeserver: Command 'uvx' not found in PATH
# [WARNING] my_server: No associated SKILL found
```

**验证检查项**:
- [ ] 配置文件存在且JSON格式正确
- [ ] server文件存在
- [ ] transport字段有效（stdio/http）
- [ ] stdio: command命令可用（在PATH中）
- [ ] http: URL格式正确
- [ ] Python文件语法正确
- [ ] （可选）对应的SKILL文件存在

---

### 方案C: 热重载支持 (P2, 中价值)

**目标**: 无需重启Gateway即可添加MCP server

**实现**:
1. 监控`~/.fastreact/config.json`变化
2. 自动加载新配置
3. 动态注册新MCP工具

**API端点**:
```bash
# 手动触发重载
curl -X POST http://localhost:9000/api/mcp/reload

# 响应
{
  "status": "success",
  "reloaded_servers": ["my_server"],
  "errors": []
}
```

---

### 方案D: 统一配置管理 (P2, 中价值) ✅ 已完成

**目标**: 配置文件与server文件放在一起

**v2.4.2 已实现**:
```
mcp_servers/builtin/{name}/
├── server.py       # server代码
├── config.json     # server元数据
├── README.md       # 文档
└── requirements.txt # 依赖（可选）
```

**已实现的优点**:
- ✅ 配置与代码在一起，易于维护
- ✅ 魔法路径简化配置：`@builtin/{name}/server.py`
- ✅ 标准化目录结构

---

### 方案E: MCP Marketplace集成 (P3, 低价值)

**目标**: 从前端直接安装MCP server

**实现**: 前端`/marketplace`页面
1. 浏览可用的MCP servers
2. 一键安装到本地
3. 自动配置和启用

---

## 推荐实施顺序

### Phase 1: CLI工具改进 (1-2天)
1. **方案A**: MCP Server模板生成器
   - 添加`fastreact add-mcp`命令
   - 生成server代码模板
   - 生成config.json和README.md
   - 生成SKILL模板（可选）

2. **方案B**: 配置验证工具
   - 添加`fastreact validate-mcp`命令
   - 验证配置文件
   - 验证server文件
   - 验证命令可用性

### Phase 2: 中期改进 (3-5天)
3. **方案C**: 热重载支持
   - 配置文件监控
   - 动态加载机制
   - API端点

### Phase 3: 长期改进 (可选)
4. **方案E**: MCP Marketplace集成
   - 前端UI
   - server仓库
   - 自动安装

---

## 总结

### 已完成 (v2.4.2)
- ✅ 统一目录结构 (`mcp_servers/builtin/{name}/`)
- ✅ 魔法路径支持 (`@builtin/`)
- ✅ HTTP 传输支持
- ✅ 凭证管理分离

### 待实现
- ⏳ `fastreact add-mcp` - 模板生成器
- ⏳ `fastreact validate-mcp` - 配置验证
- ⏳ 热重载支持
- ⏳ Marketplace 集成

### 优先级
1. **P1**: 模板生成器 + 配置验证（1-2天）
2. **P2**: 热重载支持（3-5天）
3. **P3**: Marketplace 集成（可选）

---

**文档版本**: 2.0
**最后更新**: 2025-02-24
**维护者**: FastReAct Team
