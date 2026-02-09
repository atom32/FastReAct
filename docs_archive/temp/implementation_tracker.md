# FastReAct Nano 实施追踪

**开始日期**: 2026-02-10
**目标**: MVP (Phase 1-4)
**预计时间**: 7天

---

## 实施原则

### CLAUDE.md 规则严格遵守

1. **无 Emoji**: 使用文本标记 `[OK]`, `[ERROR]`, `[WARNING]`, `[INFO]`
2. **无硬编码路径**: 使用 `pathlib.Path` 和配置
3. **UTF-8 编码**: 所有文件操作指定 `encoding='utf-8'`
4. **模块独立**: 禁止层级渗透，通过公开API访问
5. **DRY 原则**: 避免重复代码，提取共享逻辑
6. **跨平台**: Windows/Linux 兼容

### 文档要求

- 每完成一个模块，更新对应文档
- 使用 Markdown 格式
- 代码示例必须可运行
- 记录设计决策

---

## Phase 1: Gateway 基础设施

### 目标
- FastAPI 服务器
- WebSocket 路由
- Session 管理
- MessageBus 集成

### 进度追踪

#### 1.1 项目结构搭建
- [x] 创建目录结构
- [x] 配置文件 setup (utils/config.py)
- [ ] 依赖管理 (pyproject.toml)

#### 1.2 MessageBus 实现
- [x] 异步队列封装 (core/bus.py)
- [x] 消息类型定义 (InboundMessage, OutboundMessage)
- [ ] 单元测试

#### 1.3 WebSocket Gateway
- [ ] FastAPI 服务器
- [ ] WebSocket 路由
- [ ] 连接管理

#### 1.4 Session 管理
- [ ] Session 类
- [ ] 存储后端
- [ ] 生命周期管理

---

## Phase 2: ReAct 核心

### 目标
- ReActCore 循环
- LLM Provider
- Tool Registry
- 基础工具

### 进度追踪

#### 2.1 LLM Provider
- [x] LiteLLM 封装 (providers/litellm.py)
- [x] 多提供商支持 (自动检测)
- [x] 流式输出支持

#### 2.2 Tool 系统
- [x] Tool 基类 (core/tools.py)
- [x] ToolRegistry
- [x] 参数验证 (JSON Schema)
- [x] 示例工具 (EchoTool, AddTool)

#### 2.3 ReActCore
- [x] 主循环实现 (core/react.py)
- [x] 工具调用
- [x] 错误处理
- [x] 事件系统 (StepEvent)

---

## Phase 3: 上下文管理

### 目标
- ContextManager
- Token 监控
- 智能截断
- 文件存储

### 进度追踪

#### 3.1 ContextManager
- [x] 上下文构建 (core/context.py)
- [x] 历史管理 (Context, ContextStore)
- [x] 消息截断 (prune_context)

#### 3.2 Token 监控
- [x] Token 计数 (TokenMonitor)
- [x] 预算计算 (calculate_budget)
- [x] 警告系统 (should_warn)

#### 3.3 文件存储
- [x] JSONL 存储 (FileContextStore)
- [x] 异步读写
- [x] 会话持久化

---

## Phase 4: 渠道系统

### 目标
- Channel 抽象
- Channel Registry
- Telegram 实现
- CLI 渠道

### 进度追踪

#### 4.1 Channel 抽象
- [ ] 基类定义
- [ ] 统一接口
- [ ] 消息格式

#### 4.2 Channel Registry
- [ ] 注册机制
- [ ] 查找接口
- [ ] 元数据管理

#### 4.3 Telegram 渠道
- [ ] Bot 集成
- [ ] 消息处理
- [ ] WebSocket 连接

#### 4.4 CLI 渠道
- [ ] 命令行界面
- [ ] 交互模式
- [ ] 流式输出

---

## 代码统计

| 模块 | 预估行数 | 实际行数 | 完成度 |
|------|---------|---------|--------|
| Core (bus, react, tools) | 400 | ~600 | 100% |
| Context | 400 | ~450 | 100% |
| Providers | 150 | ~250 | 100% |
| Gateway | 450 | 0 | 0% |
| Channels | 400 | 0 | 0% |
| **总计** | **1700** | **~1300** | **50%** |

---

## 测试覆盖

| 模块 | 单元测试 | 集成测试 | 覆盖率 |
|------|---------|---------|--------|
| Gateway | - | - | -% |
| Core | - | - | -% |
| Context | - | - | -% |
| Channels | - | - | -% |

---

## 问题追踪

### 待解决问题

无

### 已解决问题

无

---

## 设计决策记录

### 1. 为什么选择 FastAPI？

**日期**: 2026-02-10
**决策**: 使用 FastAPI 而非 Hono (Node.js)

**理由**:
- 与现有 Python 生态兼容
- 原生 WebSocket 支持
- 自动 API 文档
- 类型检查
- 异步性能优秀

### 2. 为什么文件存储？

**日期**: 2026-02-10
**决策**: 使用 JSONL 文件存储会话

**理由**:
- 简单可靠
- 人类可读
- 无需数据库
- 易于备份

### 3. 为什么使用 LiteLLM？

**日期**: 2026-02-10
**决策**: 使用 LiteLLM 作为 LLM 提供商接口

**理由**:
- 统一接口支持多个 LLM
- 自动 API key 检测
- 简化配置
- 生产就绪

### 4. 为什么使用 asyncio.to_thread？

**日期**: 2026-02-10
**决策**: 文件 I/O 使用 asyncio.to_thread 而非 aiofiles

**理由**:
- Python 3.9+ 内置支持
- 无需额外依赖
- 性能相当
- 代码更简单

---

## 已完成模块详情

### MessageBus (core/bus.py)
- 异步队列封装
- InboundMessage/OutboundMessage 数据类
- 支持队列大小限制
- 提供清空和状态查询

### LiteLLM Provider (providers/litellm.py)
- 多提供商自动检测
- 从环境变量读取配置
- 支持工具调用
- 流式输出支持
- Token 使用统计

### Tool System (core/tools.py)
- Tool 抽象基类
- JSON Schema 参数验证
- ToolRegistry 管理工具
- 示例工具实现

### ReActCore (core/react.py)
- Think-Act-Observe 循环
- 事件系统 (StepEvent)
- 错误处理
- 流式回调支持

### ContextManager (core/context.py)
- Token 监控和警告
- 智能上下文截断
- FileContextStore (JSONL)
- 内存缓存

### Configuration (utils/config.py)
- 环境变量支持
- YAML/JSON 配置文件
- 路径管理 (Paths 类)
- 全局单例模式

---

## 下一步行动

- [ ] 完成 Phase 1.3: WebSocket Gateway
- [ ] 完成 Phase 1.4: Session 管理
- [ ] 完成 Phase 4.1: Channel 抽象
- [ ] 完成 Phase 4.4: CLI 渠道 (用于测试)

---

**最后更新**: 2026-02-10 01:00
**进度**: 50% (Phase 2, 3 完成 | Phase 1, 4 进行中)
