# Core Audit Report - Agent.py 四大致命隐患

**Date**: 2025-02-18
**Auditor**: Claude Code
**Scope**: `src/fastreact/agent.py` + Core components
**Status**: 🔍 Audit Complete | 🚧 1 Critical Issue Found

---

## Executive Summary

审计了 agent.py 及其核心组件的四个"致命隐患"。结果：

| 隐患 | 状态 | 风险等级 | 位置 |
|------|------|----------|------|
| 工具崩溃 | ✅ 已保护 | 🟢 Low | agent.py:799-811 |
| 上下文爆炸 | ✅ 已保护 | 🟢 Low | agent.py:807-808, context.py:78-107 |
| 死循环 | ❌ **未保护** | 🔴 **Critical** | agent.py:678 |
| 格式幻觉 | ⚠️ 部分保护 | 🟡 Medium | litellm.py:323-326 |

**关键发现**: Agent.py 的主循环缺少迭代计数器，存在死循环风险。

---

## 1. 工具崩溃 (Tool Failure) ✅

### 审计发现

**位置**: `src/fastreact/agent.py:799-811`

```python
# Execute tool
try:
    result = await self._tools.execute(
        tool_name,
        tool_params,
        user_context=user_context
    )

    # Context truncate if needed
    if self._context_monitor:
        result = self._context_monitor.truncate_tool_output(result)

except Exception as e:
    result = f"[ERROR] {str(e)}"
```

### 现状评估 ✅

- **异常捕获**: ✅ 所有工具调用异常被捕获
- **错误传递**: ✅ 错误转换为 `[ERROR]` 消息
- **LLM 自修正**: ✅ 错误信息喂回给 LLM，可以自我修正

### 测试场景

```python
# 场景1: 命令不存在
User: "运行 xyzcommand"
Agent: 调用 exec("xyzcommand")
Error: [ERROR] Command not found: xyzcommand
LLM: "我应该尝试其他命令..."  ✅ 自修正

# 场景2: 工具超时
User: "读取超大文件"
Agent: 调用 read_file("/huge.log")
Timeout: [ERROR] Timeout after 30s
LLM: "文件太大，让我试试分页读取..."  ✅ 自修正
```

### 结论

**无需修改** - 异常处理机制完善。

---

## 2. 上下文爆炸 (Context Overflow) ✅

### 审计发现

**位置**: `src/fastreact/agent.py:807-808` + `src/fastreact/core/context.py:78-107`

```python
# agent.py:807-808
if self._context_monitor:
    result = self._context_monitor.truncate_tool_output(result)
```

```python
# context.py:78-107
def truncate_tool_output(self, output: str, tool_name: str = "unknown") -> str:
    """智能截断策略：80% head + 20% tail"""
    if len(output) <= self._max_tool_output_chars:
        return output

    # 80% head + 20% tail
    head_chars = int(self._max_tool_output_chars * 0.8)
    tail_chars = int(self._max_tool_output_chars * 0.2)

    head = output[:head_chars]
    tail = output[-tail_chars:] if tail_chars > 0 else ""

    return f"{head}\n\n... [Tool output truncated] ...\n\n{tail}"
```

### 现状评估 ✅

- **工具输出截断**: ✅ 智能策略（保留首尾）
- **配置化阈值**: ✅ `max_tool_output_chars` 可配置
- **统计追踪**: ✅ 记录截断次数和最后截断的工具

### 配置参数

```python
# src/fastreact/core/config.py
@dataclass
class ReActConfig:
    max_tool_output_chars: int = 5000  # 默认 5KB
    max_context_tokens: int = 16000    # 默认 16K tokens
```

### 测试场景

```python
# 场景1: 读取 10MB 日志文件
User: "读取 /var/log/app.log"
Agent: read_file("/var/log/app.log")
Tool Result: [前 4000 字符]...[后 1000 字符]  ✅ 截断保护

# 场景2: 多轮对话累积
Messages: 50 轮对话 × 500 tokens = 25K tokens
Context Monitor: 启动上下文压缩  ✅ 溢出保护
```

### 结论

**无需修改** - 截断策略完善。

---

## 3. 死循环 (Infinite Loop) ❌ **CRITICAL**

### 审计发现

**位置**: `src/fastreact/agent.py:678-851`

```python
# === Outer loop: Process follow-up messages ===
while True:  # ⚠️ 没有迭代计数器！
    has_more_tool_calls = True
    executed_tools_this_iteration = False

    # === Inner loop: Process tools ===
    while has_more_tool_calls:
        # 1. Brain: Ask LLM for reasoning
        # 2. Body: Execute tools
        # 3. Check for follow-up messages

    # Check if we should continue
    if executed_tools_this_iteration and not has_followup:
        continue  # ⚠️ 可能无限循环！

    if has_followup:
        continue  # ⚠️ 可能无限循环！

    # Otherwise, we're done
    break
```

### 现状评估 ❌

- **迭代计数器**: ❌ **不存在**
- **强制终止**: ❌ **无 max_iterations 检查**
- **循环退出条件**: ⚠️ 依赖 LLM 返回空工具调用

### 风险场景

```python
# 场景1: LLM 陷入"思考-出错-思考-出错"
User: "修复这个 bug"
LLM: "我应该检查日志" → 调用 exec("tail log")
Tool: [ERROR] Permission denied
LLM: "让我试试 sudo" → 调用 exec("sudo tail log")
Tool: [ERROR] Permission denied
LLM: "让我试试看日志文件" → 调用 read_file("log")
Tool: [ERROR] File not found
... 无限循环  ❌ 死循环！

# 场景2: 工具返回空结果，LLM 不断重试
User: "分析这个文件"
LLM: "读取文件" → read_file("data.txt")
Tool: "" (空文件)
LLM: "可能是格式问题，再读一次" → read_file("data.txt")
Tool: ""
LLM: "让我换个编码再读" → read_file("data.txt")
... 无限循环  ❌ 死循环！
```

