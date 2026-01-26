# FastReAct 示例说明

本目录包含FastReAct框架的使用示例。

## 📁 示例文件

### 1. `example_react_demo.py` - 完整功能演示
**用途**: 运行多个测试用例，展示ReACT循环的完整功能

**特点**:
- 使用配置文件 (`config.json`) 中的API设置
- 运行3个不同复杂度的测试
- 显示每个测试的迭代次数和性能统计
- 支持多个LLM提供商（SiliconFlow、OpenAI、Ollama等）

**运行方法**:
```bash
# 确保已配置 config.json
python example_react_demo.py
```

**适用场景**:
- 快速验证FastReAct是否正常工作
- 观察不同类型问题的推理过程
- 性能测试和基准测试

---

### 2. `example_react_debug.py` - 调试模式
**用途**: 显示ReACT循环的每一步详细信息

**特点**:
- 显示LLM的完整响应
- 显示解析到的工具调用
- 显示工具执行结果
- 适合学习和调试

**运行方法**:
```bash
python example_react_debug.py
```

**适用场景**:
- 学习ReACT循环的工作原理
- 调试工具调用问题
- 理解LLM的推理过程

---

## ⚙️ 配置说明

### ⚠️ 安全提醒

**不要提交包含真实API密钥的配置文件！**

1. 使用 `config.json.example` 作为模板
2. 真实的 `config.json` 已在 `.gitignore` 中
3. 详见 [SECURITY.md](SECURITY.md)

### 配置文件: `config.json`

复制示例配置并填入你的密钥：
```bash
cp config.json.example config.json
vim config.json
```

```json
{
  "llm": {
    "providers": {
      "siliconflow": {
        "enabled": true,
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key": "your-api-key",
        "model": "deepseek-ai/DeepSeek-V3"
      }
    },
    "default_provider": "siliconflow"
  }
}
```

### 支持的LLM提供商

1. **SiliconFlow** (默认)
   - 模型: deepseek-ai/DeepSeek-V3
   - 优势: 性价比高，中文支持好

2. **OpenAI**
   - 模型: gpt-4, gpt-3.5-turbo
   - 优势: 质量稳定，生态完善

3. **Ollama** (本地)
   - 模型: llama3.1:8b, qwen2.5:7b
   - 优势: 完全免费，数据隐私

---

## 🚀 快速开始

### 第一次运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置API密钥 (编辑 config.json)
# 或使用环境变量
set OPENAI_API_KEY=sk-your-key

# 3. 运行演示
python example_react_demo.py
```

### 切换LLM提供商

编辑 `config.json`，修改 `default_provider`：
```json
{
  "llm": {
    "default_provider": "openai"  // 或 "ollama"
  }
}
```

---

## 📊 输出示例

```
======================================================================
 📝 测试 #1: 帮我计算 (25 + 35) * 2 - 40
======================================================================

  🔄 步骤 1
  💭 Thought: 需要使用计算器工具...
  🔧 Action: CalculatorTool({'expression': '(25 + 35) * 2 - 40'})
  👀 Observation: 计算结果 = 80

  🔄 步骤 2
  💭 Thought: 已经得到结果...
  🎯 Final Answer: 结果是80

  📊 迭代: 1次 | 工具: 1次 | 耗时: 10.60秒
```

---

## 🛠️ 自定义示例

### 创建自己的测试

```python
import asyncio
from fastreact import FastReAct
from fastreact.tools import CalculatorTool
from fastreact.utils.config import get_config

async def main():
    config = get_config()
    llm_config = config.get_llm_config()

    async with FastReAct(
        api_key=llm_config["api_key"],
        base_url=llm_config["base_url"],
        model=llm_config["model"],
        tools=[CalculatorTool()],
    ) as react:
        result = await react.run_async("你的查询")
        print(result['answer'])

asyncio.run(main())
```

---

## 📖 更多资源

- **完整测试指南**: [docs/REACT_FRAMEWORK_TESTING_GUIDE.md](docs/REACT_FRAMEWORK_TESTING_GUIDE.md)
- **源码**: [src/fastreact/core/engine.py](src/fastreact/core/engine.py)
- **配置管理**: [src/fastreact/utils/config.py](src/fastreact/utils/config.py)

---

**提示**: 遇到问题？运行 `example_react_debug.py` 查看详细日志！
