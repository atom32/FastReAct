# FastReAct 文档索引

完整的 FastReAct 文档导航。

## 📚 核心文档

### 入门文档
- **[README.md](../README.md)** - 项目概述和快速开始
- **[QUICKSTART.md](QUICKSTART.md)** - GraphRAG 快速开始指南
- **[CONFIG.md](../CONFIG.md)** - 配置文件说明
- **[CHANGELOG.md](../CHANGELOG.md)** - 版本更新历史

### 架构和设计
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - 系统架构和设计原理
- **[FEATURES_COMPARISON.md](FEATURES_COMPARISON.md)** - 与 Moltbot、MiroFish 的对比分析
- **[IMPROVEMENT_ROADMAP.md](IMPROVEMENT_ROADMAP.md)** - 学习改进方案

### 功能文档
- **[GRAPHrag_INTEGRATION.md](GRAPHrag_INTEGRATION.md)** - GraphRAG 集成指南
- **[MCP_CLIENT_GUIDE.md](MCP_CLIENT_GUIDE.md)** - MCP 客户端使用指南
- **[BOOTSTRAP_GUIDE.md](BOOTSTRAP_GUIDE.md)** - Bootstrap 配置系统

### Gateway 和通道
- **[WEBSOCKET_GATEWAY.md](WEBSOCKET_GATEWAY.md)** - WebSocket 网关文档
- **[WECHAT_CHANNEL.md](WECHAT_CHANNEL.md)** - 微信通道集成

### 搜索工具
- **[TAVILY_SEARCH.md](TAVILY_SEARCH.md)** - Tavily 搜索工具
- **[TAVILY_SETUP.md](TAVILY_SETUP.md)** - Tavily 配置指南

---

## 🎯 学习路径

### 1. 新手入门
1. 阅读 [README.md](../README.md)
2. 配置 [config.json](../config.json)
3. 运行 [01_basic.py](../examples/01_basic.py)
4. 阅读 [ARCHITECTURE.md](ARCHITECTURE.md)

### 2. 进阶使用
1. 学习自定义工具 ([03_custom_tools.py](../examples/03_custom_tools.py))
2. 理解事件流 ([04_events_and_retry.py](../examples/04_events_and_retry.py))
3. 配置 Bootstrap ([BOOTSTRAP_GUIDE.md](BOOTSTRAP_GUIDE.md))
4. 集成 MCP ([MCP_CLIENT_GUIDE.md](MCP_CLIENT_GUIDE.md))

### 3. 高级开发
1. 沙箱开发 (sandbox/docker.py)
2. Gateway 开发 (gateway/server.py)
3. 通道扩展 (channels/base.py)
4. 贡献代码

---

## 📖 示例代码

| 示例 | 说明 |
|------|------|
| [01_basic.py](../examples/01_basic.py) | 基础 ReACT 使用 |
| [02_async_concurrent.py](../examples/02_async_concurrent.py) | 异步并发 |
| [03_custom_tools.py](../examples/03_custom_tools.py) | 自定义工具 |
| [04_events_and_retry.py](../examples/04_events_and_retry.py) | 事件流和重试 |
| [05_comprehensive_e2e_test.py](../examples/05_comprehensive_e2e_test.py) | E2E 测试 (7/7) |

---

## 🔍 快速查找

### 按主题

**ReACT 框架**: [ARCHITECTURE.md](ARCHITECTURE.md)
**工具系统**: [MCP_CLIENT_GUIDE.md](MCP_CLIENT_GUIDE.md)
**Docker 沙箱**: [ARCHITECTURE.md](ARCHITECTURE.md#2-docker-沙箱)
**Gateway**: [WEBSOCKET_GATEWAY.md](WEBSOCKET_GATEWAY.md)
**配置**: [CONFIG.md](../CONFIG.md)
**事件流**: [ARCHITECTURE.md](ARCHITECTURE.md#3-事件流系统)

---

**最后更新**: 2026-01-30
