# 微信通道集成指南

## 概述

FastReAct 支持两种微信集成方式：

1. **微信公众号** - 面向公众用户的服务号/订阅号
2. **企业微信** - 面向企业内部的应用

## 目录

- [微信公众号集成](#微信公众号集成)
- [企业微信集成](#企业微信集成)
- [API 参考](#api-参考)
- [常见问题](#常见问题)
- [最佳实践](#最佳实践)

---

## 微信公众号集成

### 前置准备

1. **注册微信公众号**
   - 访问 https://mp.weixin.qq.com/
   - 推荐使用**服务号**（支持更多API）
   - 完成认证（需要企业资质）

2. **获取凭证**
   - AppID: 应用ID
   - AppSecret: 应用密钥
   - 位置: 开发 → 基本配置

3. **配置服务器**
   - Token: 自定义令牌
   - EncodingAESKey: 消息加密密钥（可选）
   - 服务器地址 (URL): 你的 webhook 地址

### 安装依赖

```bash
pip install httpx fastapi uvicorn
```

### 环境变量配置

创建 `.env` 文件：

```bash
# 微信公众号配置
WECHAT_APP_ID=wx1234567890abcdef
WECHAT_APP_SECRET=abcdefghijklmnopqrstuvwxyz123456
WECHAT_TOKEN=your_random_token_here
WECHAT_ENCODING_AES_KEY=your_encoding_aes_key_here  # 可选

# LLM 配置
LLM_API_KEY=your_llm_api_key
LLM_MODEL=gpt-4
```

### 基础使用

```python
from fastreact import FastReAct
from fastreact.channels.wechat import WeChatChannel

# 1. 创建 Agent
agent = FastReAct(
    api_key="your-api-key",
    model="gpt-4"
)

# 2. 创建微信通道
wechat = WeChatChannel(
    app_id="wx1234567890abcdef",
    app_secret="abcdefghijklmnopqrstuvwxyz123456",
    token="your_random_token_here"
)

# 3. 设置消息处理器
async def handle_message(channel, user_id, message, metadata):
    # 处理用户消息
    response = await agent.run(message)
    await wechat.send_message(user_id, response)

wechat.set_message_handler(handle_message)

# 4. 启动通道
await wechat.start()

# 5. 启动 webhook 服务器
await wechat.run_server(host="0.0.0.0", port=8001)
```

### 服务器配置

在微信公众号后台配置：

- **URL**: `https://your-domain.com/wechat`
- **Token**: 与代码中的 `token` 一致
- **EncodingAESKey**: 随机生成或自定义（可选）
- **消息加解密方式**: 推荐使用"安全模式"

---

## 企业微信集成

### 前置准备

1. **注册企业微信**
   - 访问 https://work.weixin.qq.com/
   - 创建企业
   - 创建应用（自建应用）

2. **获取凭证**
   - CorpID: 企业ID
   - AgentID: 应用ID
   - Secret: 应用Secret

### 安装依赖

```bash
pip install httpx
```

### 环境变量配置

```bash
# 企业微信配置
WECHAT_WORK_CORP_ID=your_corp_id
WECHAT_WORK_AGENT_ID=1001
WECHAT_WORK_SECRET=your_app_secret

# LLM 配置
LLM_API_KEY=your_llm_api_key
LLM_MODEL=gpt-4
```

### 基础使用

```python
from fastreact import FastReAct
from fastreact.channels.wechat import WeChatWorkChannel

# 1. 创建 Agent
agent = FastReAct(
    api_key="your-api-key",
    model="gpt-4"
)

# 2. 创建企业微信通道
work = WeChatWorkChannel(
    corp_id="your_corp_id",
    agent_id=1001,
    secret="your_app_secret"
)

# 3. 启动通道
await work.start()

# 4. 发送消息
await work.send_message(
    user_id="user_id",
    message="你好！这是一条测试消息。"
)

# 5. 发送文本卡片
await work.send_message(
    user_id="user_id",
    msg_type="textcard",
    message="点击查看详情",
    title="重要通知",
    url="https://example.com"
)
```

---

## API 参考

### WeChatChannel

微信公众号通道类。

#### 初始化参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `app_id` | str | ✅ | 公众号 AppID |
| `app_secret` | str | ✅ | 公众号 AppSecret |
| `token` | str | ✅ | 服务器配置 Token |
| `encoding_aes_key` | str | ❌ | 消息加密密钥 |
| `gateway_url` | str | ❌ | Gateway WebSocket URL |
| `config` | dict | ❌ | 额外配置 |

#### 主要方法

##### start()

启动微信通道。

```python
await wechat.start()
```

##### stop()

停止微信通道。

```python
await wechat.stop()
```

##### send_message()

发送消息给用户。

```python
await wechat.send_message(
    user_id="openid",
    message="消息内容",
    msg_type="text"  # text, image, voice, video, news
)
```

**参数：**
- `user_id`: 用户 OpenID
- `message`: 消息内容（不同类型含义不同）
- `msg_type`: 消息类型
  - `text`: 文本消息
  - `image`: 图片消息（message 为 media_id）
  - `voice`: 语音消息（message 为 media_id）
  - `video`: 视频消息（message 为 media_id）
  - `news`: 图文消息（message 为 articles 列表）

##### get_user_info()

获取用户信息。

```python
user_info = await wechat.get_user_info("openid")
```

**返回：**
```python
{
    "openid": "...",
    "nickname": "...",
    "sex": 1,
    "province": "...",
    "city": "...",
    "country": "...",
    "headimgurl": "..."
}
```

##### upload_media()

上传永久素材。

```python
media_id = await wechat.upload_media(
    media_type="image",
    file_path="/path/to/image.jpg"
)
```

##### run_server()

运行 webhook 服务器。

```python
await wechat.run_server(host="0.0.0.0", port=8001)
```

---

### WeChatWorkChannel

企业微信通道类，继承自 `WeChatChannel`。

#### 初始化参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `corp_id` | str | ✅ | 企业ID |
| `agent_id` | int | ✅ | 应用ID |
| `secret` | str | ✅ | 应用Secret |
| `gateway_url` | str | ❌ | Gateway WebSocket URL |
| `config` | dict | ❌ | 额外配置 |

#### 支持的消息类型

企业微信支持更多消息类型：

- `text`: 文本消息
- `textcard`: 文本卡片消息
- `news`: 图文消息
- `image`: 图片消息
- `voice`: 语音消息
- `video`: 视频消息
- `file`: 文件消息
- `mpnews`: 图文消息（mpnews 类型）

---

## 常见问题

### Q1: 验证签名失败怎么办？

**A:** 检查以下几点：
1. Token 是否与微信公众号后台配置一致
2. 服务器地址是否正确
3. 防火墙是否开放对应端口
4. URL 是否可以通过公网访问

### Q2: 用户收不到消息？

**A:** 可能的原因：
1. 用户未关注公众号
2. 超过48小时未互动（客服消息限制）
3. access_token 过期（会自动刷新）
4. 发送频率超限

**解决方案：**
- 使用模板消息（不受48小时限制）
- 引导用户主动发送消息
- 检查返回的错误码

### Q3: 如何获取用户的 OpenID？

**A:** 微信在推送消息时会携带 OpenID（`FromUserName` 字段）。

```python
def handle_message(channel, user_id, message, metadata):
    # user_id 就是 OpenID
    print(f"OpenID: {user_id}")
```

### Q4: 企业微信和公众号有什么区别？

**A:**

| 特性 | 公众号 | 企业微信 |
|------|--------|----------|
| **适用场景** | 公众服务 | 企业内部 |
| **用户群体** | 微信用户 | 企业成员 |
| **消息限制** | 48小时内 | 无限制 |
| **认证要求** | 企业资质 | 企业认证 |
| **API丰富度** | 较少 | 丰富 |

### Q5: 如何部署到生产环境？

**A:** 推荐方案：

1. **使用进程管理器**
   ```bash
   # 使用 pm2（Node.js）或 supervisord（Python）
   pm2 start python --name wechat-bot -- examples/wechat_integration.py mp
   ```

2. **使用 Nginx 反向代理**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location /wechat {
           proxy_pass http://127.0.0.1:8001;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **使用 HTTPS**
   - 微信要求使用 HTTPS
   - 推荐使用 Let's Encrypt 免费证书

---

## 最佳实践

### 1. 消息处理

```python
async def handle_message(channel, user_id, message, metadata):
    try:
        # 处理消息
        response = await agent.run(message)

        # 分段发送长消息
        if len(response) > 2048:
            for chunk in split_message(response, 2048):
                await wechat.send_message(user_id, chunk)
                await asyncio.sleep(0.5)  # 避免频率限制
        else:
            await wechat.send_message(user_id, response)

    except Exception as e:
        logger.error(f"处理消息失败: {e}")
        await wechat.send_message(user_id, "抱歉，处理您的消息时出错了。")
```

### 2. 会话管理

```python
# 使用 user_id 作为会话ID
response = await agent.run(
    query=message,
    session_id=user_id  # 保持上下文
)
```

### 3. 错误处理

```python
import logging

logger = logging.getLogger(__name__)

async def handle_message(channel, user_id, message, metadata):
    try:
        response = await agent.run(message)
        await wechat.send_message(user_id, response)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        # 发送友好的错误消息
        await wechat.send_message(user_id, "抱歉，服务暂时不可用。")
```

### 4. 日志记录

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 在处理消息时记录
logger.info(f"收到消息: {user_id} - {message}")
```

### 5. 健康检查

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "channels": list(manager.channels.keys())}
```

---

## 进阶功能

### 1. 多通道集成

```python
from fastreact.channels import ChannelManager
from fastreact.channels.wechat import WeChatChannel
from fastreact.channels.telegram import TelegramChannel

manager = ChannelManager()

# 注册多个通道
manager.register_channel(WeChatChannel(...))
manager.register_channel(TelegramChannel(...))

# 统一处理
async def handle_message(channel, user_id, message, metadata):
    # 根据 channel 调整处理逻辑
    ...

# 启动所有通道
await manager.start_all()
```

### 2. 自定义命令

```python
async def handle_message(channel, user_id, message, metadata):
    # 处理命令
    if message.startswith("/"):
        command, *args = message.split()
        if command == "/help":
            await wechat.send_message(user_id, "帮助信息...")
        elif command == "/status":
            await wechat.send_message(user_id, "状态: 正常")
        return

    # 普通消息
    response = await agent.run(message)
    await wechat.send_message(user_id, response)
```

### 3. 富媒体消息

```python
# 发送图文消息
articles = [
    {
        "title": "标题1",
        "description": "描述1",
        "url": "https://example.com/1",
        "picurl": "https://example.com/image1.jpg"
    },
    {
        "title": "标题2",
        "description": "描述2",
        "url": "https://example.com/2",
        "picurl": "https://example.com/image2.jpg"
    }
]

await wechat.send_message(user_id, articles, msg_type="news")
```

---

## 参考资源

- [微信公众平台文档](https://developers.weixin.qq.com/doc/offiaccount/Getting_Started/Overview.html)
- [企业微信API文档](https://developer.work.weixin.qq.com/document/path/90665)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [httpx 文档](https://www.python-httpx.org/)

---

## 许可证

MIT License
