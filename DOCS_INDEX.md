# FastReAct Documentation Index

## Overview

FastReAct 文档已经整理，分为核心文档、功能文档和技术文档三类。

---

## 📚 Core Documentation

### User-Facing
- **[README.md](README.md)** - 项目主页，快速了解 FastReAct
- **[INSTALLATION.md](INSTALLATION.md)** - 安装指南

### Developer-Facing
- **[CLAUDE.md](CLAUDE.md)** - 开发规则和约束（Development Rules & Constraints）
- **[DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md)** - 开发历程（Chronological History）

---

## 🎯 Feature Documentation

### Multi-Tenant & Workspace
- **[MULTI_TENANT_WORKSPACE.md](MULTI_TENANT_WORKSPACE.md)** - 多租户工作区支持
- **[WORKSPACE_ISOLATION.md](WORKSPACE_ISOLATION.md)** - 工作区隔离机制

### Session Management
- **[SESSION_RESUME.md](SESSION_RESUME.md)** - 会话恢复功能

### MCP Integration
- **[MCP_INTEGRATION_SUCCESS.md](MCP_INTEGRATION_SUCCESS.md)** - MCP 集成完整历程
- **[GITHUB_MCP_INTEGRATION.md](GITHUB_MCP_INTEGRATION.md)** - GitHub MCP 集成指南 (TODO #16)

### Cross-Platform
- **[CROSS_PLATFORM_SUMMARY.md](CROSS_PLATFORM_SUMMARY.md)** - 跨平台兼容性总结

### Version Management
- **[VERSION_MANAGEMENT.md](VERSION_MANAGEMENT.md)** - 版本管理指南

---

## 🔧 Technical Documentation

### Configuration
- **[CONFIG.md](CONFIG.md)** - 配置文件说明
- **[CONFIG_PRIORITY.md](CONFIG_PRIORITY.md)** - 配置优先级管理（多层配置）

### Development Process
- **[IEL.md](IEL.md)** - IEL (Interactive Execution Loop) 完整指南

### Release
- **[CHANGELOG.md](CHANGELOG.md)** - 版本更新日志

### Security
- **[SECURITY.md](SECURITY.md)** - 安全策略

### Docker
- **[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)** - Docker 部署指南
- **[DOCKER_QUICKREF.md](DOCKER_QUICKREF.md)** - Docker 快速参考

---

## 📦 Archived Documentation

历史文档和开发过程文档已归档到 `docs_archive/` 目录：

- IEL 重构过程文档（PHASE 1-5）
- 测试报告和集成测试文档
- 早期版本文档（V0, WSL 特定）
- 功能总结文档（已整合到主文档）

查看归档索引：
```bash
cat docs_archive/INDEX.md
```

---

## 📖 Documentation Structure

```
FastReAct/
├── README.md                    # 项目主页
├── INSTALLATION.md              # 安装指南
├── CLAUDE.md                    # 开发规则
├── DEVELOPMENT_LOG.md           # 开发历程
├── CONFIG.md                    # 配置说明
│
├── MULTI_TENANT_WORKSPACE.md   # 多租户功能
├── WORKSPACE_ISOLATION.md      # 工作区隔离
├── SESSION_RESUME.md           # 会话恢复
├── MCP_INTEGRATION_SUCCESS.md  # MCP 集成
├── CROSS_PLATFORM_SUMMARY.md   # 跨平台兼容
├── VERSION_MANAGEMENT.md        # 版本管理
│
├── IEL.md                       # IEL 指南
├── CHANGELOG.md                 # 更新日志
├── SECURITY.md                  # 安全
├── DOCKER_DEPLOYMENT.md        # Docker 部署
├── DOCKER_QUICKREF.md           # Docker 快速参考
│
└── docs_archive/               # 历史文档
    ├── INDEX.md                 # 归档索引
    ├── IEL_PHASE*.md           # IEL 开发过程
    ├── TEST_*.md               # 测试报告
    └── ...
```

---

## 🎯 Quick Links

### For Users
1. [Getting Started](README.md)
2. [Installation](INSTALLATION.md)
3. [New Environment Setup](NEW_ENVIRONMENT_SETUP.md) ← NEW!
4. [Configuration](CONFIG.md)
5. [Configuration Priority](CONFIG_PRIORITY.md) ← NEW!

### For Developers
1. [Development Rules](CLAUDE.md)
2. [Development History](DEVELOPMENT_LOG.md)
3. [Version Management](VERSION_MANAGEMENT.md)
4. [Cross-Platform Development](CROSS_PLATFORM_SUMMARY.md)

### Feature Docs
1. [Multi-Tenant Workspace](MULTI_TENANT_WORKSPACE.md)
2. [Workspace Isolation](WORKSPACE_ISOLATION.md)
3. [Session Resume](SESSION_RESUME.md)
4. [Multi-line Input](MULTILINE_INPUT.md) ← NEW!
5. [MCP Integration](MCP_INTEGRATION_SUCCESS.md)
6. [Gateway & Web UI](GATEWAY_WEB_EVALUATION.md) ← NEW!

### System Docs
1. [Memory Systems Integration](MEMORY_SYSTEMS_INTEGRATION.md) ← NEW!
2. [Memory Flush & Compaction](MEMORY_FLUSH_COMPACTION_INTERACTION.md) ← NEW!
3. [Memory Flush Bug Analysis](MEMORY_FLUSH_BUG_ANALYSIS.md) ← NEW!

---

## 📝 Documentation Guidelines

### Adding New Documentation

1. **用户文档** - 放在根目录，中英文均可
2. **功能文档** - 命名为 `FEATURE_NAME.md`
3. **技术文档** - 描述实现细节
4. **归档** - 移动到 `docs_archive/`

### Naming Conventions

- 使用大写 snake_case: `MULTI_TENANT_WORKSPACE.md`
- 功能文档: `<FEATURE_NAME>.md`
- 技术文档: `<TOPIC>.md`

### Updating Documentation

1. 修改文档内容
2. 更新相关链接
3. 运行 `python scripts/quick_check.py` 确保无 emoji
4. 提交到版本控制

---

**FastReAct Documentation = 清晰、完整、易维护**
