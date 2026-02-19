# System Robustness Audit - Multi-turn & MCP

**Date**: 2025-02-18
**Goal**: 打造不可摧毁的系统 (Unbreakable System)
**Scope**: 多轮对话内存 + MCP工具错误处理

---

## Part 1: Multi-turn Dialog Memory 🔍

### Current Implementation

#### Agent Layer (agent.py)

```python
async def run_event_stream(
    self,
    query: str,
    session_id: Optional[str] = None,  # ✅ 支持session_id
    history: Optional[list[dict]] = None,  # ✅ 支持history
):
    # Validate and clean history
    messages = self._validate_history(history)  # ✅ 验证history

    # Add current user message
    messages.append(Message.user(query).to_llm_format())  # ✅ 添加当前消息

    # ... process with messages ...
```

**Status**: ✅ Agent 层实现正确

#### Gateway Layer (gateway.py - Session)

```python
class Session:
    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        # ❌ 没有 _history 属性！
        # ❌ 没有持久化历史记录

    async def _handle_message(self, message: dict):
        if msg_type == "query":
            query = message.get("content", "")
            skills = message.get("skills")

            # ❌ 没有传递 history！
            async for event in self.agent.run_event_stream(
                query,
                skills=skills,
                session_id=self.session_id,  # ✅ 传递了session_id
                # history=?  ❌ 缺少！
            ):
```

**Status**: ❌ **Critical Issue** - Gateway Session 没有历史记录

---

### Problem Analysis

#### Issue #1: No History Persistence ❌

**Current Behavior**:
```python
# Turn 1
User: "What is 2+2?"
Agent: "4"  ✅

# Turn 2 (new WebSocket message)
User: "What about 3+3?"
Agent: "6"  ✅ But doesn't remember "2+2=4" ❌
```

**Why**: Each call to `run_event_stream()` creates a new `messages` list from scratch.

#### Issue #2: Session State Not Saved ❌

**Current Behavior**:
```python
session = Session(session_id, websocket)
# ❌ session._history doesn't exist
# ❌ No persistence to disk
# ❌ No resume after disconnect
```

---

### Fix Strategy

#### Solution #1: Add History to Session

```python
class Session:
    def __init__(self, session_id: str, websocket: WebSocket, max_history: int = 50):
        self.session_id = session_id
        self._history: list[dict] = []  # ✅ 添加历史记录
        self._max_history = max_history  # ✅ 限制历史长度

    async def _handle_message(self, message: dict):
        if msg_type == "query":
            query = message.get("content", "")

            # ✅ 传递历史记录
            async for event in self.agent.run_event_stream(
                query,
                skills=skills,
                session_id=self.session_id,
                history=self._history,  # ✅ 传递历史
            ):
                # Send event to frontend
                await self.send(event.to_dict())

                # ✅ 更新历史记录
                if event.type == EventType.SESSION_END:
                    self._update_history(query, event.content)

    def _update_history(self, user_query: str, assistant_response: str):
        """Update conversation history"""
        # Add user message
        self._history.append({"role": "user", "content": user_query})

        # Add assistant message
        self._history.append({"role": "assistant", "content": assistant_response})

        # Prune if too long
        if len(self._history) > self._max_history:
            # Keep only recent messages (FIFO)
            self._history = self._history[-self._max_history:]
```

#### Solution #2: Optional Persistence

```python
import json
from pathlib import Path

class Session:
    def __init__(self, ..., persist_history: bool = False):
        self._persist_history = persist_history
        self._history_file = None

        if persist_history:
            # Create workspace/.fastreact/sessions/
            sessions_dir = Path.cwd() / "workspace" / ".fastreact" / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)
            self._history_file = sessions_dir / f"{session_id}.json"

            # Load existing history
            self._history = self._load_history()
        else:
            self._history = []

    def _load_history(self) -> list[dict]:
        """Load history from disk"""
        if self._history_file and self._history_file.exists():
            try:
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARNING] Failed to load history: {e}", file=sys.stderr)
                return []
        return []

    def _save_history(self):
        """Save history to disk"""
        if self._history_file:
            try:
                with open(self._history_file, 'w', encoding='utf-8') as f:
                    json.dump(self._history, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[ERROR] Failed to save history: {e}", file=sys.stderr)

    def _update_history(self, user_query: str, assistant_response: str):
        """Update and optionally persist history"""
        # ... update logic ...

        if self._persist_history:
            self._save_history()  # ✅ 持久化
```

---

## Part 2: MCP Tool Error Handling 🔍

### Current Implementation

