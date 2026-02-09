# FastReAct Documentation Index

## Overview

FastReAct 文档已精简，只保留核心和实用的文档。

---

## 核心文档 (Must Read)

### Getting Started
- **[README.md](README.md)** - 项目概述，当前状态 v1.1.0-alpha
- **[INSTALLATION.md](INSTALLATION.md)** - 安装指南
- **[NEW_ENVIRONMENT_SETUP.md](NEW_ENVIRONMENT_SETUP.md)** - 新环境配置
- **[CLI_TROUBLESHOOTING.md](CLI_TROUBLESHOOTING.md)** - CLI常见问题解答 ⭐ 最新

### Configuration
- **[CONFIG_PRIORITY.md](CONFIG_PRIORITY.md)** - 配置优先级系统（4 层）

### Development
- **[CLAUDE.md](CLAUDE.md)** - 开发规则和约束 ⭐ 必读
- **[CODING_STANDARDS.md](CODING_STANDARDS.md)** - 文档和测试管理规范 ⭐ 新增
- **[DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md)** - 开发历程

---

## 功能文档

### Core Features
- **[SESSION_RESUME.md](SESSION_RESUME.md)** - 会话恢复功能
- **[MCP_INTEGRATION_SUCCESS.md](MCP_INTEGRATION_SUCCESS.md)** - MCP 集成成功记录
- **[CONTEXT_SAVE.md](CONTEXT_SAVE.md)** - 上下文保存机制

### Technical Details
- **[IEL.md](IEL.md)** - IEL (Interactive Execution Loop) 完整指南
- **[IEL_TECHNICAL_DEEP_DIVE.md](IEL_TECHNICAL_DEEP_DIVE.md)** - IEL 技术深度分析
- **[GRAPHAGENT_REPL_GUIDE.md](GRAPHAGENT_REPL_GUIDE.md)** - GraphAgent REPL 使用指南
- **[REPL_FLOW.md](REPL_FLOW.md)** - REPL 执行流程详解

---

## 系统文档

### Architecture
- **[MULTI_TENANT_WORKSPACE.md](MULTI_TENANT_WORKSPACE.md)** - 多租户工作区
- **[WORKSPACE_ISOLATION.md](WORKSPACE_ISOLATION.md)** - 工作区隔离机制

### Quick Reference
- **[DOCKER_QUICKREF.md](DOCKER_QUICKREF.md)** - Docker 快速参考

---

## Archived (Historical)

### Bug Fixes
- **docs_archive/bugfixes/** - Bug修复记录

### Sprint Summaries
- **docs_archive/sprints/** - Sprint总结文档

### Temporary Analysis
- **docs_archive/temp/** - 临时分析报告
  - **v2.0 Research** - FastReAct v2.0 研究文档
    - `nanobot_deep_analysis.md` - nanobot 深度分析（核心代码、设计模式）
    - `fastreact_v2_final_plan.md` - v2.0 最终方案（基于 nanobot 改造）
    - `fastreact_v2_architecture_final.md` - v2.0 架构设计（分层架构、组件设计）
    - `nanobot_to_fastreact_migration.md` - 迁移指南（分阶段实施）
    - `nanobot_vs_rewrite.md` - 决策分析（改造 vs 从头写）
    - `research_phase_complete.md` - 研究阶段完成总结

---

## 文档结构

```
FastReAct/
├── README.md                    # 项目主页
├── DOCS_INDEX.md               # 文档导航（本文件）
├── CLAUDE.md                   # 开发规则
├── INSTALLATION.md             # 安装指南
├── CLI_TROUBLESHOOTING.md      # CLI问题解答
│
├── [Feature Docs]              # 功能文档
│   ├── SESSION_RESUME.md
│   ├── MCP_INTEGRATION_SUCCESS.md
│   ├── IEL.md
│   └── GRAPHAGENT_REPL_GUIDE.md
│
├── [Technical Docs]            # 技术文档
│   ├── CONFIG_PRIORITY.md
│   ├── CONTEXT_SAVE.md
│   └── REPL_FLOW.md
│
└── docs_archive/               # 归档文档
    ├── bugfixes/
    ├── sprints/
    └── temp/
```

---

## 最新更新 (2026-02-07)

### 新增文档
- **CLI_TROUBLESHOOTING.md** - CLI使用常见问题

### 更新内容
- ContextMonitor显示改进（token数而非百分比）
- Memory Flush阈值百分比化（自动适配context window）
- 会话存储逻辑修复（更新同一文件）
- 历史消息截断（2000字符限制）

---

## 文档原则

1. **诚实**: 只描述已实现且验证的功能
2. **简洁**: 避免过度详细的文档
3. **实用**: 专注于用户真正需要的信息
4. **可维护**: 及时归档过时文档
5. **无Emoji**: 使用文本标记 ([OK], [ERROR], [WARNING])

---

**最后更新**: 2026-02-07
