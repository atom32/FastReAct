# FastReAct 配置文件位置说明

**版本**: 2.4.2
**更新日期**: 2025-02-19

---

## 核心原则

**所有 Adapter 共用同一个配置文件**！

Gateway、Feishu、CLI 等所有 adapter 都使用同一个配置系统，**不是每个 adapter 单独的配置文件**。

---

## 配置文件搜索顺序

Config.load() 会按以下顺序搜索配置文件（找到第一个就停止）：

```
1. ~/.fastreact/config.json              ← 最高优先级（用户级配置）
2. ./.fastreact/config.json              ← 项目级配置
3. ./config.json                        ← 项目根目录配置
```

### 查看当前生效的配置

```bash
# 运行诊断脚本
python3 diagnose_agent.py

# 输出会显示实际加载的配置路径
```

---

## 配置文件位置详解

### 1. 用户级配置（推荐）

**位置**: `~/.fastreact/config.json`

**适用场景**:
- ✅ 个人开发（所有项目共用）
- ✅ 多个项目使用同一配置
- ✅ API Key 等敏感信息（不上传到 Git）

**创建方法**:
```bash
# 创建目录
mkdir -p ~/.fastreact

# 创建配置文件
cat > ~/.fastreact/config.json << 'EOF'
{
  "llm": {
    "model": "deepseek-ai/DeepSeek-V3",
    "api_base": "https://api.siliconflow.cn/v1",
    "api_key": "sk-your-real-api-key-here"
  }
}
EOF
```

**优先级**: 最高（会覆盖其他位置的配置）

---

### 2. 项目级配置

**位置**: `/Users/xudawei/FastReAct/fastreact-nano/.fastreact/config.json`

**适用场景**:
- ✅ 项目特定配置
- ✅ 团队共享配置（可以提交到 Git）
- ✅ 示例配置

**创建方法**:
```bash
# 在项目根目录
cd /Users/xudawei/FastReAct/fastreact-nano

# 创建配置文件
mkdir -p .fastreact
cat > .fastreact/config.json << 'EOF'
{
  "llm": {
    "model": "gpt-4o-mini",
    "api_key": "sk-project-specific-key"
  }
}
EOF
```

**注意**:
- ⚠️ 如果存在 `~/.fastreact/config.json`，**项目配置会被忽略**
- ✅ 可以添加到 `.gitignore`，避免提交敏感信息

---

### 3. 根目录配置（兼容性）

**位置**: `/Users/xudawei/FastReAct/fastreact-nano/config.json`

**适用场景**:
- ✅ 兼容旧版本
- ✅ 简单项目

**注意**:
- ⚠️ 优先级最低（如果没有其他配置文件才会使用）
- ⚠️ 不推荐使用

---

## 当前项目实际使用的配置

### Gateway（单租户）

**当前生效的配置**:
```bash
$ cat ~/.fastreact/config.json
```

**内容**:
```json
{
  "llm": {
    "model": "deepseek-ai/DeepSeek-V3.2",
    "api_base": "https://api.siliconflow.cn/v1",
    "api_key": "sk-xxx"  ← 占位符，需要替换！
  }
}
```

**问题**: API Key 是 `sk-xxx`，不是真实的！

---

### Feishu（多租户）

Feishu 也使用**同一个配置文件**，但会读取额外的 Feishu 特定配置：

```json
{
  "llm": { ... },
  "feishu": {
    "app_id": "cli_xxx",
    "app_secret": "xxx",
    "enable_multitenant": true
  }
}
```

---

## 临时配置

启动配置不再通过环境变量覆盖。需要临时切换模型、API base、service token
或 PSKA 设置时，复制一份 JSON config，然后显式传给启动命令：

```bash
cp ~/.fastreact/config.json /tmp/fastreact-test-config.json
python3 -m fastreact.adapters.http --config /tmp/fastreact-test-config.json
```
- ✅ Docker 容器

---

## 推荐配置方式

### 方案 1: 用户级配置（推荐）

