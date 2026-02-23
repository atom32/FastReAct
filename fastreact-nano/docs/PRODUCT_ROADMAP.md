# FastReAct Nano - 产品路线图

**版本**: v2.4.1 → v3.0.0
**更新日期**: 2025-02-23
**目标读者**: 产品经理、技术决策者

---

## 执行摘要

FastReAct Nano当前核心功能完备（SKILL系统、MCP集成、多租户、事件驱动），但缺少**产品差异化**和**企业级能力**。

基于对OpenClaw和NanoBot的研究，以及多租户安全审计，识别出**8个高价值功能缺口**。

### 优先级矩阵

```
影响 │ 高 │ [1] SOUL.md人格系统      │ [3] 资源配额管理
     │    │ [2] Bootstrap配置注入    │ [4] SKILL安全验证
─────┼────┼──────────────────────────┼───────────────────
     │ 低 │ [5] 渐进式SKILL加载      │ [7] Rate Limiting
     │    │ [6] Memory智能整合       │ [8] 用户黑白名单
         └────┴──────────────────────────┴───────────────────
               实现难度: 低  ←────→  高
```

**建议MVP路径**: [1] → [2] → [3] → [4] (约2周)

---

## 功能需求清单

### P0 - 核心差异化 (必须有)

#### [1] SOUL.md 人格系统

**问题**: Agent缺乏个性化，用户体验像"搜索引擎+工具"，不是"数字伙伴"

**解决方案**: 引入OpenClaw的SOUL.md人格定义系统

**用户价值**:
- Agent有自己的"性格"和"观点"
- 对话更自然、有人情味
- 可根据用户/场景定制人格

**技术方案**:
```
skills/builtin/soul/SKILL.md (always: true)
├── Core Truths (5条核心真理)
├── Boundaries (行为边界)
├── Vibe (交流风格)
└── Continuity (记忆延续性)
```

**关键特性**:
- Agent可修改自己的SOUL.md（需通知用户）
- 实现"soul growth"（人格成长）

**工作量**: 2-3天
**风险**: 低（纯prompt工程）

**验收标准**:
- [ ] Agent拒绝回答时会说"我不同意"而非"让我保持中立"
- [ ] Agent不会每句话都说"我很乐意帮忙"
- [ ] 对话风格明显区别于ChatGPT

---

#### [2] Workspace Bootstrap 配置注入

**问题**: 每个workspace无法自定义Agent行为，所有用户共享同一个system prompt

**解决方案**: 支持workspace级配置文件注入（类似OpenClaw/NanoBot）

**用户价值**:
- 不同团队可定制自己的Agent规范
- 支持企业级场景（合规、保密等）
- 降低新用户配置门槛

**技术方案**:
```
workspaces/{user}/
├── AGENTS.md     # 开发规范
├── SOUL.md       # 人格定义
├── TOOLS.md      # 工具使用指南
├── IDENTITY.md   # Agent身份
├── USER.md       # 用户偏好
└── MEMORY.md     # 长期记忆
```

**注入时机**: 每次会话开始时自动加载到system prompt

**大小限制**:
- 单文件: 20,000字符
- 总计: 150,000字符

**工作量**: 3-4天
**风险**: 中（需考虑上下文窗口）

**验收标准**:
- [ ] workspace/AGENTS.md内容注入到system prompt
- [ ] 文件超过限制时自动截断并提示
- [ ] 子Agent只注入AGENTS.md+TOOLS.md（节省token）

---

### P1 - 企业级能力 (重要)

#### [3] 资源配额管理

**问题**: 多租户模式下，用户可无限制消耗资源（CPU、内存、进程），导致DoS

**解决方案**: 实现per-user资源限制

**用户价值**:
- 防止恶意/异常用户耗尽系统资源
- 支持按用户等级分配资源
- 满足企业SLA要求

**技术方案**:
```python
# MCP Server资源限制
class MCPResourceQuota:
    max_memory_mb: int = 512      # 每用户内存上限
    max_cpu_time: int = 300       # 每用户CPU时间上限
    max_instances: int = 10       # 每用户MCP进程数
    max_concurrent_requests: int = 5  # 并发请求数

# 实现方式
import resource
resource.setrlimit(resource.RLIMIT_AS, (max_memory, hard_limit))
resource.setrlimit(resource.RLIMIT_CPU, (max_cpu, hard_limit))
```

