# FastReAct Nano 设计哲学

**核心原则**: 极简工具 + 丰富 Skills + exec 调用

---

## 设计公式

```
FastReAct Nano =
  4 个极简工具（Core）
  + N 个丰富 Skills（实现方案）
  + exec 万能调用（执行）
```

---

## 三层架构

### Layer 1: 极简工具（4 个）

**永不扩展，保持稳定**：

```python
src/fastreact/tools/
├── exec_tool.py       # 万能执行工具
├── read_file.py       # 读取文件
├── write_file.py      # 写入文件
└── edit_file.py       # 编辑文件
```

**特点**：
- ✅ 精简到极致
- ✅ 长期稳定
- ✅ 无外部依赖
- ✅ 类型安全

---

### Layer 2: 丰富 Skills（无限扩展）

**零代码扩展，基于 Markdown**：

```
skills/builtin/
├── http/              # HTTP 操作
├── search/            # Web 搜索
├── json/              # JSON 处理
├── database/          # 数据库操作
├── image/             # 图像处理
├── git/               # Git 操作
├── cron/              # 定时任务
├── news_aggregator/   # 新闻聚合（已有）
├── code_review/       # 代码审查（已有）
└── ...                # 无限扩展
```

**每个 Skill 的格式**：

```yaml
---
name: http_fetch
description: Fetch HTTP content using curl
tags: [http, web, api]
requirements:
  bins: ["curl"]      # 声明依赖的命令
---

# HTTP Fetch

Use `exec` tool with curl:

\`\`\`bash
# GET request
curl -s https://api.example.com

# POST request
curl -X POST -H "Content-Type: application/json" \
  -d '{"key":"value"}' https://api.example.com

# With authentication
curl -H "Authorization: Bearer $TOKEN" \
  https://api.example.com
\`\`\"
```

**特点**：
- ✅ 零代码（只要 Markdown）
- ✅ 立即可用（只要 bash 命令存在）
- ✅ 无限扩展（想加什么加什么）
- ✅ 易于分享（复制粘贴 SKILL.md）

---

### Layer 3: exec 万能调用

**所有功能最终通过 exec 实现**：

```python
# Agent 思考链
Thought: "我需要获取 API 数据"
Action: "使用 http_fetch Skill"
Tool: "exec"
Command: "curl -s https://api.example.com"

Thought: "我需要搜索网络"
Action: "使用 web_search Skill"
Tool: "exec"
Command: "curl -s 'https://ddg.gg/?q=query' | grep ..."

Thought: "我需要处理 JSON"
Action: "使用 json_process Skill"
Tool: "exec"
Command: "echo '{...}' | jq ."
```

**执行流程**：
```
Agent → 选择 Skill → 提取命令 → exec 工具执行 → 返回结果
```

---

## 为什么这样设计？

### 1️⃣ **极简工具 = 稳定性**

**4 个工具，永不增加**：
- ✅ 代码库小（< 2000 行核心代码）
- ✅ 维护成本低
- ✅ 测试覆盖完整
- ✅ API 稳定不变

**对比**：
- ❌ 如果添加 10+ 个工具 → 代码膨胀 → 维护困难

---

### 2️⃣ **丰富 Skills = 灵活性**

**无限扩展，零代码**：
- ✅ 想加功能？写个 SKILL.md
- ✅ 不需要改核心代码
- ✅ 不需要重新编译
- ✅ 热加载支持

**示例**：
```
需要 HTTP 功能？
  → 创建 skills/http/SKILL.md
  → 提供 curl 命令示例
  → 立即可用 ✅

需要定时任务？
  → 创建 skills/cron/SKILL.md
  → 提供 crontab 命令示例
  → 立即可用 ✅

需要图像处理？
  → 创建 skills/image/SKILL.md
  → 提供 convert 命令示例
  → 立即可用 ✅
```

---

### 3️⃣ **exec 调用 = 通用性**

**所有功能归一化**：
- ✅ 统一接口（exec 工具）
- ✅ 统一调用方式（bash 命令）
- ✅ 统一错误处理

**优势**：
- ✅ Agent 学习成本低（只需要学会 exec）
- ✅ 用户理解成本低（bash 命令通俗易懂）
- ✅ 调试简单（直接复制命令到终端测试）

---

## 与 OpenClaw 的对比

| 维度 | OpenClaw | FastReAct Nano（新方向） |
|------|----------|------------------------|
| **核心工具** | 10+ 个 TypeScript Tools | 4 个 Python Tools（极简） |
| **Skills** | 59 个（Markdown + CLI） | 无限个（Markdown + CLI） |
| **调用方式** | exec / 直接 API | exec（统一） |
| **扩展难度** | 低（Markdown） | 低（Markdown） |
| **代码量** | ~5000 行工具代码 | ~2000 行核心代码 |
| **MCP 依赖** | 可选 | 可选 |

**关键差异**：
- OpenClaw: Tools（TS）+ Skills（CLI）
- FastReAct: Skills（CLI）为主，Tools 最小化

---

## 实施计划

### Phase 1: 确认核心工具（已完成）

✅ 4 个工具：
- exec_tool
- read_file
- write_file
- edit_file

**承诺**：不再增加内建工具

---

### Phase 2: 创建核心 Skills（1 周）

创建 8 个常用 Skills：

1. **http** - HTTP 操作
   ```bash
   curl -s https://api.example.com
   ```

2. **search** - Web 搜索
   ```bash
   curl -s "https://ddg.gg/?q=query" | grep ...
   ```

