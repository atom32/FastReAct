# FastReAct v2.0 - 基于 nanobot 的改造方案

## 执行摘要

基于对 nanobot 的深入分析，我们提出 FastReAct v2.0 的完整改造方案。

**核心决策**：以 nanobot 为基础，保留其 70% 的优秀设计，增强 30% 的企业特性。

**目标**：
- 代码量：<6000 行（v1.0 的 12%）
- Token 成本：降低 70%+
- 功能：保留所有企业特性
- 渠道：支持 6+ 种渠道

---

## 一、nanobot 核心分析

### 1.1 loop.py - ReAct 循环（377 行）

**关键设计**：

```python
# 核心循环（50 行实现完整 ReAct）
while iteration < max_iterations:
    # 1. 调用 LLM
    response = await provider.chat(messages, tools, model)

    # 2. 处理工具调用
    if response.has_tool_calls:
        for tool_call in response.tool_calls:
            result = await tools.execute(tool_call.name, tool_call.arguments)
            messages = add_tool_result(messages, ...)
    else:
        break  # 无工具调用，结束
```

**优势**：
- ✅ 极简 - 核心逻辑只有 50 行
- ✅ 清晰 - 单一职责，易于理解
- ✅ 可靠 - 最大迭代保护（20 次）
- ✅ 异步 - 原生 async/await

**对比 FastReAct**：
- nanobot: 377 行
- FastReAct: 3,043 行
- **差异：8x**

### 1.2 context.py - 上下文构建（235 行）

**分层加载策略**：

```python
def build_system_prompt(self):
    parts = []

    # Layer 1: 核心身份 (~200 词)
    parts.append(self._get_identity())

    # Layer 2: Bootstrap 文件 (~1000 词)
    parts.append(self._load_bootstrap_files())

    # Layer 3: Always 技能 (~3000 词)
    always_skills = self.skills.get_always_skills()
    parts.append(self.load_skills_for_context(always_skills))

    # Layer 4: Available 技能 (~500 词)
    skills_summary = self.skills.build_skills_summary()
    parts.append(skills_summary)

    return "\n\n---\n\n".join(parts)
```

**Token 节省**：
- Moltbot: ~10,000 tokens
- nanobot: ~4,700 tokens
- **节省: 53%**

### 1.3 skills.py - Skills 系统（228 行）

**三层加载系统**：

```python
# 1. 列出所有技能
def list_skills(self, filter_unavailable=True):
    # Workspace skills（优先）
    for skill_dir in self.workspace_skills.iterdir():
        ...
    # Built-in skills
    for skill_dir in self.builtin_skills.iterdir():
        ...

# 2. 加载单个技能
def load_skill(self, name: str):
    # 检查 workspace 优先
    workspace_skill = self.workspace_skills / name / "SKILL.md"
    if workspace_skill.exists():
        return workspace_skill.read_text()

    # 检查 builtin
    builtin_skill = self.builtin_skills / name / "SKILL.md"
    if builtin_skill.exists():
        return builtin_skill.read_text()

    return None

# 3. 构建摘要（XML 格式）
def build_skills_summary(self):
    lines = ["<skills>"]
    for skill in all_skills:
        available = self._check_requirements(skill)
        lines.append(f"""<skill available="{str(available).lower()}">
    <name>{name}</name>
    <description>{desc}</description>
    <location>{path}</location>
    <requires>{missing_requirements}</requires>
</skill>""")
    return "\n".join(lines)
```

**关键特性**：
- ✅ Workspace 技能优先级高于 Built-in
- ✅ 依赖自动检查（`shutil.which()`）
- ✅ XML 格式摘要（LLM 可解析）
- ✅ 按需加载（`read_file`）

---

## 二、可复用的设计模式

### 2.1 Bootstrap 文件系统 ⭐⭐⭐⭐⭐

**文件结构**：
```
~/.nanobot/
├── AGENTS.md      # Agent 角色
├── SOUL.md        # 个性特征
├── USER.md        # 用户偏好
├── TOOLS.md       # 工具指南
└── IDENTITY.md    # 身份信息
```

**优势**：
- ✅ 用户可通过 Markdown 定制
- ✅ 无需修改代码
- ✅ 版本控制友好
- ✅ 易于 A/B 测试

### 2.2 Skills 系统 ⭐⭐⭐⭐⭐

**SKILL.md 格式**：
```yaml
---
name: github
description: "Interact with GitHub using gh CLI"
dependencies: ["gh"]
always_load: false
---

# GitHub 技能

## 如何使用

### 搜索仓库
\```bash
gh search repos "language:python"
\```

## 注意事项
- 需要 `gh` CLI
- 需要 `gh auth login`
```

