# Infinite Loop Protection - Fix Summary

**Date**: 2025-02-18
**Severity**: 🔴 Critical
**Status**: ✅ Fixed & Tested
**Files Modified**: `src/fastreact/agent.py`

---

## Problem

Agent.py 的主循环 (`while True:`) **没有迭代计数器**，可能导致：
- LLM 陷入"思考-出错-重试"死循环
- 无限消耗 token 和时间
- 用户无法中断（控制消息也可能来不及处理）

### Risk Scenario

```python
# LLM 陷入死循环
User: "修复这个 bug"
LLM: "检查日志" → exec("tail log")
Tool: [ERROR] Permission denied
LLM: "试试 sudo" → exec("sudo tail log")
Tool: [ERROR] Permission denied
LLM: "试试看日志文件" → read_file("log")
Tool: [ERROR] File not found
... 无限循环  ❌ 消耗 token + 时间
```

---

## Solution

### 1. 硬限 (Hard Limit)

```python
# 从配置读取，保底值 25
max_iterations = self._config.react.max_iterations if self._config else 25
```

### 2. 计数器 (The Counter)

```python
# 循环外初始化
iteration_count = 0

while True:
    iteration_count += 1  # 每次循环自增
```

### 3. 熔断机制 (Circuit Breaker)

```python
if iteration_count > max_iterations:
    # 立即终止并发送明确错误消息
    yield AgentEvent.session_end(
        session_id,
        f"[STOPPED] Task stopped due to maximum iteration limit ({max_iterations}). "
        f"This usually means the agent is stuck in a loop or the task is too complex. "
        f"Please try breaking down the task into smaller steps."
    )
    return
```

---

## Changes

### File: `src/fastreact/agent.py`

**Location**: Line 674-693 (新增 15 行)

```diff
            # Interrupt flag
            interrupted = False

+           # Iteration counter with hard limit to prevent infinite loops
+           iteration_count = 0
+           max_iterations = self._config.react.max_iterations if self._config else 25
+
            # === Outer loop: Process follow-up messages ===
            while True:
+               # HARD LIMIT: Prevent infinite loops
+               iteration_count += 1
+               if iteration_count > max_iterations:
+                   # Circuit breaker: immediately terminate with clear error message
+                   yield AgentEvent.session_end(
+                       session_id,
+                       f"[STOPPED] Task stopped due to maximum iteration limit ({max_iterations}). "
+                       f"This usually means the agent is stuck in a loop or the task is too complex. "
+                       f"Please try breaking down the task into smaller steps."
+                   )
+                   return
                has_more_tool_calls = True
                executed_tools_this_iteration = False
```

---

## Testing

### Test File: `tests/unit/test_infinite_loop_protection.py`

Created 3 test cases:

1. **test_max_iterations_limit**: 验证超限时终止
2. **test_normal_query_completes**: 验证正常查询不受影响
3. **test_iteration_counter_increments**: 验证计数器正确工作

### Test Results

```bash
$ pytest tests/unit/test_infinite_loop_protection.py -v

tests/unit/test_infinite_loop_protection.py::test_max_iterations_limit PASSED
tests/unit/test_infinite_loop_protection.py::test_normal_query_completes PASSED
tests/unit/test_infinite_loop_protection.py::test_iteration_counter_increments PASSED

========================= 3 passed in 85.10s =========================
```

✅ **All tests passed**

---

## Configuration

### Default Value

```python
# src/fastreact/core/config.py
@dataclass
class ReActConfig:
    max_iterations: int = 20  # 默认 20 次迭代
```

### Override via Environment

```bash
export FASTRACT_MAX_ITERATIONS=25
```

### Override via Config File

```json
// ~/.fastreact/config.json or ./.fastreact/config.json
{
  "react": {
    "max_iterations": 25
  }
}
```

---

## Behavior Changes

### Before Fix ❌

```python
# 可能无限循环
while True:
    # 执行工具...
    if has_tool_calls:
        continue  # 可能永远不退出
```

**Risk**: Agent could run forever consuming tokens

### After Fix ✅

```python
iteration_count = 0
while True:
    iteration_count += 1
    if iteration_count > max_iterations:
        # 明确终止
        yield AgentEvent.session_end(...)
        return
```

**Guarantee**: Agent stops after max_iterations (default: 20-25)

---

## User Experience

### When Limit is Reached

Frontend receives clear error message:

```json
{
  "type": "event",
  "event_type": "session_end",
  "content": "[STOPPED] Task stopped due to maximum iteration limit (20). This usually means the agent is stuck in a loop or the task is too complex. Please try breaking down the task into smaller steps."
}
```

User sees:
```
[STOPPED] Task stopped due to maximum iteration limit (20).
This usually means the agent is stuck in a loop or the task is too complex.
Please try breaking down the task into smaller steps.
```

---

## Deployment

### Gateway Server

**Restart Required**: ✅ Completed

```bash
$ pkill -f "fastreact.adapters.gateway"
$ python3 -m fastreact.adapters.gateway > /tmp/gateway.log 2>&1 &
```

**Status**: Running on http://0.0.0.0:9000

---

## Verification

### Manual Test

1. Open frontend: http://localhost:3000
2. Send query that might cause loop: "Repeat 'hello' forever"
3. Verify agent stops after ~20 iterations
4. Verify clear error message displayed

### Automated Test

```bash
$ pytest tests/unit/test_infinite_loop_protection.py -v
```

---

## Future Improvements

### Optional Enhancements

1. **Adaptive Limit**: 根据任务复杂度动态调整
   ```python
   max_iterations = estimate_complexity(query) * BASE_LIMIT
   ```

2. **Progressive Warnings**: 接近限制时发出警告
   ```python
   if iteration_count == max_iterations * 0.8:
       yield AgentEvent.warning("Approaching iteration limit...")
   ```

3. **Smart Retry**: 检测循环模式并自动切换策略
   ```python
   if detect_loop_pattern(messages):
       yield AgentEvent.suggestion("Try breaking down the task...")
   ```

---

## Related Issues

- Fixes: #Infinite Loop Risk
- Related: #Context Overflow Protection
- Related: #Tool Failure Handling

---

## Checklist

- [x] Code fix implemented
- [x] Tests created and passing
- [x] Gateway server restarted
- [x] Documentation updated
- [x] Config default value verified
- [x] Error message user-friendly

---

**Status**: ✅ **COMPLETE** - Ready for production
**Next**: Monitor production for iteration limit hits, adjust if needed
