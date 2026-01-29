# Bootstrap 配置系统使用指南

> **版本**: v0.3.0+
> **更新**: 2026-01-29

---

## 📚 什么是 Bootstrap 配置系统？

Bootstrap 配置系统允许你通过配置文件**自定义 Agent 行为**，无需修改任何代码。

### 核心优势

- ✅ **无需编程** - 通过文本文件配置 Agent
- ✅ **灵活定制** - 定义人格、操作规则、工具使用方式
- ✅ **即时生效** - 修改配置文件后立即生效
- ✅ **工作区隔离** - 不同项目使用不同配置
- ✅ **版本控制** - 配置文件可以纳入 Git 管理

---

## 🚀 快速开始

### 1. 初始化工作区

```bash
# 方式 1：使用 Python 代码
from fastreact.bootstrap import init_workspace

manager = init_workspace()

# 方式 2：使用 CLI（即将推出）
fastreact init
```

这会在 `~/.fastreact/` 创建以下文件：

```
~/.fastreact/
├── AGENTS.md       # Agent 操作指令
├── SOUL.md         # 人格和边界
├── TOOLS.md        # 工具使用指南
├── WORKSPACE.md    # 工作区配置
└── config.json     # 技术配置
```

### 2. 使用 Bootstrap 配置

```python
from fastreact import FastReAct

# Bootstrap 自动启用（默认）
agent = FastReAct(
    api_key="your-api-key",
    model="gpt-4",
    # enable_bootstrap=True,  # 默认启用
    # workspace="~/.fastreact"  # 默认工作区
)

# 运行 Agent
result = await agent.run_async("帮我搜索最新的 AI 新闻")
print(result['answer'])
```

---

## 📝 配置文件详解

### AGENTS.md - Agent 操作指令

定义 Agent 的工作流程和核心原则。

**示例**：

```markdown
# Agent 操作指令

## 核心原则

1. **准确性优先** - 确保所有信息准确无误
2. **工具使用** - 积极使用可用工具获取信息
3. **逐步推理** - 清晰展示思考过程

## 工作流程

1. 理解用户需求
2. 分析需要什么信息
3. 选择合适的工具
4. 执行并分析结果
5. 综合给出答案

## 禁止行为

- 不得编造信息
- 不得忽略工具结果
- 不得跳过推理步骤
```

**影响**：
- Agent 如何思考和推理
- 如何使用工具
- 什么是可以/不可以做的

---

### SOUL.md - Agent 人格定义

定义 Agent 的性格、语气和行为边界。

**示例**：

```markdown
# Agent 人格定义

你是一个**友好、专业的 AI 助手**。

## 特点

- **专业**：在专业领域表现出深度知识
- **友好**：使用温暖、亲切的语言
- **耐心**：详细解释复杂概念
- **诚实**：不确定时明确说明

## 语气

- 清晰简洁
- 避免过于技术化
- 适当使用例子
- 保持积极态度

## 边界

- 不涉及政治、宗教等敏感话题
- 不提供可能造成伤害的建议
- 尊重用户隐私
```

**影响**：
- Agent 的"性格"
- 回答的语气和风格
- 行为边界和道德标准

---

### TOOLS.md - 工具使用指南

提供如何有效使用可用工具的指导。

**示例**：

```markdown
# 工具使用指南

## 通用原则

1. **优先使用工具** - 不要仅依靠训练数据
2. **并行调用** - 独立的工具可以并行调用
3. **参数准确** - 确保工具参数正确

## 可用工具

### 搜索工具 (search)
- **用途**：搜索网络信息
- **何时使用**：需要最新信息或特定事实

### 计算器 (calculator)
- **用途**：执行数学计算
- **何时使用**：需要精确计算结果
```

**影响**：
- Agent 如何选择工具
- 工具使用最佳实践
- 何时使用哪个工具

---

### WORKSPACE.md - 工作区配置

定义项目特定的上下文信息。

**示例**：

```markdown
# 工作区配置

## 项目背景

本项目是一个 Python Web 应用，使用 FastAPI 框架。

## 技术栈

- 后端：FastAPI + Pydantic
- 前端：React + TypeScript
- 数据库：PostgreSQL

## 编码规范

- 遵循 PEP 8
- 使用类型提示
- 编写单元测试
```

**影响**：
- Agent 了解项目上下文
- 提供领域特定知识
- 统一团队规范

---

## 🔧 高级用法

### 自定义工作区

```python
agent = FastReAct(
    api_key="your-api-key",
    workspace="./my-custom-workspace"  # 自定义工作区路径
)
```

### 禁用 Bootstrap

```python
agent = FastReAct(
    api_key="your-api-key",
    enable_bootstrap=False  # 禁用 Bootstrap
)
```

### 编程方式管理配置

```python
from fastreact.bootstrap import BootstrapLoader, WorkspaceManager

# 创建工作区
manager = WorkspaceManager("./my-workspace")
manager.create_workspace()

# 读取配置
loader = BootstrapLoader("./my-workspace")
files = loader.load()

# 获取单个文件
agents_content = loader.get_file("agents")

# 写入文件
manager.write_file("AGENTS.md", "# Custom Rules")

# 重新加载
loader.reload()
```

