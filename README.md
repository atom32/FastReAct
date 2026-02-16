# FastReAct Nano

> **轻量级 AI Agent** - 基于 ReAct 的智能对话系统

[![Python 3.10+](https://img.shshield.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shshield.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version: 2.1.0](https://img.shshield.io/badge/version-2.1.0-brightgreen.svg)](https://github.com/atom32/FastReAct)
[![Branch: nano](https://img.shshield.io/badge/branch-nano-orange.svg)](https://github.com/atom32/FastReAct/tree/nano)

---

## 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- API Key (OpenAI/Anthropic/DeepSeek/etc.)

### 一键启动

```bash
# 克隆仓库（nano分支）
git clone -b nano https://github.com/atom32/FastReAct.git
cd FastReAct

# 启动服务（自动启动后端和前端）
./start.sh
```

启动后访问：
- **Web UI**: http://localhost:3000
- **Gateway**: ws://localhost:9000/ws

### 停止服务

```bash
./stop.sh
```

---

## 项目结构

```
FastReAct/
├── fastreact-nano/          # 后端（Python）
│   ├── src/fastreact/       # 核心 Agent 逻辑
│   ├── tests/               # 单元测试 & 集成测试
│   └── CLAUDE.md            # 开发规则
│
├── fastreact-nano-web/      # 前端（Next.js）
│   ├── app/                 # Next.js App Router
│   ├── components/          # React 组件
│   └── lib/                 # 工具函数
│
├── start.sh                 # 一键启动脚本
├── stop.sh                  # 停止脚本
├── README_NANO.md          # 详细文档
└── docs_archive/            # 归档的文档和代码
```

---

## 核心特性

### ✅ 已实现

1. **非阻塞对话**
   - 输入框始终可用
   - 支持快速连续发送多条消息
   - 无加载等待

2. **优雅中断**
   - 发送 `stop` 可立即停止长任务
   - LLM 自然确认并结束
   - 保持对话上下文

3. **实时事件流**
   - WebSocket 双向通信
   - 实时显示思考过程
   - 工具执行可视化

4. **MCP 协议支持**
   - Model Context Protocol
   - 工具集成
   - 服务器管理

---

## 架构设计

### Brain-Body 分离

**Core (大脑)** - 纯推理引擎
- 位置: `fastreact-nano/src/fastreact/core/react.py`
- 职责: 生成 THOUGHT 和 TOOL_CALL
- 特点: 无状态、纯函数

**Agent (身体)** - 循环控制
- 位置: `fastreact-nano/src/fastreact/agent.py`
- 职责: 执行工具、管理状态
- 特点: 事件驱动、可恢复

### 事件驱动协议

统一的 `AgentEvent` 流：
- `SESSION_START` - 会话开始
- `THINK` - LLM 推理
- `TOOL_CALL` - 工具调用
- `TOOL_RESULT` - 工具结果
- `SESSION_END` - 会话结束

---

## 安装

### 后端安装

```bash
cd fastreact-nano

# 安装依赖
pip install -e ".[all]"

# 配置环境变量
cp .env.example .env
# 编辑 .env，添加 API Key
```

### 前端安装

```bash
cd fastreact-nano-web

# 安装依赖
npm install
```

---

## 使用示例

### Web UI

```bash
# 启动服务
./start.sh

# 打开浏览器
open http://localhost:3000
```

### Python API

```python
from fastreact import Agent

# 初始化 Agent
agent = Agent()

# 运行查询
async for event in agent.run_event_stream("分析项目结构"):
    if event.type == "THINK":
        print(f"思考: {event.content}")
    elif event.type == "TOOL_CALL":
        print(f"调用工具: {event.tool_name}")
    elif event.type == "SESSION_END":
        print(f"答案: {event.content}")
```

### 命令行

```bash
# 使用 CLI
cd fastreact-nano
python -m fastreact.adapters.cli_enhanced

# 输入查询
> 分析当前目录的文件
```

---

## 测试

### 自动化测试

```bash
# 快速 Web 测试
python3 tests/integration/quick_web_test.py

# 所有单元测试
python3 run_tests.py unit

# 所有集成测试
python3 run_tests.py integration

# 全部测试
python3 run_tests.py all
```

### 手动测试

1. **重复消息测试**
   - 发送 "Hello"
   - 确认只显示一个消息

2. **非阻塞测试**
   - 快速发送 3 条消息
   - 确认输入框始终可用

3. **中断测试**
   - 发送长任务
   - 立即发送 "stop"
   - 确认优雅停止

---

## 配置

### 后端配置 (`.env`)

```bash
# LLM 配置
FASTRACT_API_KEY=sk-xxx
FASTRACT_MODEL=gpt-4o-mini
FASTRACT_API_BASE=https://api.openai.com/v1

# 服务器配置
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=9000
```

### 前端配置 (`.env.local`)

```bash
NEXT_PUBLIC_API_URL=ws://localhost:9000/ws
```

---

## 文档

- **[README_NANO.md](README_NANO.md)** - 分支详细说明
- **[QUICKSTART.md](fastreact-nano/QUICKSTART.md)** - 快速开始指南
- **[WEB_CHAT_FIX_SUMMARY.md](fastreact-nano/WEB_CHAT_FIX_SUMMARY.md)** - Web 功能实现
- **[CLAUDE.md](fastreact-nano/CLAUDE.md)** - 开发规则

---

## 与主分支的区别

### 主分支 (V1)
- **双模式**: ReAct + IEL/ToolGraph
- **功能**: 完整的企业框架
- **复杂度**: 更多配置选项
- **代码**: `/src`, `/tests` (根目录)

### Nano 分支
- **单模式**: ReAct only
- **定位**: 简化版本
- **Web UI**: 内置 React 界面
- **代码**: `/fastreact-nano`, `/fastreact-nano-web`

**V1 代码已归档**: `docs_archive/v1_code/`

---

## 开发

### 代码规范

遵循 `fastreact-nano/CLAUDE.md` 规则：
- ✅ 无 emoji（使用 `[OK]`, `[ERROR]` 等）
- ✅ 无硬编码路径（使用 `pathlib`）
- ✅ UTF-8 编码
- ✅ 跨平台兼容

### 贡献

1. Fork 项目
2. 创建特性分支
3. 遵循代码规范
4. 添加测试
5. 提交 Pull Request

---

## 故障排除

### Gateway 无法启动

```bash
# 检查日志
tail -f /tmp/fastreact-gateway.log

# 检查端口占用
lsof -i :9000

# 重启服务
./stop.sh
./start.sh
```

### Web UI 无法连接

```bash
# 确认 Gateway 运行
ps aux | grep gateway

# 检查 WebSocket URL
echo $NEXT_PUBLIC_API_URL

# 查看浏览器控制台错误
```

### 测试失败

```bash
# 检查 API Key
echo $FASTRACT_API_KEY

# 运行详细输出
pytest tests/unit/test_agent.py -v -s
```

---

## 路线图

### v2.2.0 (计划中)
- [ ] 多用户会话管理
- [ ] 工具取消令牌
- [ ] 恢复中断任务
- [ ] 性能监控面板

### v3.0.0 (未来)
- [ ] 插件系统
- [ ] 多语言支持
- [ ] 云端部署
- [ ] 移动端适配

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 致谢

- **Claude Sonnet 4.5** - AI 协助开发
- **OpenAI** - GPT-4o-mini API
- **Vercel** - Next.js 框架
- **Anthropic** - Claude API

---

## 联系方式

- **GitHub**: [atom32/FastReAct](https://github.com/atom32/FastReAct)
- **分支**: [nano](https://github.com/atom32/FastReAct/tree/nano)
- **文档**: [README_NANO.md](README_NANO.md)

---

**开始使用 FastReAct Nano 吧！** 🚀
