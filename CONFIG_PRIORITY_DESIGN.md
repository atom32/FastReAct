# FastReAct 配置优先级设计

## 问题

**多租户场景**：
- API key 是个人的，不应该放在项目 config 里
- 不同用户有不同的 key
- 不想每次都设置环境变量

**个人使用场景**：
- 在自己的机器上开发
- 不想每次都 `export API_KEY=...`
- 希望配置一次，永久生效

---

## 解决方案：多层次配置加载

### 配置优先级

```python
FINAL_CONFIG = merge(
    DEFAULTS,           # 最低优先级
    PROJECT_CONFIG,     # ./config.json
    USER_CONFIG,        # ~/.fastreact/config.json
    ENV_VARS            # 最高优先级
)
```

---

## 配置文件结构

### 1. 项目配置 (`./config.json`)

**用途**：项目共享配置，不包含敏感信息

**示例**：
```json
{
  "llm": {
    "default_provider": "siliconflow",
    "timeout_seconds": 60
  },
  "mcp": {
    "enabled": true,
    "servers": {
      "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"]
      }
    }
  }
}
```

**特点**：
- ✅ 可以提交到 Git
- ✅ 团队共享
- ❌ 不包含 API keys

---

### 2. 用户配置 (`~/.fastreact/config.json`)

**用途**：个人配置，包含敏感信息

**路径**：
- Windows: `C:\Users\<user>\.fastreact\config.json`
- Mac/Linux: `~/.fastreact/config.json`

**示例**：
```json
{
  "llm": {
    "providers": {
      "siliconflow": {
        "api_key": "sk-your-personal-key"
      },
      "openai": {
        "api_key": "sk-your-openai-key"
      }
    }
  },
  "mcp": {
    "servers": {
      "github": {
        "env": {
          "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_your-github-token"
        }
      }
    }
  }
}
```

**特点**：
- ✅ 包含 API keys
- ✅ 个人机器独有
- ❌ 不提交到 Git（在 `.gitignore` 中）

---

### 3. 环境变量 (`.env` 或系统环境)

**用途**：临时覆盖、CI/CD、多租户

**示例**：
```bash
# .env
AIDEV_API_KEY=sk-team-key
AIDEV_GITHUB_TOKEN=ghp_team-token
```

**特点**：
- ✅ 最高优先级
- ✅ 不提交到 Git
- ✅ 适合 CI/CD

---

## 配置加载逻辑

### 实现代码

```python
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigManager:
    """多层次配置管理器"""

    def __init__(self):
        self.config = {}
        self._load_all()

    def _load_all(self):
        """按优先级加载配置"""
        # 1. 默认值
        self.config = self._get_defaults()

        # 2. 项目配置
        project_config = self._load_project_config()
        if project_config:
            self._deep_merge(self.config, project_config)

        # 3. 用户配置
        user_config = self._load_user_config()
        if user_config:
            self._deep_merge(self.config, user_config)

        # 4. 环境变量
        env_config = self._load_env_vars()
        if env_config:
            self._deep_merge(self.config, env_config)

    def _get_defaults(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "llm": {
                "default_provider": "siliconflow",
                "timeout_seconds": 60,
                "retry_attempts": 3
            },
            "mcp": {
                "enabled": False,
                "servers": {}
            }
        }

    def _load_project_config(self) -> Optional[Dict[str, Any]]:
        """加载项目配置 (./config.json)"""
        config_path = Path.cwd() / "config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def _load_user_config(self) -> Optional[Dict[str, Any]]:
        """加载用户配置 (~/.fastreact/config.json)"""
        # 获取用户主目录
        home = Path.home()
        config_dir = home / ".fastreact"
        config_path = config_dir / "config.json"

        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def _load_env_vars(self) -> Dict[str, Any]:
        """加载环境变量"""
        env_config = {}

        # API keys
        if os.getenv("FASTREACT_API_KEY"):
            if "llm" not in env_config:
                env_config["llm"] = {}
            if "providers" not in env_config["llm"]:
                env_config["llm"]["providers"] = {}

            provider = os.getenv("FASTREACT_PROVIDER", "siliconflow")
            if provider not in env_config["llm"]["providers"]:
                env_config["llm"]["providers"][provider] = {}

            env_config["llm"]["providers"][provider]["api_key"] = os.getenv("FASTREACT_API_KEY")

        # GitHub token
        if os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"):
            if "mcp" not in env_config:
                env_config["mcp"] = {}
            if "servers" not in env_config["mcp"]:
                env_config["mcp"]["servers"] = {}
            if "github" not in env_config["mcp"]["servers"]:
                env_config["mcp"]["servers"]["github"] = {}

            env_config["mcp"]["servers"]["github"]["env"] = {
                "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PERSONAL_ACCESS_TOKEN}"
            }

        return env_config

    def _deep_merge(self, base: Dict, update: Dict):
        """深度合并字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
```

