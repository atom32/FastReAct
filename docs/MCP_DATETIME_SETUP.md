# mcp-datetime MCP 服务器配置指南

## 仓库信息

- **GitHub**: https://github.com/ZeparHyfar/mcp-datetime
- **作者**: ZeparHyfar
- **功能**: 提供日期时间相关的 MCP 服务器

## 配置步骤

### 步骤 1: 获取仓库

由于网络问题，请手动下载：

**方式 A - GitHub Desktop** (推荐):
1. 打开 GitHub Desktop
2. File > Clone Repository
3. URL: `https://github.com/ZeparHyfar/mcp-datetime`
4. 选择本地路径（如 `D:\FastReAct\mcp-datetime`）

**方式 B - 下载 ZIP**:
1. 访问: https://github.com/ZeparHyfar/mcp-datetime
2. 点击绿色的 "Code" 按钮
3. 点击 "Download ZIP"
4. 解压到 `D:\FastReAct\` 目录

**方式 C - Git (需要代理)**:
```bash
git clone https://github.com/ZeparHyfar/mcp-datetime.git
```

### 步骤 2: 安装依赖

```bash
cd mcp-datetime
npm install
```

### 步骤 3: 构建

```bash
npm run build
```

### 步骤 4: 创建 MCP 配置文件

在 `D:\FastReAct\` 目录创建 `mcp_datetime_config.json`：

```json
{
  "mcpServers": {
    "datetime": {
      "command": "node",
      "args": ["D:\\FastReAct\\mcp-datetime\\dist\\index.js"]
    }
  }
}
```

**注意**: 如果你的项目路径不同，请修改 `args` 中的路径。

### 步骤 5: 测试连接

运行配置脚本：

```bash
python examples/setup_mcp_datetime.py
```

这个脚本会：
1. 检查仓库是否存在
2. 自动安装依赖和构建
3. 创建 MCP 配置
4. 测试连接
5. （可选）启动 Agent 对话

## 快速测试

如果只想测试连接，可以运行：

```bash
python examples/setup_mcp_datetime.py
```

脚本会自动：
- 连接到 MCP 服务器
- 列出可用工具
- 测试工具调用
- 显示结果

## 可用工具

根据 README，这个服务器应该提供类似：
- `get_current_datetime` - 获取当前日期时间
- `get_timezone_info` - 获取时区信息
- 等...

## 使用示例

连接成功后，可以在代码中使用：

```python
from fastreact.tools import MCPClientManager

manager = MCPClientManager()
manager.load_config("mcp_datetime_config.json")
await manager.connect_all()

# 获取工具
tools = await manager.get_server_tools("datetime")

# 使用工具
result = await tools["get_current_datetime"].execute_async(
    format="ISO",
    timezone="Asia/Shanghai"
)
print(result)
```

## 集成到 FastReAct Agent

```python
from fastreact import FastReAct
from fastreact.tools import MCPClientManager

# 连接 MCP 服务器
manager = MCPClientManager()
manager.load_config("mcp_datetime_config.json")
await manager.connect_all()

# 获取工具
tools = await manager.get_server_tools("datetime")

# 创建 Agent（包含 MCP 工具）
agent = FastReAct(
    api_key="your-api-key",
    model="deepseek-ai/DeepSeek-V3",
    tools=list(tools.values())
)

# AI 会自动使用 MCP 时间工具
response = await agent.run("现在北京时间几点？")
print(response)
```

## 故障排除

### 问题: npm install 失败

**解决方案**:
```bash
# 清除 npm 缓存
npm cache clean --force

# 重新安装
npm install
```

### 问题: npm run build 失败

**解决方案**:
```bash
# 检查 Node.js 版本
node --version  # 需要 Node.js 18+

# 如果版本过低，升级 Node.js
```

### 问题: 连接超时

**解决方案**:
- 确保 `mcp-datetime/dist/index.js` 文件存在
- 检查配置文件中的路径是否正确
- 确保 Node.js 在系统 PATH 中

## 替代方案

如果无法安装 MCP 服务器，可以使用 FastReAct 内置的时间工具：

```python
from fastreact.tools import GetCurrentTimeTool

tool = GetCurrentTimeTool()
result = await tool.execute_async(timezone="Asia/Shanghai")
print(result)
```

这提供了类似的功能，无需安装外部 MCP 服务器。
