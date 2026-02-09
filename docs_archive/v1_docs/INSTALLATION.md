# FastReAct 安装指南

## 概述

FastReAct 是一个**可安装的 Python 包**，支持多种安装方式。

---

## 安装方式

### 方式 1: 开发模式安装（推荐用于开发）

```bash
# 在项目根目录
cd D:\FastReAct

# 以可编辑模式安装（代码修改立即生效）
pip install -e .

# 验证安装
fastreact --version
```

**优势：**
- 代码修改立即生效
- 无需重新安装
- 适合开发和调试

---

### 方式 2: 正式安装（推荐用于生产）

```bash
# 构建 wheel 包
pip install build
python -m build

# 安装生成的 wheel
pip install dist/fastreact-1.0.0-py3-none-any.whl
```

**或者直接从源码安装：**
```bash
pip install .
```

---

### 方式 3: 从 PyPI 安装（如果已发布）

```bash
pip install fastreact
```

---

## 安装后使用

### CLI 命令

安装后，`fastreact` 命令会自动添加到 PATH：

```bash
# 查看版本
fastreact --version

# 启动 REPL
fastreact shell

# 运行单次查询
fastreact run "解释量子计算"

# 查看帮助
fastreact --help
```

### Python API

```python
# 安装后可以直接导入
from fastreact import FastReAct

agent = FastReAct(
    api_key="your-api-key",
    model="gpt-4"
)

result = await agent.run_async("你的问题")
```

---

## 当前配置状态

### pyproject.toml 配置

```toml
[project]
name = "fastreact"
version = "1.0.0"
requires-python = ">=3.10"

dependencies = [
    "openai>=1.0.0",
    "httpx>=0.25.0",
    "pydantic>=2.0.0",
    "mcp>=1.25.0",
    "rich>=13.0.0",
    "pyyaml>=6.0",
    "click>=8.0.0",
    "prompt-toolkit>=3.0.0",
]

[project.entry-points."console_scripts"]
fastreact = "fastreact.cli.main:cli"
```

### setup.py 配置（存在不一致）

```python
version="0.2.0"  # 与 pyproject.toml 不一致
entry_points={
    "fastreact=fastreact.cli.main:main",  # 入口点不一致
}
```

---

## 需要修复的问题

### 问题 1: 版本号不一致

- `pyproject.toml`: `version = "1.0.0"`
- `setup.py`: `version = "0.2.0"`

**影响：**
- 可能导致混淆
- PyPI 发布时会使用 `pyproject.toml` 的版本

### 问题 2: 入口点不一致

- `pyproject.toml`: `fastreact = "fastreact.cli.main:cli"`
- `setup.py`: `fastreact = "fastreact.cli.main:main"`

**影响：**
- 安装后可能无法正确启动
- 需要确认正确的入口函数

---

## 建议的修复

### 统一使用 pyproject.toml

**建议：删除 setup.py，完全使用 pyproject.toml**

原因：
1. `pyproject.toml` 是现代 Python 打包标准
2. 避免配置重复和不一致
3. 更好的工具支持

### 或者：统一配置

如果要保留 `setup.py`，需要确保：

1. **版本号一致**
2. **入口点一致**
3. **依赖列表一致**

---

## 验证安装

### 测试 CLI

```bash
# 安装后测试
fastreact --version
fastreact shell
```

### 测试 Python 导入

```python
python -c "from fastreact import FastReAct; print('OK')"
```

### 检查入口点

```bash
pip show fastreact
# 查看 "Entry-points" 部分
```

---

## 开发工作流

### 推荐流程（开发模式）

```bash
# 1. 克隆仓库
git clone https://github.com/yourusername/FastReAct.git
cd FastReAct

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 3. 开发模式安装
pip install -e .

# 4. 安装开发依赖
pip install -e ".[dev]"

# 5. 运行测试
pytest

# 6. 修改代码后立即生效
fastreact shell
```

### 发布流程

```bash
# 1. 更新版本号
# 编辑 pyproject.toml: version = "1.0.1"

# 2. 构建包
pip install build
python -m build

# 3. 检查包
twine check dist/*

# 4. 上传到 PyPI（测试）
twine upload --repository testpypi dist/*

# 5. 上传到 PyPI（正式）
twine upload dist/*
```

---

## 依赖管理

### 核心依赖

```
openai>=1.0.0      # OpenAI API 客户端
httpx>=0.25.0      # 异步 HTTP 客户端
pydantic>=2.0.0    # 数据验证
mcp>=1.25.0        # MCP 协议支持
rich>=13.0.0       # 终端美化输出
pyyaml>=6.0        # YAML 配置文件
click>=8.0.0       # CLI 框架
prompt-toolkit>=3.0.0  # 交互式 CLI
```

### 可选依赖（开发）

```
pytest>=7.0.0      # 测试框架
pytest-asyncio     # 异步测试支持
pytest-cov>=4.0.0  # 测试覆盖率
black>=23.0.0      # 代码格式化
ruff>=0.1.0        # 代码检查
mypy>=1.0.0        # 类型检查
```

### 安装可选依赖

```bash
# 安装所有依赖（包括开发依赖）
pip install -e ".[dev]"

# 只安装核心依赖
pip install -e .
```

---

## 常见问题

### Q1: 安装后找不到 `fastreact` 命令

**检查：**
```bash
# 查看 Scripts 目录
where fastreact  # Windows
which fastreact   # Linux/Mac

# 检查 PATH
echo $PATH
```

**解决：**
```bash
# 重新安装
pip uninstall fastreact
pip install -e .
```

### Q2: 导入失败

**症状：**
```python
>>> from fastreact import FastReAct
ModuleNotFoundError: No module named 'fastreact'
```

**解决：**
```bash
# 确认安装
pip list | grep fastreact

# 重新安装
pip install -e .
```

### Q3: 版本冲突

**症状：**
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed.
```

**解决：**
```bash
# 使用虚拟环境隔离依赖
python -m venv venv
source venv/bin/activate
pip install -e .
```

---

## 卸载

```bash
pip uninstall fastreact
```

---

## 总结

| 方面 | 状态 | 说明 |
|------|------|------|
| 可安装性 | ✅ 完全支持 | pip install -e . |
| CLI 入口 | ⚠️ 需确认 | 入口点配置不一致 |
| Python API | ✅ 可用 | from fastreact import FastReAct |
| 依赖声明 | ⚠️ 需整理 | setup.py 和 pyproject.toml 不一致 |
| 开发模式 | ✅ 完美支持 | pip install -e . |

**推荐：**
1. **开发时使用**: `pip install -e .`
2. **生产环境使用**: `pip install .`
3. **修复配置不一致**: 统一使用 pyproject.toml

---

**FastReAct = 可安装、可开发、可生产的企业级框架**
