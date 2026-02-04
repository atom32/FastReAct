# Configuration Priority - Multi-Layer Configuration

## Status

**[INTEGRATED]** - The 4-layer configuration system is now active and integrated into the main codebase.

All components (CLI, REPL, Gateway) now use the new `ConfigManager` for configuration loading.

## Overview

FastReAct 现在支持**四层配置加载**，解决了个人使用、团队协作和多租户场景的配置管理问题。

---

## Configuration Priority (Highest to Lowest)

```
1. ENV (Environment Variables)     ← 最高优先级（CI/CD、多租户）
2. USER (~/.fastreact/config.json)  ← 个人使用
3. PROJECT (./config.json)          ← 团队共享
4. DEFAULT (code)                   ← 兜底值
```

**后加载的配置会覆盖先加载的配置。**

---

## Usage Examples

### Scenario 1: Personal Development (推荐)

**Setup** (一次性):
```bash
# 创建用户配置目录
mkdir -p ~/.fastreact

# 创建用户配置文件
cp user_config.example.json ~/.fastreact/config.json

# 编辑配置，添加你的 API keys
notepad ~/.fastreact/config.json
```

**Usage**:
```bash
# 之后直接启动，不用每次设置环境变量
python -m fastreact.cli.main shell
```

**优点**:
- ✅ 配置一次，永久生效
- ✅ API keys 不在项目里
- ✅ 不同项目用同一套配置

---

### Scenario 2: Team Development

**Project Configuration** (`./config.json`):
```json
{
  "llm": {
    "default_provider": "openai",
    "timeout_seconds": 60
  },
  "mcp": {
    "servers": { ... }
  }
}
```

**User Configuration** (`~/.fastreact/config.json`):
```json
{
  "llm": {
    "providers": {
      "openai": {
        "api_key": "sk-my-personal-key"
      }
    }
  }
}
```

**Result**:
- 使用 OpenAI（项目配置）
- API key 从个人配置读取
- 团队成员各用各的 keys

---

### Scenario 3: CI/CD or Multi-Tenant

```bash
# 设置环境变量（临时）
export FASTREACT_API_KEY=sk-deployment-key
export FASTREACT_MODEL=gpt-4

# 启动服务
python -m fastreact.cli.main gateway start
```

**优先级**：
- 环境变量 > 用户配置 > 项目配置

---

## Configuration Files

### Project Configuration

**File**: `./config.json` (or `config.example.json` as template)

**Purpose**: 项目共享配置（不含敏感信息）

**Content**:
- LLM provider settings
- Tool configurations
- MCP server definitions
- Logging settings

**Can be committed to Git**: ❌ **NO** (may contain sensitive info)
**Use**: 项目级配置，团队共享

---

### User Configuration

**File**: `~/.fastreact/config.json` (or `user_config.example.json` as template)

**Purpose**: 个人 API keys 和偏好设置

**Content**:
- API keys (SiliconFlow, OpenAI, etc.)
- GitHub tokens
- 个人偏好设置

**Can be committed to Git**: ❌ **NO** (绝对不要提交)
**Use**: 个人开发机器

**Location**:
- Windows: `C:\Users\<user>\.fastreact\config.json`
- Mac/Linux: `~/.fastreact/config.json`

---

### Environment Variables

**Variables**:
- `FASTREACT_API_KEY` - API key（覆盖所有配置）
- `FASTREACT_MODEL` - 模型名称覆盖
- `FASTREACT_BASE_URL` - API base URL 覆盖
- `GITHUB_PERSONAL_ACCESS_TOKEN` - GitHub token

**Use**: CI/CD、多租户、临时覆盖

---

## Security

### .gitignore 配置

```gitignore
# Sensitive configuration
config.json
config.*.json
config.local.json

# User configuration (personal API keys)
.fastreact/
!.fastreact/*.example

# Environment variables
.env
.env.local
```

### 安全检查

**运行安全检查**:
```bash
python test_config_priority.py
```

**验证**:
- ✅ 敏感信息不在项目配置
- ✅ 用户配置在 .gitignore 中
- ✅ 环境变量优先级正确

---

## Migration Guide

### 从旧配置迁移

