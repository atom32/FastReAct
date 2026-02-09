# Skills 系统：AI Agent 的"职业技能树"

## 核心观点

> **Skills 不是插件，是 AI Agent 的"职业技能树"**
>
> - 用 Markdown 写操作指南
> - 按需注入给大模型
> - Agent 可以自己写新技能
> - **这个模式以后一定是标配**

---

## 一、为什么 Skills 比插件更优？

### 1.1 对比分析

| 维度 | 插件系统 | Skills 系统 | 优势 |
|------|---------|------------|------|
| **实现方式** | Python 代码 | Markdown 文件 | **Skills** |
| **开发门槛** | 需要编程 | 会写文档即可 | **Skills** |
| **热更新** | 需要重启 | 文件修改即生效 | **Skills** |
| **版本控制** | 难（二进制） | 易（Git 友好） | **Skills** |
| **调试难度** | 需要调试器 | 直接读文档 | **Skills** |
| **可读性** | 需要读代码 | 自然语言 | **Skills** |
| **AI 理解** | 无法理解 | 完全理解 | **Skills** |
| **自修改** | 无法做到 | Agent 可修改 | **Skills** |
| **分发** | 需要安装包 | 复制文件即可 | **Skills** |
| **Token 成本** | 高（代码描述） | 低（自然语言） | **Skills** |

### 1.2 核心差异

**插件 = 代码扩展**
- ❌ 需要编程知识
- ❌ 需要理解代码库
- ❌ 需要编译/重启
- ❌ AI 无法理解或修改
- ❌ 分发困难

**Skills = 知识扩展**
- ✅ 只需写 Markdown
- ✅ 自然语言描述
- ✅ 文件修改即生效
- ✅ AI 完全理解
- ✅ AI 可以修改和创建
- ✅ 复制文件即可分发

---

## 二、nanobot 的 Skills 设计

### 2.1 文件结构

```
~/.nanobot/skills/
├── web_search/
│   └── SKILL.md
├── weather/
│   └── SKILL.md
├── code_analysis/
│   └── SKILL.md
└── data_processing/
    └── SKILL.md
```

### 2.2 SKILL.md 格式

**YAML Frontmatter + Markdown**：

```yaml
---
name: web_search
description: Search the web using Brave Search API
version: 1.0
dependencies: []
always_load: true
---

# Web Search Skill

Search the web for information using Brave Search API.

## Usage

The agent will automatically use this skill when you ask to search the web.

**Example queries**:
- "Search for the latest Python 3.12 features"
- "Find information about Rust vs Go performance"
- "What's the weather like in Tokyo?"

## How it Works

1. Parse the search query from user request
2. Call Brave Search API with the query
3. Return top 10 results with snippets and URLs
4. User can ask to fetch specific pages for more details

## Notes

- Returns top 10 results by default
- Includes snippets for quick preview
- Requires `BRAVE_API_KEY` environment variable
- To get an API key: https://brave.com/search/api

## Examples

### Example 1: Basic Search

**User**: "Search for Python 3.12 new features"

**Agent Action**:
```python
search(query="Python 3.12 new features")
```

**Result**: Top 10 results with snippets and URLs

### Example 2: Specific Site Search

**User**: "Search in docs.python.org for async syntax"

**Agent Action**:
```python
search(query="async syntax site:docs.python.org")
```

## Implementation Details

This skill uses the `web_search` tool which wraps Brave Search API.

**API Endpoint**: `https://api.search.brave.com/res/v1/web/search`

**Parameters**:
- `q`: Search query (required)
- `count`: Number of results (default: 10)
- `offset`: Pagination offset (default: 0)

