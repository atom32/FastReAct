# FastReAct Nano 实施追踪 v2.0

**开始日期**: 2026-02-10
**版本**: 2.0.0-alpha
**状态**: 重构为高级 ReAct 核心

---

## 设计变更说明

### v1.0 → v2.0

**v1.0** (已完成 90%):
- 基础 ReAct 循环
- MessageBus 解耦
- Token 监控
- Gateway + WebSocket
- 基础工具

**v2.0** (新方向):
- **双层循环** (Moltbot 模式)
- **转向消息** (实时干预)
- **后续消息** (异步任务)
- **极简工具** (Pi 哲学: 4 个核心工具)
- **作为智能体核心存在**

---

## 实施路线图 (v2.0)

### Phase 1: 双层循环重构 (2-3 小时)

#### 目标
实现 Moltbot 风格的双层循环架构

#### 任务
- [ ] 1.1 扩展 Message 类型
  - [ ] 添加 `steering` 消息类型
  - [ ] 添加 `followup` 消息类型
  - [ ] 更新 InboundMessage/OutboundMessage

- [ ] 1.2 重构 ReActCore
  - [ ] 实现外层循环（后续消息队列）
  - [ ] 实现内层循环（工具 + 转向）
  - [ ] 添加循环控制逻辑

- [ ] 1.3 回调系统
  - [ ] SteeringCallback 接口
  - [ ] FollowUpCallback 接口
  - [ ] 集成到 ReActCore

- [ ] 1.4 测试
  - [ ] 单元测试
  - [ ] 集成测试

#### 输出
- 更新的 `core/react.py`
- 新的 `core/messages.py`
- 回调接口

---

### Phase 2: 极简工具集 (2-3 小时)

#### 目标
按 Pi 哲学实现 4 个核心工具

#### 任务
- [ ] 2.1 ReadFileTool
  - [ ] 读取文件内容
  - [ ] 大小限制（10KB）
  - [ ] 错误处理

- [ ] 2.2 WriteFileTool
  - [ ] 写入文件
  - [ ] 创建目录
  - [ ] 路径保护

- [ ] 2.3 ExecTool (Bash)
  - [ ] 执行 Shell 命令
  - [ ] 超时控制
  - [ ] 安全检查（危险命令）
  - [ ] 工作区限制

- [ ] 2.4 EditFileTool
  - [ ] 文本替换
  - [ ] 单次替换
  - [ ] 错误处理

- [ ] 2.5 工具管理
  - [ ] 按模式选择工具（core/readonly/all）
  - [ ] 工具验证
  - [ ] 测试

#### 输出
- `tools/read_file.py`
- `tools/write_file.py`
- `tools/exec.py`
- `tools/edit_file.py`
- 更新的 `core/tools.py`

---

### Phase 3: 高级特性 (3-4 小时)

#### 目标
添加企业级特性

#### 任务
- [ ] 3.1 流式输出
  - [ ] 流式 LLM 调用
  - [ ] 流式回调
  - [ ] SSE/WebSocket 支持

- [ ] 3.2 转向消息系统
  - [ ] 文件监控（.steering.jsonl）
  - [ ] 实时干预接口
  - [ ] 测试

- [ ] 3.3 后续消息系统
  - [ ] 异步任务队列
  - [ ] 延迟调度
  - [ ] 任务管理

- [ ] 3.4 配置管理
  - [ ] ReActConfig 数据类
  - [ ] 工厂方法
  - [ ] 环境变量支持

#### 输出
- `core/streaming.py`
- `core/steering.py`
- `core/followup.py`
- `core/config.py`

---

### Phase 4: 简化插件系统 (2-3 小时)

#### 目标
实现 Nanobot 风格的技能加载

#### 任务
- [ ] 4.1 Skill 类
  - [ ] Markdown 解析
  - [ ] 元数据管理
  - [ ] always_load vs available

- [ ] 4.2 PluginManager
  - [ ] 扫描技能目录
  - [ ] 加载技能
  - [ ] 构建提示词

- [ ] 4.3 集成
  - [ ] 与 ContextBuilder 集成
  - [ ] 自动加载启动技能
  - [ ] 动态加载可用技能

#### 输出
- `plugins/manager.py`
- `plugins/skill.py`
- `plugins/loader.py`

---

## 代码统计 (v2.0 预期)

| 模块 | 当前行数 | 预期行数 | 变化 |
|------|---------|---------|------|
| Core | ~600 | ~800 | +200 |
| Tools | ~250 | ~400 | +150 |
| Gateway | ~550 | ~550 | 0 |
| Channels | ~350 | ~350 | 0 |
| **新增** | 0 | ~500 | +500 |
| **总计** | **~2,731** | **~3,100** | **+369** |

**目标**: 保持在 3,500 行以下（Nanobot 的 23%）

---

## 测试计划 (v2.0)

### 单元测试

| 模块 | 测试数 | 状态 |
|------|--------|------|
| 双层循环 | 8 | TODO |
| 转向消息 | 4 | TODO |
| 后续消息 | 4 | TODO |
| 4 个工具 | 12 | TODO |
| 流式输出 | 4 | TODO |
| **总计** | **32** | **0%** |

### 集成测试

- [ ] 端到端双层循环
- [ ] 实时转向测试
- [ ] 异步任务测试
- [ ] 工具链测试（read → edit → write → exec）

---

## 设计文档位置

- **主文档**: `docs/DESIGN.md`
- **追踪文档**: `docs_archive/temp/implementation_tracker.md`
- **对比分析**: `docs_archive/temp/completion_comparison.md`

---

## 下一步行动

### 立即开始：Phase 1 (双层循环重构)

这是最重要的架构变更，需要：

1. **扩展消息类型**
   - 添加 `steering` 和 `followup` 类型
   - 更新消息序列化

2. **重构 ReActCore**
   - 将单层循环改为双层循环
   - 添加 pending_messages 处理
   - 添加 followup_queue 支持

3. **实现回调**
   - SteeringCallback（文件监控）
   - FollowUpCallback（队列管理）

**预计时间**: 2-3 小时
**价值**: 实现高级 ReAct 特性，接近 Moltbot 功能

---

## 设计原则（v2.0）

1. **极简工具**: 只保留 4-5 个核心工具
2. **Bash 优先**: 让 AI 用 Bash 解决问题
3. **双层循环**: 支持后续任务和实时干预
4. **异步优先**: 全栈 asyncio
5. **智能体核心**: 作为基础设施，不绑定应用
6. **<3,500 行**: 保持轻量级

---

**最后更新**: 2026-02-10
**版本**: 2.0.0-alpha
**状态**: 设计完成，等待实施
