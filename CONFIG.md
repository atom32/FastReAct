# 配置说明

FastReAct 支持两种配置方式，推荐使用 **config.json**。

---

## 🎯 推荐方式：config.json（新）

### 优点
- ✅ 支持多个LLM提供商
- ✅ 结构化配置，易于管理
- ✅ 支持嵌套和复杂配置
- ✅ 有专门的配置管理器

### 使用方法

1. **复制模板**：
```bash
cp config.json.example config.json
```

2. **编辑配置**：
```json
{
  "llm": {
    "providers": {
      "siliconflow": {
        "enabled": true,
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key": "你的真实API密钥",
        "model": "deepseek-ai/DeepSeek-V3"
      }
    },
    "default_provider": "siliconflow"
  }
}
```

3. **在代码中使用**：
```python
from fastreact.utils.config import get_config

config = get_config()
llm_config = config.get_llm_config()

# 使用配置
api_key = llm_config["api_key"]
base_url = llm_config["base_url"]
model = llm_config["model"]
```

### 切换提供商

只需修改 `default_provider`：
```json
{
  "llm": {
    "default_provider": "openai"  // 或 "ollama"
  }
}
```

---

## 🔧 备选方式：.env（旧）

### 适用场景
- 部署到容器环境（Docker、K8s）
- CI/CD管道
- 传统12-factor应用

### 使用方法

1. **创建 .env 文件**：
```bash
cp .env.example .env
```

2. **编辑环境变量**：
```env
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
```

3. **在代码中读取**：
```python
import os
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件

api_key = os.getenv("OPENAI_API_KEY")
```

**注意**: 需要先安装 `python-dotenv`

---

## 📌 两种方式对比

| 特性 | config.json | .env |
|------|-------------|------|
| 多提供商支持 | ✅ 原生支持 | ❌ 需要多个变量 |
| 结构化配置 | ✅ JSON嵌套 | ❌ 扁平结构 |
| 易读性 | ✅ 清晰直观 | ⚠️ 较难阅读 |
| 容器部署 | ⚠️ 需要挂载文件 | ✅ 原生支持 |
| 环境变量集成 | ❌ 需要转换 | ✅ 直接使用 |
| 配置管理器 | ✅ 专门支持 | ❌ 无 |

---

## 🎯 推荐配置

### 开发环境
**使用 config.json**（推荐）

### 生产环境
**选项1**: config.json（配置文件管理）
**选项2**: 环境变量（.env或直接设置）

### 容器部署
**使用环境变量**
```yaml
# docker-compose.yml
environment:
  - OPENAI_API_KEY=${OPENAI_API_KEY}
  - OPENAI_BASE_URL=${OPENAI_BASE_URL}
```

---

## ⚙️ 迁移指南

### 从 .env 迁移到 config.json

**旧方式**:
```env
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4
```

**新方式**:
```json
{
  "llm": {
    "providers": {
      "openai": {
        "api_key": "sk-xxx",
        "model": "gpt-4",
        "base_url": "https://api.openai.com/v1"
      }
    },
    "default_provider": "openai"
  }
}
```

---

## 🔐 安全提示

无论使用哪种方式，都不要提交包含真实密钥的文件！

- ✅ `config.json.example` - 可提交
- ✅ `.env.example` - 可提交
- ❌ `config.json` - 不要提交（已在.gitignore）
- ❌ `.env` - 不要提交（已在.gitignore）

---

**总结**: 推荐 **config.json**，功能更强，更易管理！
