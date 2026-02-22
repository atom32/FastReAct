# FastReAct Nano - 学习改进清单

**创建日期**: 2026-02-22
**基于**: 与 nanobot、openclaw 竞品对比分析
**状态**: 待实施

---

## 一、高优先级改进 (P0 - 1-2 周内)

### 1.1 增加多通道支持 🔴

**目标**: 从 2 个通道扩展到 5+ 个通道

**优先级**:
1. ✅ Telegram (2-3 小时) - 最简单，2 亿用户
2. ✅ Discord (2-3 小时) - 开发者喜欢
3. ✅ Slack (2-3 小时) - 企业常用

**实施方式**:
- 创建 BaseAdapter 统一接口
- 从 nanobot 移植通道代码（95% 可复用）
- 每个适配器独立管理会话

**预期成果**: 3 个新通道，总计 5+ 个平台

---

### 1.2 实现 Cron 定时任务系统 🔴

**学习对象**: nanobot 的 CronTool 和 CronService

**功能需求**:
- 定时执行任务
- 周期性任务
- 后台任务调度

**参考代码**:
```python
# nanobot/agent/tools/cron.py
class CronTool:
    async def schedule(self, cron_expression: str, task: str):
        """调度定时任务"""
        pass

    async def list_schedules(self):
        """列出所有定时任务"""
        pass
```

**实施方式**:
- 添加后台调度器（APScheduler）
- 实现工具函数 `cron_schedule()`
- 支持标准 cron 表达式

**预期成果**: 完整的 Cron 系统

---

### 1.3 改进记忆系统 🔴

**学习对象**: nanobot 的双层记忆机制

**问题**:
- 当前仅有文件系统记忆
- 无法智能整合信息

**改进方案**:
```
MEMORY.md:
- 长期事实
- 用户偏好
- 重要结论

HISTORY.md:
- 可搜索的历史记录
- 自动整合旧对话
```

**实施方式**:
- 实现 Memory.consolidate() 方法
- 当历史超过 50 条时自动整合
- 使用 LLM 提取关键信息到 MEMORY.md

**预期成果**: 双层记忆系统，更智能的上下文管理

---

### 1.4 完善 SKILL 系统 🔴

**问题**:
- SKILL 自动选择机制不完善
- SKILL 依赖管理缺失

**改进方案**:
1. **自动选择**: 根据查询内容自动加载相关 SKILL
2. **依赖管理**: SKILL 可以声明依赖的其他 SKILL
3. **热加载**: 运行时添加/移除 SKILL
4. **调试工具**: 查看 SKILL 加载状态和依赖图

**实施方式**:
```python
# skills/builtin/coding/__skill__.json
{
  "name": "coding",
  "triggers": ["代码", "编程", "debug", "refactor"],
  "depends_on": ["filesystem", "web_search"],
  "auto_load": true
}
```

**预期成果**: 智能 SKILL 系统

---

## 二、中优先级改进 (P1 - 1-2 月内)

### 2.1 添加语音交互 🟡

**学习对象**: openclaw 的语音功能

**功能需求**:
1. 语音识别 (STT): OpenAI Whisper
2. 语音合成 (TTS): ElevenLabs
3. 交互模式:
   - PTT (Push-to-Talk)
   - Talk 模式 (持续对话)
   - 语音唤醒 (可选)

**实施方式**:
- 前端添加录音按钮
- 后端集成 Whisper 和 ElevenLabs
- WebSocket 传输音频数据

**预期成果**: 完整的语音交互能力

---

### 2.2 Provider 自动检测 🟡

**学习对象**: nanobot 的 Provider Registry

**问题**:
- 用户需要手动配置 Provider
- 不支持多 Provider 同时使用

**改进方案**:
```python
class ProviderRegistry:
    """Provider 注册表（自动检测）"""

    def auto_detect(self) -> list[Provider]:
        """自动检测可用的 Provider"""
        providers = []

        # 检查环境变量
        if os.getenv("OPENAI_API_KEY"):
            providers.append(OpenAIProvider())

        if os.getenv("ANTHROPIC_API_KEY"):
            providers.append(AnthropicProvider())

        # 检查配置文件
        # ...

        return providers

    def route(self, model: str) -> Provider:
        """根据模型名路由到对应 Provider"""
        if model.startswith("gpt-"):
            return self.get_provider("openai")
        elif model.startswith("claude-"):
            return self.get_provider("anthropic")
```

