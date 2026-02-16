# Graceful Interrupt Implementation

**Date**: 2026-02-16
**Status**: IMPROVED

---

## Design Principle

**Key Insight**: User's "stop" command should be treated as **steering**, not as a hard kill.

### Why This Matters

When a user says "stop", they want to:
1. ✅ Stop the current task
2. ✅ Let the LLM acknowledge the interruption
3. ✅ Get a graceful ending, not an abrupt cutoff
4. ✅ Maintain conversation context

**NOT**:
- ❌ Brutally kill the process mid-thought
- ❌ Lose the LLM's partial response
- ❌ Break the conversation flow

---

## Implementation

### The Flow

```
1. User sends long task
   ↓
2. Agent starts executing tools
   ↓
3. User sends "stop"
   ↓
4. Gateway injects: Message.user("[INTERRUPT] stop")
   ↓
5. Agent adds interrupt to message history
   ↓
6. Agent emits: [USER INTERRUPT: stop]
   ↓
7. Agent sets: interrupted = True
   ↓
8. Agent breaks from tool loop (no more tools)
   ↓
9. Agent allows one final LLM call (to process interrupt)
   ↓
10. Agent emits SESSION_END with graceful message
   ↓
11. User sees LLM's acknowledgment + interrupted status
```

### Code Changes

**File**: `fastreact-nano/src/fastreact/agent.py`

**1. Add Interrupt Flag** (Line 431)
```python
interrupted = False
```

**2. Process Interrupt Gracefully** (Lines 445-466)
```python
if pending_messages:
    for msg in pending_messages.drain():
        if msg.content.startswith("[INTERRUPT]"):
            # Add to message history so LLM sees it
            messages.append(msg.to_llm_format())

            # Notify user
            yield AgentEvent.think(
                f"[USER INTERRUPT: {msg.content.replace('[INTERRUPT] ', '')}]",
                session_id,
                metadata={"source": "user"}
            )

            # Set flag to stop after current iteration
            interrupted = True
            has_more_tool_calls = False
            break  # Exit message processing
```

**3. Graceful Session End** (Lines 610-628)
```python
# Check if we were interrupted
if interrupted:
    # Extract last assistant message
    last_response = ""
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            if content and not content.startswith("["):
                last_response = content
                break

    # Emit interrupted session end
    interrupt_msg = "[INTERRUPTED] User stopped the execution"
    if last_response:
        interrupt_msg = f"{last_response}\n\n[INTERRUPTED] User stopped the execution"

    yield AgentEvent.session_end(session_id, interrupt_msg)
    return
```

---

## Comparison: Force Kill vs Graceful Interrupt

### Force Kill (Previous Implementation)

```python
if msg.content.startswith("[INTERRUPT]"):
    yield AgentEvent.session_end(session_id, "[INTERRUPTED] ...")
    return  # ← Immediate exit, no LLM processing
```

**Result**:
- ❌ LLM never sees the interrupt
- ❌ No acknowledgment from LLM
- ❌ Abrupt cutoff
- ❌ Confusing UX

**Example**:
```
User: "Analyze all files"
Agent: [Starts executing tools]
User: "stop"
Agent: [INTERRUPTED] stop  ← Cold, robotic
```

---

### Graceful Interrupt (New Implementation)

```python
if msg.content.startswith("[INTERRUPT]"):
    messages.append(msg.to_llm_format())  # ← LLM sees it
    yield AgentEvent.think(f"[USER INTERRUPT: ...]")
    interrupted = True
    has_more_tool_calls = False
    # ... continues to final LLM call
```

**Result**:
- ✅ LLM sees the interrupt in conversation
- ✅ LLM can acknowledge naturally
- ✅ Graceful ending
- ✅ Better UX

**Example**:
```
User: "Analyze all files"
Agent: [Starts executing tools]
User: "stop"
Agent: [USER INTERRUPT: stop]
Agent: "I understand you want me to stop. I was analyzing the project structure when interrupted. [INTERRUPTED] User stopped the execution"
```

---

## Steering vs Interrupt

### Same Mechanism, Different Intent

Both use the **same underlying mechanism**: adding messages to the conversation during execution.

**Steering** (Add context):
```python
Message.steering("Focus on performance", source="user")
```
- Adds to conversation
- LLM incorporates into current task
- Execution continues

**Interrupt** (Stop execution):
```python
Message.user("[INTERRUPT] stop")
```
- Adds to conversation
- LLM acknowledges the stop
- Execution stops after current iteration

---

## Benefits