**Response Format**:
```json
{
  "web": {
    "results": [
      {
        "title": "...",
        "url": "...",
        "snippet": "..."
      }
    ]
  }
}
```
```

### 2.3 加载策略

**渐进式加载**：

1. **Always-Load Skills**（始终加载）
   - 标记：`always_load: true`
   - 完整内容注入系统 Prompt
   - 用于高频技能（搜索、文件操作...）

2. **Available Skills**（按需加载）
   - 标记：`always_load: false`
   - 只显示摘要（名称、描述）
   - Agent 使用 `read_file` 读取完整内容

**示例**：

```python
class SkillsLoader:
    def load_for_context(self) -> str:
        """加载技能到上下文"""
        parts = []

        # 1. Always-Load Skills（完整内容）
        always_skills = self.get_always_skills()
        for skill in always_skills:
            content = skill.load_full_content()
            parts.append(f"## {skill.name}\n\n{content}")

        # 2. Available Skills（只显示摘要）
        available_skills = self.get_available_skills()
        if available_skills:
            summaries = []
            for skill in available_skills:
                summaries.append(
                    f"- **{skill.name}**: {skill.description}\n"
                    f"  Dependencies: {skill.dependencies}\n"
                    f"  Load with: `read_file('{skill.path}/SKILL.md')`"
                )
            parts.append(
                "## Available Skills\n\n"
                "The following skills are available. To use a skill, read its SKILL.md file:\n\n"
                + "\n".join(summaries)
            )

        return "\n\n---\n\n".join(parts)
```

---

## 三、Skills 的威力

### 3.1 降低 Token 成本

**对比分析**：

| 方案 | Token 消耗 | 说明 |
|------|-----------|------|
| **所有工具加载** | 10000+ tokens | 工具描述全部加载 |
| **Skills 摘要** | 500 tokens | 只显示摘要 |
| **按需加载** | 1000-2000 tokens | 只加载需要的技能 |
| **节省** | **80-90%** | **Token 成本降 72%** |

**关键点**：
- ❌ 传统方式：所有工具描述全部加载到系统 Prompt
- ✅ Skills 方式：只加载摘要 + 按需读取完整内容

### 3.2 示例对比

**传统方式（工具描述）**：

```
## Available Tools

### web_search
Search the web using Brave Search API. Returns top 10 results with snippets
and URLs. Requires BRAVE_API_KEY environment variable.

Parameters:
- query (str): The search query
- count (int): Number of results (default: 10)

### weather_query
Get current weather for a location. Uses OpenWeatherMap API.
Requires WEATHER_API_KEY.

Parameters:
- location (str): City name or coordinates
- units (str): Units system (metric/imperial)

### code_analyzer
Analyze Python code for complexity, bugs, and style issues.
Uses AST parsing and static analysis.

Parameters:
- code (str): Python code to analyze
- rules (list): Analysis rules to apply

[... 20 more tools ...]

Total: 5000+ tokens
```

**Skills 方式（摘要）**：

```
## Active Skills

### Web Search
Always available for searching the web.

### Available Skills

- **Weather**: Get weather information
  Dependencies: curl
  Load with: `read_file('skills/weather/SKILL.md')`

- **Code Analyzer**: Analyze Python code
  Dependencies: pylint, astroid
  Load with: `read_file('skills/code_analyzer/SKILL.md')`

- **Data Processing**: Process CSV/JSON data
  Dependencies: pandas
  Load with: `read_file('skills/data_processing/SKILL.md')`

Total: 500 tokens
```

**节省**：5000 → 500 tokens（**90% 节省**）

---

## 四、FastReAct v2.0 的 Skills 系统

### 4.1 设计目标

**核心特性**：
1. ✅ 文件驱动（Markdown）
2. ✅ 渐进加载（always vs available）
3. ✅ 依赖检查（自动验证）
4. ✅ AI 可修改（Agent 可写新技能）
5. ✅ 版本控制（Git 友好）
6. ✅ 热重载（文件监听）

### 4.2 文件结构

```
~/.fastreact/skills/
├── .gitkeep
├── README.md                      # Skills 目录说明
├── _always/                       # 始终加载的技能
│   ├── file_operations/
│   │   └── SKILL.md
│   ├── web_search/
│   │   └── SKILL.md
│   └── shell/
│       └── SKILL.md
├── _available/                    # 可用技能
│   ├── weather/
│   │   └── SKILL.md
│   ├── code_analysis/
│   │   └── SKILL.md
│   └── data_processing/
│       └── SKILL.md
└── _user/                         # 用户自定义技能
    └── my_custom_skill/
        └── SKILL.md
