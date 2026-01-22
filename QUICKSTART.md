# FastReAct 快速开始指南 🚀

## 项目已创建完成！

恭喜！你的独立ReACT框架项目 **FastReAct** 已经创建完成。

### 📍 项目位置

```
D:\FastReAct\
```

### 📁 项目结构

```
FastReAct/
├── src/fastreact/          # 源代码
│   ├── core/              # 核心引擎
│   │   ├── engine.py      # ReACT引擎 ⭐
│   │   ├── tool.py        # 工具基类
│   │   └── cache.py       # 缓存系统
│   └── tools/             # 内置工具
│       ├── calculator.py   # 计算器
│       ├── search.py       # 搜索
│       ├── weather.py      # 天气
│       └── http.py         # HTTP
├── examples/              # 示例代码
├── docs/                  # 文档
├── requirements.txt       # 依赖
└── README.md             # 说明
```

## 🔧 安装步骤

### 1. 安装依赖

```bash
cd D:\FastReAct
pip install -r requirements.txt
```

### 2. 设置API密钥

编辑示例文件，将 `your-api-key` 替换为你的OpenAI API密钥：

```python
react = FastReAct(
    api_key="sk-your-actual-api-key-here",  # 替换这里
    model="gpt-4",
)
```

### 3. 运行第一个示例

```bash
python examples/01_basic.py
```

## ✨ 核心特性

### 1. 轻量级
- 核心代码不到600行
- 依赖少，易于理解
- 适合学习ReACT原理

### 2. 易于使用

```python
from fastreact import FastReAct
from fastreact.tools import CalculatorTool

# 创建引擎
react = FastReAct(
    api_key="your-key",
    tools=[CalculatorTool()],
)

# 运行
result = react.run("计算 2 + 2")
print(result['answer'])
```

### 3. 自定义工具

```python
from fastreact import Tool

class MyTool(Tool):
    def _get_description(self):
        return "我的工具"

    def _get_parameters(self):
        return {"type": "object", "properties": {...}}

    async def execute_async(self, **kwargs):
        return "结果"

# 使用
react = FastReAct(tools=[MyTool()])
```

## 📚 示例代码

### 示例1: 基础使用
```bash
python examples/01_basic.py
```

### 示例2: 异步并发
```bash
python examples/02_async_concurrent.py
```

### 示例3: 自定义工具
```bash
python examples/03_custom_tools.py
```

## 🎯 下一步

### 1. 了解API
阅读 `docs/01_getting_started.md` 了解详细API

### 2. 优化建议
- 启用缓存: `enable_cache=True`
- 调整并发: `max_concurrent_tools=5`
- 使用流式: `enable_streaming=True`

### 3. 集成到项目
```python
# 将FastReAct集成到MiroFish
from fastreact import FastReAct

react = FastReAct(
    api_key=Config.LLM_API_KEY,
    base_url=Config.LLM_BASE_URL,
    model=Config.LLM_MODEL_NAME,
    tools=[...],
)

# 替换原有的report_agent.py
result = await react.run_async(query)
```

## 🔗 相关链接

- [完整文档](docs/01_getting_started.md)
- [项目概览](PROJECT_OVERVIEW.md)
- [GitHub Repository](https://github.com/atom32/FastReAct)

## 💡 常见问题

**Q: 如何使用兼容OpenAI的API？**
```python
react = FastReAct(
    base_url="https://your-api.com/v1",
    model="your-model",
)
```

**Q: 如何查看性能统计？**
```python
stats = result['stats']
print(f"耗时: {stats['total_time']}秒")
print(f"缓存命中率: {stats['cache_hit_rate']*100}%")
```

**Q: 如何清空缓存？**
```python
react.clear_cache()
```

---

**开始学习ReACT框架的实现吧！** 🎉
