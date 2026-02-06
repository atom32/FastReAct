# ReACT框架完整测试指南

> 本指南将带你从零开始，逐步测试和理解FastReAct是如何实现ReACT框架的。

---

## 📋 测试路线图

```
第1层: 核心组件测试（理解基础）
  ↓
第2层: ReACT循环观察（单工具）
  ↓
第3层: 多工具协同（复杂推理）
  ↓
第4层: 异步并发（性能测试）
  ↓
第5层: 高级功能（缓存、流式）
```

---

## 🔧 第0步：环境准备

### 1. 安装依赖
```bash
cd D:\FastReAct
pip install -r requirements.txt
```

### 2. 设置API密钥
```bash
# 创建.env文件
cat > .env << EOF
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
EOF
```

### 3. 验证安装
```bash
python -c "from fastreact import FastReAct; print('✅ 安装成功')"
```

---

## 🧪 第1层：核心组件测试

### 目标：理解ReACT的基础构建块

### 测试1.1：工具系统（Tool基类）
```bash
# 运行工具基础测试
pytest tests/test_tool.py -v -s
```

**观察要点**：
- ✅ 工具如何注册和调用
- ✅ 参数验证（JSON Schema）
- ✅ 异步执行机制

**代码位置**：`src/fastreact/core/tool.py`

### 测试1.2：缓存系统（LRU Cache）
```bash
# 运行缓存测试
pytest tests/test_cache.py -v -s
```

**观察要点**：
- ✅ 缓存命中/未命中
- ✅ LRU淘汰策略
- ✅ 缓存大小限制

**代码位置**：`src/fastreact/core/cache.py`

### 测试1.3：日志系统
```bash
# 运行日志测试
pytest tests/test_logger.py -v -s
```

**观察要点**：
- ✅ 日志格式化
- ✅ 文件输出
- ✅ 日志级别控制

**代码位置**：`src/fastreact/utils/logger.py`

---

## 🔄 第2层：ReACT循环观察（单工具）

### 目标：观察完整的Thought-Action-Observation循环

### 测试2.1：最简单的ReACT循环
创建文件 `test_simple_react.py`：

```python
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastreact import FastReAct
from fastreact.tools import CalculatorTool

async def main():
    print("=" * 70)
    print("测试：观察ReACT循环")
    print("=" * 70)

    # 创建引擎（只用计算器工具）
    async with FastReAct(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4",
        tools=[CalculatorTool()],
        enable_cache=True,
        max_iterations=5,
    ) as react:

        # 定义详细的回调函数
        def debug_callback(step):
            print("\n" + "=" * 70)
            print(f"📍 迭代 #{step['iteration'] + 1}")
            print("=" * 70)

            # 1. Thought（LLM的思考）
            if 'thought' in step:
                print(f"💭 Thought:")
                print(f"   {step['thought']}")

            # 2. Action（调用工具）
            if 'tool_calls' in step:
                print(f"\n🔧 Action:")
                for tc in step['tool_calls']:
                    print(f"   工具: {tc['name']}")
                    print(f"   参数: {tc['parameters']}")

            # 3. Observation（工具返回结果）
            if 'observation' in step:
                print(f"\n👀 Observation:")
                print(f"   {step['observation']}")

            # 4. Final Answer（最终答案）
            if step.get('is_final'):
                print(f"\n🎯 Final Answer:")
                print(f"   {step['answer']}")

        # 运行一个简单的数学问题
        result = await react.run_async(
            query="帮我计算 (25 + 35) * 2 - 40",
            step_callback=debug_callback
        )

        # 显示统计
        print("\n" + "=" * 70)
        print("📊 执行统计")
        print("=" * 70)
        stats = result['stats']
        print(f"总迭代次数: {stats['total_calls']}")
        print(f"工具调用次数: {stats['tool_calls']}")
        print(f"缓存命中: {stats['cache_hits']}")
        print(f"缓存未命中: {stats['cache_misses']}")
        print(f"总耗时: {stats['total_time']:.2f}秒")

if __name__ == "__main__":
    asyncio.run(main())
```

运行：
```bash
python test_simple_react.py
```