```

### 4.3 SKILL.md 模板

```yaml
---
name: ${SKILL_NAME}
description: ${ONE_LINE_DESCRIPTION}
version: 1.0.0
author: ${OPTIONAL_AUTHOR}
dependencies: ${LIST_OF_DEPENDENCIES}
always_load: ${true_if_always_load_else_false}
tags: ${LIST_OF_TAGS}
category: ${CATEGORY}

# API Keys (if needed)
env_vars:
  - ${ENV_VAR_NAME}
---

# ${SKILL_DISPLAY_NAME}

## Description

${DETAILED_DESCRIPTION}

## Prerequisites

${REQUIRED_DEPENDENCIES}

## Installation

```bash
# Installation commands
${INSTALL_COMMANDS}
```

## Usage

### Basic Usage

${BASIC_USAGE_EXAMPLES}

### Advanced Usage

${ADVANCED_USAGE_EXAMPLES}

## Implementation

${IMPLEMENTATION_DETAILS}

## Examples

${REAL_WORLD_EXAMPLES}

## Troubleshooting

${COMMON_ISSUES_AND_SOLUTIONS}

## See Also

${RELATED_SKILLS_OR_TOOLS}
```

### 4.4 技能加载器实现

```python
class SkillsLoader:
    """技能加载器"""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.skills_dir = workspace / "skills"

        # 技能缓存
        self._always_skills: list[Skill] = []
        self._available_skills: list[Skill] = []
        self._cache: dict[str, Skill] = {}

    def load_all(self) -> None:
        """加载所有技能"""
        # 1. 加载始终加载的技能
        always_dir = self.skills_dir / "_always"
        if always_dir.exists():
            for skill_dir in always_dir.iterdir():
                if skill_dir.is_dir():
                    skill = Skill.from_directory(skill_dir)
                    if skill.always_load:
                        self._always_skills.append(skill)
                        self._cache[skill.name] = skill

        # 2. 加载可用技能
        available_dir = self.skills_dir / "_available"
        if available_dir.exists():
            for skill_dir in available_dir.iterdir():
                if skill_dir.is_dir():
                    skill = Skill.from_directory(skill_dir)
                    self._available_skills.append(skill)
                    self._cache[skill.name] = skill

        # 3. 加载用户技能
        user_dir = self.skills_dir / "_user"
        if user_dir.exists():
            for skill_dir in user_dir.iterdir():
                if skill_dir.is_dir():
                    skill = Skill.from_directory(skill_dir)
                    self._available_skills.append(skill)
                    self._cache[skill.name] = skill

    def get_always_skills(self) -> list[Skill]:
        """获取始终加载的技能"""
        return self._always_skills

    def get_available_skills(self) -> list[Skill]:
        """获取可用技能"""
        return self._available_skills

    def get_skill(self, name: str) -> Skill | None:
        """获取指定技能"""
        return self._cache.get(name)

    def build_context(self) -> str:
        """构建技能上下文"""
        parts = []

        # 1. Always-Load Skills（完整内容）
        if self._always_skills:
            always_content = "\n\n---\n\n".join([
                skill.load_content()
                for skill in self._always_skills
            ])
            parts.append(f"## Active Skills\n\n{always_content}")

        # 2. Available Skills（摘要）
        if self._available_skills:
            summaries = []
            for skill in self._available_skills:
                deps_status = self._check_dependencies(skill)
                status = "✅" if deps_status else "❌"
                summaries.append(
                    f"- **{skill.name}**: {skill.description}\n"
                    f"  Status: {status}\n"
                    f"  Dependencies: {skill.dependencies}\n"
                    f"  Load with: `read_file('{skill.path}/SKILL.md')`"
                )
            parts.append(
                "## Available Skills\n\n"
                "The following skills are available. To use a skill, read its SKILL.md file:\n\n"
                + "\n\n".join(summaries)
            )

        return "\n\n---\n\n".join(parts)

    def _check_dependencies(self, skill: Skill) -> bool:
        """检查依赖是否满足"""
        for dep in skill.dependencies:
            # 检查命令是否存在
            if shutil.which(dep) is None:
                return False
        return True

    def reload(self) -> None:
        """重新加载技能（热重载）"""
        self._always_skills.clear()
        self._available_skills.clear()
        self._cache.clear()
        self.load_all()
