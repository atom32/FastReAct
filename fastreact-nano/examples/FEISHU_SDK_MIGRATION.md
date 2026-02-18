# Feishu SDK Adapter - Ultimate Form

This document describes the migration from Webhook-based Feishu integration to the official lark-oapi SDK with WebSocket long connection.

## Overview

The **Feishu SDK Adapter** is the "ultimate form" of Feishu integration:
- No webhook server needed
- No public network exposure
- Automatic reconnection
- Multi-tenant user isolation
- Real-time streaming updates

## Architecture Comparison

### Webhook Mode (Legacy)
```
Feishu Platform -> HTTP POST -> Webhook Server -> Agent
                     (requires public URL)
```

### SDK Mode (Recommended)
```
Feishu Platform <- WebSocket Long Connection -> Agent
                      (no public URL needed)
```

## Installation

```bash
# Install with Feishu adapter support
pip install "fastreact-nano[all]"

# Or install just the Feishu adapter
pip install "fastreact-nano[feishu]"
```

## Configuration

### Environment Variables

```bash
# FastReAct Agent Configuration
export FASTRACT_API_KEY="sk-xxx"
export FASTRACT_MODEL="gpt-4o-mini"

# Feishu App Credentials
export FEISHU_APP_ID="cli_xxxxxxxxx"
export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxx"

# Connection Mode (default: "sdk")
export FEISHU_CONNECTION_MODE="sdk"

# Multi-tenant Settings
export FEISHU_MULTITENANT="true"  # Enable user workspace isolation
export FEISHU_WORKSPACE="/path/to/workspace"  # Base workspace directory

# SDK Settings
export FEISHU_AUTO_RECONNECT="true"  # Auto-reconnect on connection loss
export FEISHU_LOG_LEVEL="info"  # Log level: debug, info, warn, error
```

### Config File

You can also create a `config.json` file:

```json
{
  "llm": {
    "model": "gpt-4o-mini",
    "api_key": "sk-xxx"
  },
  "feishu": {
    "connection_mode": "sdk",
    "app_id": "cli_xxxxxxxxx",
    "app_secret": "xxxxxxxxxxxxxxxxxxxx",
    "enable_multitenant": true,
    "auto_reconnect": true,
    "log_level": "info"
  }
}
```

## Usage

### Quickstart

```python
from fastreact import Agent, Config, FeishuConfig
from fastreact.adapters.feishu_sdk import FeishuSDKAdapter

# Load configuration
config = Config.from_env()
feishu_config = FeishuConfig.from_env()

# Create agent
agent = Agent(config=config)

# Create Feishu SDK adapter
adapter = FeishuSDKAdapter(agent, feishu_config)

# Start the bot (blocking)
adapter.start()
```

### Command Line

```bash
# Run the example bot
python examples/feishu_sdk_bot.py
```

## Multi-Tenant Support

The Feishu SDK adapter supports multi-tenant user isolation:

1. **User Identification**: `feishu:ou_xxx` format
2. **Workspace Isolation**: Each user has their own workspace
   ```
   workspace/
   ├── feishu_ou_user_a/
   │   ├── config.json
   │   ├── skills/
   │   └── memory.json
   └── feishu_ou_user_b/
       ├── config.json
       ├── skills/
       └── memory.json
   ```

3. **Configuration Isolation**: Each user has their own config
4. **Skill Isolation**: Each user can have custom skills
5. **Memory Isolation**: Each user has their own conversation history

## Event Handling

The SDK adapter uses the official lark-oapi event handler system:

1. **WebSocket Long Connection**: Connects to Feishu via WebSocket
2. **Event Dispatcher**: Handles incoming events
3. **Message Handler**: Processes message events
4. **Async Processing**: Processes events asynchronously

## Message Flow