**优势**：
- ✅ Markdown 易于编写
- ✅ 依赖自动检查
- ✅ 按需加载（节省 Token）
- ✅ Agent 可理解

### 2.3 工具安全防护 ⭐⭐⭐⭐

```python
self.deny_patterns = [
    r"\brm\s+-[rf]{1,2}\b",     # rm -r, rm -rf
    r"\bdd\s+if=",                 # dd
    r">\s*/dev/sd",                # 写入磁盘
]
```

**优势**：
- ✅ 模式匹配黑名单
- ✅ 防止危险操作
- ✅ 用户可配置

### 2.4 记忆系统 ⭐⭐⭐⭐

```
~/.nanobot/memory/
├── MEMORY.md          # 长期记忆
└── 2025-02-09.md      # 每日笔记
```

**优势**：
- ✅ 文件系统存储
- ✅ 长期 + 临时分离
- ✅ 用户可编辑

---

## 三、需要改造的部分

### 3.1 核心 → 桥接层

**nanobot 现状**：
- 核心直接处理渠道消息
- 耦合度高

**v2.0 改造**：
```
nanobot:    核心 → 渠道
FastReAct: 核心 → MessageBus → 渠道

解耦核心和渠道
```

**实现**：
```python
# 核心（ReActCore）
async def reason(query, context):
    # 纯推理逻辑
    ...

# 桥接（MessageBus）
async def process(message):
    context = {...}
    result = await core.reason(message.content, context)
    return result

# 渠道（CLIChannel）
async def start():
    message = StandardMessage(...)
    result = await bus.process(message)
    print(result.answer)
```

### 3.2 渠道 → 统一接口

**nanobot 现状**：
- 每个渠道独立实现
- 代码重复

**v2.0 改造**：
```python
class Channel(ABC):
    @abstractmethod
    async def start(self): pass

    @abstractmethod
    async def send(self, result, recipient): pass

    @abstractmethod
    async def receive(self) -> StandardMessage: pass
```

**优势**：
- ✅ 统一接口
- ✅ 易于扩展
- ✅ 代码复用

---

## 四、实施方案

### 4.1 目录结构（基于 nanobot）

```
fastreact-v2/
├── core/                      # 核心引擎（基于 nanobot）
│   ├── __init__.py
│   ├── loop.py               # ReAct 循环（~400 行）
│   ├── context.py            # 上下文（~250 行）
│   ├── skills.py             # Skills（~250 行）
│   └── session.py            # 会话（~200 行）
│
├── bridge/                    # 桥接层（新增）
│   ├── __init__.py
│   ├── messagebus.py         # 消息总线（~150 行）
│   ├── message.py            # 标准消息（~100 行）
│   └── session.py            # 会话管理（~150 行）
│
├── channels/                 # 渠道（基于 nanobot）
│   ├── __init__.py
│   ├── base.py                # 渠道基类（~150 行）
│   ├── cli.py                 # CLI 渠道（~400 行）
│   ├── web.py                 # Web 渠道（~500 行）
│   ├── telegram.py           # IM 渠道（~500 行）
│   └── discord.py            # IM 渠道（~400 行）
│
├── tools/                     # 工具（简化）
│   ├── base.py                # 工具基类（~150 行）
│   ├── filesystem.py         # 文件操作（~400 行）
│   ├── shell.py              # Shell（~300 行）
│   └── web.py                # Web（~300 行）
│
├── providers/                 # LLM 提供商（基于 nanobot）
│   ├── __init__.py
│   ├── base.py                # 提供商基类（~150 行）
│   ├── registry.py           # 注册表（~300 行）
│   └── litellm_provider.py    # LiteLLM（~200 行）
│
├── plugins/                   # 插件（新增）
│   ├── observability/         # 可观测性（~500 行）
│   └── storage/               # 存储（~400 行）
│
├── cli/                       # CLI 工具
│   └── commands.py            # CLI 命令（~300 行）
│
└── templates/                 # 模板文件
    ├── AGENTS.md
    ├── TOOLS.md
    └── skills/               # Skills 模板
```

**预计代码量**：
- 核心：~1100 行
- 桥接：~400 行
- 渠道：~1800 行
- 工具：~1000 行
- 提供商：~650 行
- 插件：~900 行
- CLI：~300 行
- **总计：~6150 行**

### 4.2 实施步骤

**第 1 阶段：Fork 和清理（3 天）**
```bash
# 1. Fork nanobot
cd D:/FastReAct
git clone https://github.com/HKUDS/nanobot.git fastreact-v2
cd fastreact-v2

# 2. 清理不需要的文件
rm -rf nanobot/
rm -rf .github/

# 3. 初始化 git
git init
git add .
git commit -m "Initial: Forked from nanobot"
```