```

### 4.5 Skill 类实现

```python
@dataclass
class Skill:
    """技能类"""

    # 元数据
    name: str
    description: str
    version: str
    author: str | None = None
    dependencies: list[str] = field(default_factory=list)
    always_load: bool = False
    tags: list[str] = field(default_factory=list)
    category: str | None = None
    env_vars: list[str] = field(default_factory=list)

    # 文件路径
    path: Path | None = None

    @classmethod
    def from_directory(cls, skill_dir: Path) -> "Skill":
        """从目录加载技能"""
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            raise ValueError(f"Skill file not found: {skill_file}")

        # 解析 Frontmatter
        content = skill_file.read_text()
        frontmatter, markdown = cls._parse_frontmatter(content)

        return cls(
            path=skill_dir,
            name=frontmatter.get("name", skill_dir.name),
            description=frontmatter.get("description", ""),
            version=frontmatter.get("version", "1.0.0"),
            author=frontmatter.get("author"),
            dependencies=frontmatter.get("dependencies", []),
            always_load=frontmatter.get("always_load", False),
            tags=frontmatter.get("tags", []),
            category=frontmatter.get("category"),
            env_vars=frontmatter.get("env_vars", []),
        )

    def load_content(self) -> str:
        """加载技能内容"""
        if self.path:
            skill_file = self.path / "SKILL.md"
            if skill_file.exists():
                content = skill_file.read_text()
                # 移除 Frontmatter
                _, markdown = self._parse_frontmatter(content)
                return markdown
        return ""

    @staticmethod
    def _parse_frontmatter(content: str) -> tuple[dict, str]:
        """解析 YAML Frontmatter"""
        import re
        pattern = r"^---\n(.*?)\n---\n(.*)$"
        match = re.match(pattern, content, re.DOTALL)
        if match:
            import yaml
            frontmatter = yaml.safe_load(match.group(1))
            markdown = match.group(2)
            return frontmatter, markdown
        return {}, content

    def is_available(self) -> bool:
        """检查技能是否可用"""
        for dep in self.dependencies:
            if shutil.which(dep) is None:
                return False
        return True
```

---

## 五、Agent 自写技能

### 5.1 核心想法

**Agent 可以自己创建新技能！**

**场景**：
1. Agent 发现需要新技能
2. Agent 编写 SKILL.md
3. Agent 测试技能
4. 技能可用

### 5.2 实现

**添加 `create_skill` 工具**：

```python
class CreateSkillTool(Tool):
    """创建新技能工具"""

    @property
    def name(self) -> str:
        return "create_skill"

    @property
    def description(self) -> str:
        return "Create a new skill by writing a SKILL.md file"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Skill name"},
                "description": {"type": "string", "description": "Skill description"},
                "usage": {"type": "string", "description": "Usage instructions"},
                "examples": {"type": "string", "description": "Usage examples"},
                "always_load": {"type": "boolean", "description": "Load immediately"},
            },
            "required": ["name", "description", "usage"],
        }

    async def execute(self, name: str, description: str, usage: str,
                     examples: str, always_load: bool = False, **kwargs) -> str:
        # 创建技能目录
        skills_dir = self.workspace / "skills" / "_user"
        skill_dir = skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # 生成 SKILL.md
        content = self._generate_skill_md(
            name=name,
            description=description,
            usage=usage,
            examples=examples,
            always_load=always_load,
        )

        # 写入文件
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(content, encoding="utf-8")

        return f"Created skill: {name}\nLocation: {skill_dir}\nPlease review and test the skill."

    def _generate_skill_md(self, name: str, description: str,
                          usage: str, examples: str, always_load: bool) -> str:
        """生成 SKILL.md 内容"""
        return f"""---
name: {name}
description: {description}
version: 1.0.0
author: Agent (auto-generated)
dependencies: []
always_load: {str(always_load).lower()}
tags: [auto-generated]
category: user

---

# {name.title()}

## Description

{description}

## Usage

{usage}

## Examples

{examples}

## Notes

This skill was auto-generated by the AI agent. Please review and improve it.
"""
```

### 5.3 使用场景

**示例 1：Agent 创建 SQL 技能**

```
User: I need to query databases frequently

