# Tavily API Key 配置指南

## 获取 Tavily API Key

1. 访问 https://tavily.com/
2. 注册账号（免费额度：每月 1000 次搜索）
3. 登录后进入 Dashboard
4. 复制你的 API Key

## 配置方式

### 方式 1: 环境变量（推荐）

**Windows PowerShell:**
```powershell
# 临时设置（仅当前会话有效）
$env:TAVILY_API_KEY="tvly-your-api-key-here"

# 永久设置（重启后仍有效）
[System.Environment]::SetEnvironmentVariable('TAVILY_API_KEY', 'tvly-your-api-key-here', 'User')
```

**Windows CMD:**
```cmd
# 临时设置
set TAVILY_API_KEY=tvly-your-api-key-here

# 永久设置
setx TAVILY_API_KEY "tvly-your-api-key-here"
```

**Linux/Mac:**
```bash
# 临时设置
export TAVILY_API_KEY="tvly-your-api-key-here"

# 永久设置（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export TAVILY_API_KEY="tvly-your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### 方式 2: 在代码中直接传入

```python
from fastreact.tools import TavilySearchTool

# 直接传入 API Key
search_tool = TavilySearchTool(api_key="tvly-your-api-key-here")
```

示例文件: `examples/tavily_demo_with_key.py`

### 方式 3: 配置文件

在 `config.json` 中添加：

```json
{
  "llm": {
    "providers": {
      "siliconflow": {
        "api_key": "your-siliconflow-api-key"
      }
    }
  },
  "tools": {
    "tavily": {
      "api_key": "tvly-your-api-key-here"
    }
  }
}
```

然后在代码中读取：

```python
import json
from fastreact.tools import TavilySearchTool

# 读取配置
with open("config.json", "r") as f:
    config = json.load(f)

tavily_api_key = config["tools"]["tavily"]["api_key"]

# 创建工具
search_tool = TavilySearchTool(api_key=tavily_api_key)
```

## 使用示例

配置好后，即可使用 Tavily 搜索：

```python
from fastreact import FastReAct
from fastreact.tools import TavilySearchTool

# 方式 1: 使用环境变量
search_tool = TavilySearchTool()  # 自动从环境变量读取

# 方式 2: 直接传入
search_tool = TavilySearchTool(api_key="tvly-your-api-key-here")

# 创建 Agent
agent = FastReAct(
    api_key="your-fastreact-api-key",
    model="deepseek-ai/DeepSeek-V3",
    tools=[search_tool]
)

# 使用搜索
response = await agent.run_async("搜索最新的 AI 新闻")
print(response)
```

## 测试配置

运行测试脚本验证配置：

```bash
# 如果设置了环境变量
python -c "from fastreact.tools import TavilySearchTool; t = TavilySearchTool(); print('[OK] Tavily API Key configured')"

# 或者运行演示脚本
python examples/tavily_demo_with_key.py
```

## 免费额度说明

Tavily 免费计划：
- 每月 1000 次搜索
- 适合开发和测试
- 超出后需要付费升级

查看使用量: https://tavily.com/dashboard

## 常见问题

### Q: API Key 从哪里获取？
A: 访问 https://tavily.com/ 注册账号后在 Dashboard 获取

### Q: 免费额度够用吗？
A: 开发测试足够，每月 1000 次搜索

### Q: 如何查看剩余额度？
A: 登录 Tavily Dashboard 查看

### Q: 可以不用 Tavily 吗？
A: 可以，使用 FastReAct 内置的 SearchTool 或其他搜索工具