#### Timeout Handling ✅

```python
# mcp/client.py
class SimpleMCPClient:
    def __init__(self, ..., timeout: float = 30.0):
        self._timeout = timeout  # ✅ 默认30秒

    async def _read_response(self):
        try:
            line = await asyncio.wait_for(
                self._process.stdout.readline(),
                timeout=self._timeout,  # ✅ 超时保护
            )
        except asyncio.TimeoutError:
            raise RuntimeError(f"MCP request timeout ({self._timeout}s)")
```

**Status**: ✅ 超时处理已实现

#### Error Catching ✅

```python
# mcp/manager.py
class MCPToolWrapper:
    async def execute(self, **kwargs) -> str:
        try:
            return await self._mcp_client.call_tool(...)
        except Exception as e:
            return f"[MCP_ERROR] {type(e).__name__}: {str(e)}"  # ✅ 捕获所有异常
```

**Status**: ✅ 错误捕获已实现

---

### Problem Analysis

#### Issue #1: No Auto-Reconnect ❌

**Current Behavior**:
```python
# MCP server times out → Connection corrupted
Next tool call → ❌ RuntimeError: "MCP server not connected"
No recovery → ❌ Tool permanently broken
```

**Why**: No automatic reconnection logic.

#### Issue #2: No Server Health Check ❌

**Current Behavior**:
```python
# MCP server crashes (process killed)
Next tool call → ❌ Hangs forever or timeout
No detection → ❌ Doesn't know server is dead
```

**Why**: No health check mechanism.

#### Issue #3: No Restart Mechanism ❌

**Current Behavior**:
```python
# MCP server crashes during execution
Tool execution → ❌ Fails with [MCP_ERROR]
User retry → ❌ Same error (server still dead)
Manual intervention required → ❌ Not "unbreakable"
```

**Why**: No automatic restart logic.

---

### Fix Strategy

#### Solution #1: Auto-Reconnect with Retry

```python
class MCPToolWrapper:
    def __init__(self, ..., max_retries: int = 3, retry_delay: float = 1.0):
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    async def execute(self, user_context=None, **kwargs) -> str:
        """Execute with auto-reconnect on failure"""
        for attempt in range(self._max_retries):
            try:
                return await self._mcp_client.call_tool(
                    self._tool_name,
                    kwargs,
                    user_key=user_context.user_key if user_context else None
                )

            except RuntimeError as e:
                if "not connected" in str(e).lower() and attempt < self._max_retries - 1:
                    # Try to reconnect
                    print(f"[WARNING] MCP connection lost, reconnecting... (attempt {attempt + 1}/{self._max_retries})", file=sys.stderr)

                    try:
                        await asyncio.sleep(self._retry_delay)
                        await self._mcp_client.connect()  # Reconnect
                        print(f"[OK] Reconnected to MCP server", file=sys.stderr)
                        continue  # Retry the call
                    except Exception as reconnect_error:
                        print(f"[ERROR] Reconnect failed: {reconnect_error}", file=sys.stderr)

                # All retries failed
                return f"[MCP_ERROR] {type(e).__name__}: {str(e)} (after {self._max_retries} retries)"

            except Exception as e:
                # Other errors, don't retry
                return f"[MCP_ERROR] {type(e).__name__}: {str(e)}"
```

#### Solution #2: Health Check Mechanism

```python
class SimpleMCPClient:
    async def health_check(self) -> bool:
        """Check if server is still alive"""
        try:
            # Quick timeout for health check
            line = await asyncio.wait_for(
                self._process.stdout.readline(),
                timeout=1.0,  # 1 second timeout
            )
            return bool(line)  # Got data = alive
        except:
            return False  # Timeout or error = dead

    async def ensure_connected(self) -> bool:
        """Ensure connection is alive, reconnect if needed"""
        if not self._process or self._process.returncode is not None:
            # Process is dead
            print(f"[WARNING] MCP server process died, restarting...", file=sys.stderr)
            await self.connect()
            return True

        # Check if connection is responsive
        if not await self.health_check():
            print(f"[WARNING] MCP connection unresponsive, reconnecting...", file=sys.stderr)
            await self.close()
            await self.connect()
            return True

        return True
```

#### Solution #3: Server Restart on Crash

