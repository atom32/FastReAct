# FastReAct 文档索引

> **FastReAct v0.3.0** - 生产级 ReAct Agent 框架
> 支持多智能体、Gateway 认证、事件流、工具调用、Bootstrap 配置

---

## 📚 快速开始

- [README](README.md) - 快速开始指南
- [配置指南](../CONFIG.md) - 配置文件说明
- [变更日志](../CHANGELOG.md) - 版本更新历史

---

## 🎯 核心功能

### 多智能体系统
- [多智能体系统](features/MULTI_AGENT_SYSTEM.md) - 智能体架构和路由
- [会话持久化](features/SESSION_PERSISTENCE.md) - 存储和恢复

### Gateway 认证
- [WebSocket Gateway](features/WEBSOCKET_GATEWAY.md) - 网关服务器
- [错误处理改进](features/ERROR_HANDLING_IMPROVEMENT.md) - 统一错误处理
- [去重机制](features/DEDUPLICATION_IMPROVEMENT.md) - 防重放攻击
- [函数调用 API](features/FUNCTION_CALLING_API_IMPROVEMENT.md) - 工具调用优化
- [同步接口修复](features/SYNC_INTERFACE_FIX.md) - 同步 API 支持

### Bootstrap 系统
- [Bootstrap 指南](features/BOOTSTRAP_GUIDE.md) - 配置系统使用
- [Bootstrap 实现](features/BOOTSTRAP_IMPLEMENTATION.md) - 技术实现细节

### 集成通道
- [微信通道](features/WECHAT_CHANNEL.md) - 微信公众号/企业微信集成
- [GraphRAG 集成](features/GRAPHrag_INTEGRATION.md) - 知识图谱增强

---

## 🔧 工具集成

### MCP 工具
- [MCP 客户端指南](tools/MCP_CLIENT_GUIDE.md) - Model Context Protocol
- [MCP 测试总结](tools/MCP_CLIENT_TEST_SUMMARY.md)
- [MCP Datetime 设置](tools/MCP_DATETIME_SETUP.md)

### Tavily 搜索
- [Tavily 搜索](tools/TAVILY_SEARCH.md) - 搜索引擎集成
- [Tavily 设置](tools/TAVILY_SETUP.md)
- [Tavily MCP 状态](tools/TAVILY_MCP_STATUS.md)

---

## 📊 项目状态

### Phase 总结
- [Phase 2 P0 总结](status/PHASE2_P0_REVIEW.md) - Gateway 认证 + 协议
- [Phase 2 P1 总结](status/PHASE2_P1_SUMMARY.md) - 多通道 + 沙箱
- [合并状态总结](status/MERGE_STATUS_SUMMARY.md) - 本地远程合并
- [P0 改进总结](status/P0_IMPROVEMENTS_SUMMARY.md)

### 项目回顾
- [项目状态回顾](status/PROJECT_STATUS_REVIEW.md)
- [项目规划](status/PROJECT_REVIEW_PLANNER.md)
- [清理总结](status/CLEANUP_SUMMARY.md)

---

## 🔬 研究文档

### 项目分析
- [Moltbot 分析](research/MOLTBOT_ANALYSIS.md)
- [Moltbot 启发的路线图](research/MOLTBOT_INSPRIED_ROADMAP.md)
- [Moltbot 研究改进](research/MOLTBOT_RESEARCH_IMPROVEMENTS.md)
- [PMono 分析](research/PMONO_ANALYSIS.md)
- [Mirofish 分析](research/mirofish_analysis.md)
- [从 BIRO 到 FastReAct](research/FROM_BIRO_TO_FASTREACT.md)

### 实现路线图
- [实现路线图](implementation_roadmap.md)
- [生产路线图](research/PRODUCTION_ROADMAP.md)

---

## 🧪 测试

- [ReAct 框架测试指南](testing/REACT_FRAMEWORK_TESTING_GUIDE.md)

---

## 📁 归档文档

过时或参考文档：
- [Agent 架构](archive/agent_architecture.md)
- [甘特图](archive/gantt_chart.md)
- [事件流重试计划](archive/EVENT_STREAM_RETRY_PLAN.md)

---

## 🎯 按场景查找文档

### 我想...

| 场景 | 推荐文档 |
|------|----------|
| **快速了解项目** | [README](../README.md) |
| **立即开始使用** | [README](README.md) |
| **配置 API Key** | [配置指南](../CONFIG.md) |
| **使用 Gateway** | [WebSocket Gateway](features/WEBSOCKET_GATEWAY.md) |
| **连接 MCP 工具** | [MCP 客户端指南](tools/MCP_CLIENT_GUIDE.md) |
| **使用微信通道** | [微信通道](features/WECHAT_CHANNEL.md) |
| **了解多智能体** | [多智能体系统](features/MULTI_AGENT_SYSTEM.md) |
| **查看项目状态** | [项目状态回顾](status/PROJECT_STATUS_REVIEW.md) |

---

## 🔄 文档更新日志

- **2026-01-30**: 重组文档结构，分类整理到子目录
- **2026-01-26**: 重组文档结构，归档历史文档
- **2026-01-23**: 添加MCP客户端集成文档
- **2026-01-22**: 添加P0修复总结和版本更新
- **2026-01-22**: 创建文档索引，整理结构

---

## 📌 文档阅读建议

### 新手入门（按顺序阅读）
1. [README](README.md) - 快速开始
2. [配置指南](../CONFIG.md) - 配置 API Key
3. [Bootstrap 指南](features/BOOTSTRAP_GUIDE.md) - 自定义配置（可选）

### 开发者进阶
1. [多智能体系统](features/MULTI_AGENT_SYSTEM.md) - 理解架构
2. [WebSocket Gateway](features/WEBSOCKET_GATEWAY.md) - Gateway 认证
3. [项目状态回顾](status/PROJECT_STATUS_REVIEW.md) - 当前状态
4. [实现路线图](implementation_roadmap.md) - 未来规划

---

**最后更新**: 2026-01-30
**版本**: v0.3.0
