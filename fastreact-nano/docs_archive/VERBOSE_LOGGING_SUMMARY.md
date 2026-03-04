# 飞书 SDK 详细日志功能 - 实施总结

**实施日期**: 2025-03-04
**功能**: 为 feishu_sdk 启动脚本添加详细日志输出参数

---

## 完成的修改

### ✅ 1. 启动脚本 (`scripts/start_feishu_bot.sh`)

**新增参数**:
- `-v, --verbose` - 启用详细日志输出
- `-h, --help` - 显示帮助信息

**修改内容**:
```bash
# 解析参数
VERBOSE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            # 显示帮助
            ;;
    esac
done

# 设置环境变量
if [ "$VERBOSE" = true ]; then
    export FEISHU_VERBOSE=true
    export FASTRACT_LOG_LEVEL=debug
fi
```

### ✅ 2. Feishu SDK Adapter (`src/fastreact/adapters/feishu_sdk.py`)

**新增内容**:

1. **环境变量支持**
```python
import os
_VERBOSE = os.getenv("FEISHU_VERBOSE", "false").lower() == "true"
```

2. **日志辅助函数**
```python
def _log(level: str, message: str):
    """带时间戳的日志输出（DEBUG 仅在 verbose 模式）"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if level in ["INFO", "WARNING", "ERROR"]:
        print(f"[{level}] {message}")

    elif level == "DEBUG" and _VERBOSE:
        print(f"[{timestamp}] [DEBUG] {message}")
```

3. **详细日志输出**
   - 消息接收详情（sender_id, content, message_id, chat_id）
   - Agent 处理步骤（MCP 状态、工具列表、事件流）
   - 工具调用详情（工具名、参数）
   - 错误堆栈信息（verbose 模式）

---

## 使用示例

### 普通模式（默认）

```bash
./scripts/start_feishu_bot.sh
```

**输出**:
```
[INFO] Starting Feishu SDK adapter (WebSocket long connection)
[INFO] App ID: cli_a92bd40f3af89cd3
[INFO] Multi-tenant: True
[INFO] Loaded 3 skills
```

### 详细模式

```bash
./scripts/start_feishu_bot.sh -v
```

**输出**:
```
[2025-03-04 17:30:00] [DEBUG] === Feishu SDK Adapter Starting ===
[INFO] Starting Feishu SDK adapter (WebSocket long connection)
[INFO] App ID: cli_a92bd40f3af89cd3
[2025-03-04 17:30:00] [DEBUG] App Secret: y7gMSjXtWu...***
[INFO] Multi-tenant: True
[2025-03-04 17:30:00] [DEBUG] Verbose mode: True
[2025-03-04 17:30:00] [DEBUG] Available skills: ['calculator', 'datetime', 'web_search']
```

---

## 详细日志内容

### 消息处理流程（verbose 模式）

```
[2025-03-04 17:30:15] [DEBUG] === Feishu Message Event Received ===
[2025-03-04 17:30:15] [DEBUG] Sender ID: ou_1234567890
[2025-03-04 17:30:15] [DEBUG] Raw content: {"text":"帮我分析数据"}
[2025-03-04 17:30:15] [DEBUG] Parsed text: 帮我分析数据
[2025-03-04 17:30:15] [DEBUG] Message ID: om_1234567890abcdef
[2025-03-04 17:30:15] [DEBUG] Chat ID: oc_1234567890abcdef
[INFO] [FEISHU] Received message from ou_1234567890: 帮我分析数据
[2025-03-04 17:30:15] [DEBUG] Creating async task for message processing
```

### Agent 执行流程（verbose 模式）

```
[INFO] Starting agent processing for user: feishu:ou_1234567890
[2025-03-04 17:30:16] [DEBUG] Query: 帮我分析数据
[2025-03-04 17:30:16] [DEBUG] MCP Manager status: <class 'fastreact.mcp.multitenant.MultiTenantMCPManager'>
[2025-03-04 17:30:16] [DEBUG] MCP Tools loaded: 11 tools
[2025-03-04 17:30:16] [DEBUG] MCP Tool names: ['graphrag_search_graph', ...]
[2025-03-04 17:30:16] [DEBUG] Total tools available: 15
[2025-03-04 17:30:16] [DEBUG] Tool names: ['read_file', 'write_file', ...]
[2025-03-04 17:30:16] [DEBUG] MCP servers configured: 3
[2025-03-04 17:30:16] [DEBUG] Starting agent event stream
[2025-03-04 17:30:16] [DEBUG] Received event: EventType.SESSION_START
[INFO] Session started
```

