# FastReAct Docker 快速参考

## 🚀 快速开始

### 验证 MCP 集成（推荐）

```powershell
test_docs\test_mcp_docker.bat
```

**预期输出**:
```
[INFO] Connecting to 'apollo_core' (native MCP client)...
[INFO] Connected to 'apollo_core'
[INFO] Loaded 2 tools from 'apollo_core'
[MCP-Tool] Calling apollo_core.generate_audit_code
[Result] AUDIT-HIGH-4812
```

### Web UI

```powershell
docker-compose up -d
# 访问 http://localhost:8765
```

### 命令行 REPL

```powershell
docker run -it --rm ^
  -v %cd%:/app ^
  -v %cd%\config:/app/config ^
  fastreact-app ^
  python -m fastreact.cli.main shell
```

---

## 📝 常用命令

### 构建镜像

```powershell
# 主应用
docker build -t fastreact-app .

# MCP Server
docker build -f test_docs/Dockerfile -t apollo-mcp-server .

# 测试镜像
docker build -f test_docs/Dockerfile.test -t fastreact-mcp-test .
```

### 容器管理

```powershell
# 列出容器
docker ps

# 停止所有
docker-compose down

# 查看日志
docker-compose logs -f

# 进入容器
docker exec -it fastreact bash
```

---

## 🔧 配置 MCP

`config.json`:
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

## ✅ 验证清单

- [ ] Docker Desktop 运行中
- [ ] 镜像构建成功
- [ ] MCP 测试通过 (4/4)
- [ ] Web UI 可访问 (http://localhost:8765)
- [ ] REPL 可用

---

## 📖 完整文档

详见: `DOCKER_DEPLOYMENT.md`
