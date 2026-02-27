# Gateway + ClawFeed 使用指南

**Date**: 2025-02-27
**Status**: ✅ 完全支持

---

## 架构说明

```
┌─────────────────────────────────────────────────────────────┐
│                        用户界面                              │
│              fastreact-nano-web (Next.js 14)                │
└───────────────────────────┬─────────────────────────────────┘
                            │ WebSocket
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Gateway Adapter (后端)                     │
│         FastAPI WebSocket Server (port 9000)                │
│                                                              │
│   ┌──────────────────────────────────────────────────────┐  │
│   │  Agent (单租户模式)                                    │  │
│   │  - multitenant: False                                 │  │
│   │  - 已加载 57 个技能                                     │  │
│   │  - 自动技能选择                                        │  │
│   └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴──────────────────┐
        │                                         │
   ┌────▼─────┐                           ┌─────▼──────┐
   │ news_    │                           │  其他技能   │
   │ aggregator│                          │  (56个)     │
   └──────────┘                           └────────────┘
        │
        ↓
   HackerNews API
   RSS Feeds
```

---

## 验证支持

### 快速验证

```bash
cd /Users/ning/FastReAct/fastreact-nano

python3 -c "
from fastreact import Agent

agent = Agent(multitenant=False)
skills = agent._skills.list_available()

print(f'已加载 {len(skills)} 个技能')
print(f'news_aggregator: {\"✅\" if \"news_aggregator\" in skills else \"❌\"}')
"
```

**预期输出**:
```
已加载 57 个技能
news_aggregator: ✅
```

---

## 启动 Gateway 服务器

### 方式 1: 直接运行

```bash
cd /Users/ning/FastReAct/fastreact-nano

# 启动 Gateway
python3 -m fastreact.adapters.gateway

# 或使用 uvicorn
uvicorn fastreact.adapters.gateway:create_gateway_app --host 0.0.0.0 --port 9000
```

**输出**:
```
[INFO] Starting Gateway adapter
[INFO] Loaded 57 skills
[INFO] WebSocket server on ws://0.0.0.0:9000
```

### 方式 2: 使用环境变量

```bash
# 设置配置
export FASTRACT_MODEL=deepseek-ai/DeepSeek-V3.2
export FASTRACT_API_BASE=https://api.siliconflow.cn/v1
export FASTRACT_API_KEY=sk-your-key

# 启动 Gateway
python3 -m fastreact.adapters.gateway
```

---

## 前端集成

### WebSocket 连接

```javascript
// fastreact-nano-web/app/page.tsx

const ws = new WebSocket('ws://localhost:9000/ws');

ws.onopen = () => {
  console.log('[OK] 已连接到 Gateway');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  // 处理不同类型的事件
  switch (data.type) {
    case 'SESSION_START':
      console.log('[会话开始]', data.session_id);
      break;

    case 'THINK':
      console.log('[思考]', data.content);
      break;

    case 'TOOL_CALL':
      console.log('[工具调用]', data.tool, data.arguments);
      break;

    case 'TOOL_RESULT':
      console.log('[工具结果]', data.content);
      break;

    case 'STEP_END':
      console.log('[完成]', data.content);
      break;

    case 'SESSION_END':
      console.log('[会话结束]', data.content);
      break;

    case 'ERROR':
      console.error('[错误]', data.content);
      break;
  }
};
```

### 发送查询请求

```javascript
// ClawFeed 查询示例
function getHackerNews() {
  const query = {
    type: 'query',
    query: '获取 HackerNews 最新的 3 条热门新闻并生成中文摘要',
    session_id: 'clawfeed-session-' + Date.now()
  };

  ws.send(JSON.stringify(query));
}

// 调用
getHackerNews();
```

---

## ClawFeed 使用场景

### 场景 1: 获取最新新闻

**前端查询**:
```javascript
ws.send(JSON.stringify({
  type: 'query',
  query: '帮我获取 HackerNews 最新的 5 条新闻'
}));
```

**Gateway 处理流程**:
1. 接收查询
2. Agent 自动选择 `news_aggregator` 技能
3. 调用 HackerNews API
4. 生成中文摘要
5. 返回结果到前端

### 场景 2: 定时新闻摘要

**前端定时查询**:
```javascript
// 每小时获取一次
setInterval(() => {
  ws.send(JSON.stringify({
    type: 'query',
    query: '获取 HackerNews 和科技新闻的最新摘要'
  }));
}, 60 * 60 * 1000);
```

### 场景 3: 特定主题新闻

**前端查询**:
```javascript
ws.send(JSON.stringify({
  type: 'query',
  query: '获取关于 AI 和机器学习的最新新闻'
}));
```

---

## 技能自动选择

### news_aggregator 何时被触发

**触发关键词** (自动选择机制):
- `news` - 新闻
- `hackernews` / `hacker news` - HackerNews
- `rss` - RSS 订阅
- `新闻` - 中文关键词
- `摘要` - 摘要
- `聚合` - 聚合
- `feed` - 订阅源

**示例查询**:
- ✅ "给我最新的科技新闻"
- ✅ "HackerNews 上有什么热门"
- ✅ "获取 AI 相关的新闻摘要"
- ✅ "fetch latest news"

---

## 前端 UI 示例

### ClawFeed 组件

