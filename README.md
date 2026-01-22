# FastReAct

> 一个轻量级的ReACT框架实现，适合学习和参考

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ 特性

- 📚 **学习友好** - 代码简洁清晰，适合理解ReACT原理
- ⚡ **异步支持** - 基于asyncio，支持并发工具调用
- 💾 **内置缓存** - LRU缓存减少重复计算
- 🌊 **流式响应** - 支持流式输出
- 🛠️ **易于扩展** - 插件式工具系统，支持MCP工具
- 📦 **轻量级** - 核心代码不到600行
- 🔥 **GraphRAG集成** - 内置5个GraphRAG工具，支持知识图谱查询和推理

## 🎯 项目定位

这是一个**学习项目**，旨在展示如何从零实现一个ReACT框架。代码力求简洁清晰，方便理解ReACT的工作原理。

**适用场景：**
- 学习ReACT原理
- 理解Agent框架设计
- 作为项目参考实现
- 轻量级应用原型

**不推荐场景：**
- 企业级生产环境（缺少完善的错误处理和监控）
- 需要丰富工具生态的场景（工具库较少）
- 需要可视化和调试的场景（暂无）

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/atom32/FastReAct.git
cd FastReAct

# 安装依赖
pip install -r requirements.txt

# 或以可编辑模式安装
pip install -e .
```

### 基础使用

```python
from fastreact import FastReAct, Tool
import asyncio

# 1. 定义自定义工具
class Calculator(Tool):
    """计算器工具"""

    def _get_description(self):
        return "执行数学计算"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式"
                }
            }
        }

    async def execute_async(self, expression: str) -> str:
        try:
            result = eval(expression)
            return f"计算结果: {result}"
        except Exception as e:
            return f"错误: {str(e)}"

# 2. 创建ReACT引擎
react = FastReAct(
    api_key="your-api-key",
    base_url="https://api.openai.com/v1",
    model="gpt-4",
    tools=[Calculator()],
    enable_cache=True,
    max_concurrent_tools=3
)

# 3. 运行
async def main():
    result = await react.run_async(
        query="帮我计算 (15 + 25) * 2",
        stream_callback=lambda x: print(x, end="", flush=True)
    )

    print(f"\n最终答案: {result['answer']}")
    print(f"执行统计: {result['stats']}")

asyncio.run(main())
```

### 运行示例

```bash
# 示例1: 基础ReACT
python examples/01_basic.py

# 示例2: 异步并发
python examples/02_async_concurrent.py

# 示例3: 智能缓存
python examples/03_caching.py

# 示例4: 流式响应
python examples/04_streaming.py

# 示例5: 自定义工具
python examples/05_custom_tools.py

# 🔥 示例6: GraphRAG知识图谱查询（NEW）
python examples/graphrag_query_demo.py
```

## 🔥 GraphRAG集成

FastReAct现在完全支持GraphRAG！使用真正的ReAct循环查询和推理知识图谱。

### 快速开始

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑.env，设置OPENAI_API_KEY和HIPPO_RAG_URL

# 2. 运行GraphRAG查询示例
python examples/graphrag_query_demo.py
```

### GraphRAG工具

| 工具 | 功能 | 参数 |
|------|------|------|
| `query_graph_rag` | 自然语言查询知识图谱 | query, max_results, reasoning_depth |
| `analyze_relationships` | 分析实体间关系 | entities[], relationship_types[] |
| `multi_hop_reasoning` | 多跳推理找路径 | start_entity, end_entity, max_hops |
| `knowledge_extraction` | 从文本提取知识 | text, extract_relationships |
| `check_graph_rag_config` | 检查GraphRAG配置 | 无 |

### 使用示例

