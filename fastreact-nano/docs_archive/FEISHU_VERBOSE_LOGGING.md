# 飞书 SDK 详细日志说明

**功能**: 通过 `-v` 或 `--verbose` 参数启用详细日志输出

---

## 使用方法

### 基础启动

```bash
./scripts/start_feishu_bot.sh
```

**输出**: INFO 级别日志（关键信息）

```
[INFO] Starting Feishu SDK adapter (WebSocket long connection)
[INFO] App ID: cli_a92bd40f3af89cd3
[INFO] Multi-tenant: True
[INFO] Auto-reconnect: True
[INFO] MCP Manager initialized
[INFO] Loaded 3 skills
[INFO] Connecting to Feishu WebSocket...
```

### 详细日志模式

```bash
./scripts/start_feishu_bot.sh -v
# 或
./scripts/start_feishu_bot.sh --verbose
```

**输出**: DEBUG 级别日志（包含时间戳、详细信息）

```
[2025-03-04 17:30:00] [DEBUG] === Feishu SDK Adapter Starting ===
[2025-03-04 17:30:00] [DEBUG] Lark SDK log level: LogLevel.INFO
[2025-03-04 17:30:00] [DEBUG] Initializing HTTP client...
[2025-03-04 17:30:00] [DEBUG] Preloading MCP servers...
[INFO] Preloading MCP servers...
[INFO] MCP preload completed
[2025-03-04 17:30:00] [DEBUG] Total tools available: 15
[2025-03-04 17:30:00] [DEBUG] Tool names: ['read_file', 'write_file', 'edit_file', 'exec', 'graphrag_search_graph', ...]
[2025-03-04 17:30:00] [DEBUG] Creating WebSocket client...
[INFO] Starting Feishu SDK adapter (WebSocket long connection)
[INFO] App ID: cli_a92bd40f3af89cd3
[2025-03-04 17:30:00] [DEBUG] App Secret: y7gMSjXtWu...***
[INFO] Multi-tenant: True
[INFO] Auto-reconnect: True
[2025-03-04 17:30:00] [DEBUG] Verbose mode: True
[INFO] MCP Manager initialized
[INFO] Loaded 3 skills
[2025-03-04 17:30:00] [DEBUG] Available skills: ['calculator', 'datetime', 'web_search']
[INFO] Connecting to Feishu WebSocket...
[2025-03-04 17:30:00] [DEBUG] === WebSocket Connection Starting ===
```

---

## 详细日志内容

### 1. 消息接收（详细）

**普通模式**:
```
[INFO] [FEISHU] Received message from ou_1234567890: 帮我分析数据
```

**详细模式**:
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

### 2. Agent 处理（详细）

**普通模式**:
```
[INFO] Starting agent processing for user: feishu:ou_1234567890
[INFO] Query: 帮我分析数据
[INFO] Session started
```

**详细模式**:
```
[INFO] Starting agent processing for user: feishu:ou_1234567890
[2025-03-04 17:30:16] [DEBUG] Query: 帮我分析数据
[2025-03-04 17:30:16] [DEBUG] MCP Manager status: <class 'fastreact.mcp.multitenant.MultiTenantMCPManager'>
[2025-03-04 17:30:16] [DEBUG] MCP Tools loaded: 11 tools
[2025-03-04 17:30:16] [DEBUG] MCP Tool names: ['graphrag_search_graph', 'graphrag_search_entities', 'filesystem_read_file', ...]
[2025-03-04 17:30:16] [DEBUG] Total tools available: 15
[2025-03-04 17:30:16] [DEBUG] Tool names: ['read_file', 'write_file', 'edit_file', 'exec', 'graphrag_search_graph', ...]
[2025-03-04 17:30:16] [DEBUG] MCP servers configured: 3
[2025-03-04 17:30:16] [DEBUG]   [1] graphrag:
[2025-03-04 17:30:16] [DEBUG]       command: uvx
[2025-03-04 17:30:16] [DEBUG]       args: ['--from', 'graphrag-mcp', 'graphrag_mcp.server']
[2025-03-04 17:30:16] [DEBUG] Starting agent event stream
[2025-03-04 17:30:16] [DEBUG] Received event: EventType.SESSION_START
[INFO] Session started
```

### 3. 工具调用（详细）

**普通模式**:
```
[INFO] [TOOL] Calling exec
```

**详细模式**:
```
[2025-03-04 17:30:17] [DEBUG] Received event: EventType.TOOL_CALL
[INFO] [TOOL] Calling exec
[2025-03-04 17:30:17] [DEBUG] [TOOL] Args: {'command': 'python analyze_data.py', 'timeout': 30}
```

### 4. 错误处理（详细）

**普通模式**:
```
[ERROR] Agent processing failed: connection timeout
```

**详细模式**:
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

## 日志级别说明

| 级别 | 输出条件 | 示例 |
|------|----------|------|
| **ERROR** | 始终输出 | 错误信息、异常 |
| **WARNING** | 始终输出 | 警告、配置问题 |
| **INFO** | 始终输出 | 关键操作、状态变化 |
| **DEBUG** | 仅 verbose 模式 | 详细步骤、参数详情 |

---

## 环境变量

详细模式也可以通过环境变量启用：

```bash
export FEISHU_VERBOSE=true
export FASTRACT_LOG_LEVEL=debug
./scripts/start_feishu_bot.sh
```

---

## 调试技巧

### 1. 检查 MCP 服务器状态

```bash
./scripts/start_feishu_bot.sh -v
```

查看输出：
```
[DEBUG] MCP Tools loaded: 11 tools
[DEBUG] MCP Tool names: ['graphrag_search_graph', ...]
```

### 2. 检查用户消息解析

```bash
./scripts/start_feishu_bot.sh -v
```

查看输出：
```
[DEBUG] Raw content: {"text":"用户消息"}
[DEBUG] Parsed text: 用户消息
```

### 3. 检查 Agent 执行步骤

```bash
./scripts/start_feishu_bot.sh -v
```

查看输出：
```
[DEBUG] Starting agent event stream
[DEBUG] Received event: EventType.SESSION_START
[DEBUG] Received event: EventType.THINK
[DEBUG] Received event: EventType.TOOL_CALL
```

### 4. 检查错误堆栈

```bash
./scripts/start_feishu_bot.sh -v
```

查看输出：
```
[ERROR] Agent processing failed: ...
[ERROR] Traceback:
Traceback (most recent call last):
  ...
```

---

## 日志文件位置

除了控制台输出，日志也会写入文件：

```bash
# 查看完整日志
tail -f ~/.fastreact/logs/feishu.log

# 搜索错误
grep ERROR ~/.fastreact/logs/feishu.log

# 搜索特定用户
grep "ou_1234567890" ~/.fastreact/logs/feishu.log
```

---

## 性能影响

详细日志模式会：

✅ **增加** 控制台输出量
✅ **增加** 时间戳格式化开销
✅ **增加** 字符串拼接开销

❌ **不会** 影响 WebSocket 性能
❌ **不会** 影响 Agent 执行速度
❌ **不会** 影响消息处理延迟

**建议**:
- **生产环境**: 使用普通模式（不加 `-v`）
- **开发调试**: 使用详细模式（加 `-v`）
- **问题排查**: 使用详细模式并保存日志

---

**最后更新**: 2025-03-04
**版本**: v2.4.2