---

## 📂 工作区组织

### 单一工作区（默认）

```
~/.fastreact/
├── AGENTS.md
├── SOUL.md
├── TOOLS.md
└── config.json
```

**适用场景**：
- 个人使用
- 统一配置
- 快速开始

### 项目级工作区

```
project-a/
├── .fastreact/
│   ├── AGENTS.md      # 项目特定的 Agent 配置
│   ├── SOUL.md
│   └── TOOLS.md
├── src/
└── tests/
```

**适用场景**：
- 团队协作
- 项目特定配置
- 纳入版本控制

```python
agent = FastReAct(
    api_key="your-api-key",
    workspace="./.fastreact"  # 项目级工作区
)
```

### 多环境配置

```
project/
├── .fastreact.dev/
├── .fastreact.staging/
└── .fastreact.prod/
```

```python
import os

env = os.getenv("ENVIRONMENT", "dev")
workspace = f"./.fastreact.{env}"

agent = FastReAct(
    api_key="your-api-key",
    workspace=workspace
)
```

---

## 🎨 实际案例

### 案例 1：专业编程助手

**SOUL.md**:

```markdown
# 编程助手人格

你是一位**资深软件工程师**，精通 Python、JavaScript、Go。

## 专长

- 系统架构设计
- 性能优化
- 代码审查
- 技术选型

## 代码风格

- 优先考虑可读性和可维护性
- 遵循 SOLID 原则
- 编写自文档化的代码
- 适当的错误处理

## 回答风格

- 提供可运行的代码示例
- 解释为什么这样做
- 指出潜在问题和改进建议
```

### 案例 2：创意写作助手

**AGENTS.md**:

```markdown
# 创作流程

1. **理解主题** - 明确创作的核心主题和目标
2. **构思大纲** - 构建内容框架和逻辑
3. **丰富细节** - 添加生动的细节和例子
4. **语言润色** - 优化表达，增加感染力

## 创作原则

- 保持原创性
- 注重情感共鸣
- 使用生动的语言
- 结构清晰连贯

## 避免模式

- 陈词滥调
- 过度修饰
- 逻辑混乱
```

### 案例 3：数据分析专家

**TOOLS.md**:

```markdown
# 数据分析工具指南

## 工具优先级

1. **Python 代码执行** - 优先用于数据处理
2. **计算器** - 用于快速统计计算
3. **搜索** - 查找数据背景信息

## 分析流程

1. 数据探索 → 使用 Python 查看数据
2. 数据清洗 → 处理缺失值和异常
3. 数据分析 → 统计分析和可视化
4. 结果解释 → 清晰解释发现

## 输出格式

- 使用 Markdown 表格
- 包含代码示例
- 解释关键发现
```

---

## 🔄 热重载（即将推出）

```python
agent = FastReAct(
    api_key="your-api-key",
    enable_bootstrap=True,
    auto_reload=True  # 自动重新加载配置文件
)
```

---

## 🧪 测试和调试

### 查看注入后的系统提示

```python
from fastreact.bootstrap import BootstrapLoader

loader = BootstrapLoader()
prompt = loader.build_system_prompt("You are helpful")

print(prompt)
```

### 验证配置文件

```python
loader = BootstrapLoader()

# 检查文件是否存在
print(loader.has_file("agents"))  # True/False

# 检查工作区是否已初始化
print(loader.is_workspace_initialized())  # True/False

# 列出工作区文件
print(loader.workspace)
```

---

## 🐛 常见问题

### Q: Bootstrap 配置不生效？

**A**: 检查以下几点：
1. `enable_bootstrap=True`（默认启用）
2. 工作区路径正确
3. 文件名正确（AGENTS.md 而非 agent.md）
4. 文件编码为 UTF-8

### Q: 如何覆盖默认配置？

**A**: 使用 `inject_position` 参数：

```python
# Bootstrap 内容在基础提示之后（默认）
loader.build_system_prompt(base, inject_position="after")

# Bootstrap 内容在基础提示之前
loader.build_system_prompt(base, inject_position="before")

# Bootstrap 内容完全替换基础提示
loader.build_system_prompt(base, inject_position="replace")
```

### Q: 可以使用多个工作区吗？

**A**: 可以，为不同的 Agent 实例指定不同的工作区：

```python
agent1 = FastReAct(api_key="...", workspace="./workspace-1")
agent2 = FastReAct(api_key="...", workspace="./workspace-2")
```

---

## 📚 更多资源

- **示例代码**: `examples/example_bootstrap.py`
- **单元测试**: `tests/test_bootstrap.py`
- **源代码**: `src/fastreact/bootstrap/`

---

## 🎯 最佳实践

1. **版本控制** - 将配置文件纳入 Git
2. **文档化** - 在配置文件中添加注释
3. **渐进式** - 从简单配置开始，逐步完善
4. **测试** - 验证配置对 Agent 行为的影响
5. **分离** - 不同环境使用不同配置

---

**准备好自定义你的 Agent 了吗？开始配置吧！**