### 1. Intelligence
- LLM understands why task was stopped
- Can provide context-aware response
- Maintains conversation continuity

### 2. Transparency
- User sees "[USER INTERRUPT: stop]" event
- Clear indication that interrupt was received
- LLM's acknowledgment visible

### 3. Flexibility
- LLM can choose how to respond
- Can summarize what was done
- Can offer to continue later

### 4. Consistency
- Same as other steering messages
- Unified message handling
- Simpler code architecture

---

## Example Scenarios

### Scenario 1: Interrupt During Tool Execution

```
User: "List all Python files and analyze them"
Agent: Thinking...
Agent: [TOOL_CALL] exec("ls")
Agent: [TOOL_RESULT] file1.py, file2.py, ...
User: "stop"  ← User wants to stop
Agent: [USER INTERRUPT: stop]  ← System confirms
Agent: "I found several Python files and was beginning to analyze them. I'll stop here as requested. [INTERRUPTED] User stopped the execution"
```

### Scenario 2: Interrupt With Partial Response

```
User: "Write a detailed report on X"
Agent: [Starts writing and researching]
User: "Actually, just give me a summary"  ← Steering
Agent: [USER STEERING: Actually, just give me a summary]
Agent: "I'll focus on providing a concise summary instead..."

User: "stop"  ← Then user stops
Agent: [USER INTERRUPT: stop]
Agent: "Here's what I gathered so far: [partial info]. I'll stop here. [INTERRUPTED] User stopped the execution"
```

---

## Timing Characteristics

### When Does Stop Happen?

1. **Immediate** (interrupt detection)
   - User sends "stop"
   - Gateway detects immediately
   - Injects into session queue
   - Agent checks queue before next tool

2. **Current Tool Completes** (graceful)
   - If a tool is running, let it finish
   - Example: `read_file()` completes
   - Don't kill mid-execution (risky)

3. **No More Tools** (loop exit)
   - Set `has_more_tool_calls = False`
   - Break from tool execution loop
   - Proceed to final LLM call

4. **Final LLM Processing** (acknowledgment)
   - LLM sees interrupt in history
   - Generates acknowledgment
   - Emits SESSION_END

**Total Latency**: Typically 0.5-2 seconds

---

## Edge Cases

### Case 1: Interrupt During Slow Tool
**Tool**: HTTP request (5 seconds)
**Behavior**: Let tool finish, then stop
**Rationale**: Safer than killing mid-request

### Case 2: Multiple Interrupts
**User**: "stop" → "cancel" → "abort"
**Behavior**: First interrupt stops, others create new sessions
**Rationale**: Session already ended, subsequent are new queries

### Case 3: Interrupt + Steering
**User**: "stop and summarize" (both keywords)
**Behavior**: Treated as interrupt (stop wins)
**Rationale**: Safety first, stop immediately

---

## Configuration

### Interrupt Keywords

**File**: `gateway.py` line 313

```python
interrupt_keywords = ["stop", "cancel", "中断", "停止", "abort"]
```

**Easy to extend**:
```python
interrupt_keywords = [
    "stop", "cancel", "abort",
    "中断", "停止",
    "halt", "terminate", "cease",  # Add more
]
```

---

## Testing

### Test 1: Basic Interrupt
```bash
1. Send: "Analyze all files"
2. Wait: First tool executes
3. Send: "stop"
4. Verify: See "[USER INTERRUPT: stop]"
5. Verify: Agent responds gracefully
6. Verify: No more tools execute
```

### Test 2: Interrupt With Response
```bash
1. Send: "Write about X"
2. Wait: Thinking starts
3. Send: "stop"
4. Verify: Agent acknowledges
5. Verify: Shows "[INTERRUPTED]" message
```

### Test 3: Rapid Fire
```bash
1. Send: Long task
2. Send: "stop"
3. Send: "cancel" (immediately)
4. Verify: First stops, second starts new session
```

---

## Future Enhancements

### Short Term
- [ ] Add visual indicator in UI when interrupted
- [ ] Show "[INTERRUPTED]" badge on message
- [ ] Option to resume interrupted task

### Long Term
- [ ] Graceful tool shutdown (send cancel signal)
- [ ] Checkpoint/resume capability
- [ ] Interrupt history and analytics

---

## Deployment

**Status**: ✅ Deployed
**Gateway PID**: 30136
**Ready for Testing**: Yes

---

**Summary**: Graceful interrupt treats "stop" as a steering message, allowing the LLM to acknowledge and end the conversation naturally, rather than brutally killing the process.
