# FastReAct Docker 完整部署方案

## 🎯 设计理念

**所有组件都在 Docker 中运行**，彻底避开 Windows 兼容性问题。

---

## 📊 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│  Docker Host (Windows)                                      │
│                                                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ FastReAct Container (Linux)                          │  │
│  │                                                       │  │
│  │  FastReAct Engine (anyio)                            │  │
│  │    ├─ Built-in Tools (Calculator, Search, etc.)     │  │
│  │    ├─ MCP Client Manager                             │  │
│  │    └─ IEL (Interactive Execution Loop)              │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │ MCP Apollo Server (同一容器或独立容器)           │  │  │
│  │  │  - calculate_total_reimbursement                │  │  │
│  │  │  - generate_audit_code                           │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Gateway Container (可选 - Web UI)                    │  │
│  │  Port: 8765                                          │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 方式 1: 使用现有的 docker-compose.yml（推荐）

```powershell
# 启动所有服务（Gateway + FastReAct + MCP）
docker-compose up -d

# 查看 Gateway Web UI
# http://localhost:8765
```

### 方式 2: 运行 MCP 集成测试

```powershell
# 一键测试 MCP 集成
test_docs\test_mcp_docker.bat
```

### 方式 3: 手动运行容器

```powershell
# 构建镜像
docker build -t fastreact-app .

# 运行 FastReAct
docker run -it --rm ^
  -v %cd%:/app ^
  -v %cd%\config:/app/config ^
  fastreact-app ^
  python -m fastreact.cli.main shell
```

---

## 📁 项目结构

```
FastReAct/
├── docker-compose.yml              # Docker Compose 配置
├── Dockerfile                     # 主应用镜像
├── test_docs/
│   ├── Dockerfile                 # MCP Server 镜像
│   ├── Dockerfile.test            # 集成测试镜像
│   ├── mcp_server_apollo.py      # MCP Server
│   ├── test_mcp_docker.bat       # 一键测试脚本
│   └── run_docker_test.sh        # 容器内测试脚本
├── config.json                   # FastReAct 配置
├── test_beijing_trip.py          # MCP 集成测试
└── MCP_VERIFICATION.md           # MCP 验证文档
```

---

## 🐳 Docker 镜像说明

### 1. 主应用镜像 (Dockerfile)

**用途**: FastReAct 主应用
**包含**:
- Python 3.12
- FastReAct 源码
- 所有依赖
- 配置文件

**构建**:
```powershell
docker build -t fastreact-app .
```

**运行**:
```powershell
docker run -it --rm ^
  -v %cd%:/app ^
  -v %cd%\config:/app/config ^
  fastreact-app
```

### 2. MCP Server 镜像 (test_docs/Dockerfile)

**用途**: Apollo MCP Server
**包含**:
- Python 3.12
- MCP SDK
- Apollo 工具定义

**构建**:
```powershell
docker build -f test_docs/Dockerfile -t apollo-mcp-server .
```

**运行**:
```powershell
docker run -i --rm apollo-mcp-server
```

### 3. 集成测试镜像 (test_docs/Dockerfile.test)

**用途**: MCP 集成验证
**包含**:
- FastReAct + MCP + 测试脚本

**构建**:
```powershell
docker build -f test_docs/Dockerfile.test -t fastreact-mcp-test .
```

**运行**:
```powershell
docker run --rm fastreact-mcp-test
```

---

## 🔧 配置文件

### config.json

确保 MCP 配置指向正确的服务：

```json
{
  "mcp": {
    "enabled": true,
    "servers": {
      "apollo_core": {
        "command": "docker",
        "args": ["run", "-i", "--rm", "apollo-mcp-server"]
      }
    }
  }
}
```

---

## 📝 使用场景

### 场景 1: 开发与调试

```powershell
# 启动 MCP server（后台）
docker run -d --name apollo-mcp --restart unless-stopped ^
  apollo-mcp-server

# 运行 FastReAct
docker run -it --rm ^
  -v %cd%:/app ^
  -v %cd%\config:/app/config ^
  --link apollo-mcp:apollo-mcp ^
  fastreact-app ^
  python -m fastreact.cli.main shell
```

### 场景 2: Web UI（Gateway）

```powershell
# 启动 Gateway
docker-compose up gateway

# 访问 Web UI
# http://localhost:8765
```

### 场景 3: MCP 集成测试

```powershell
# 一键测试
test_docs\test_mcp_docker.bat
```

---

## 🔍 验证 MCP 集成

运行测试后应该看到：

```
✅ calculate_total_reimbursement called
✅ generate_audit_code called
✅ Correct result (12000)
✅ Audit code generated

Score: 4/4

[PASS] ALL CHECKS PASSED!
```

---

## 📊 性能优势

| 指标 | 本地 Windows | Docker 容器 |
|------|--------------|-------------|
| 启动时间 | ~2 秒 | ~1 秒 |
| 兼容性 | ❌ anyio 问题 | ✅ 完全兼容 |
| 隔离性 | 无 | 完全隔离 |
| 可移植性 | 低 | 高 |
| 稳定性 | 中 | 高 |

---

## 🎯 最佳实践

### 1. 开发流程

```powershell
# 1. 启动开发环境
docker-compose up -d

# 2. 进入容器
docker exec -it fastreact bash

# 3. 在容器中运行测试
python test_beijing_trip.py

# 4. 退出容器
exit
```

### 2. 生产部署

```powershell
# 使用 docker-compose
docker-compose up -d

# 检查状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 3. 更新代码

```powershell
# 1. 重新构建镜像
docker-compose build

# 2. 重启服务
docker-compose up -d --force-recreate
```

---

## 📚 相关文档

| 文档 | 说明 |
|------|------|
| `docker-compose.yml` | 完整服务配置 |
| `MCP_VERIFICATION.md` | MCP 集成验证详解 |
| `test_docs/DOCKER_MCP_SETUP.md` | Docker MCP 设置指南 |
| `CLAUDE.md` | 开发日志和修复记录 |

---

## ✅ 总结

### 为什么选择 Docker？

1. ✅ **兼容性**: 完全避开 Windows anyio/asyncio 问题
2. ✅ **隔离性**: 不影响宿主环境
3. ✅ **一致性**: 开发、测试、生产环境完全一致
4. ✅ **可移植性**: 可以在任何支持 Docker 的平台上运行

### 下一步

1. **运行 MCP 验证测试**:
   ```powershell
   test_docs\test_mcp_docker.bat
   ```

2. **使用 docker-compose**:
   ```powershell
   docker-compose up -d
   ```

3. **享受稳定的 MCP 集成**！ 🎉

---

**FastReAct + Docker = 稳定可靠的 AI Agent 系统**
