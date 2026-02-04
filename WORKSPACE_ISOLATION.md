# FastReAct 工作区隔离说明

## 核心特性：基于启动目录的自动隔离

FastReAct CLI 的会话和 workspace 完全基于**启动目录**，实现自动隔离。

---

## 工作原理

### 启动时确定上下文

```python
# REPLState.__init__()
self.workspace = Path.cwd()  # 使用当前工作目录
```

### 会话存储位置

```
启动目录/.fastreact/
├── autosave_*.json
└── sessions/
```

---

## 使用示例

### 场景 1: 不同项目独立工作

```bash
# 项目 A
cd ~/projects/project-a
python -m fastreact.cli.main shell
# 工作区: ~/projects/project-a
# 会话: ~/projects/project-a/.fastreact/

# 项目 B
cd ~/projects/project-b
python -m fastreact.cli.main shell
# 工作区: ~/projects/project-b
# 会话: ~/projects/project-b/.fastreact/
```

**完全隔离！两个项目的会话互不影响。**

### 场景 2: 使用绝对路径

```bash
# 在任何目录启动，指定绝对路径
cd /tmp
python D:\FastReAct\src\fastreact\cli\main.py shell
# 工作区: /tmp  （注意：是启动目录，不是脚本所在目录！）
# 会话: /tmp/.fastreact/
```

**重要：工作区是启动目录（`cwd`），不是脚本所在目录！**

### 场景 3: 父子目录隔离

```bash
# 父目录
cd ~/workspace
python -m fastreact.cli.main shell
# 会话保存在: ~/workspace/.fastreact/

# 子目录
cd ~/workspace/subproject
python -m fastreact.cli.main shell
# 会话保存在: ~/workspace/subproject/.fastreact/
```

**父子目录的会话完全独立！**

---

## 实际操作演示

### 创建多个独立项目

```bash
# 项目 1：财务分析
mkdir -p ~/projects/finance
cd ~/projects/finance
python -m fastreact.cli.main shell
> run 分析2024年财务数据
> save finance-2024
# 会话保存到: ~/projects/finance/.fastreact/

# 项目 2：市场调研
cd ~/projects/market-research
python -m fastreact.cli.main shell
> run 调研竞争对手情况
> save market-analysis
# 会话保存到: ~/projects/market-research/.fastreact/

# 再次回到财务项目
cd ~/projects/finance
python -m fastreact.cli.main shell
# 会自动提示：
# "Previous session detected: finance-2024"
# Continue? [Y/n]
```

---

## 目录结构示例

```
~/
└── projects/
    ├── finance/
    │   ├── .fastreact/
    │   │   ├── autosave_20260204_100000.json
    │   │   └── sessions/
    │   │       └── finance-2024.json
    │   ├── data.xlsx
    │   └── notes.md
    │
    ├── market-research/
    │   ├── .fastreact/
    │   │   ├── autosave_20260204_110000.json
    │   │   └── sessions/
    │   │       └── market-analysis.json
    │   └── competitors.md
    │
    └── development/
        ├── .fastreact/
        │   └── autosave_20260204_120000.json
        └── code/
```

**每个项目有独立的 `.fastreact/` 目录，互不干扰。**

---

## 验证当前工作区

### 在 REPL 中查看

```
> status
...
  workspace: /home/user/projects/finance
...
```

### 查看会话文件

```bash
# 查看当前目录的会话
ls -la .fastreact/

# 查看所有项目的会话
find ~/projects -name ".fastreact" -type d
```

---

## 最佳实践

### 1. 为每个项目创建独立目录

```bash
mkdir -p ~/projects/my-project
cd ~/projects/my-project
python -m fastreact.cli.main shell
```

### 2. 在项目根目录使用

```bash
my-project/
├── .fastreact/          # FastReAct 会话（自动生成）
├── data/                # 项目数据
├── docs/                # 项目文档
└── config.json          # 可选的项目配置
```

### 3. Git 忽略

在每个项目的 `.gitignore` 中添加：

```
.fastreact/
```

**不要提交会话文件到版本控制！**

### 4. 使用绝对路径启动（可选）

如果你想在特定目录工作但从其他位置启动：

```bash
# Windows
cd D:\Work\ProjectA
python D:\FastReAct\src\fastreact\cli\main.py shell

# Linux/Mac
cd ~/work/project-a
python ~/src/FastReAct/src/fastreact/cli/main.py shell
```

---

## 清理会话

### 清理当前项目会话

```bash
rm -rf .fastreact/
```

### 清理所有项目会话

```bash
find ~/projects -name ".fastreact" -type d -exec rm -rf {} +
```

### 清理特定类型的会话

```bash
# 只删除自动保存的会话
rm .fastreact/autosave_*.json

# 保留手动保存的会话
```

---

## 与 Workspace 切换命令的配合

### `/workspace` 命令 vs 启动目录

| 方式 | 作用域 | 生命周期 |
|------|--------|----------|
| 启动目录 | REPL workspace | 整个会话 |
| `/workspace <path>` | RAG 检索路径 | 运行时可改 |

### 组合使用

```bash
# 在项目 A 目录启动
cd ~/projects/project-a
python -m fastreact.cli.main shell

# REPL 中切换到租户 B 的知识库
> /workspace ~/data/tenant-b/docs
> run 查询问题

# 这样：
# - 会话保存在: ~/projects/project-a/.fastreact/
# - 但检索的是: ~/data/tenant-b/docs 的文档
```

---

## 故障排除

### 问题：会话混乱

**症状**：不同项目的会话混在一起

**原因**：在同一个目录启动了多个项目

**解决方案**：
```bash
# 为每个项目创建独立目录
mkdir project-a project-b
cd project-a
python -m fastreact.cli.main shell
```

### 问题：找不到会话

**症状**：之前保存的会话找不到

**原因**：在不同目录启动了

**检查**：
```bash
pwd  # 确认当前目录
ls -la .fastreact/  # 查看会话文件
```

**解决方案**：
```bash
# 回到原来的目录
cd ~/projects/where-you-were
python -m fastreact.cli.main shell
```

---

## 优势

### 1. 零配置
- 无需手动指定工作区
- 自动基于当前目录

### 2. 天然隔离
- 不同项目自动隔离
- 父子目录互不干扰

### 3. 符合直觉
- 在哪里工作，就在哪里启动
- 类似 Git 的行为

### 4. 易于管理
- 会话文件在项目目录内
- 清晰的目录结构

---

## 总结

**核心原则：**

> **你在哪个目录启动 `fastreact shell`，那个目录就是你的工作区。**

**记住：**
- ✅ 工作区 = 启动目录（`cwd`）
- ✅ 会话 = 启动目录/.fastreact/
- ✅ 不同目录 = 不同工作区
- ❌ 工作区 ≠ 脚本所在目录

**FastReAct = 你在哪儿启动，就在哪儿工作**
