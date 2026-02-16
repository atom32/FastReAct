# FastReAct Nano v2.0 - 测试与使用指南

## 第一步：环境准备

### 1.1 检查Python版本

```bash
python --version
# 需要 Python 3.10 或更高
```

### 1.2 设置API Key

```bash
# 方式1: 环境变量 (推荐)
export FASTRACT_API_KEY=sk-your-api-key-here
export FASTRACT_MODEL=gpt-4o-mini

# 方式2: 保存到文件
echo "export FASTRACT_API_KEY=sk-xxx" >> ~/.bashrc
source ~/.bashrc
```

**如果没有API Key**，可以使用本地模型：

```bash
# 使用Ollama本地模型
export FASTRACT_MODEL=ollama/llama3
export FASTRACT_API_BASE=http://localhost:11434
```

---

## 第二步：安装

### 2.1 克隆项目

```bash
cd /path/to/your/workspace
git clone <repository-url> fastreact-nano
cd fastreact-nano
```

### 2.2 安装核心

```bash
# 最小安装 (仅内核)
pip install -e .

# 或者安装完整功能
pip install -e ".[all]"
```

**安装说明**:
- `-e` 表示开发模式安装
- `.[all]` 包含所有适配器 + 开发工具
- 如果只需要核心: `pip install -e .`

### 2.3 验证安装

```bash
python -c "from fastreact import Agent; print('[OK] Installation successful!')"
```

---

## 第三步：运行测试

### 3.1 运行所有测试

```bash
# 运行完整测试套件
pytest tests/ -v
```

**预期输出**:
```
tests/unit/test_tools.py::TestTool::test_echo_tool PASSED
tests/unit/test_tools.py::TestTool::test_add_tool PASSED
...
======================== 64 passed in 0.XX s ========================
```

### 3.2 运行特定测试

```bash
# 测试核心功能
pytest tests/unit/test_v2_messages.py -v

# 测试工具
pytest tests/unit/test_tools.py -v

# 测试Skills
pytest tests/unit/test_skills.py -v

# 测试配置
pytest tests/unit/test_config.py -v

# 测试流式输出
pytest tests/unit/test_streaming.py -v
```

### 3.3 测试覆盖率

```bash
# 生成覆盖率报告
pytest --cov=fastreact --cov-report=html

# 查看报告
# Windows: start htmlcov/index.html
# Mac/Linux: open htmlcov/index.html
```

---

## 第四步：基础使用测试

### 4.1 Python API测试

创建测试文件 `test_usage.py`:

```python
"""测试FastReAct Nano基础使用"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastreact import ask_sync, Agent

# 测试1: 最简单的使用
def test_sync_query():
    """测试同步查询"""
    print("\n=== 测试1: 同步查询 ===")

    response = ask_sync("What is 2+2?")
    print(f"[Response] {response}")
    print("[OK] 同步查询测试通过\n")


# 测试2: Agent基础使用
async def test_agent_basic():
    """测试Agent基础使用"""
    print("=== 测试2: Agent基础使用 ===")

    agent = Agent()

    # 列出可用工具
    tools = agent.list_tools()
    print(f"[INFO] 可用工具: {tools}")

    # 列出可用skills
    skills = agent.list_skills()
    print(f"[INFO] 可用skills: {skills}")

    print("[OK] Agent基础测试通过\n")


# 测试3: 使用Skills
async def test_with_skills():
    """测试使用Skills"""
    print("=== 测试3: 使用Skills ===")

    agent = Agent()

    response = await agent.run(
        "如何创建git分支？",
        skills=["git_workflow"]
    )

    print(f"[Response] {response[:200]}...")
    print("[OK] Skills测试通过\n")


# 运行所有测试
async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("  FastReAct Nano - 使用测试")
    print("=" * 60)

    try:
        # 测试1: 同步查询
        test_sync_query()

        # 测试2: Agent基础
        await test_agent_basic()

        # 测试3: Skills
        await test_with_skills()

        print("=" * 60)
        print("  [SUCCESS] 所有测试通过!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
```

**运行测试**:

```bash
python test_usage.py
```

---

## 第五步：CLI使用测试

### 5.1 安装CLI适配器

```bash
pip install -e ".[cli]"
```

### 5.2 测试CLI命令

```bash
# 查看版本
fastreact version

# 列出工具
fastreact tools

# 列出skills
fastreact skills

# 执行查询
fastreact "What is 2+2?"

# 使用skill
fastreact "如何创建git分支？" --skill git_workflow

# 指定模型
fastreact "分析这个文件" --model gpt-4o
```

### 5.3 测试交互模式

```bash
fastreact interactive
```

在交互模式中：
```
>>> 分析这个代码库
[Agent响应...]
>>> 使用git_workflow创建分支
[Agent响应...]
>>> quit
```

---

## 第六步：HTTP API测试

### 6.1 安装HTTP适配器

```bash
pip install -e ".[http]"
```

### 6.2 启动HTTP服务

```bash
# 方式1: 使用python -m
python -m fastreact.adapters.http

# 方式2: 使用uvicorn
uvicorn fastreact.adapters.http:create_app
```