3. **json** - JSON 处理
   ```bash
   echo '{...}' | jq .
   ```

4. **database** - 数据库操作
   ```bash
   sqlite3 db.db "SELECT ..."
   ```

5. **image** - 图像处理
   ```bash
   convert input.jpg -resize 800x output.jpg
   ```

6. **git** - Git 操作
   ```bash
   git status
   ```

7. **cron** - 定时任务
   ```bash
   crontab -l
   ```

8. **file** - 高级文件操作
   ```bash
   find . -name "*.py"
   ```

---

### Phase 3: 改进 Skill 机制（1 周）

1. **依赖检查**
   ```python
   def _check_requirements(skill):
       if "bins" in skill.requires:
           for bin in skill.requires.bins:
               if not shutil.which(bin):
                   return False
       return True
   ```

2. **优雅降级**
   ```python
   # 如果 curl 不存在，http Skill 不可用
   # 但不影响其他 Skill
   ```

3. **错误提示**
   ```python
   if not shutil.which("curl"):
       print("[WARNING] http_fetch Skill requires 'curl'")
       print("[INFO] Install with: brew install curl")
   ```

---

### Phase 4: 文档和最佳实践（1 周）

1. **Skill 编写指南**
   - 如何创建 SKILL.md
   - 如何写 bash 命令示例
   - 如何声明 requirements

2. **最佳实践文档**
   - 常用 bash 命令参考
   - exec 工具使用技巧
   - Skills 复用指南

3. **示例库**
   - 50+ 个常用 Skills
   - 覆盖常见场景
   - 社区贡献

---

## 示例：完整的 Skill

### http/SKILL.md

```yaml
---
name: http
description: HTTP operations using curl
version: 1.0.0
tags: [http, web, api, rest]
author: FastReAct Team
requirements:
  bins: ["curl"]
---

# HTTP Operations

Use `exec` tool with curl for HTTP requests.

## GET Request

Fetch data from an API:

\`\`\`bash
curl -s https://api.example.com/users
\`\`\`

## POST Request

Send JSON data:

\`\`\`bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"name":"John","age":30}' \
  https://api.example.com/users
\`\`\`

## Authentication

Bearer token:

\`\`\`bash
curl -H "Authorization: Bearer $TOKEN" \
  https://api.example.com/protected
\`\`\`

Basic auth:

\`\`\`bash
curl -u username:password \
  https://api.example.com/protected
\`\`\`

## Headers

Custom headers:

\`\`\`bash
curl -H "X-Custom-Header: value" \
  https://api.example.com
\`\`\`

## Output Format

Pretty print JSON:

\`\`\`bash
curl -s https://api.example.com | jq .
\`\`\`

Save to file:

\`\`\`bash
curl -s https://api.example.com -o output.json
\`\`\`

## Examples

### Fetch HackerNews top stories

\`\`\`bash
curl -s https://hacker-news.firebaseio.com/v0/topstories.json | \
  python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin)[:5], indent=2))"
\`\`\`

### Download file

\`\`\`bash
curl -O https://example.com/file.zip
\`\`\`

### Check response headers

\`\`\`bash
curl -I https://api.example.com
\`\`\`

## Tips

1. **Use `-s`** for silent mode (no progress bar)
2. **Use `-v`** for verbose mode (debugging)
3. **Use `-o file`** to save to file
4. **Pipe to `jq .`** for pretty JSON
```

---

## 优势总结

### 对用户

- ✅ **简单** - 只需要懂 bash 命令
- ✅ **灵活** - 想加什么功能就写 Skill
- ✅ **透明** - 可以直接复制命令测试
- ✅ **可扩展** - 社区可以贡献 Skills

### 对开发者

- ✅ **维护成本低** - 核心代码少
- ✅ **稳定** - 4 个工具不变
- ✅ **扩展容易** - 添加 Skill 不需要改代码
- ✅ **测试简单** - 只需要测试 exec 工具

### 对 Agent

- ✅ **学习成本低** - 只需要学会 exec
- ✅ **统一接口** - 所有功能归一化
- ✅ **可预测** - bash 命令行为一致
- ✅ **可调试** - 可以在终端直接测试

---

## FAQ

**Q: 为什么不直接用 MCP？**

A:
- ✅ MCP 是可选的，用于复杂功能（浏览器、SSH）
- ✅ 简单功能用 Skills + bash 更直接
- ✅ 不依赖 MCP 服务器加载

**Q: 如果系统没有 curl 怎么办？**

A:
- ✅ Skills 依赖检查会跳过 http Skill
- ✅ 不影响其他功能
- ✅ 提示用户安装

**Q: Skills 可以调用 Python 代码吗？**

A:
- ✅ 可以！`python3 -c "..."` 也是 bash 命令
- ✅ 参考 news_aggregator Skill

**Q: 这样会不会太慢？**

A:
- ✅ bash 命令启动很快（毫秒级）
- ✅ 对于 AI 应用，这个开销可以接受
- ✅ 如果需要性能，可以用 MCP

---

## 结论

**FastReAct Nano 的正确方向**：

```
极简工具（4 个）+ 丰富 Skills（无限）+ exec 调用（万能）
```

**核心价值**：
- ✅ 保持 Nano 特性
- ✅ 无限扩展能力
- ✅ 零代码集成
- ✅ 社区友好

**这才是真正的 "Nano" + "强大"！**

---

**作者**: FastReAct Team
**设计哲学**: 极简核心，丰富生态
**承诺**: 4 个核心工具永不增加