Agent: I'll create a SQL skill for you.

[Agent calls create_skill]

Agent: I've created a SQL skill with:
- Connection management
- Query execution
- Result formatting

You can review it at: ~/.fastreact/skills/_user/sql/SKILL.md

Shall I test it now?
```

**示例 2：Agent 创建测试技能**

```
User: I need to test Python code

Agent: Creating a Python testing skill...

[Agent calls create_skill]

Agent: Created! The skill includes:
- pytest integration
- Coverage reporting
- Mock examples

Location: ~/.fastreact/skills/_user/python_testing/SKILL.md
```

---

## 六、热重载

### 6.1 文件监听

```python
class SkillsWatcher:
    """技能文件监听器（热重载）"""

    def __init__(self, skills_loader: SkillsLoader):
        self.loader = skills_loader
        self.watcher = watchdog.Observer()
        self.running = False

    def start(self) -> None:
        """启动文件监听"""
        self.watcher.schedule(
            self._create_handler(),
            path=str(self.loader.skills_dir),
            recursive=True,
        )
        self.watcher.start()
        self.running = True

    def _create_handler) -> watchdog.events.FileSystemEventHandler:
        """创建文件变化处理器"""
        class Handler(watchdog.events.FileSystemEventHandler):
            def __init__(self, loader: SkillsLoader):
                self.loader = loader

            def on_modified(self, event):
                if event.src_path.endswith("SKILL.md"):
                    logger.info(f"Skill modified: {event.src_path}")
                    self.loader.reload()

        return Handler(self.loader)

    def stop(self) -> None:
        """停止文件监听"""
        if self.running:
            self.watcher.stop()
            self.watcher.join()
            self.running = False
```

**效果**：
- 用户修改 SKILL.md
- 自动重新加载
- 无需重启 Agent

---

## 七、Skills 生态系统

### 7.1 技能市场

**未来设想**：

```
fastreact-skills/
├── official/                       # 官方技能
│   ├── web_search/
│   ├── code_analysis/
│   └── data_processing/
├── community/                     # 社区技能
│   ├── bioinformatics/
│   ├── finance/
│   └── devops/
└── user/                          # 用户技能
    └── custom/
```

**安装技能**：

```bash
# 从 GitHub 安装
fastreact skills install github:user/repo/skill_name

# 从本地安装
fastreact skills install /path/to/skill

# 列出已安装技能
fastreact skills list

# 更新技能
fastreact skills update skill_name

# 卸载技能
fastreact skills uninstall skill_name
```

### 7.2 技能分享

**发布技能**：

```bash
# 发布到 GitHub
fastreact skills publish my_skill

