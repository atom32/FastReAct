# FastReAct 项目概览

## 🎯 项目简介

FastReAct是一个轻量级的ReACT（Reasoning + Acting）框架实现，代码简洁清晰，适合学习和参考。

### 核心特性

- 📚 **学习友好** - 代码简洁，易于理解ReACT原理
- ⚡ **异步支持** - 基于asyncio，支持并发工具调用
- 💾 **内置缓存** - LRU缓存减少重复计算
- 🌊 **流式响应** - 支持流式输出
- 🛠️ **易于扩展** - 插件式工具系统

## 📁 项目结构

```
FastReAct/
├── src/
│   └── fastreact/
│       ├── core/
│       │   ├── engine.py       # 核心ReACT引擎
│       │   ├── tool.py         # 工具基类
│       │   ├── cache.py        # LRU缓存实现
│       │   └── __init__.py
│       ├── tools/
│       │   ├── calculator.py   # 计算器工具
│       │   ├── search.py       # 搜索工具
│       │   ├── weather.py      # 天气工具
│       │   ├── http.py         # HTTP工具
│       │   └── __init__.py
│       ├── utils/              # 工具函数
│       └── __init__.py
├── examples/
│   ├── 01_basic.py            # 基础示例
│   ├── 02_async_concurrent.py # 异步并发示例
│   ├── 03_custom_tools.py     # 自定义工具示例
│   ├── 04_streaming.py        # 流式响应示例
│   └── 05_caching.py          # 缓存示例
├── tests/
│   ├── test_engine.py         # 引擎测试
│   ├── test_tools.py          # 工具测试
│   └── benchmark.py           # 性能测试
├── docs/
│   ├── 01_getting_started.md  # 快速入门
│   ├── 02_advanced.md         # 高级用法
│   ├── 03_api.md              # API参考
│   ├── 04_performance.md      # 性能优化
│   └── 05_tools.md            # 工具开发
├── requirements.txt           # 依赖列表
├── setup.py                   # 安装配置
├── pyproject.toml            # 项目配置
├── LICENSE                    # MIT许可证
├── README.md                  # 项目说明
└── .gitignore
```

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/yourusername/FastReAct.git
cd FastReAct
pip install -r requirements.txt
```

### 基础使用

```python
from fastreact import FastReAct
from fastreact.tools import CalculatorTool
import asyncio

async def main():
    # 创建引擎
    react = FastReAct(
        api_key="your-api-key",
        model="gpt-4",
        tools=[CalculatorTool()],
        enable_cache=True,
    )

    # 运行
    result = await react.run_async("计算 2 + 2")
    print(result['answer'])

asyncio.run(main())
```

## 🔧 核心模块说明

### 1. engine.py - ReACT引擎

- `FastReAct`: 主引擎类
- 实现ReACT循环
- 支持异步工具调用
- LRU缓存支持
- 流式响应支持

### 2. tool.py - 工具系统

- `Tool`: 工具基类
- `ToolCall`: 工具调用对象
- `ToolResult`: 工具执行结果

### 3. cache.py - 缓存系统

- `LRUCache`: 高效LRU缓存
- O(1)时间复杂度
- 自动淘汰机制

### 4. tools/ - 内置工具集

- `CalculatorTool`: 计算器
- `SearchTool`: 搜索
- `WeatherTool`: 天气查询
- `HTTPTool`: HTTP请求

## 📖 文档

- [快速入门](docs/01_getting_started.md)
- [高级用法](docs/02_advanced.md)
- [API参考](docs/03_api.md)
- [性能优化](docs/04_performance.md)
- [工具开发](docs/05_tools.md)

## 🧪 运行示例

```bash
# 基础示例
python examples/01_basic.py

# 异步并发
python examples/02_async_concurrent.py

# 自定义工具
python examples/03_custom_tools.py
```

## 📈 性能优化建议

### 1. 启用缓存
```python
react = FastReAct(..., enable_cache=True, cache_size=2000)
```

### 2. 调整并发数
```python
react = FastReAct(..., max_concurrent_tools=5)
```

### 3. 使用异步
```python
result = await react.run_async("查询")  # 而非 react.run()
```

### 4. 启用流式响应
```python
react = FastReAct(..., enable_streaming=True)
```

## 🤝 贡献指南

欢迎贡献！特别是添加测试用例和完善文档。

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
