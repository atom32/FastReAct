# FastReAct 快速入门

## 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/FastReAct.git
cd FastReAct

# 安装依赖
pip install -r requirements.txt

# 或使用pip安装（如果已发布到PyPI）
pip install fastreact
```

## 5分钟上手

### 步骤1: 创建工具

```python
from fastreact import Tool

class MyTool(Tool):
    def _get_description(self):
        return "我的工具描述"

    def _get_parameters(self):
        return {
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "参数"}
            },
            "required": ["param"]
        }

    async def execute_async(self, param: str) -> str:
        return f"处理结果: {param}"
```

### 步骤2: 创建引擎

```python
from fastreact import FastReAct

react = FastReAct(
    api_key="your-api-key",
    base_url="https://api.openai.com/v1",
    model="gpt-4",
    tools=[MyTool()],
    enable_cache=True,
)
```

### 步骤3: 运行

```python
import asyncio

async def main():
    result = await react.run_async("帮我处理这个请求")
    print(result['answer'])

asyncio.run(main())
```

## 内置工具

FastReAct提供了几个常用的内置工具：

### 1. 计算器

```python
from fastreact.tools import CalculatorTool

react = FastReAct(
    api_key="your-key",
    tools=[CalculatorTool()],
)

result = await react.run_async("计算 2 + 2")
```

### 2. 搜索工具

```python
from fastreact.tools import SearchTool

react = FastReAct(
    api_key="your-key",
    tools=[SearchTool()],
)

result = await react.run_async("搜索AI最新进展")
```

### 3. 天气工具

```python
from fastreact.tools import WeatherTool

react = FastReAct(
    api_key="your-key",
    tools=[WeatherTool()],
)

result = await react.run_async("查询北京天气")
```

## 高级配置

### 启用流式响应

```python
react = FastReAct(
    api_key="your-key",
    tools=[...],
    enable_streaming=True,  # 启用流式
)

# 流式回调
def on_stream(chunk):
    print(chunk, end="", flush=True)

result = await react.run_async(
    "分析数据",
    stream_callback=on_stream
)
```

### 监听执行步骤

```python
def on_step(step):
    print(f"步骤 {step['iteration']}")
    if "tool_calls" in step:
        print(f"调用工具: {step['tool_calls']}")
    if "observation" in step:
        print(f"观察: {step['observation']}")

result = await react.run_async(
    "查询",
    step_callback=on_step
)
```

### 性能优化

```python
react = FastReAct(
    api_key="your-key",
    tools=[...],
    max_concurrent_tools=5,  # 并发工具数
    enable_cache=True,       # 启用缓存
    cache_size=2000,         # 缓存大小
)
```

## 运行示例

```bash
# 进入项目目录
cd FastReAct

# 运行基础示例
python examples/01_basic.py

# 运行异步并发示例
python examples/02_async_concurrent.py

# 运行自定义工具示例
python examples/03_custom_tools.py
```

## 常见问题

### Q: 如何使用兼容OpenAI格式的API？

```python
react = FastReAct(
    api_key="your-key",
    base_url="https://your-api.com/v1",  # 修改base_url
    model="your-model",
)
```

### Q: 如何查看性能统计？

```python
result = await react.run_async("查询")
stats = result['stats']
print(f"总耗时: {stats['total_time']}秒")
print(f"工具调用: {stats['tool_calls']}次")
print(f"缓存命中率: {stats['cache_hit_rate']*100}%")
```

### Q: 如何清空缓存？

```python
react.clear_cache()
```

## 下一步

- 阅读[高级用法](02_advanced.md)
- 查看[API参考](03_api.md)
- 了解[性能优化](04_performance.md)
- 学习[工具开发](05_tools.md)