**Before** (旧方式):
```json
{
  "llm": {
    "providers": {
      "siliconflow": {
        "api_key": "sk-xxx"
      }
    }
  }
}
```

**After** (新方式):
1. 项目配置 (`./config.json`): 移除 `api_key`
2. 用户配置 (`~/.fastreact/config.json`): 添加 `api_key`
3. 或者使用环境变量

**Setup**:
```bash
# 1. 创建用户配置
mkdir -p ~/.fastreact
cp user_config.example.json ~/.fastreact/config.json

# 2. 添加你的 keys
notepad ~/.fastreact/config.json

# 3. （可选）清理项目配置中的 keys
# 编辑 ./config.json，移除 api_key 字段
```

---

## Configuration Templates

### Available Templates

1. **`config.example.json`** - 项目配置模板
2. **`user_config.example.json`** - 用户配置模板

**Usage**:
```bash
# 复制模板
cp config.example.json config.json
cp user_config.example.json ~/.fastreact/config.json

# 编辑配置
notepad config.json
notepad ~/.fastreact/config.json
```

---

## Testing

### Test Configuration Priority

```bash
# 测试配置优先级
python test_config_priority.py

# 创建用户配置模板
python test_config_priority.py --create-user-config
```

### Expected Output

```
[Test 1] Default Configuration
API Key: YOUR_SILICONFLOW_KEY_HERE

[Test 2] Project Configuration Override
[OK] Project configuration loaded

[Test 3] User Configuration Override
[OK] User configuration loaded
API Key: sk-xxx...xxxx

[Test 4] Environment Variable Override
[OK] Environment variable loaded (highest priority)
```

---

## Benefits

### For Personal Developers
- ✅ 配置一次，永久生效
- ✅ 不用每次 `export API_KEY=...`
- ✅ API keys 安全存储在用户目录

### For Teams
- ✅ 项目配置可共享（不含 keys）
- ✅ 每个成员用自己的 keys
- ✅ 不会意外泄露团队 keys

### For CI/CD
- ✅ 环境变量优先级最高
- ✅ 不同环境用不同配置
- ✅ 符合 12-factor app 原则

### For Multi-Tenant
- ✅ 每个租户用环境变量
- ✅ 租户隔离
- ✅ 配置优先级清晰

---

## Troubleshooting

### Configuration Not Loading?

**Check**:
```bash
python test_config_priority.py
```

**Debug**:
1. 检查文件路径
2. 验证 JSON 格式
3. 查看日志输出

---

### API Key Not Found?

**Priority Check**:
1. 环境变量 `FASTREACT_API_KEY`
2. 用户配置 `~/.fastreact/config.json`
3. 项目配置 `./config.json`
4. 默认值

---

### Want to Override Temporarily?

**Use Environment Variables**:
```bash
export FASTREACT_API_KEY=sk-temp-key
export FASTREACT_MODEL=gpt-4

python -m fastreact.cli.main shell
```

---

## API Reference

### ConfigManager Class

```python
from fastreact.core.config_manager import ConfigManager

# Create manager
manager = ConfigManager(project_root=Path.cwd())

# Get configuration
config = manager.get_config()

# Get specific value
api_key = manager.get("llm.providers.siliconflow.api_key")
```

---

## Implementation Details

**Core Module**: `src/fastreact/core/config_manager.py`
- Implements the 4-layer configuration loading system
- Provides `ConfigManager` class with deep merge functionality

**Integration**: `src/fastreact/bootstrap/config_loader.py`
- Updated to use `ConfigManager` when available
- Falls back to 3-layer system for backward compatibility
- All CLI commands (`run`, `chat`, `shell`) now use the new system

**Key Methods**:
- `_load_all()` - 加载所有配置层
- `_load_project_config()` - 加载项目配置
- `_load_user_config()` - 加载用户配置
- `_load_env_vars()` - 加载环境变量
- `_deep_merge()` - 深度合并配置

**Usage in FastReAct**:
```python
from fastreact.bootstrap.config_loader import load_config, get_api_key

# Load merged configuration (4-layer priority)
config = load_config()

# Get API key (automatically finds from highest priority layer)
api_key = get_api_key(config)
```

---

**FastReAct = 安全、灵活的多层配置系统**
