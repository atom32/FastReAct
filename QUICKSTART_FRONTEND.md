# FastReAct 前端快速启动指南

## 🚀 三步启动前端

### 步骤 1: 准备 v0.dev Prompt

1. 打开 `V0_DEV_PROMPT.md`（我刚创建的）
2. 复制整个 prompt 内容
3. 访问 https://v0.dev
4. 粘贴 prompt 并生成项目

### 步骤 2: 启动 FastReAct Gateway

```bash
# 使用你的配置
cd D:/FastReAct

# 方式 1: 直接使用环境变量
set OPENAI_API_KEY=sk-vvtexslykgurxcvvzcasnarhyohlxhsapzcdmgolmncoqqwh
set OPENAI_BASE_URL=https://api.siliconflow.cn/v1
set OPENAI_MODEL=deepseek-ai/DeepSeek-V3.2

# 启动服务
python scripts/run_gateway.py
```

你会看到：
```
============================================================
🚀 FastReAct WebSocket Gateway
============================================================
📡 API: https://api.siliconflow.cn/v1
🤖 模型: deepseek-ai/DeepSeek-V3.2
🔧 工具: 5 个内置工具
💾 存储: SQLite (./data/sessions.db)
🔄 自动保存: True
============================================================

✅ 存储初始化成功

✅ 服务器启动中...
📍 WebSocket: ws://localhost:8080/ws/{session_id}
🌐 前端页面: 打开 public/index.html
📊 健康检查: http://localhost:8080/health
📋 会话列表: http://localhost:8080/sessions

按 Ctrl+C 停止服务器
============================================================
```

### 步骤 3: 运行 v0.dev 生成的项目

```bash
# 在 v0.dev 生成项目后，下载并解压
cd fastreact-frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 `http://localhost:3000`，开始聊天！

---

## 🎨 v0.dev Prompt 使用说明

我已经在 `V0_DEV_PROMPT.md` 中准备好了完整的 prompt，包含：

### ✅ 完整的功能规格

1. **界面布局**
   - 左侧聊天面板 (60%)
   - 右侧事件面板 (40%)
   - 响应式设计

2. **实时事件流**
   - 💭 思考事件 (蓝色)
   - 🔧 工具调用 (紫色)
   - 📊 观察结果 (绿色)
   - ✅ 最终答案 (橙色)

3. **WebSocket 集成**
   - 自动连接
   - 自动重连
   - 事件流处理

4. **UI/UX**
   - Dark mode
   - 动画效果
   - 键盘快捷键
   - 移动端适配

### 🎯 核心特性

```typescript
// WebSocket 连接
ws://localhost:8080/ws/{session_id}

// 发送消息
{
  "type": "message",
  "content": "你的问题"
}

// 接收事件流
{
  "type": "thought",
  "content": "正在思考..."
}
→ {
  "type": "action",
  "content": "调用计算器"
}
→ {
  "type": "observation",
  "content": "结果: 450"
}
→ {
  "type": "final",
  "content": "答案是 450"
}
```

---

## 📝 对接说明

### 现有的 Gateway 已支持实时事件流！

Gateway 已经实现了 `step_callback`，可以实时发送：
- `thought` - 思考过程
- `action` - 工具调用
- `observation` - 观察结果
- `final` - 最终答案

### 协议格式

**客户端发送**:
```json
{
  "query": "帮我计算 25 * 18"
}
```

**服务端推送**:
```json
{"type": "status", "status": "thinking"}
{"type": "thought", "content": "我需要使用计算器", "iteration": 1}
{"type": "action", "content": "调用 Calculator", "tool_calls": [...]}
{"type": "observation", "content": "450", "iteration": 1}
{"type": "final", "content": "25 * 18 = 450"}
```

---

## 🔄 升级到新回调系统（可选）

如果你想使用刚实现的更强大的回调系统（支持 9 个阶段），需要：

### 修改 Gateway 使用 StreamingCallbacks

见 `docs/WEBSOCKET_INTEGRATION.md` 中的完整示例。

核心代码：
```python
from fastreact.core.callbacks import StreamingCallbacks, StepEvent, Phase

class WebSocketCallbacks(StreamingCallbacks):
    def __init__(self, websocket):
        super().__init__()
        self.websocket = websocket

    async def emit(self, event: StepEvent):
        await self.websocket.send_json({
            "type": event.phase.value,
            "content": event.content,
            "metadata": event.metadata
        })

# 在 Gateway 中使用
callbacks = WebSocketCallbacks(websocket)
result = await agent.run_async_streaming(
    query=query,
    callbacks=callbacks
)
```

这样可以得到更详细的事件流：
- `start` - 开始
- `think` - 思考
- `action` - 行动
- `tool_start` - 工具开始
- `tool_end` - 工具结束
- `observation` - 观察
- `answer` - 答案
- `end` - 结束

---

## 🧪 测试

### 测试现有 Gateway

```bash
# 1. 启动 Gateway
python scripts/run_gateway.py

# 2. 打开 public/index.html
# 这是现有的简单前端
```

### 测试 v0.dev 前端

```bash
# 1. 启动 Gateway
python scripts/run_gateway.py

# 2. 启动 v0.dev 前端
cd fastreact-frontend
npm run dev

# 3. 访问 http://localhost:3000
```

---

## 📚 文档索引

1. **V0_DEV_PROMPT.md** - v0.dev 生成前端的完整 prompt
2. **docs/WEBSOCKET_INTEGRATION.md** - WebSocket 集成完整指南
3. **src/fastreact/gateway/server.py** - Gateway 服务端实现
4. **public/index.html** - 现有的简单前端示例

---

## ✅ 检查清单

在生成前端前，确保：

- [ ] Gateway 能正常启动 (`python scripts/run_gateway.py`)
- [ ] 访问 http://localhost:8080/health 返回正常
- [ ] 已阅读 `V0_DEV_PROMPT.md`
- [ ] 已阅读 `docs/WEBSOCKET_INTEGRATION.md`
- [ ] 了解 WebSocket 事件格式

---

## 🆘 常见问题

### Q: Gateway 启动失败？
**A**: 检查：
1. API Key 是否正确
2. config.json 是否存在
3. Python 依赖是否安装 (`pip install -r requirements.txt`)

### Q: 前端无法连接 WebSocket？
**A**: 检查：
1. Gateway 是否在运行 (端口 8080)
2. 浏览器控制台是否有错误
3. WebSocket URL 是否正确: `ws://localhost:8080/ws/session-123`

### Q: 事件流不显示？
**A**: 检查：
1. 浏览器控制台 Network → WS 标签
2. 查看接收到的消息格式
3. 确认前端代码正确解析事件

---

## 🎉 开始吧！

1. 复制 `V0_DEV_PROMPT.md` 的内容
2. 访问 https://v0.dev
3. 生成你的 FastReAct 前端
4. 享受实时 AI Agent 对话体验！

需要帮助？查看 `docs/WEBSOCKET_INTEGRATION.md` 获取详细文档。
