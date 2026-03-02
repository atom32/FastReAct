# FastReAct Nano 文档导航

欢迎来到 FastReAct Nano 文档！本文档将引导你从零开始逐步掌握 FastReAct Nano。

## 🚀 快速开始

1. **安装**: [安装指南](../README.md#installation)
2. **配置**: [配置说明](../README.md#configuration)
3. **第一个查询**: [示例代码](../examples/)

---

## 📚 渐进式学习路径

### 阶段 1: 核心概念（必读）

**理解 FastReAct Nano 的核心架构**

- [x] [核心架构设计](ARCHITECTURE/DESIGN.md)
  - Brain-Body 分离架构
  - 事件驱动协议
  - 反熵增原则

- [x] [目录结构](ARCHITECTURE/DIRECTORY_STRUCTURE.md)
  - 项目文件组织
  - 模块职责划分

**预计学习时间**: 30 分钟

---

### 阶段 2: 核心功能（推荐）

**掌握核心功能和扩展机制**

- [x] [Skills 和 MCP 系统](SKILLS_AND_MCP.md)
  - Skills: 零代码知识扩展
  - MCP: 工具协议集成
  - 使用场景对比

- [x] [MCP 调用机制](MCP_CALLING_MECHANISM.md)
  - MCP 服务器配置
  - 工具调用流程
  - 最佳实践

- [x] [多租户指南](MULTITENANT_GUIDE.md)
  - 会话隔离
  - 用户工作空间
  - 生产部署

**预计学习时间**: 1 小时

---

### 阶段 3: 高级特性（可选）

**深入高级功能和优化**

- [配置文件位置](CONFIG_FILE_LOCATIONS.md)
  - 配置优先级
  - 多环境配置

- [动态技能选择](DYNAMIC_SKILL_SELECTION.md)
  - 语义匹配算法
  - 中文分词优化
  - 性能调优

**预计学习时间**: 30 分钟

---

### 阶段 4: 平台生态（扩展）

**了解平台集成和扩展**

- [产品路线图](FEATURES/PRODUCT_ROADMAP.md)
  - 已实现功能
  - 规划中的特性

**预计学习时间**: 15 分钟

---

## 🎯 按场景查找文档

### 我想...

**快速开始**
- [安装指南](../README.md#installation)
- [配置说明](../README.md#configuration)
- [示例代码](../examples/)

**添加自定义功能**
- [添加 Skills](../README.md#adding-custom-skills-and-mcp)
- [配置 MCP 服务器](MCP_CALLING_MECHANISM.md)
- [创建 MCP 服务器](../mcp_servers/)

**部署到生产**
- [Docker 部署](../deploy/README.md)
- [多租户配置](MULTITENANT_GUIDE.md)
- [Feishu 集成](../deploy/feishu.md)

**理解架构**
- [设计哲学](ARCHITECTURE/DESIGN.md)
- [目录结构](ARCHITECTURE/DIRECTORY_STRUCTURE.md)
- [Brain-Body 分离](../CLAUDE.md#architecture-iron-rules-critical)

**调试问题**
- [常见问题](../README.md#troubleshooting)
- [配置诊断](CONFIG_FILE_LOCATIONS.md)

---

## 📊 文档分类索引

### 按类型

**架构文档** (`docs/ARCHITECTURE/`):
- 设计理念
- 目录结构

**平台文档** (`docs/PLATFORM/`):
- Skills 和 MCP
- 工具和扩展

**分析文档** (`docs/ANALYSIS/`):
- OpenClaw 对比分析
- 动态技能选择

**指南文档** (`docs/GUIDES/`):
- 多租户部署
- 配置文件位置

**功能文档** (`docs/FEATURES/`):
- 产品路线图

---

## 🔗 快速链接

**常用文档**:
- [README](../README.md) - 项目概述
- [CLAUDE.md](../CLAUDE.md) - 开发规则
- [CHANGELOG](../CHANGELOG.md) - 版本历史

**核心概念**:
- [Brain-Body 分离](../CLAUDE.md#1-brain-body-separation)
- [事件协议](../CLAUDE.md#2-event-driven-protocol)
- [工具系统](../CLAUDE.md#tool-system-philosophy)

**扩展机制**:
- [Skills 系统](../README.md#adding-custom-skills-and-mcp)
- [MCP 服务器](../mcp_servers/)
- [Adapter 模式](../CLAUDE.md#ecosystem-isolation)

---

## 📝 文档更新日志

**2025-02-28**:
- ✅ 添加渐进式学习路径
- ✅ 创建 examples/ 目录
- ✅ 重组文档导航

---

**开始学习**: [示例代码](../examples/) → [核心架构](ARCHITECTURE/DESIGN.md)