### 修复建议

```python
# 在 run_event_stream() 开始添加迭代计数
async def run_event_stream(self, query: str, ...) -> AsyncIterator["AgentEvent"]:
    # ... 现有代码 ...

    iteration = 0
    max_iterations = self._config.react.max_iterations  # 默认 20

    # === Outer loop ===
    while True:
        # 强制检查迭代次数
        if iteration >= max_iterations:
            yield AgentEvent.session_end(
                session_id,
                f"[STOPPED] Max iterations ({max_iterations}) reached. "
                f"Last action: {last_action}"
            )
            break

        iteration += 1
        # ... 其余代码 ...
```

### 优先级

🔴 **Critical** - 必须修复

**预估修复时间**: 30分钟

---

## 4. 格式幻觉 (JSON Hallucination) ⚠️

### 审计发现

**位置**: `src/fastreact/providers/litellm.py:323-326`

```python
def _parse_function_args(self, arguments: str) -> dict[str, Any]:
    """Parse JSON function arguments"""
    import json

    try:
        return json.loads(arguments)
    except json.JSONDecodeError:
        return {}  # ⚠️ 返回空字典，不重试
```

### 现状评估 ⚠️

- **异常捕获**: ✅ 捕获 JSONDecodeError
- **降级策略**: ⚠️ 返回空字典（导致工具调用失败）
- **重试机制**: ❌ **不存在**

### 风险场景

```python
# 场景1: LLM 输出残缺 JSON
LLM Output: {"command": "ls -la",  (缺少闭合括号)
Parser: json.loads() → JSONDecodeError
Fallback: return {}
Tool Call: exec({}) → 执行空命令  ⚠️ 错误行为

# 场景2: LLM 输出格式错误的 JSON
LLM Output: {"command": "ls -la", "cwd": "/tmp"}  (缺少引号)
Parser: json.loads() → JSONDecodeError
Fallback: return {}
Tool Call: exec({}) → 执行空命令  ⚠️ 错误行为
```

### 修复建议

```python
def _parse_function_args(self, arguments: str) -> dict[str, Any]:
    """Parse JSON function arguments with robust fallback"""
    import json
    import re

    try:
        return json.loads(arguments)

    except json.JSONDecodeError as e:
        # 尝试修复常见 JSON 错误
        try:
            # 1. 尝试修复缺少的引号
            fixed = re.sub(r'(\w+):', r'"\1":', arguments)
            return json.loads(fixed)

        except:
            # 2. 尝试修复尾随逗号
            try:
                fixed = re.sub(r',\s*}', '}', arguments)
                return json.loads(fixed)

            except:
                # 3. 最后的降级：记录错误并返回空
                print(f"[ERROR] JSON parsing failed: {e}", file=sys.stderr)
                print(f"[ERROR] Raw input: {arguments[:200]}...", file=sys.stderr)
                return {}
```

### 优先级

🟡 **Medium** - 建议修复（但不紧急）

**预估修复时间**: 1小时

---

## 综合建议

### 立即修复 (Critical)

1. **添加迭代计数器** - 防止死循环
   ```python
   iteration = 0
   while iteration < max_iterations:
       iteration += 1
       # ... 循环体 ...
   ```

### 建议修复 (Medium)

2. **增强 JSON 解析鲁棒性** - 添加修复尝试和重试
   ```python
   try:
       return json.loads(arguments)
   except JSONDecodeError:
       # 尝试修复常见错误
       # 或重试 LLM 调用
   ```

### 已确认良好 (无需修改)

3. ✅ 工具崩溃处理 - 完善的异常捕获
4. ✅ 上下文溢出保护 - 智能截断策略

---

## 测试计划

### 死循环测试

```python
# test_infinite_loop_protection.py
async def test_max_iterations():
    """测试迭代次数限制"""
    agent = Agent()

    # 触发可能死循环的场景
    events = []
    async for event in agent.run_event_stream("无限循环触发"):
        events.append(event)
        if event.type == EventType.SESSION_END:
            break

    # 验证：不超过 max_iterations
    tool_calls = [e for e in events if e.type == EventType.TOOL_CALL]
    assert len(tool_calls) <= agent._config.react.max_iterations
```

### JSON 解析测试

```python
# test_json_robustness.py
def test_malformed_json():
    """测试残缺 JSON 处理"""
    provider = LiteLLMProvider(model="gpt-4o-mini")

    # 场景1: 缺少闭合括号
    result = provider._parse_function_args('{"cmd": "ls"')
    assert result == {} or result == {"cmd": "ls"}  # 至少不崩溃

    # 场景2: 完全错误的 JSON
    result = provider._parse_function_args('not json at all')
    assert result == {}  # 安全降级
```

---

## 结论

**审计总结**:
- ✅ 2/4 隐患已妥善处理
- ❌ 1/4 隐患需要立即修复（死循环）
- ⚠️ 1/4 隐患建议改进（JSON 解析）

**下一步行动**:
1. 🔴 **Critical**: 修复迭代计数器 - 30分钟
2. 🟡 **Medium**: 增强 JSON 解析 - 1小时
3. ✅ **Good**: 添加测试用例验证修复

**Phase 1.5 完成标准**:
- [ ] 死循环保护已实现
- [ ] JSON 解析更鲁棒
- [ ] 测试用例通过
- [ ] 文档更新

---

**Auditor**: Claude Code
**Date**: 2025-02-18
**Status**: 🔍 Audit Complete | 🚧 1 Critical Fix Required