**预期输出**:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 6.3 测试API端点

**新开一个终端窗口**:

```bash
# 健康检查
curl http://localhost:8000/health

# 列出skills
curl http://localhost:8000/skills

# 列出tools
curl http://localhost:8000/tools

# 运行查询
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"query": "What is FastReAct Nano?"}'
```

### 6.4 使用Python客户端

```bash
# 运行HTTP客户端示例
python examples/http_client.py
```

---

## 第七步：Gateway测试

### 7.1 安装Gateway适配器

```bash
pip install -e ".[gateway]"
```

### 7.2 启动Gateway服务

```bash
python -m fastreact.adapters.gateway
```

**预期输出**:
```
INFO:     Started server process [xxxxx]
INFO:     Uvicorn running on http://0.0.0.0:9000
```

### 7.3 访问Web界面

1. 打开浏览器
2. 访问 `http://localhost:9000`
3. 在输入框中输入问题
4. 点击"发送"

### 7.4 测试WebSocket客户端

```bash
# 运行Gateway客户端示例
python examples/gateway_client.py
```

---

## 第八步：实际使用场景

### 场景1: 代码分析

```bash
# CLI方式
fastreact "分析src/fastreact目录的代码结构" --skill file_ops
```

```python
# Python API方式
from fastreact import ask_sync

response = ask_sync(
    "分析src/fastreact目录的代码结构",
    skills=["file_ops"]
)
print(response)
```

### 场景2: Git操作

```bash
fastreact "创建新分支feature-nano并切换" --skill git_workflow
```

### 场景3: 代码审查

```bash
fastreact "审查src/fastreact/core/react.py的代码质量" --skill code_review
```

### 场景4: 批量文件操作

```python
import asyncio
from fastreact import Agent

async def batch_operations():
    agent = Agent()

    # 读取多个文件
    files = ["README.md", "USAGE.md", "SUMMARY.md"]

    for file in files:
        response = await agent.run(
            f"读取{file}并总结内容",
            skills=["file_ops"]
        )
        print(f"\n=== {file} ===\n{response}\n")

asyncio.run(batch_operations())
```

---

## 第九步：配置自定义

### 9.1 创建配置文件

创建 `config.json`:

```json
{
  "llm": {
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "react": {
    "max_iterations": 30,
    "enable_steering": true,
    "enable_followup": true
  },
  "tools": {
    "max_file_size": 2097152,
    "exec_timeout": 60
  }
}
```

### 9.2 使用配置

```python
from fastreact import Config, Agent

config = Config.from_env()  # 从环境变量
# 或
config = Config.load(Path("config.json"))  # 从文件

agent = Agent(config=config)
```

---

## 第十步：自定义Skill

### 10.1 创建Skill

创建 `skills/my_skill/SKILL.md`:

```markdown
---
name: my_skill
description: 我自定义的技能
version: 1.0.0
---

# My Skill

## When to Use
- 使用场景1
- 使用场景2

## How it Works
1. 步骤1
2. 步骤2

## Instructions
具体的使用说明和注意事项
```

### 10.2 使用自定义Skill

```bash
fastreact "使用我的技能" --skill my_skill
```

---

## 故障排除

### 问题1: ImportError

```bash
# 错误: ModuleNotFoundError: No module named 'fastreact'
# 解决: 确保从项目根目录安装
cd fastreact-nano
pip install -e .
```

### 问题2: CLI命令不可用

```bash
# 错误: bash: fastreact: command not found
# 解决: 安装CLI适配器
pip install -e ".[cli]"
```

### 问题3: API Key错误

```bash
# 错误: API Error: No API key provided
# 解决: 设置环境变量
export FASTRACT_API_KEY=sk-xxx

# 或在代码中设置
import os
os.environ["FASTRACT_API_KEY"] = "sk-xxx"
```

### 问题4: 端口占用

```bash
# 错误: [Errno 48] Address already in use
# 解决: 更改端口或终止占用进程

# 查找占用端口的进程
# Mac/Linux
lsof -i :8000

# 杀死进程
kill -9 <PID>
```

---

## 性能测试

### 测试1: 启动速度

```bash
time python -c "from fastreact import Agent; Agent()"
```

预期: < 1秒

### 测试2: 响应速度

```bash
time fastreact "What is 2+2?"
```

预期: < 10秒 (取决于LLM响应时间)

---

## 下一步

1. **创建自己的Skill**: 参考 `skills/` 目录中的示例
2. **集成到项目**: 作为库嵌入你的应用
3. **部署服务**: 使用Docker或Systemd部署
4. **性能优化**: 使用本地模型、调整迭代次数

---

## 获取帮助

- 文档: [USAGE.md](USAGE.md)
- 项目状态: [PROJECT_STATUS.md](PROJECT_STATUS.md)
- 总结: [SUMMARY.md](SUMMARY.md)
- Issues: https://github.com/atom32/FastReAct/issues

---

**开始使用FastReAct Nano吧！** 🚀