**观察要点**：
- ✅ Thought（LLM如何分析问题）
- ✅ Action（如何选择工具和参数）
- ✅ Observation（工具返回什么）
- ✅ 循环次数（需要几次才得到答案）

---

## 🤖 第3层：多工具协同

### 目标：测试LLM如何在多个工具间选择和组合

### 测试3.1：工具选择测试
创建文件 `test_multi_tool.py`：

```python
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastreact import FastReAct
from fastreact.tools import (
    CalculatorTool,
    SearchTool,
    WeatherTool,
)

async def main():
    print("=" * 70)
    print("测试：多工具协同")
    print("=" * 70)

    # 注册多个工具
    tools = [
        CalculatorTool(),  # 计算
        SearchTool(),      # 搜索
        WeatherTool(),     # 天气
    ]

    async with FastReAct(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4",
        tools=tools,
        enable_cache=True,
        max_iterations=10,
    ) as react:

        # 测试用例：需要组合多个工具
        query = """
        请帮我完成以下任务：
        1. 搜索今天的天气
        2. 计算 25 * 4 + 100
        3. 总结结果
        """

        print(f"📝 查询: {query}\n")

        def step_callback(step):
            if not step.get('is_final'):
                print(f"\n🔄 步骤 {step['iteration'] + 1}")
                print(f"💭 {step.get('thought', '')[:100]}...")

                if 'tool_calls' in step:
                    for tc in step['tool_calls']:
                        print(f"   🔧 使用工具: {tc['name']}")
                        print(f"   📋 参数: {tc['parameters']}")

                if 'observation' in step:
                    print(f"   👀 结果: {step['observation'][:80]}...")

        result = await react.run_async(
            query=query,
            step_callback=step_callback
        )

        print(f"\n✅ 最终答案: {result['answer']}")

        # 显示每个工具的使用情况
        print("\n📊 工具使用统计:")
        stats = result['stats']
        print(f"  总工具调用: {stats['tool_calls']}")

if __name__ == "__main__":
    asyncio.run(main())
```

**观察要点**：
- ✅ LLM如何选择正确的工具
- ✅ 工具调用顺序
- ✅ 多个工具如何协同工作

---

## ⚡ 第4层：异步并发

### 目标：测试并发工具调用的性能优势

### 测试4.1：并发vs串行对比
创建文件 `test_concurrent.py`：

```python
import asyncio
import sys
import os
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastreact import FastReAct
from fastreact.tools import CalculatorTool

async def main():
    print("=" * 70)
    print("测试：异步并发性能")
    print("=" * 70)

    # 测试用例：多个独立计算
    query = """
    请帮我计算以下5个独立的表达式：
    1. 123 + 456
    2. 789 - 234
    3. 56 * 78
    4. 9012 / 34
    5. 2 ** 10
    """

    # 测试不同并发数
    for max_concurrent in [1, 3, 5]:
        print(f"\n{'=' * 70}")
        print(f"测试并发数: {max_concurrent}")
        print('=' * 70)

        async with FastReAct(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4",
            tools=[CalculatorTool()],
            enable_cache=False,  # 关闭缓存以测试真实性能
            max_concurrent_tools=max_concurrent,
        ) as react:

            start = time.time()
            result = await react.run_async(query=query)
            elapsed = time.time() - start

            stats = result['stats']
            print(f"\n⏱️ 总耗时: {elapsed:.2f}秒")
            print(f"🔧 工具调用: {stats['tool_calls']}次")
            print(f"📞 LLM调用: {stats['total_calls']}次")

if __name__ == "__main__":
    asyncio.run(main())
```

**观察要点**：
- ✅ 并发数1 vs 3 vs 5的性能差异
- ✅ 工具调用是否真正并发执行

---

## 💾 第5层：高级功能

### 测试5.1：缓存效果
创建文件 `test_cache_effect.py`：

