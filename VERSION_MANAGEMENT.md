# FastReAct 版本管理

## 版本号统一管理

**核心原则：版本号只在一个地方定义，所有其他地方都从这里读取。**

---

## 版本号位置

### 唯一真相源 (Single Source of Truth)

**文件：** `src/fastreact/__init__.py`

```python
"""
FastReAct: Enterprise-grade ReAct Agent Infrastructure
...

Version: 1.1.0
"""

__version__ = "1.1.0"  # ← 这里是唯一的版本号定义
__author__ = "FastReAct Team"
__license__ = "MIT"
```

---

## 使用版本号的地方

### 1. pyproject.toml

**动态读取版本：**

```toml
[project]
name = "fastreact"
dynamic = ["version"]  # 标记为动态

[tool.setuptools.dynamic]
version = {attr = "fastreact.__version__"}  # 从 __init__.py 读取
```

### 2. setup.py

**动态读取版本：**

```python
def get_version():
    """从 __init__.py 读取版本号"""
    import re
    with open("src/fastreact/__init__.py", "r", encoding="utf-8") as f:
        version_file = f.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

setup(
    version=get_version(),  # 动态读取
    ...
)
```

### 3. CLI 命令

**导入并使用：**

```python
# src/fastreact/cli/main.py
from fastreact import __version__

@click.version_option(version=__version__, prog_name="fastreact")
def cli():
    ...

@cli.command()
def version():
    """显示版本信息"""
    click.echo(f"FastReAct v{__version__}")
```

### 4. Python API

**用户代码中使用：**

```python
from fastreact import __version__

print(f"FastReAct version: {__version__}")
# 输出: FastReAct version: 1.1.0
```

---

## 更新版本号

### 步骤

**只需修改一个文件：**

```bash
# 1. 编辑 src/fastreact/__init__.py
vim src/fastreact/__init__.py

# 2. 修改这一行
__version__ = "1.2.0"  # 从 1.1.0 改为 1.2.0

# 3. 完成！所有地方都会自动使用新版本号
```

### 验证

```bash
# 检查版本号
python -c "from fastreact import __version__; print(__version__)"
# 输出: 1.2.0

# 查看 CLI 版本
fastreact --version
# 输出: FastReAct v1.2.0

# 检查安装的包版本
pip show fastreact
# 输出: Version: 1.2.0
```

---

## 版本号规则

### 语义化版本 (Semantic Versioning)

```
MAJOR.MINOR.PATCH

示例：1.1.0
  │  │  │
  │  │  └─ PATCH: bug 修复
  │  └──── MINOR: 新功能（向后兼容）
  └─────── MAJOR: 破坏性变更
```

### 当前版本

```
__version__ = "1.1.0"
```

**含义：**
- **1 (MAJOR)**: 第一个主要版本
- **1 (MINOR)**: 包含多租户、会话恢复等新功能
- **0 (PATCH)**: 稳定版本

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.1.0 | 2026-02-04 | + 多租户 workspace<br>+ 会话恢复<br>+ 工作区隔离<br>+ MCP 集成 |
| 1.0.0 | 2025-XX-XX | 初始稳定版本 |

---

## 发布流程

### 1. 更新版本号

```bash
# 编辑 src/fastreact/__init__.py
__version__ = "1.2.0"  # 新版本
```

### 2. 更新 CHANGELOG

```bash
# 创建 CHANGELOG.md
echo "# Changelog" > CHANGELOG.md
echo "## [1.2.0] - 2026-02-XX" >> CHANGELOG.md
echo "### Added" >> CHANGELOG.md
echo "- 新功能描述" >> CHANGELOG.md
```

### 3. 构建发布

```bash
# 构建 wheel
pip install build
python -m build

# 检查
twine check dist/*

# 发布到 PyPI
twine upload dist/*
```

### 4. Git 标签

```bash
# 创建标签
git tag v1.2.0
git push origin v1.2.0
```

---

## 常见问题

### Q: 为什么要统一版本号？

**A: 避免不一致问题**

之前的问题：
- `pyproject.toml`: version = "1.0.0"
- `setup.py`: version = "0.2.0" ❌
- `main.py`: hardcode "v1.0.0" ❌

现在：
- 只在 `__init__.py` 定义一次
- 所有地方都从那里读取 ✅

### Q: 如何知道当前版本？

**A: 三种方式**

```bash
# 方式 1: Python
python -c "from fastreact import __version__; print(__version__)"

# 方式 2: CLI
fastreact --version

# 方式 3: pip
pip show fastreact
```

### Q: 忘记更新版本号会怎样？

**A: 构建时会自动使用 __version__ 的值**

只要修改了 `__init__.py`，其他地方会自动同步，无需手动修改多个文件。

---

## 相关文件

### 需要维护的文件

| 文件 | 作用 | 维护方式 |
|------|------|----------|
| `src/fastreact/__init__.py` | **定义版本号** | 手动修改 |
| `pyproject.toml` | 读取版本号 | 自动（dynamic） |
| `setup.py` | 读取版本号 | 自动（get_version()） |
| `src/fastreact/cli/main.py` | 显示版本号 | 自动（导入 __version__） |

### 不需要手动修改

❌ `pyproject.toml` 中的 `version = "1.0.0"`
❌ `setup.py` 中的 `version="0.2.0"`
❌ `main.py` 中的硬编码版本字符串

---

## 最佳实践

### 1. 版本号变更流程

```bash
# 1. 修改版本号
vim src/fastreact/__init__.py
__version__ = "1.2.0"

# 2. 提交变更
git add src/fastreact/__init__.py
git commit -m "Bump version to 1.2.0"

# 3. 创建标签
git tag v1.2.0

# 4. 推送
git push origin main --tags
```

### 2. 开发版本

在开发过程中，可以使用开发版本号：

```python
__version__ = "1.2.0.dev0"  # 开发版本
```

### 3. 预发布版本

```python
__version__ = "1.2.0a1"  # Alpha 1
__version__ = "1.2.0b1"  # Beta 1
__version__ = "1.2.0rc1" # Release Candidate 1
```

---

## 总结

**核心原则：**

> **版本号只在一个地方定义：`src/fastreact/__init__.py`**

**好处：**
1. ✅ 避免版本号不一致
2. ✅ 只需修改一个地方
3. ✅ 自动同步到所有地方
4. ✅ 易于维护和发布

**记住：**
- 修改版本 → 只改 `__init__.py`
- 读取版本 → 从 `fastreact.__version__`

---

**FastReAct = 统一版本管理 + 清晰的发布流程**