**监控指标**:
- 每用户内存使用量
- 每用户MCP进程数
- 每用户请求频率

**工作量**: 4-5天
**风险**: 中（需仔细测试限制触发场景）

**验收标准**:
- [ ] 超过内存限制时MCP进程被终止
- [ ] 超过max_instances时返回明确错误
- [ ] 管理员可查看每用户资源使用情况

---

#### [4] SKILL路径安全验证

**问题**: user_context.skills_dir未重新验证，存在路径穿越风险（审计发现）

**解决方案**: 在加载user skills前验证路径合法性

**用户价值**:
- 防止恶意用户访问其他用户的SKILL
- 满足安全合规要求
- 避免敏感信息泄露

**技术方案**:
```python
# 在agent.py中加载user skills之前
def _validate_user_skills_dir(self, skills_dir: Path, workspace: Path) -> None:
    try:
        skills_dir.resolve().relative_to(workspace.resolve())
    except ValueError:
        raise SecurityError(
            f"User skills_dir '{skills_dir}' is not contained within workspace '{workspace}'"
        )
```

**工作量**: 1天
**风险**: 低

**验收标准**:
- [ ] skills_dir指向workspace外部时抛出SecurityError
- [ ] 通过安全测试用例（路径穿越攻击）

---

### P2 - 体验优化 (可选)

#### [5] 渐进式SKILL加载

**问题**: 所有SKILL内容注入system prompt，导致token浪费（很多SKILL用不上）

**解决方案**: 先显示SKILL摘要，agent按需用read_file加载

**用户价值**:
- 降低每轮对话的token成本
- 支持更多SKILL而不影响性能
- 提升响应速度

**技术方案**:
```
## Skills (mandatory)
Before replying: scan <available_skills> <description> entries.
- If exactly one skill clearly applies: read its SKILL.md at <location> with `read_file`
- If multiple could apply: choose the most specific one
- If none clearly apply: do not read any SKILL.md

<available_skills>
  <skill>
    <name>code_review</name>
    <description>Review code changes with best practices</description>
    <location>/workspace/skills/code_review/SKILL.md</location>
  </skill>
</available_skills>
```

**特殊处理**:
- `always: true`的SKILL仍然完整注入

**工作量**: 2-3天
**风险**: 低

**验收标准**:
- [ ] system prompt只包含SKILL摘要
- [ ] Agent调用read_file加载SKILL.md
- [ ] `always: true`的SKILL仍完整注入

---

#### [6] Memory智能整合

**问题**: 长对话导致context溢出，重要信息丢失

**解决方案**: 自动压缩长对话到MEMORY.md，保留关键信息

**用户价值**:
- 支持长对话不丢失上下文
- 自动提取"值得记住"的信息
- 降低token使用

**技术方案**:
```python
# 触发条件
if len(session.messages) > memory_window:
    asyncio.create_task(_consolidate_memory(session))

# 整合逻辑
async def _consolidate_memory(self, session):
    # 1. 提取关键信息（用LLM）
    summary = await llm.summarize(session.messages)

    # 2. 追加到MEMORY.md
    memory_file = workspace / "memory" / "MEMORY.md"
    memory_file.write_text(
        memory_file.read_text() + f"\n\n## {datetime.now()}\n{summary}"
    )

    # 3. 清空旧会话
    session.clear()
```

**工作量**: 3-4天
**风险**: 中（LLM总结质量不稳定）

**验收标准**:
- [ ] 会话超过50轮时自动触发整合
- [ ] MEMORY.md包含结构化的关键信息
- [ ] 整合后新会话仍可访问旧信息（通过MEMORY.md）

---

#### [7] Rate Limiting (频率限制)

**问题**: 无频率限制，用户可无限制调用API，导致成本失控

**解决方案**: 实现per-user请求频率限制

**用户价值**:
- 控制API成本
- 防止滥用/刷请求
- 支持按用户等级分配配额

