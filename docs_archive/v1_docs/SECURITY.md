# ⚠️ 安全注意事项

## 🔐 保护你的API密钥

### 不要提交敏感信息

以下文件包含敏感信息，**绝对不要提交到Git**：
- `config.json` - 包含真实API密钥
- `.env` - 包含环境变量和密钥
- 任何包含 `api_key`、`password`、`token` 的文件

### .gitignore 已配置

`.gitignore` 已配置忽略以下文件：
```
config.json
.env
*.log
*.db
```

### 设置你的配置

FastReAct 支持两种配置方式，**推荐使用 `config.json`**。

#### 方式1：config.json（推荐）

```bash
# 1. 复制示例配置
cp config.json.example config.json

# 2. 编辑配置文件
vim config.json  # 或使用你喜欢的编辑器

# 3. 填入你的API密钥
```

#### 方式2：.env（备选）

```bash
# 1. 复制示例配置
cp .env.example .env

# 2. 编辑环境变量
vim .env

# 3. 需要安装 python-dotenv
pip install python-dotenv
```

> 📖 **详见**: [CONFIG.md](CONFIG.md) - 完整配置指南

### 确保配置不被追踪

```bash
# 检查git状态（config.json 和 .env 不应该出现）
git status

# 如果意外提交了，立即删除
git rm --cached config.json
git rm --cached .env
git commit -m "Remove sensitive config"
```

### 环境变量方式（直接设置）

如果你不想使用配置文件，也可以直接设置环境变量：

```bash
# Linux/Mac
export OPENAI_API_KEY="sk-your-key"
export SILICONFLOW_API_KEY="sk-your-key"

# Windows (CMD)
set OPENAI_API_KEY=sk-your-key
set SILICONFLOW_API_KEY=sk-your-key

# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-your-key"
$env:SILICONFLOW_API_KEY="sk-your-key"
```

然后在代码中使用：
```python
import os
api_key = os.getenv("OPENAI_API_KEY")
```

### 常见错误

❌ **错误做法**：
- 把 `config.json` 提交到仓库
- 在代码中硬编码API密钥
- 在公开的Issue中粘贴密钥
- 把密钥发到聊天记录或邮件中

✅ **正确做法**：
- 使用 `config.json.example` 作为模板
- 使用环境变量存储密钥
- 定期轮换API密钥
- 使用密钥管理服务（如AWS Secrets Manager）

### 如果密钥已泄露

1. 立即到API提供商处撤销密钥
2. 生成新的密钥
3. 更新本地配置
4. 检查Git历史，确保已删除泄露的记录

---

**记住：API密钥等同于密码，务必妥善保管！**