**第 2 阶段：添加桥接层（1 周）**
```bash
# 1. 创建 bridge/ 目录
mkdir -p bridge

# 2. 实现 MessageBus
touch bridge/messagebus.py

# 3. 实现标准消息格式
touch bridge/message.py

# 4. 实现会话管理
touch bridge/session.py
```

**第 3 阶段：重构渠道（1 周）**
- 重构 CLI 渠道
- 重构 Web 渠道
- 实现 MessageBus 集成

**第 4 阶段：添加插件（1 周）**
- 实现插件接口
- 实现可观测性插件
- 实现存储插件

**第 5 阶段：测试和发布（1 周）**
- 集成测试
- 性能测试
- 文档编写
- 发布 v2.0

---

## 五、关键设计决策

### 5.1 核心 - 采用 nanobot 的设计

**保留**：
- ✅ ReAct 循环（377 行）
- ✅ 上下文构建（235 行）
- ✅ Skills 系统（228 行）
- ✅ 记忆系统

**改造**：
- 🔄 移除渠道依赖
- 🔄 通过 MessageBus 接收消息

### 5.2 渠道 - 采用 nanobot + 统一接口

**保留**：
- ✅ CLI 渠道（复用）
- ✅ Web 渠道（复用）
- ✅ IM 渠道（复用）

**新增**：
- ➕ Channel 基类
- ➕ MessageBus 集成
- ➕ 更多渠道（Slack, Email...）

### 5.3 Skills - 完整采用

**保留**：
- ✅ SKILL.md 格式
- ✅ 渐进式加载
- ✅ 依赖检查
- ✅ XML 摘要

**新增**：
- ➕ Agent 自写技能工具
- ➕ 技能市场
- ➕ 更多官方技能

---

## 六、预期成果

### 6.1 对比表

| 维度 | FastReAct v1 | nanobot | FastReAct v2 |
|------|--------------|---------|--------------|
| **代码量** | 50,792 | 7,095 | **~6,150** |
| **核心大小** | ~30,000 | ~2,000 | **~1,100** |
| **启动时间** | ~3s | <1s | **<1s** |
| **首响延迟** | ~2s | <1s | **<1s** |
| **Token 成本** | 高 | 低 72% | **低 70%** |
| **Skills** | ❌ | ✅ | **✅** |
| **Bootstrap** | ❌ | ✅ | **✅** |
| **多渠道** | ✅ (5) | ✅ (6) | **✅ (6+)** |
| **插件** | ❌ | ❌ | **✅** |
| **可观测性** | ✅ | ⚠️ | **✅** |

### 6.2 时间估算

| 阶段 | 时间 | 产出 |
|------|------|------|
| Fork & 清理 | 3 天 | 干净的代码库 |
| 添加桥接层 | 1 周 | MessageBus、标准消息 |
| 重构渠道 | 1 周 | 统一接口 |
| 添加插件 | 1 周 | 插件系统 |
| 测试发布 | 1 周 | v2.0 正式版 |
| **总计** | **5-6 周** | **FastReAct v2.0** |

---

## 七、下一步行动

### 立即开始（本周）

1. ✅ **Fork nanobot** - 已完成
2. ⏳ **代码审查** - 深入分析核心文件
3. ⏳ **创建 POC** - MessageBus 概念验证
4. ⏳ **设计文档** - 完整设计文档

### 本周目标

- [ ] 完成 5 个核心文件的代码审查
- [ ] 创建 MessageBus POC
- [ ] 创建标准消息格式
- [ ] 验证解耦架构

### 下周目标

- [ ] 实现 MessageBus
- [ ] 重构第一个渠道（CLI）
- [ ] 测试端到端流程
- [ ] 验证 Token 节省

---

## 八、总结

**FastReAct v2.0 = nanobot 的简洁 + 企业级特性**

**核心优势**：
1. ✅ 代码精简 83%（50,792 → 6,150 行）
2. ✅ Token 成本降低 70%
3. ✅ Skills 系统（文件驱动）
4. ✅ Bootstrap 文件（用户定制）
5. ✅ 多渠道支持（6+ 种）
6. ✅ 插件系统（企业特性）

**关键创新**：
- 🎯 极简核心（<1200 行）
- 🎯 完全解耦（核心 ↔ 渠道）
- 🎯 文件驱动（Skills + Bootstrap）
- 🎯 按需加载（Token 节省）
- 🎯 易于扩展（插件 + 渠道）

**nanobot 已经证明了 Less is More！**

让我们基于它的成功，打造更好的 FastReAct！🚀

---

**准备好开始改造了吗？**