```python
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastreact import FastReAct
from fastreact.tools import CalculatorTool

async def main():
    print("=" * 70)
    print("测试：缓存效果")
    print("=" * 70)

    async with FastReAct(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4",
        tools=[CalculatorTool()],
        enable_cache=True,
        cache_size=100,
    ) as react:

        # 第一次运行（无缓存）
        print("\n🔄 第一次运行（无缓存）")
        result1 = await react.run_async(query="计算 123 + 456")
        stats1 = result1['stats']

        # 第二次运行（有缓存）
        print("\n🔄 第二次运行（有缓存）")
        result2 = await react.run_async(query="计算 123 + 456")
        stats2 = result2['stats']

        # 对比
        print("\n" + "=" * 70)
        print("📊 对比结果")
        print("=" * 70)
        print(f"\n第一次:")
        print(f"  耗时: {stats1['total_time']:.2f}秒")
        print(f"  缓存命中: {stats1['cache_hits']}")
        print(f"  缓存未命中: {stats1['cache_misses']}")

        print(f"\n第二次:")
        print(f"  耗时: {stats2['total_time']:.2f}秒")
        print(f"  缓存命中: {stats2['cache_hits']}")
        print(f"  缓存未命中: {stats2['cache_misses']}")

        if stats2['total_time'] < stats1['total_time']:
            speedup = (stats1['total_time'] / stats2['total_time'] - 1) * 100
            print(f"\n✅ 缓存加速: {speedup:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())
```

**观察要点**：
- ✅ 缓存是否生效
- ✅ 性能提升幅度

### 测试5.2：流式响应
创建文件 `test_streaming.py`：

```python
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from fastreact import FastReAct
from fastreact.tools import CalculatorTool

async def main():
    print("=" * 70)
    print("测试：流式响应")
    print("=" * 70)

    async with FastReAct(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4",
        tools=[CalculatorTool()],
        enable_streaming=True,  # 启用流式
    ) as react:

        print("\n📝 查询: 解释什么是斐波那契数列\n")
        print("🌊 流式输出:\n")

        result = await react.run_async(
            query="解释什么是斐波那契数列，并计算前10项",
            stream_callback=lambda chunk: print(chunk, end="", flush=True)
        )

        print(f"\n\n✅ 完成！总token: {result['stats'].get('total_tokens', 0)}")

if __name__ == "__main__":
    asyncio.run(main())
```

**观察要点**：
- ✅ 文本逐字输出
- ✅ 实时响应体验

---

## 📊 测试总结清单

完成所有测试后，你应该理解：

- ✅ [ ] **工具系统** - 如何注册、调用工具
- ✅ [ ] **ReACT循环** - Thought-Action-Observation完整流程
- ✅ [ ] **工具选择** - LLM如何选择合适的工具
- ✅ [ ] **异步并发** - 并发执行的性能优势
- ✅ [ ] **缓存机制** - LRU缓存的工作原理
- ✅ [ ] **流式响应** - 实时输出的实现
- ✅ [ ] **资源管理** - 上下文管理器的自动清理

---

## 🎯 进阶测试

### 测试：GraphRAG集成
```bash
python examples/graphrag_query_demo.py
```

### 测试：MCP客户端
```bash
python examples/mcp_client_example.py
```

### 测试：所有单元测试
```bash
pytest tests/ -v --cov=fastreact --cov-report=html
```

---

## 📖 阅读代码顺序

如果你想深入理解实现，建议按以下顺序阅读：

1. **工具基础** (`src/fastreact/core/tool.py`) - 140行
2. **缓存系统** (`src/fastreact/core/cache.py`) - 80行
3. **核心引擎** (`src/fastreact/core/engine.py`) - 400行
4. **响应解析** (`src/fastreact/utils/parser.py`) - 150行
5. **GraphRAG工具** (`src/fastreact/tools/graph_rag_tools.py`) - 200行
6. **MCP客户端** (`src/fastreact/tools/mcp_client_manager.py`) - 650行

**总计核心代码: ~1620行**

---

## 💡 常见问题

**Q: 测试失败怎么办？**
A: 检查API密钥是否正确，网络是否通畅

**Q: 如何查看详细日志？**
A: 设置环境变量 `LOG_LEVEL=DEBUG`

**Q: 缓存什么时候会失效？**
A: 缓存达到max_size时会自动淘汰最久未使用的项

---

**测试愉快！🚀**