```tsx
// fastreact-nano-web/app/components/ClawFeed.tsx

'use client';

import { useState, useEffect } from 'react';

export function ClawFeed() {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [news, setNews] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // 连接 Gateway
    const gateway = new WebSocket('ws://localhost:9000/ws');

    gateway.onopen = () => {
      console.log('[OK] 已连接到 Gateway');
      setWs(gateway);
    };

    gateway.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'STEP_END') {
        setNews(prev => [...prev, data.content]);
        setLoading(false);
      }

      if (data.type === 'ERROR') {
        console.error('[ERROR]', data.content);
        setLoading(false);
      }
    };

    return () => gateway.close();
  }, []);

  const getNews = () => {
    if (!ws) return;

    setLoading(true);
    ws.send(JSON.stringify({
      type: 'query',
      query: '获取 HackerNews 最新的 3 条热门新闻并生成中文摘要',
      session_id: 'clawfeed-' + Date.now()
    }));
  };

  return (
    <div className="clawfeed-container">
      <h2>📰 ClawFeed - AI 新闻聚合</h2>

      <button
        onClick={getNews}
        disabled={loading}
        className="get-news-btn"
      >
        {loading ? '获取中...' : '获取最新新闻'}
      </button>

      <div className="news-list">
        {news.map((item, idx) => (
          <div key={idx} className="news-item">
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## API 参考

### WebSocket 消息格式

#### 发送消息（前端 → Gateway）

```typescript
interface QueryMessage {
  type: 'query';
  query: string;           // 用户查询
  session_id?: string;     // 会话ID（可选）
}
```

#### 接收消息（Gateway → 前端）

```typescript
// 会话开始
interface SessionStartEvent {
  type: 'SESSION_START';
  session_id: string;
}

// 思考过程
interface ThinkEvent {
  type: 'THINK';
  content: string;
}

// 工具调用
interface ToolCallEvent {
  type: 'TOOL_CALL';
  tool: string;
  arguments: Record<string, any>;
}

// 工具结果
interface ToolResultEvent {
  type: 'TOOL_RESULT';
  content: string;
}

// 步骤完成
interface StepEndEvent {
  type: 'STEP_END';
  content: string;
}

// 会话结束
interface SessionEndEvent {
  type: 'SESSION_END';
  content: string;
}

// 错误
interface ErrorEvent {
  type: 'ERROR';
  content: string;
}
```

---

## 性能优化

### Gateway 模式特点

**优势**:
- ✅ 完整 Agent 功能（57个技能）
- ✅ 自动技能选择
- ✅ 支持复杂工具调用
- ✅ 会话管理
- ✅ WebSocket 实时通信

**资源占用**:
- 内存: ~150MB (加载所有技能)
- CPU: 正常（LLM 调用期间）
- 网络依赖: 需要 HackerNews API

### 优化建议

1. **缓存查询结果**
```javascript
const cache = new Map();

function getNewsCached() {
  const key = 'hackernews-latest';
  const cached = cache.get(key);

  if (cached && Date.now() - cached.time < 5 * 60 * 1000) {
    return cached.data; // 5分钟内使用缓存
  }

  // 发起新查询
  ws.send(JSON.stringify({ type: 'query', query: '...' }));
}
```

2. **限制并发查询**
```javascript
let pendingQuery = false;

function getNewsThrottled() {
  if (pendingQuery) return;

  pendingQuery = true;
  ws.send(JSON.stringify({ type: 'query', query: '...' }));

  // 收到响应后重置
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'STEP_END') {
      pendingQuery = false;
    }
  };
}
```

---

## 故障排查

### 问题 1: 技能未加载

**症状**: `news_aggregator` 技能不可用

**解决**:
```bash
# 检查技能目录
ls -la skills/builtin/

# 应该看到 57 个技能目录
```

### 问题 2: WebSocket 连接失败

**症状**: 前端无法连接到 Gateway

**解决**:
```bash
# 检查 Gateway 是否运行
lsof -i :9000

# 如果没有，启动 Gateway
python3 -m fastreact.adapters.gateway
```

### 问题 3: API 调用失败

**症状**: 返回 `[ERROR] LLM call failed`

**解决**:
```bash
# 检查 API key
python3 scripts/diagnose_config.py

# 或设置环境变量
export FASTRACT_API_KEY=sk-your-key
```

---

## 总结

### ✅ Gateway 完全支持 ClawFeed

**架构**:
```
前端 (fastreact-nano-web)
  ↓ WebSocket
Gateway Adapter (FastAPI)
  ↓
Agent (单租户，57个技能)
  ↓
news_aggregator 技能
  ↓
HackerNews API + AI 摘要
```

**使用步骤**:
1. 启动 Gateway: `python3 -m fastreact.adapters.gateway`
2. 前端连接: `ws://localhost:9000/ws`
3. 发送查询: `{"type": "query", "query": "获取最新新闻"}`
4. 接收结果: `STEP_END` 事件包含新闻摘要

**优势**:
- ✅ 无需额外配置
- ✅ 自动技能选择
- ✅ 完整 Agent 功能
- ✅ 实时 WebSocket 通信
- ✅ 支持所有 57 个技能

---

**维护者**: FastReAct Team
**最后更新**: 2025-02-27