```python
from fastreact.core.engine import FastReAct
from fastreact.tools import export_tools_to_fastreact

# 创建引擎
agent = FastReAct(
    api_key="your-openai-api-key",
    model="gpt-4",
)

# 注册GraphRAG工具
for tool in export_tools_to_fastreact():
    agent.register_tool(tool)

# 查询知识图谱
result = await agent.run_async(
    query="Alice和Bob有什么共同兴趣？",
    step_callback=lambda step: print(f"💭 {step['thought']}")
)

# 输出:
# 💭 我需要查询Alice的兴趣
# 👀 Alice喜欢Python、AI和音乐
# 💭 现在查询Bob的兴趣
# 👀 Bob喜欢Python、AI和游戏
# 💭 我可以分析共同兴趣了
# 🎯 Alice和Bob的共同兴趣是Python和AI
```

**完整文档**: [GraphRAG集成指南](docs/GRAPHrag_INTEGRATION.md) | [快速开始](docs/QUICKSTART.md)

## 📖 文档

- [快速入门](docs/01_getting_started.md) - 如何快速开始
- [示例代码](examples/) - 参考示例了解用法

> 注意：文档正在完善中，欢迎贡献！

## 🧪 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行性能测试
pytest tests/benchmark.py -v

# 生成覆盖率报告
pytest tests/ --cov=fastreact --cov-report=html
```

## 🔧 技术特性

### 1. 异步支持

```python
# 基于asyncio实现异步工具调用
tools = [search_tool, calculator, weather_tool]
# 可以并发执行多个工具
```

### 2. 内置缓存

```python
# 使用LRU缓存减少重复调用
react = FastReAct(tools=[...], enable_cache=True)
# 相同输入会返回缓存结果
```

### 3. 流式输出

```python
# 支持流式响应，实时返回结果
await react.run_async(
    query="分析数据",
    stream_callback=lambda chunk: print(chunk, end="")
)
```

## 🛠️ 内置工具

### FastReAct原生工具
- `SearchTool` - 搜索工具
- `CalculatorTool` - 计算器
- `WeatherTool` - 天气查询
- `HTTPTool` - HTTP请求

### GraphRAG工具（MCP格式）
- `query_graph_rag` - 自然语言查询知识图谱
- `analyze_relationships` - 分析实体间关系
- `multi_hop_reasoning` - 多跳推理找路径
- `knowledge_extraction` - 从文本提取知识
- `check_graph_rag_config` - 检查GraphRAG配置

### Python工具（MCP格式）
- `run_python_code` - 执行Python代码
- `calculate_expression` - 计算数学表达式

**总计11个工具，支持MCP格式扩展！**

你可以轻松扩展自定义工具：
- 使用`@register_mcp_tool`装饰器（MCP格式）
- 继承`Tool`基类（FastReAct原生格式）

详见示例代码和文档。

## 📁 项目结构

```
FastReAct/
├── src/
│   └── fastreact/
│       ├── core/
│       │   ├── engine.py       # 核心引擎
│       │   ├── tool.py         # 工具基类
│       │   └── cache.py        # 缓存管理
│       ├── tools/
│       │   ├── search.py       # 搜索工具
│       │   ├── calculator.py   # 计算器
│       │   └── ...
│       ├── utils/
│       │   ├── logger.py       # 日志工具
│       │   └── parser.py       # 响应解析
│       └── __init__.py
├── examples/                   # 示例代码
├── tests/                      # 测试代码
├── docs/                       # 文档
├── requirements.txt            # 依赖
├── setup.py                    # 安装配置
├── pyproject.toml             # 项目配置
└── README.md
```

## 🤝 贡献

欢迎贡献！特别是：

- 添加测试用例
- 完善文档
- 报告bug
- 提出改进建议

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 🙏 致谢

本项目从以下项目中获得灵感：
- MiroFish - ReACT实现参考
- LangChain - Agent框架设计思路
- AgentScope - 异步并发优化

## 📮 联系方式

- GitHub: https://github.com/atom32/FastReAct

---

**一个简洁的ReACT框架实现，适合学习和参考**