```bash
# 1. 创建用户级配置
mkdir -p ~/.fastreact
cat > ~/.fastreact/config.json << 'EOF'
{
  "llm": {
    "model": "gpt-4o-mini",
    "api_base": "https://api.openai.com/v1",
    "api_key": "sk-your-real-openai-key"
  },
  "mcp": {
    "servers": [
      {
        "name": "timeserver",
        "command": "uvx",
        "args": ["--from", "mcp_servers/builtin/timeserver", "mcp-timeserver"],
        "isolation": "shared",
        "description": "Current time and date information"
      }
    ]
  }
}
EOF

# 2. 添加到 .gitignore（避免提交敏感信息）
echo ".fastreact/" >> .gitignore

# 3. 验证配置
python3 diagnose_agent.py
```

**优点**:
- ✅ 所有项目共用
- ✅ 敏感信息不在项目目录
- ✅ 一次配置，到处使用

---

### 方案 2: 项目级单一配置

```bash
# 1. 创建项目配置
mkdir -p .fastreact
cat > .fastreact/config.json << 'EOF'
{
  "llm": {
    "model": "gpt-4o-mini",
    "api_base": "https://api.openai.com/v1",
    "api_key": "sk-your-real-api-key"
  },
  "service": {
    "host": "127.0.0.1",
    "port": 8000,
    "service_token": "replace-with-local-service-token"
  }
}
EOF

# 2. 添加到 .gitignore，避免提交本机敏感配置
echo ".fastreact/config.json" >> .gitignore
```

**优点**:
- ✅ 项目配置可控
- ✅ 启动输入唯一
- ✅ 团队协作友好

---

## 验证配置

### 查看当前生效的配置

```bash
# 方法 1: 诊断脚本
python3 diagnose_agent.py

# 方法 2: 直接查看
python3 -c "from fastreact.core.config import Config; import json; c = Config.load(); print(json.dumps(c.__dict__, indent=2, default=str))"
```

### 测试 API Key 是否有效

```bash
# 设置测试 API Key
export FASTRACT_API_KEY=sk-test-key

# 运行诊断
python3 diagnose_agent.py

# 预期看到:
# ❌ API Key 无效: sk-test-key
```

---

## 常见问题

### Q1: 我修改了配置文件，为什么没有生效？

**A**: 检查配置优先级：
```bash
# 1. 检查用户级配置（会覆盖项目配置）
cat ~/.fastreact/config.json

# 2. 如果存在，删除或重命名
mv ~/.fastreact/config.json ~/.fastreact/config.json.bak

# 3. 重启 Gateway
```

### Q2: 如何在不同项目使用不同的 API Key？

**A**: 使用项目级配置：
```bash
# 项目 A
cd /path/to/project-a
mkdir -p .fastreact
cat > .fastreact/config.json << EOF
{"llm": {"api_key": "sk-key-a"}}
EOF

# 项目 B
cd /path/to/project-b
mkdir -p .fastreact
cat > .fastreact/config.json << EOF
{"llm": {"api_key": "sk-key-b"}}
EOF
```

### Q3: Gateway 和 Feishu 可以用不同的配置吗？

**A**: 可以，但都在同一个配置文件中：
```json
{
  "llm": {
    "api_key": "sk-shared-key"  ← Gateway 和 Feishu 共用
  },
  "feishu": {
    "app_id": "cli_xxx",        ← Feishu 特定
    "app_secret": "xxx",
    "enable_multitenant": true
  }
}
```

---

## 总结

### 配置文件位置（优先级从高到低）

```
1. ~/.fastreact/config.json           ← 用户级（推荐）
2.
./.fastreact/config.json       ← 项目级
3. ./config.json                     ← 根目录（兼容）
```

### 核心原则

- ✅ **所有 Adapter 共用配置**（Gateway、Feishu、CLI）
- ✅ **优先级明确**（用户级 > 项目级 > 根目录）
- ✅ **显式 config 文件**（临时测试复制 config，不靠环境变量覆盖）

### 推荐做法

```bash
# 个人开发：使用用户级配置
mkdir -p ~/.fastreact
# 编辑 ~/.fastreact/config.json

# 团队协作：提交 config.example.json，个人复制到 .fastreact/config.json
# 敏感信息放在本机 .fastreact/config.json，或用 llm.api_key_file 显式指向本机 key 文件
```

---

**维护者**: Claude Code
**最后更新**: 2025-02-19
**版本**: 2.4.2