---

## 使用示例

### 场景 1：个人开发（推荐配置）

**Step 1**: 创建用户配置
```bash
# 首次设置
mkdir -p ~/.fastreact
cat > ~/.fastreact/config.json << EOF
{
  "llm": {
    "providers": {
      "siliconflow": {
        "api_key": "sk-your-personal-key"
      },
      "openai": {
        "api_key": "sk-your-openai-key"
      }
    }
  }
}
EOF
```

**Step 2**: 启动 FastReAct
```bash
python -m fastreact.cli.main shell
# 自动从 ~/.fastreact/config.json 读取 keys
```

---

### 场景 2：团队开发

**项目配置** (`./config.json`):
```json
{
  "llm": {
    "default_provider": "openai"
  },
  "mcp": {
    "servers": { ... }
  }
}
```

**用户配置** (`~/.fastreact/config.json`):
```json
{
  "llm": {
    "providers": {
      "openai": {
        "api_key": "sk-my-key"
      }
    }
  }
}
```

**结果**：
- 使用 OpenAI（项目配置）
- API key 从个人配置读取
- 团队成员各用各的 key

---

### 场景 3：CI/CD 或多租户

**使用环境变量**：
```bash
export FASTREACT_API_KEY=sk-deployment-key
python -m fastreact.cli.main shell
```

**优先级**：
- 环境变量 > 用户配置 > 项目配置

---

## .gitignore 配置

```gitignore
# 用户配置（包含敏感信息）
.fastreact/
config.local.json

# 环境变量
.env
.env.local
```

---

## 配置模板

### 项目配置模板 (`config.example.json`)

```json
{
  "_comment": "FastReAct project configuration template",
  "_instructions": "Copy this file to config.json and customize",

  "llm": {
    "default_provider": "siliconflow",
    "timeout_seconds": 60
  },
  "mcp": {
    "enabled": true,
    "servers": {
      "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"]
      }
    }
  }
}
```

### 用户配置模板 (`user_config.example.json`)

```json
{
  "_comment": "FastReAct user configuration template",
  "_location": "~/.fastreact/config.json",
  "_purpose": "Personal API keys and preferences",

  "llm": {
    "providers": {
      "siliconflow": {
        "api_key": "your-siliconflow-key-here"
      },
      "openai": {
        "api_key": "your-openai-key-here"
      }
    }
  },
  "mcp": {
    "servers": {
      "github": {
        "env": {
          "GITHUB_PERSONAL_ACCESS_TOKEN": "your-github-token-here"
        }
      }
    }
  }
}
```

---

## 向后兼容

**当前项目配置** (`./config.json`)：
- 继续支持
- 包含 API keys 也行（向后兼容）
- 但建议迁移到用户配置

**迁移脚本**：
```bash
# 自动迁移 API keys 到用户配置
python scripts/migrate_config.py --to-user
```

---

## 优点

### 个人开发者
- ✅ 配置一次，永久生效
- ✅ API keys 不在项目里
- ✅ 不同项目用同一套 keys

### 团队协作
- ✅ 项目配置共享（不含敏感信息）
- ✅ 每个成员用自己的 keys
- ✅ 不用担心泄露团队 keys

### CI/CD
- ✅ 用环境变量覆盖
- ✅ 不同环境用不同 keys
- ✅ 安全合规

### 多租户（未来）
- ✅ 每个租户用环境变量
- ✅ 租户隔离
- ✅ 配置优先级清晰

---

## 实现优先级

**Phase 1**: 实现配置管理器
- [ ] 创建 `ConfigManager` 类
- [ ] 实现四层配置加载
- [ ] 添加配置合并逻辑

**Phase 2**: 迁移现有配置
- [ ] 更新配置加载代码
- [ ] 添加用户配置支持
- [ ] 保持向后兼容

**Phase 3**: 文档和工具
- [ ] 更新配置文档
- [ ] 添加配置迁移脚本
- [ ] 添加配置验证命令

---

## 要实现吗？

这是一个 **独立于重命名** 的功能改进。

**你想要**：
1. **现在就实现** → 我可以开始编码
2. **先设计一下** → 创建 GitHub issue 讨论
3. **作为 TODO** → 记录下来，以后做

选哪个？