**预期成果**: 智能的 Provider 管理

---

### 2.3 前端 Admin 增强 🟡

**功能需求**:
1. 会话管理界面
2. 工具使用统计
3. 性能监控面板
4. 配置可视化编辑
5. SKILL 管理界面

**实施方式**:
- 添加 `/admin/sessions` 页面
- 添加 `/admin/metrics` 页面
- 添加 `/admin/skills` 页面
- 集成图表库（Recharts）

**预期成果**: 完善的管理后台

---

### 2.4 Agent Pool 优化 🟡

**问题**:
- 每个 Session 创建一个 Agent 实例
- 多用户场景内存占用高（800MB for 10 users）

**改进方案**:
```python
class AgentPool:
    """Agent 池（复用 Agent 实例）"""

    def __init__(self, max_agents: int = 10):
        self._max_agents = max_agents
        self._pool: asyncio.Queue[Agent] = asyncio.Queue(maxsize=max_agents)
        self._created = 0
        self._acquired = 0

    async def acquire(self, session_id: str) -> Agent:
        """获取 Agent（复用或创建）"""
        try:
            # 尝试从池中获取（超时 100ms）
            agent = await asyncio.wait_for(
                self._pool.get(),
                timeout=0.1
            )
            self._acquired += 1
            logger.info(f"[POOL] Reusing agent for {session_id} (active: {self._acquired})")
            return agent
        except asyncio.TimeoutError:
            # 池为空，创建新的
            if self._created < self._max_agents:
                agent = Agent()
                self._created += 1
                self._acquired += 1
                logger.info(f"[POOL] Created new agent for {session_id} (total: {self._created})")
                return agent
            else:
                # 等待可用 Agent
                agent = await self._pool.get()
                self._acquired += 1
                return agent

    async def release(self, agent: Agent, session_id: str):
        """归还 Agent 到池中"""
        # 重置 Agent 状态
        agent._session_queues.clear()

        # 归还到池中
        await self._pool.put(agent)
        self._acquired -= 1
        logger.info(f"[POOL] Released agent for {session_id} (active: {self._acquired})")
```

**预期成果**: 内存占用降低 60%+

---

### 2.5 统一适配器接口 🟡

**问题**:
- 每个适配器独立实现
- 代码重复（会话管理逻辑）

**改进方案**:
```python
# fastreact/adapters/base.py

from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    """适配器基类（统一接口）"""

    name: str = "base"

    def __init__(self, agent: Agent, config: Any):
        self.agent = agent
        self.config = config
        self._running = False
        self._sessions: dict[str, list[dict]] = {}

    @abstractmethod
    async def start(self) -> None:
        """启动适配器"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止适配器"""
        pass

    @abstractmethod
    async def send_event(self, event: AgentEvent, target: str) -> None:
        """发送事件到目标客户端"""
        pass

    async def handle_message(
        self,
        sender_id: str,
        chat_id: str,
        content: str,
        session_key: str | None = None
    ):
        """处理消息（统一逻辑）"""
        session_key = session_key or f"{self.name}:{chat_id}"
        history = self._sessions.get(session_key, [])

        response_text = ""
        async for event in self.agent.run_event_stream(
            query=content,
            session_id=session_key,
            history=history,
            user_key=f"{self.name}:{sender_id}",
        ):
            # 发送事件到客户端
            await self.send_event(event, chat_id)

            # 记录最终响应
            if event.type == EventType.STEP_END:
                response_text = event.content

        # 更新历史
        if response_text:
            self._sessions[session_key] = history + [
                {"role": "user", "content": content},
                {"role": "assistant", "content": response_text},
            ]
```

**预期成果**: 代码重复减少 50%+

---

## 三、低优先级改进 (P2 - 长期规划)

### 3.1 配套应用 🟢

**学习对象**: openclaw 的配套应用

**功能需求**:
1. macOS 菜单栏应用
2. iOS/Android 移动应用（React Native）
3. 系统通知集成
4. 快捷键支持

**实施方式**:
- 使用 Electron/macOS SwiftUI
- React Native for mobile
- 本地通知 API

**预期成果**: 全平台覆盖

---

### 3.2 浏览器自动化 🟢

**学习对象**: openclaw 的浏览器自动化

**功能需求**:
1. Chrome/Chromium 控制
2. Playwright 集成
3. 自动化脚本支持
4. 配置文件隔离

**实施方式**:
- 添加 browser 工具
- 集成 Playwright/Puppeteer
- 支持脚本录制和回放