# 效果：
# 1. 打包技能目录
# 2. 创建 GitHub release
# 3. 发布到技能市场
```

---

## 八、最佳实践

### 8.1 编写 Skills

**DO**：
- ✅ 使用清晰的标题和结构
- ✅ 提供具体示例
- ✅ 说明依赖和安装
- ✅ 包含故障排除
- ✅ 使用代码块
- ✅ 添加标签和分类

**DON'T**：
- ❌ 写得太抽象
- ❌ 假设读者有背景知识
- ❌ 忽略错误处理
- ❌ 过于复杂

### 8.2 技能组织

**建议**：
- 每个技能做一件事
- 保持技能独立
- 避免技能依赖
- 提供测试示例

---

## 九、总结

### 9.1 核心价值

**Skills 系统 = AI Agent 的"职业技能树"**

1. **降低门槛** - 只需写 Markdown
2. **节省 Token** - 按需加载，节省 80-90%
3. **AI 可理解** - 自然语言描述
4. **AI 可修改** - Agent 可自写技能
5. **易于分发** - 复制文件即可
6. **版本控制** - Git 友好

### 9.2 未来趋势

**Skills 系统会成为标配**：

1. ✅ nanobot 已经实现
2. ✅ FastReAct v2.0 会采用
3. 🔮 其他 Agent 框架会跟进

**为什么？**
- 用户可定制
- Token 成本低
- AI 可理解
- 易于维护

---

## 十、FastReAct v2.0 的 Skills 系统

### 10.1 实现计划

**阶段 1：基础实现（1 周）**
- [ ] 实现 `Skill` 类
- [ ] 实现 `SkillsLoader`
- [ ] 实现 SKILL.md 模板
- [ ] 单元测试

**阶段 2：Agent 自写（3 天）**
- [ ] 实现 `create_skill` 工具
- [ ] 实现 `update_skill` 工具
- [ ] 实现 `delete_skill` 工具
- [ ] 集成测试

**阶段 3：热重载（2 天）**
- [ ] 实现 `SkillsWatcher`
- [ ] 集成到主循环
- [ ] 测试

**阶段 4：生态建设（长期）**
- [ ] 技能市场
- [ ] 官方技能库
- [ ] 社区贡献

### 10.2 示例技能

**文件操作技能**：

```yaml
---
name: file_operations
description: Advanced file operations and manipulation
version: 1.0.0
dependencies: []
always_load: true
tags: [file-system, core]
category: core
---

# File Operations

## Description

Advanced file operations including reading, writing, searching, and manipulating files.

## Basic Operations

### Reading Files

Use the `read_file` tool to read file contents:

```python
read_file(path="example.txt")
```

### Writing Files

Use the `write_file` tool to create or overwrite files:

```python
write_file(
    path="output.txt",
    content="Hello, World!"
)
```

### Editing Files

Use the `edit_file` tool to make targeted edits:

```python
edit_file(
    path="config.py",
    replacements=[{
        "old_text": "DEBUG = True",
        "new_text": "DEBUG = False"
    }]
)
```

## Advanced Operations

### Searching Files

Use `grep` via shell to search within files:

```python
shell("grep -r 'TODO' src/")
```

### Batch Operations

Process multiple files:

```python
for file in list_files("src/"):
    if file.endswith(".py"):
        process_file(file)
```

## Best Practices

1. **Always read before editing**
2. **Use absolute paths when possible**
3. **Handle errors gracefully**
4. **Backup before batch operations**

## Examples

### Example 1: Refactor Code

Find all TODO comments and add tasks:

```python
# 1. Find all TODOs
results = shell("grep -rn 'TODO' src/")

# 2. Parse results
todos = parse_todos(results)

# 3. Create task file
write_file(
    path="tasks.md",
    content=format_todos(todos)
)
```

### Example 2: Batch Rename

Rename all .txt files to .md:

```python
files = list_files(".", pattern="*.txt")
for file in files:
    new_name = file.replace(".txt", ".md")
    shell(f"mv {file} {new_name}")
```

## Troubleshooting

### Permission Errors

If you get permission errors:
1. Check file permissions with `ls -la`
2. Use `chmod` to fix permissions
3. Consider using `sudo` if necessary

### Encoding Issues

If you encounter encoding errors:
1. Try specifying `encoding='utf-8'`
2. Use `errors='replace'` for robustness
3. Check file encoding with `file -i filename`
```

---

**Skills 系统将是 FastReAct v2.0 的核心特性！** 🚀