**技术方案**:
```python
class RateLimiter:
    def __init__(self):
        self._user_call_counts: dict[str, int] = {}
        self._user_limits: dict[str, int] = {
            "default": 100,      # 每小时100次
            "premium": 1000,     # 每小时1000次
            "enterprise": -1,    # 无限制
        }

    async def check_rate_limit(self, user_key: str) -> bool:
        count = self._user_call_counts.get(user_key, 0)
        limit = self._get_user_limit(user_key)

        if limit > 0 and count >= limit:
            raise RateLimitError(f"User '{user_key}' exceeded rate limit: {limit}/hour")

        self._user_call_counts[user_key] = count + 1
        return True
```

**工作量**: 2-3天
**风险**: 低

**验收标准**:
- [ ] 超过限制时返回429错误
- [ ] 管理员可配置每用户限制
- [ ] 每小时自动重置计数器

---

#### [8] 用户黑白名单

**问题**: 无法禁止特定用户使用系统（安全风险）

**解决方案**: 实现用户黑名单/白名单机制

**用户价值**:
- 可快速封禁恶意用户
- 企业模式支持白名单（仅授权用户）
- 提升系统安全性

**技术方案**:
```python
class MultiTenantMCPManager:
    def __init__(self, ...):
        self._blocked_users: set[str] = set()
        self._allowed_users: Optional[set[str]] = None  # None = all users

    async def get_manager(self, server_name, server_config, user_key):
        # Check blacklist
        if user_key in self._blocked_users:
            raise SecurityError(f"User '{user_key}' is blocked")

        # Check whitelist if enabled
        if self._allowed_users is not None and user_key not in self._allowed_users:
            raise SecurityError(f"User '{user_key}' is not allowed")
```

**工作量**: 1-2天
**风险**: 低

**验收标准**:
- [ ] 黑名单用户无法访问任何功能
- [ ] 白名单模式：仅白名单用户可访问
- [ ] 管理员可动态修改黑白名单

---

## 竞品对比

### 功能对比表

| 功能 | FastReAct | OpenClaw | NanoBot | LangChain |
|------|-----------|----------|---------|-----------|
| **SKILL系统** | ✅ 完整 | ✅ 完整 | ✅ 完整 | ❌ 无 |
| **MCP集成** | ✅ 3种模式 | ✅ 支持 | ✅ 支持 | ❌ 无 |
| **多租户** | ✅ Workspace隔离 | ✅ 支持 | ✅ 支持 | ❌ 无 |
| **事件驱动** | ✅ AsyncIterator | ✅ | ❌ | ❌ |
| **SOUL.md人格** | ❌ | ✅ | 可选 | ❌ |
| **Bootstrap注入** | ❌ | ✅ | ✅ | ❌ |
| **渐进式SKILL** | ❌ | ✅ | ✅ | ❌ |
| **资源配额** | ❌ | ❌ | ❌ | ❌ |
| **Rate Limiting** | ❌ | ❌ | ❌ | 部分支持 |
| **Memory整合** | ❌ | ❌ | ✅ | ❌ |
| **Brain-Body分离** | ✅ | ❌ | ❌ | ❌ |

**差异化优势** (FastReAct独有):
- Brain-Body架构（Core纯推理 + Agent执行）
- MCP 3种隔离模式（shared/per_user/lazy_per_user）
- 事件驱动协议（统一的事件流）

**补齐后优势**:
- 完整的产品能力（人格 + 配置 + 安全）
- 企业级可靠性（配额 + 限流 + 黑白名单）
- 更好的用户体验（渐进式加载 + Memory整合）

---

## 开发计划

### Phase 1: 核心差异化 (1周)

**目标**: 打造产品辨识度，实现"人格化Agent"

| 任务 | 工作量 | 优先级 | 依赖 |
|------|--------|--------|------|
| SOUL.md实现 | 2-3天 | P0 | 无 |
| Bootstrap注入 | 3-4天 | P0 | 无 |
| 测试 + 文档 | 1-2天 | P0 | 以上 |

**里程碑**:
- [ ] Agent有明显的个性化回复
- [ ] Workspace可自定义AGENTS.md/SOUL.md
- [ ] 用户手册更新

---

### Phase 2: 企业级能力 (1周)

**目标**: 满足企业部署要求，实现多租户安全

| 任务 | 工作量 | 优先级 | 依赖 |
|------|--------|--------|------|
| 资源配额 | 4-5天 | P1 | 无 |
| SKILL安全验证 | 1天 | P1 | 无 |
| 测试 + 文档 | 1-2天 | P1 | 以上 |

