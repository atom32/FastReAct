# New Environment Setup Guide

## 新开发环境配置指南

在一个新的开发环境中设置 FastReAct。

---

## 快速开始（3 步）

### 1. 获取代码

```bash
git clone https://github.com/atom32/FastReAct.git
cd FastReAct
```

### 2. 安装依赖

```bash
# 使用虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装 FastReAct
pip install -e .
```

### 3. 配置 API Keys

**方法 A（推荐）**：使用用户配置文件

```bash
# 创建用户配置目录
mkdir -p ~/.fastreact

# 复制模板
cp user_config.example.json ~/.fastreact/config.json

# 编辑配置，添加你的 API keys
notepad ~/.fastreact/config.json  # Windows
nano ~/.fastreact/config.json     # Linux/Mac
```

**方法 B**：使用项目配置文件

```bash
# 复制项目配置模板
cp config.example.json config.json

# 编辑配置，添加你的 API keys
# 警告：不要提交 config.json 到 git！
notepad config.json
```

**配置示例**：

```json
{
  "llm": {
    "providers": {
      "siliconflow": {
        "api_key": "sk-your-actual-api-key-here"
      }
    }
  },
  "tools": {
    "tavily": {
      "api_key": "tvly-your-tavily-key-here"
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

## 配置文件说明

### config.example.json（项目配置模板）

**包含内容**：
- ✓ 完整的项目配置结构
- ✓ MCP servers 配置（GitHub, Apollo Core）
- ✓ Memory Flush 配置
- ✓ Progressive Compaction 配置
- ✓ RAG 配置
- ✓ 所有工具配置

**不包含**：
- ✗ API keys（使用占位符 `YOUR_*_HERE`）
- ✗ 敏感 tokens

**用途**：
```
config.example.json → 新环境中复制为 config.json
→ 添加个人 API keys
→ 开始使用
```

### user_config.example.json（用户配置模板）

**包含内容**：
- ✓ 个人 API keys 结构
- ✓ MCP tokens 结构

**用途**：
```
user_config.example.json → 复制到 ~/.fastreact/config.json
→ 添加个人 API keys
→ 项目配置和个人配置分离
```

---

## MCP Servers 配置

### GitHub MCP（默认可用）

**要求**：
- GitHub Personal Access Token
- 权限：repo, issues

**配置**：
```json
{
  "mcp": {
    "servers": {
      "github": {
        "env": {
          "GITHUB_PERSONAL_ACCESS_TOKEN": "your-token-here"
        }
      }
    }
  }
}
```

**获取 Token**：
1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 勾选 `repo` 和 `issues` 权限
4. 生成并复制 token

### Apollo Core MCP（需要 Docker）

**要求**：
- Docker 安装并运行
- Apollo MCP server 容器

**配置**：
```json
{
  "mcp": {
    "servers": {
      "apollo_core": {
        "command": "docker",
        "args": ["run", "-i", "--rm", "apollo-mcp-server"]
      }
    }
  }
}
```

**启动容器**：
```bash
# 注意：start_apollo_server.py 在 test_docs/ 目录中（不会提交到 git）
# 如果需要，可以从旧环境复制这个文件

# 或者使用 docker-compose
docker-compose -f docker-compose.mcp.yml up -d
```

---

## 配置优先级（多租户支持）

FastReAct 支持四层配置加载：

```
1. ENV (环境变量)        ← 最高优先级
2. USER (~/.fastreact/config.json)
3. PROJECT (./config.json)
4. DEFAULT (代码默认值)   ← 最低优先级
```

### 使用场景

**场景 A：个人开发（推荐）**
```bash
# 一次性设置用户配置
mkdir -p ~/.fastreact
cp user_config.example.json ~/.fastreact/config.json
# 添加你的 API keys

# 之后直接启动
python -m fastreact.cli.main shell
```

**场景 B：团队协作**
```bash
# 项目配置：config.json（不含 keys，团队共享）
# 个人配置：~/.fastreact/config.json（个人 keys）
# 每个成员用自己的 API keys
```

**场景 C：CI/CD 或多租户**
```bash
# 使用环境变量
export FASTREACT_API_KEY=sk-tenant-a-key
export GITHUB_PERSONAL_ACCESS_TOKEN=ghp-tenant-a-token

python -m fastreact.cli.main shell
```

---

## 新环境配置检查清单

### 必需配置

- [ ] Python 3.10+ 已安装
- [ ] 虚拟环境已创建
- [ ] FastReAct 已安装 (`pip install -e .`)
- [ ] API key 已配置（~/.fastreact/config.json 或 config.json）

### 可选配置

- [ ] Tavily API key（用于 Web Search）
- [ ] GitHub Personal Access Token（用于 GitHub MCP）
- [ ] Apollo MCP server（Docker 容器）
- [ ] 本地嵌入模型（`models/Qwen/Qwen3-Embedding-0.6B`）

### 验证安装

```bash
# 运行测试脚本
python test_config_priority.py

# 启动 REPL
python -m fastreact.cli.main shell

# 测试简单查询
>>> What is 2 + 2?
```

---

## 常见问题

### Q: config.json 和 ~/.fastreact/config.json 有什么区别？

**A**:
- `config.json`：项目配置，团队共享（不含敏感信息）
- `~/.fastreact/config.json`：个人配置，包含 API keys

**推荐**：使用 `~/.fastreact/config.json`，避免意外提交 API keys。

### Q: MCP servers 配置在哪里？

**A**:
- MCP servers 配置在 `config.json` 中
- 但敏感 tokens（GitHub token）应该放在 `~/.fastreact/config.json`
- 两者会自动合并

### Q: 为什么 Apollo Core 提到 test_docs/start_apollo_server.py？

**A**:
- `test_docs/` 目录包含测试和临时文件
- 不会提交到 git（在 .gitignore 中）
- 如果需要 Apollo Core，可以从旧环境复制这个文件
- 或使用 `docker-compose.mcp.yml` 启动

### Q: 如何验证配置是否正确？

**A**:
```bash
# 运行配置测试
python test_config_priority.py

# 检查 API key 加载
python -c "
from fastreact.bootstrap.config_loader import load_config, get_api_key
config = load_config()
try:
    api_key = get_api_key(config)
    print(f'[OK] API key loaded: {api_key[:20]}...')
except ValueError as e:
    print(f'[ERROR] {e}')
"
```

---

## 下一步

配置完成后，你可以：

1. **启动 REPL**
   ```bash
   python -m fastreact.cli.main shell
   ```

2. **启用 Gateway + Web UI**
   ```bash
   # 终端 1：启动 Gateway
   python scripts/run_gateway.py

   # 终端 2：启动 Web UI
   cd ../FastReAct-web
   npm run dev

   # 浏览器：http://localhost:3001
   ```

3. **测试 MCP Integration**
   ```bash
   # 在 REPL 中测试 GitHub MCP
   >>> Create a GitHub issue for repository test-repo
   ```

4. **启用 RAG（可选）**
   ```json
   // 在 config.json 中设置
   {
     "context": {
       "retrieval": {
         "enabled": true
       }
     }
   }
   ```

---

**快速配置命令**：

```bash
# 一键设置（Unix/Linux/Mac）
cp config.example.json config.json && \
mkdir -p ~/.fastreact && \
cp user_config.example.json ~/.fastreact/config.json && \
echo "请编辑 ~/.fastreact/config.json 添加你的 API keys"

# Windows
copy config.example.json config.json
mkdir %USERPROFILE%\.fastreact
copy user_config.example.json %USERPROFILE%\.fastreact\config.json
notepad %USERPROFILE%\.fastreact\config.json
```
