# FastReAct Session Resume Feature

## Overview

FastReAct CLI 现在支持**会话自动检测与恢复**，类似 Claude Code 的行为：
- 启动时自动检测当前目录的会话文件
- 显示历史会话信息
- 询问用户是否继续
- 支持自动恢复模式

---

## 行为说明

### 启动流程

```
1. 运行 `fastreact shell`
      ↓
2. 检查当前目录是否存在会话文件
   - .fastreact/autosave_*.json
   - .fastreact/sessions/*.json
      ↓
3a. 如果发现会话 → 显示信息并询问用户
      ├─ 用户选择 Y → 加载会话并继续
      └─ 用户选择 N → 启动新会话

3b. 如果未发现会话 → 直接启动新会话
```

### 示例输出

**发现历史会话时：**
```
======================================================================
Previous session detected:
======================================================================
  Title: Test Session
  Messages: 4
  Modified: 2026-02-04 22:17:57
  File: autosave_20260204_221757.json
  Variables: Yes
======================================================================

Continue? [Y/n] _
```

**加载会话成功：**
```
[Success] Session restored: autosave_20260204_221757.json
  - 4 messages
  - 2 variables
```

**用户选择不继续：**
```
Starting fresh session...
```

---

## 配置选项

### 环境变量

#### `FASTREACT_AUTO_RESUME`

自动恢复最新会话，无需用户确认。

```bash
# 启用自动恢复
export FASTREACT_AUTO_RESUME=true
fastreact shell

# Windows
set FASTREACT_AUTO_RESUME=true
fastreact shell
```

**行为对比：**

| 模式 | 发现会话时 |
|------|-----------|
| 默认模式 | 询问用户是否继续 |
| AUTO_RESUME | 自动加载最新会话 |

---

## 会话文件位置

### 存储目录结构

```
当前目录/
└── .fastreact/
    ├── autosave_20260204_220000.json    # 自动保存的会话
    ├── autosave_20260204_221500.json
    └── sessions/
        ├── session_001.json             # 手动保存的会话
        └── session_002.json
```

### 检测优先级

1. **最新修改的会话**优先（按 `mtime` 排序）
2. `autosave_*.json` 和 `sessions/*.json` 都会被检测
3. 损坏的文件会被跳过

---

## 实现细节

### 核心模块

#### `session_detector.py`

```python
# 主要函数
find_session_files(start_dir) -> List[Path]
    # 查找所有会话文件

get_session_info(session_file) -> Dict[str, Any]
    # 获取会话信息（标题、消息数、时间等）

should_resume_session(start_dir, force_prompt) -> (bool, Path)
    # 主入口：决定是否恢复会话
```

### REPL 集成

```python
# repl.py - run_repl()
def run_repl():
    # 1. 检测会话
    should_resume, session_file = should_resume_session()

    if not should_resume and session_file is not None:
        # 用户选择不继续
        print("Starting fresh session...")

    # 2. 创建 REPL 实例（传入会话文件）
    repl = InteractiveREPL(session_to_load=session_file)

    # 3. 运行 REPL（会自动加载会话）
    asyncio.run(repl.run_async())
```

---

## 使用场景

### 场景 1: 意外中断后恢复

```bash
# 工作进行中...
$ fastreact shell
> run 开始复杂任务...
[中断 - Ctrl+C]

# 重新启动
$ fastreact shell
Previous session detected:
  Title: 新对话
  Messages: 15
  Modified: 2026-02-04 22:30:00

Continue? [Y/n] y
[Success] Session restored: autosave_20260204_223000.json
  - 15 messages
  - 3 variables

# 继续之前的工作
> run 继续任务
```

### 场景 2: 自动恢复（脚本模式）

```bash
# 启用自动恢复
export FASTREACT_AUTO_RESUME=true

# 每次启动都自动继续上次的会话
$ fastreact shell
Auto-resuming latest session...
[Success] Session restored
```

### 场景 3: 项目间切换

```bash
# 项目 A
cd ~/project-a
fastreact shell
# 使用项目 A 的会话

# 项目 B
cd ~/project-b
fastreact shell
# 使用项目 B 的会话（独立的）
```

---

## 最佳实践

### 1. 定期保存会话

```
> save project-milestone-1
```

手动保存的会话保存在 `.fastreact/sessions/`，不会被自动覆盖。

### 2. 清理旧会话

```bash
# 删除不需要的会话
rm .fastreact/autosave_*.json
rm .fastreact/sessions/old-*.json
```

### 3. Git 忽略

建议在 `.gitignore` 中添加：

```
.fastreact/
```

会话文件包含对话历史和变量，不应提交到版本控制。

### 4. 多项目隔离

每个项目目录有独立的 `.fastreact/`，会话自动隔离。

```
~/projects/a/.fastreact/autosave_*.json  # 项目 A 的会话
~/projects/b/.fastreact/autosave_*.json  # 项目 B 的会话
```

---

## 测试

### 运行测试套件

```bash
python test_session_resume.py
```

### 测试覆盖

- ✅ 查找会话文件
- ✅ 提取会话信息
- ✅ 格式化显示
- ✅ 处理无会话情况
- ✅ 处理损坏文件
- ✅ 自动恢复模式

---

## API 示例

### 编程方式使用

```python
from pathlib import Path
from fastreact.cli.session_detector import (
    find_session_files,
    get_session_info,
    should_resume_session,
)

# 查找会话
sessions = find_session_files(Path.cwd())

# 获取信息
if sessions:
    info = get_session_info(sessions[0])
    print(f"Found: {info['title']}")
    print(f"Messages: {info['message_count']}")

# 决定是否恢复
should_resume, session_file = should_resume_session()
if should_resume:
    print(f"Resuming: {session_file}")
```

---

## 故障排除

### 问题：未检测到会话

**检查：**
1. 确认当前目录下有 `.fastreact/` 文件夹
2. 确认会话文件存在（`autosave_*.json` 或 `sessions/*.json`）

**解决方案：**
```bash
# 检查会话文件
ls -la .fastreact/

# 如果为空，说明没有历史会话
```

### 问题：会话损坏无法加载

**检查：**
会话文件可能包含无效的 JSON。

**解决方案：**
```bash
# 删除损坏的会话
rm .fastreact/autosave_*.json

# 重新开始
fastreact shell
```

### 问题：不想每次都提示

**解决方案：**
```bash
# 启用自动恢复
export FASTREACT_AUTO_RESUME=true
```

---

## 与 Claude Code 的对比

| 功能 | Claude Code | FastReAct |
|------|-------------|-----------|
| 检测历史会话 | ✅ | ✅ |
| 显示会话信息 | ✅ | ✅ |
| 询问用户 | ✅ | ✅ |
| 自动恢复模式 | ✅ | ✅ |
| 跨项目隔离 | ✅ | ✅ |
| 损坏文件处理 | ✅ | ✅ |

**完全兼容 Claude Code 的行为模式！**

---

**FastReAct + 会话恢复 = 无缝的 AI Agent 开发体验**