**里程碑**:
- [ ] Per-user资源限制生效
- [ ] 安全测试通过（无路径穿越）
- [ ] 管理员面板可查看资源使用

---

### Phase 3: 体验优化 (1周)

**目标**: 降低成本，提升用户体验

| 任务 | 工作量 | 优先级 | 依赖 |
|------|--------|--------|------|
| 渐进式SKILL加载 | 2-3天 | P2 | 无 |
| Memory整合 | 3-4天 | P2 | 无 |
| 测试 + 文档 | 1-2天 | P2 | 以上 |

**里程碑**:
- [ ] System prompt大小降低50%
- [ ] 长对话不丢失上下文
- [ ] 用户文档更新

---

### Phase 4: 安全增强 (可选)

| 任务 | 工作量 | 优先级 | 依赖 |
|------|--------|--------|------|
| Rate Limiting | 2-3天 | P2 | 无 |
| 黑白名单 | 1-2天 | P2 | 无 |
| 测试 + 文档 | 1天 | P2 | 以上 |

---

## ROI分析

### 开发投入

| Phase | 工作量 | 人力成本 (假设) |
|-------|--------|----------------|
| Phase 1 | 1周 | 1人周 |
| Phase 2 | 1周 | 1人周 |
| Phase 3 | 1周 | 1人周 |
| Phase 4 | 1周 | 1人周 |
| **总计** | **4周** | **1人月** |

### 商业价值

**品牌差异化**:
- "有人格的Agent" vs "冷冰冰的工具"
- 用户留存率 +20-30% (OpenClaw经验)

**成本优化**:
- 渐进式加载: token成本 -30%
- Memory整合: 长对话token成本 -50%

**企业市场**:
- 资源配额 + 安全: 满足企业合规要求
- 单客户价值: $5K-20K/年

**风险降低**:
- SKILL安全验证: 避免数据泄露（法律风险）
- Rate limiting: 控制API成本（财务风险）

**预期ROI**: 3-6个月回本

---

## 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| SOUL.md效果不佳 | 中 | 中 | A/B测试不同人格模板 |
| Bootstrap注入token超限 | 低 | 中 | 严格限制文件大小 |
| 资源配额误杀正常用户 | 中 | 高 | 监控 + 白名单机制 |
| Memory整合丢失信息 | 中 | 中 | 人工审核整合结果 |
| 渐进式加载Agent不加载 | 低 | 低 | 添加强制指令 |

---

## 决策建议

### 如果资源有限 (仅2周)

**建议**: Phase 1 (SOUL.md + Bootstrap)

**理由**:
- 最高产品辨识度
- 开发风险最低
- 用户价值最直观

### 如果追求完整 (1个月)

**建议**: Phase 1 + 2 + 3

**理由**:
- 覆盖80%用户价值
- 满足企业基本要求
- 性能与体验兼顾

### 如果面向企业 (2个月)

**建议**: 全部Phase

**理由**:
- 完整的企业级能力
- 安全与合规
- 竞品全面超越

---

## 附录

### A. 参考资料

- OpenClaw SOUL.md: `/Users/xudawei/openclaw/docs/reference/templates/SOUL.md`
- OpenClaw system-prompt: `/Users/xudawei/openclaw/src/agents/system-prompt.ts`
- NanoBot skills: `/Users/xudawei/nanobot/nanobot/agent/skills.py`
- 多租户审计报告: `docs/MULTITENANT_AUDIT_REPORT.md`
- Prompt研究报告: `docs/PROMPT_RESEARCH_REPORT.md`

### B. 术语表

| 术语 | 解释 |
|------|------|
| **SOUL.md** | Agent人格定义文件（OpenClaw概念） |
| **Bootstrap** | workspace启动时自动加载的配置文件 |
| **渐进式加载** | 先显示摘要，按需加载完整内容 |
| **Memory整合** | 长对话自动压缩到MEMORY.md |
| **资源配额** | per-user CPU/内存/进程限制 |
| **Rate Limiting** | 请求频率限制 |

### C. 联系方式

**产品问题**: 联系产品团队
**技术问题**: 查看CLAUDE.md或提交issue
**进度跟踪**: 查看docs/目录下的各阶段报告

---

**文档版本**: 1.0
**最后更新**: 2025-02-23
**下次审查**: 实施开始后1周