**预期成果**: 完整的浏览器自动化能力

---

### 3.3 消息路由优化 🟢

**学习对象**: nanobot 的 MessageBus

**可选改进**:
1. 添加可选的 MessageBus 层
2. 支持单 Agent 模式（低资源场景）
3. 消息优先级队列
4. 消息持久化（防止丢失）

**实施方式**:
```python
# fastreact/core/bus.py（可选）

class MessageBus:
    """消息总线（可选，用于单 Agent 模式）"""

    def __init__(self, mode: str = "concurrent"):
        self.mode = mode  # "concurrent" or "serial"

        if mode == "serial":
            # 单 Agent + 队列模式（类似 nanobot）
            self._queue: asyncio.Queue = asyncio.Queue()
        else:
            # 并发模式（默认）
            pass
```

**预期成果**: 灵活的部署模式

---

### 3.4 可观测性增强 🟢

**功能需求**:
1. 结构化日志
2. 指标收集（Prometheus）
3. 分布式追踪（OpenTelemetry）
4. 性能分析

**实施方式**:
- 集成 structlog
- 添加 Prometheus endpoint
- 集成 OpenTelemetry

**预期成果**: 生产级可观测性

---

## 四、技术债务清理

### 4.1 配置管理简化

**问题**:
- 配置分散在多个地方
- 多层配置加载复杂

**改进方案**:
- 统一配置入口
- 配置验证和错误提示
- 配置热重载

---

### 4.2 文档完善

**待完善文档**:
1. SKILL 开发指南
2. MCP 集成指南
3. 适配器开发指南
4. 部署最佳实践
5. 故障排查指南

---

### 4.3 测试覆盖

**目标**:
- 保持 100% 测试覆盖率
- 添加集成测试
- 添加 E2E 测试
- 性能基准测试

---

## 五、学习资源

### 5.1 从 nanobot 学习

1. **MessageBus 模式** - 完全解耦的架构
2. **双层记忆系统** - MEMORY.md + HISTORY.md
3. **Provider Registry** - 自动检测和路由
4. **Cron 系统** - 定时任务调度
5. **通道抽象** - BaseChannel 接口

### 5.2 从 openclaw 学习

1. **插件生态** - ClawHub 技能市场
2. **配套应用** - macOS/iOS/Android
3. **语音交互** - Whisper + ElevenLabs
4. **浏览器自动化** - Chrome 控制
5. **安全机制** - 显式 DM 准入

---

## 六、实施时间表

### Q1 2026 (1-3 月)
- ✅ 增加多通道支持（Telegram、Discord、Slack）
- ✅ 实现 Cron 定时任务
- ✅ 改进记忆系统（双层记忆）
- ✅ 完善 SKILL 系统

### Q2 2026 (4-6 月)
- ✅ 添加语音交互
- ✅ Provider 自动检测
- ✅ 前端 Admin 增强
- ✅ Agent Pool 优化

### Q3-Q4 2026 (7-12 月)
- ✅ 统一适配器接口
- ✅ 配套应用（macOS）
- ✅ 浏览器自动化
- ✅ 可观测性增强

---

## 七、成功指标

### 功能指标
- ✅ 通道支持 ≥ 5 个
- ✅ Cron 系统完成
- ✅ 双层记忆实现
- ✅ SKILL 自动选择
- ✅ 语音交互完成

### 性能指标
- ✅ 内存占用降低 60% (Agent Pool)
- ✅ 启动时间 < 3 秒
- ✅ 多用户响应时间 < 2 秒

### 质量指标
- ✅ 测试覆盖率保持 100%
- ✅ 文档完善度 ≥ 80%
- ✅ 代码重复减少 50%

---

## 八、核心原则

**开发过程中必须遵守**:

1. ✅ **保持架构优势** - 脑体分离、事件驱动
2. ✅ **保持前端优势** - Next.js + 6 种主题
3. ✅ **保持测试优势** - 100% 覆盖率
4. ✅ **保持 MCP 优势** - 完善的 MCP 支持
5. ✅ **保持多租户优势** - 单户/企业模式

**不做的事情**:
- ❌ 不破坏脑体分离架构
- ❌ 不降低测试覆盖率
- ❌ 不牺牲实时流式体验
- ❌ 不增加不必要的复杂度

---

**文档维护**: 定期更新此清单
**最后更新**: 2026-02-22
**版本**: v1.0