```python
class MCPToolManager:
    async def get_tool_wrapper(self, tool_name: str) -> MCPToolWrapper:
        """Get tool wrapper with auto-restart on crash"""
        wrapper = self._tool_wrappers.get(tool_name)

        if wrapper:
            # Check if server is still alive
            try:
                client = wrapper._mcp_client
                if client._process and client._process.returncode is not None:
                    # Process has exited (crashed!)
                    print(f"[ERROR] MCP server for '{tool_name}' has crashed (exit code: {client._process.returncode})", file=sys.stderr)

                    # Restart server
                    print(f"[INFO] Restarting MCP server for '{tool_name}'...", file=sys.stderr)
                    await self._restart_server(tool_name)
                    wrapper = self._tool_wrappers[tool_name]

            except Exception as e:
                print(f"[ERROR] Health check failed for '{tool_name}': {e}", file=sys.stderr)

        return wrapper

    async def _restart_server(self, tool_name: str):
        """Restart crashed MCP server"""
        # Find server config for this tool
        # (Need to track server_config by tool_name)

        # Close old connection
        if tool_name in self._servers:
            try:
                await self._servers[tool_name].close()
            except:
                pass

        # Restart server
        # ... (re-use add_server logic)
```

---

## Part 3: Testing Strategy 🧪

### Multi-turn Dialog Tests

```python
@pytest.mark.asyncio
async def test_multi_turn_memory_retention():
    """Test that conversation history is maintained across turns"""
    session = Session(session_id="test-123", websocket=mock_ws)

    # Turn 1
    await session._handle_message({"type": "query", "content": "My name is Alice"})
    assert len(session._history) == 2  # user + assistant

    # Turn 2
    await session._handle_message({"type": "query", "content": "What is my name?"})
    assert len(session._history) == 4  # 2 messages per turn

    # Verify history is passed
    # Agent should remember "Alice"
```

### MCP Error Recovery Tests

```python
@pytest.mark.asyncio
async def test_mcp_timeout_reconnect():
    """Test that MCP tools reconnect after timeout"""
    # Simulate timeout
    # Verify reconnect logic
    # Verify tool works after reconnect
    pass

@pytest.mark.asyncio
async def test_mcp_server_crash_recovery():
    """Test that crashed MCP servers are restarted"""
    # Kill server process
    # Try to use tool
    # Verify automatic restart
    # Verify tool works after restart
    pass
```

---

## Priority Matrix

| Issue | Severity | Complexity | Priority |
|-------|----------|------------|----------|
| **No History in Session** | 🔴 Critical | 🟢 Low | **P0** |
| **No Auto-Reconnect** | 🔴 Critical | 🟡 Medium | **P0** |
| **No Health Check** | 🟡 Medium | 🟡 Medium | **P1** |
| **No Server Restart** | 🔴 Critical | 🔴 High | **P1** |
| **No Persistence** | 🟢 Low | 🟡 Medium | **P2** |

---

## Implementation Plan

### Phase 1: Critical Fixes (P0) - 2-3 hours

1. **Add History to Session** (1 hour)
   - Add `_history` attribute
   - Implement `_update_history()`
   - Pass history to `run_event_stream()`

2. **Add Auto-Reconnect** (1-2 hours)
   - Implement retry logic in `MCPToolWrapper.execute()`
   - Add reconnect attempt on connection loss
   - Log reconnect events

### Phase 2: Hardening (P1) - 2-3 hours

3. **Add Health Check** (1 hour)
   - Implement `health_check()` in SimpleMCPClient
   - Call health check before tool execution
   - Auto-reconnect on failed health check

4. **Add Server Restart** (1-2 hours)
   - Detect crashed servers (exit code check)
   - Implement `_restart_server()` logic
   - Track server config by tool name

### Phase 3: Persistence (P2) - 1-2 hours

5. **Add History Persistence** (optional)
   - Implement `_save_history()`
   - Implement `_load_history()`
   - Add configuration flag

---

## Success Criteria

### Multi-turn Dialog ✅
- [ ] Session maintains history across turns
- [ ] Agent remembers context from previous messages
- [ ] History is pruned when too long
- [ ] Optional: History persists to disk

### MCP Error Recovery ✅
- [ ] Timeout triggers automatic reconnect
- [ ] Connection loss triggers retry (3 attempts)
- [ ] Crashed servers are detected and restarted
- [ ] Tools work after recovery without user intervention
- [ ] Clear logging of all recovery actions

### Unbreakable System 🛡️
- [ ] No single point of failure
- [ ] Automatic recovery from all transient errors
- [ ] Clear error messages for unrecoverable errors
- [ ] Comprehensive logging for debugging

---

**Next**: Start implementation with Phase 1 (Critical Fixes)

**Auditor**: Claude Code
**Date**: 2025-02-18
**Status**: 🔍 Audit Complete | 🚧 Ready for Implementation