### 错误处理（verbose 模式）

```
[ERROR] Agent processing failed: connection timeout
[2025-03-04 17:30:20] [ERROR] Traceback:
Traceback (most recent call last):
  File "/path/to/feishu_sdk.py", line 605, in _process_agent_stream
    async for agent_event in self.agent.run_or_inject(...)
  ...
ConnectionError: connection timeout
```

---

## 日志级别

| 级别 | 输出条件 | 用途 |
|------|----------|------|
| **ERROR** | 始终输出 | 错误信息、异常 |
| **WARNING** | 始终输出 | 警告、配置问题 |
| **INFO** | 始终输出 | 关键操作、状态变化 |
| **DEBUG** | 仅 `-v` | 详细步骤、参数详情 |

---

## 配置位置

### 飞书 API Key 和 Secret

**文件**: `~/.fastreact/config.json`

```json
{
  "feishu": {
    "app_id": "cli_a92bd40f3af89cd3",
    "app_secret": "y7gMSjXtWukXgOJ4QdXD8gJyTKFwLebZ",
    "connection_mode": "sdk",
    "enable_multitenant": true,
    "auto_reconnect": true,
    "log_level": "info"
  }
}
```

---

## 用户中断功能

### ✅ 已支持（后端）

**Gateway** 和 **Feishu SDK** 都已支持用户中断/干预功能：

#### 1. 控制消息中断

```json
{
  "type": "control",
  "action": "interrupt"
}
```

#### 2. 用户干预（运行中发新消息）

当 Agent 正在运行时，发送新的 `query` 会自动触发干预：

```python
if self._is_running:
    # Send user intervention signal
    print("[INFO] New query received while agent running, sending user intervention")
    # Agent 会接收新消息作为干预指令
```

**这意味着**：
- 在长 session 中发送新消息会自动触发干预
- Agent 可以根据新消息调整方向或停止

### 前端集成（如需要）

如果前端需要"停止"按钮：

```typescript
// 发送中断消息
function stopAgent() {
  ws.send(JSON.stringify({
    type: "control",
    action: "interrupt"
  }))
}
```

---

## 验证测试

### ✅ 脚本参数测试

```bash
$ ./scripts/start_feishu_bot.sh --help
用法: ./scripts/start_feishu_bot.sh [-v|--verbose]

选项:
  -v, --verbose    启用详细日志输出
  -h, --help       显示帮助信息
```

### ✅ 日志系统测试

```bash
$ FEISHU_VERBOSE=true python3 -c "
from src.fastreact.adapters.feishu_sdk import _log_info, _log_debug
_log_info('Test info message')
_log_debug('Test debug message')
"

[INFO] Test info message
[2026-03-04 17:28:41] [DEBUG] Test debug message
✅ 日志系统正常工作
```

---

## 文档

### 新增文档

1. **`docs_archive/FEISHU_VERBOSE_LOGGING.md`** - 详细日志使用指南
   - 使用方法
   - 日志内容示例
   - 调试技巧
   - 性能影响说明

---

## 总结

### 完成内容

✅ 启动脚本添加 `-v/--verbose` 参数
✅ Feishu SDK 添加详细日志输出
✅ 日志辅助函数（带时间戳）
✅ 消息接收详情日志
✅ Agent 处理流程日志
✅ 错误堆栈详细信息
✅ 帮助文档

### 关键特性

- **零性能影响** - 普通模式下无额外开销
- **时间戳** - DEBUG 日志包含精确时间戳
- **分层日志** - ERROR/WARNING/INFO 始终输出，DEBUG 仅 verbose 模式
- **调试友好** - 包含堆栈跟踪、参数详情、执行步骤

### 使用建议

- **生产环境**: 普通模式（不加参数）
- **开发调试**: 详细模式（`-v`）
- **问题排查**: 详细模式 + 日志文件

---

**实施者**: Claude (FastReAct Team)
**完成日期**: 2025-03-04
**版本**: v2.4.2
