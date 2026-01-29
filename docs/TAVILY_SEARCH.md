# Tavily 搜索工具集成指南

## 概述

FastReAct 现在支持 [Tavily Search API](https://tavily.com/)，这是一个专门为 AI 优化的搜索引擎。

## 特性

- ✅ **实时搜索**: 获取最新的网络信息
- ✅ **AI 优化**: 搜索结果经过 AI 优化，更适合 LLM 使用
- ✅ **智能摘要**: 自动生成答案摘要
- ✅ **多源聚合**: 从多个来源聚合信息
- ✅ **多语言**: 支持中文等多种语言
- ✅ **三种模式**: 基础搜索、新闻搜索、高级搜索

## 安装

```bash
pip install httpx
```

## 获取 API Key

1. 访问 [Tavily 官网](https://tavily.com/)
2. 注册账号（免费套餐包含每月 1000 次搜索）
3. 在控制台获取 API Key

## 配置方式

### 方式 1: 环境变量（推荐）

```bash
# Windows
set TAVILY_API_KEY=tvly-your-api-key-here

# Linux/Mac
export TAVILY_API_KEY=tvly-your-api-key-here
```

### 方式 2: config.json 文件

在 `config.json` 中添加：

```json
{
  "tavily_api_key": "tvly-your-api-key-here",
  "llm": {
    ...
  }
}
```

### 方式 3: 代码中直接指定

```python
from fastreact.tools import TavilySearchTool

search = TavilySearchTool(api_key="tvly-your-api-key-here")
```

## 使用方法

### 基础使用

```python
import asyncio
from fastreact import FastReAct
from fastreact.tools import TavilySearchTool

async def main():
    # 创建搜索工具
    search_tool = TavilySearchTool()

    # 创建 Agent 并添加搜索工具
    agent = FastReAct(
        api_key="your-llm-api-key",
        model="deepseek-ai/DeepSeek-V3",
        tools=[search_tool]
    )

    # 提问，AI 会自动使用搜索工具
    response = await agent.run(
        query="2024年AI领域有哪些重大突破？",
        session_id="demo_session"
    )

    print(response)

asyncio.run(main())
```

### 三种搜索工具

#### 1. TavilySearchTool - 基础搜索

```python
from fastreact.tools import TavilySearchTool

search = TavilySearchTool(
    api_key="your-api-key",
    search_depth="basic",      # basic 或 advanced
    max_results=10,             # 最多10条结果
    include_answer=True,        # 包含AI生成的答案摘要
    include_images=False        # 是否包含图片
)
```

#### 2. TavilyNewsTool - 新闻搜索

```python
from fastreact.tools import TavilyNewsTool

news_search = TavilyNewsTool(
    api_key="your-api-key",
    max_results=10
)

# 专门用于搜索新闻
result = await news_search.execute_async("最新科技新闻")
```

#### 3. TavilyAdvancedSearchTool - 高级搜索

```python
from fastreact.tools import TavilyAdvancedSearchTool

advanced_search = TavilyAdvancedSearchTool(
    api_key="your-api-key",
    max_results=10
)

# 深度搜索，包含图片和详细内容
result = await advanced_search.execute_async("量子计算原理")
```

## 运行演示

### 测试搜索功能

```bash
# 测试搜索（无需 LLM API Key）
python examples/tavily_search_demo.py test
```

### 交互式对话

```bash
# 完整对话体验（需要 LLM API Key）
python examples/tavily_search_demo.py
```

### 示例对话

```
You: 最新的AI新闻是什么？
AI: [使用 Tavily 搜索]
    🔍 搜索 '最新AI新闻' 找到 10 条结果:

    1. **OpenAI 发布 GPT-5 预览版**
       据报道，OpenAI 正在准备发布 GPT-5，预计将具有更强的推理能力...
       🔗 https://techcrunch.com/...

    2. **Google Gemini 2.0 发布**
       Google 宣布推出 Gemini 2.0，在多模态能力上有重大突破...
       🔗 https://blog.google/...
```

## 搜索参数

### 查询参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `query` | string | ✅ | 搜索查询 |
| `search_depth` | string | ❌ | "basic" 或 "advanced"，默认 "basic" |
| `max_results` | int | ❌ | 结果数量 (1-10)，默认 10 |
| `days` | int | ❌ | 搜索最近N天 (1-30)，默认 3 |
| `topic` | string | ❌ | "general" 或 "news"，默认 "general" |

### 初始化参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api_key` | str | env var | Tavily API Key |
| `search_depth` | str | "basic" | 搜索深度 |
| `max_results` | int | 10 | 最大结果数 |
| `include_answer` | bool | True | 是否包含AI答案摘要 |
| `include_raw_content` | bool | False | 是否包含原始HTML |
| `include_images` | bool | False | 是否包含图片 |
| `include_image_descriptions` | bool | False | 是否包含图片描述 |

## 高级用法

### 自定义搜索参数

```python
from fastreact.tools import TavilySearchTool

search = TavilySearchTool()

# 搜索最近7天的科技新闻
result = await search.execute_async(
    query="AI技术进展",
    search_depth="advanced",
    max_results=5,
    days=7,
    topic="news"
)
```

### 与其他工具组合

```python
from fastreact import FastReAct
from fastreact.tools import (
    TavilySearchTool,
    CalculatorTool,
    HTTPTool
)

agent = FastReAct(
    api_key="your-llm-api-key",
    model="deepseek-ai/DeepSeek-V3",
    tools=[
        TavilySearchTool(),    # 网络搜索
        CalculatorTool(),      # 计算
        HTTPTool()             # HTTP 请求
    ]
)
```

### ReAct 循环中使用

```python
# AI 会自动决定何时使用搜索
queries = [
    "Python最新版本是多少？",      # 会触发搜索
    "计算 (15 + 25) * 2",          # 会触发计算器
    "今天北京天气怎么样？",        # 可能触发搜索
    "解释一下量子计算"             # 会触发搜索
]
```

## API 限制

### 免费套餐

- **每月**: 1,000 次搜索
- **并发**: 无限制
- **搜索深度**: basic
- **最大结果**: 10 条

### 付费套餐

- **Research**: $20/月，5,000 次搜索
- **Business**: $100/月，30,000 次搜索
- 详细信息: https://tavily.com/pricing

## 故障排除

### 未配置 API Key

如果未配置 `TAVILY_API_KEY`，工具会自动回退到模拟搜索模式：

```
🔍 搜索 'Python教程' (演示模式 - 未配置 Tavily API Key)
找到 5 条模拟结果:

1. **'Python教程' - 维基百科**
   关于 Python 教程 的详细条目...

💡 提示: 配置 TAVILY_API_KEY 环境变量以使用真实搜索
   获取 API Key: https://tavily.com/
```

### 搜索失败

如果搜索失败：

1. **检查 API Key**:
   ```bash
   echo $TAVILY_API_KEY  # Linux/Mac
   echo %TAVILY_API_KEY% # Windows
   ```

2. **检查网络连接**:
   ```python
   import httpx
   async with httpx.AsyncClient() as client:
       response = await client.get("https://api.tavily.com/")
       print(response.status_code)  # 应该是 200
   ```

3. **检查 API 配额**:
   登录 Tavily 控制台查看剩余配额

## 最佳实践

### 1. 选择合适的搜索深度

```python
# 快速搜索 - 适合简单查询
quick_search = TavilySearchTool(search_depth="basic")

# 深度搜索 - 适合研究需求
deep_search = TavilyAdvancedSearchTool(search_depth="advanced")
```

### 2. 控制结果数量

```python
# 减少结果以提高速度
result = await search.execute_async(
    query="Python教程",
    max_results=5  # 只返回5条，而不是默认的10条
)
```

### 3. 使用新闻搜索

```python
from fastreact.tools import TavilyNewsTool

# 专门搜索新闻，结果更精准
news = TavilyNewsTool()
result = await news.execute_async("特斯拉最新新闻")
```

### 4. 关闭资源

```python
search = TavilySearchTool()

try:
    result = await search.execute_async("查询")
finally:
    await search.close()  # 关闭 HTTP 连接
```

或使用异步上下文管理器：

```python
async with TavilySearchTool() as search:
    result = await search.execute_async("查询")
```

## 对比其他搜索方式

| 特性 | Tavily | 旧 SearchTool | Google API |
|------|--------|--------------|------------|
| 实时性 | ✅ 优秀 | ❌ 模拟 | ✅ 良好 |
| AI 优化 | ✅ 是 | ❌ 否 | ❌ 否 |
| 易用性 | ✅ 简单 | ✅ 简单 | ❌ 复杂 |
| 价格 | ✅ 免费额度 | ✅ 免费 | ❌ 付费 |
| 智能摘要 | ✅ 有 | ❌ 无 | ❌ 无 |
| 中文支持 | ✅ 优秀 | ⚠️ 一般 | ⚠️ 一般 |

## 参考资源

- [Tavily 官方文档](https://docs.tavily.com/)
- [Tavily API 参考](https://docs.tavily.com/docs/tavily-search/rest)
- [FastReAct 文档](https://github.com/atom32/FastReAct)

## 更新日志

- **2026-01-29**: 添加 Tavily 搜索支持
  - TavilySearchTool
  - TavilyNewsTool
  - TavilyAdvancedSearchTool