```
User sends message in Feishu
    ↓
Feishu sends event via WebSocket
    ↓
SDK adapter receives event
    ↓
Extract user_key (feishu:ou_xxx)
    ↓
Get user workspace (workspace/feishu_ou_xxx/)
    ↓
Process with Agent.run_event_stream()
    ↓
Stream events back to Feishu
    ↓
Update user in real-time
```

## Real-time Updates

The SDK adapter sends real-time updates to Feishu:

1. **THINK** - Agent is thinking
2. **TOOL_CALL** - Calling a tool
3. **TOOL_RESULT** - Tool result
4. **SESSION_END** - Final answer
5. **ERROR** - Error occurred

## Error Handling

The SDK adapter handles errors gracefully:

1. **Connection Errors**: Auto-reconnect on connection loss
2. **Event Processing Errors**: Log errors and continue
3. **Agent Errors**: Send error message to user
4. **API Errors**: Log and retry

## Security

The SDK adapter implements security measures:

1. **Signature Verification**: HMAC-SHA256 for webhooks
2. **Timestamp Validation**: Prevents replay attacks
3. **Path Traversal Prevention**: Whitelist-based validation
4. **Workspace Containment**: Users cannot escape their workspace

## Troubleshooting

### Connection Issues

```bash
# Check app credentials
export FEISHU_APP_ID="cli_xxxxxxxxx"
export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxx"

# Enable debug logging
export FEISHU_LOG_LEVEL="debug"

# Check network connectivity
python -c "import lark_oapi; print('[OK] SDK installed')"
```

### Multi-tenant Issues

```bash
# Check workspace directory
ls -la workspace/

# Check user workspace
ls -la workspace/feishu_ou_xxx/

# Check user config
cat workspace/feishu_ou_xxx/config.json
```

### Event Handling Issues

```bash
# Check event handler is registered
python -c "from fastreact.adapters.feishu_sdk import FeishuSDKAdapter; print('[OK] Adapter imported')"

# Check event handler
python -c "from lark_oapi.event.dispatcher_handler import EventDispatcherHandlerBuilder; print('[OK] Event handler available')"
```

## Migration from Webhook

To migrate from webhook to SDK mode:

1. **Change connection mode**:
   ```bash
   export FEISHU_CONNECTION_MODE="sdk"
   ```

2. **Remove webhook configuration** (no longer needed):
   ```bash
   # These are optional in SDK mode
   # export FEISHU_ENCRYPT_KEY="xxx"
   # export FEISHU_VERIFICATION_TOKEN="xxx"
   # export FEISHU_HOST="0.0.0.0"
   # export FEISHU_PORT="8001"
   # export FEISHU_WEBHOOK_PATH="/webhook/feishu"
   ```

3. **Update code**:
   ```python
   # Old (Webhook)
   from fastreact.adapters.feishu import FeishuChannel
   channel = FeishuChannel(agent, config)
   channel.run_sync()

   # New (SDK)
   from fastreact.adapters.feishu_sdk import FeishuSDKAdapter
   adapter = FeishuSDKAdapter(agent, config)
   adapter.start()
   ```

## Performance

The SDK adapter has better performance than webhook mode:

1. **Lower Latency**: WebSocket is faster than HTTP POST
2. **No Server Overhead**: No webhook server needed
3. **Automatic Reconnection**: Recovers from network issues
4. **Efficient Event Handling**: Uses async/await

## Limitations

1. **Single Connection**: Only one WebSocket connection per app
2. **No Webhook Fallback**: Cannot use both modes simultaneously
3. **Requires SDK**: Must install lark-oapi package

## Future Enhancements

1. **Card Updates**: Implement Feishu card API for rich UI
2. **Bot Permissions**: Add permission management
3. **Rate Limiting**: Add rate limiting for API calls
4. **Metrics**: Add metrics and monitoring
5. **Testing**: Add integration tests

## References

- [lark-oapi SDK Documentation](https://github.com/larksuite/oapi-sdk-python)
- [Feishu Open Platform](https://open.feishu.cn/)
- [FastReAct Nano Documentation](../README_NANO.md)
