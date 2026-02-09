# FastReAct CLI 使用指南 - 常见问题解答

**更新日期**: 2026-02-06

---

## 问题 #1: 生成的代码无法自动写入文件

### 问题描述
LLM生成了代码，但代码只显示在界面上，没有实际保存到文件中。

### 根本原因
LLM默认只是"回答问题"，不会主动使用工具来写入文件。

### 解决方案

#### 方法 A: 明确告诉LLM使用工具（推荐）
```bash
>>> 使用 write_file 工具创建 env_stress.py 文件，内容是：[您的完整需求]
```

#### 方法 B: 直接提示生成代码并保存
```bash
>>> 编写一个检测脚本 env_stress.py，[您的需求]，并使用 write_file 工具保存到当前目录
```

#### 方法 C: 使用 `/mode` 命令切换模式
```bash
>>> mode react
>>> run [您的需求]
```

### 为什么REACT模式更好？
- **GraphAgent**: 需要先生成计划（额外LLM调用），容易超时
- **REACT**: 直接执行，只需1次LLM调用，更快更直接

---

## 问题 #2: MCP工具没有显示

### 问题描述
`[INFO] Loaded 26 tools from 'github'` 表明MCP工具已加载，但LLM回答时不列出这些工具。

### 解决方案 [已修复]

使用 `/tools` 命令（已集成到快速命令中）：

**注意**: MCP工具会在首次查询时加载，首次运行显示0个MCP工具是正常的。
```bash
>>> /tools           # 首次运行：显示13个内建工具
>>> [任何查询]        # 触发MCP工具加载
>>> /tools           # 再次运行：显示13个内建 + 28个MCP工具
```

**输出示例**:
```
[统计] 总计 41 个工具
  - 内建工具: 13
  - MCP工具: 28

[内建工具] (13个)
  - calculator
  - write_file
  - read_file
  ...

[github] (26个)
  - create_or_update_file
  - search_repositories
  - ...

[apollo_core] (2个)
  - Apollo_Search
  - Apollo_Chat
```

### MCP工具已加载的证据
从日志看：
```
[INFO] Loaded 26 tools from 'github'
[INFO] Loaded 2 tools from 'apollo_core'
```

这些工具确实已注册到 `agent.tools` 中，LLM可以调用它们，只是回答时没有完整列出。

---

## 问题 #3: Spinner 和状态提示问题

### 问题描述
REACT模式下没有spinner，看不到"正在执行..."等状态提示。

### 可能原因

1. **执行速度太快** - spinner闪一下就结束了
2. **终端不支持** - 某些终端不支持ANSI转义序列
3. **console对象** - 检测为不支持rich库

### 实际情况

从您的输出看，状态提示**确实存在**：
```
[INFO] Executing tasks...
Token Usage: 6,202 → 15,438 → 25,074 → 35,378
```

这说明LLM正在思考和执行，只是没有动画式的spinner。

### 改进建议

#### 方案 A: 检查终端兼容性
```bash
# 检查是否启用了文本模式
echo %FASTREACT_TEXT_MODE%

# 如果有输出，禁用它
set FASTREACT_TEXT_MODE=
```

#### 方案 B: 使用更明显的状态文本
如果您需要更明显的状态提示，可以查看日志输出或token使用情况。

---

## 快速参考

### 常用命令
```bash
>>> /tools          # 列出所有工具（新增）
>>> /mode react     # 切换到REACT模式
>>> /tasks          # 查看任务队列
>>> /help           # 查看所有命令
>>> /save           # 保存会话
```

### 推荐工作流程

#### 代码生成任务
```bash
>>> mode react                          # 1. 切换到REACT模式
>>> 使用 write_file 创建 script.py，[需求]  # 2. 明确要求写入
>>> /save                              # 3. 保存会话
```

#### 探索性任务
```bash
>>> [直接提问]                          # AUTO模式自动选择
```

---

## 技术细节

### MCP工具加载流程
```
1. FastReAct 启动
2. 读取 config.json 中的 MCP 配置
3. 连接到 MCP 服务器
4. 获取工具列表
5. 注册到 agent.tools
6. 发送给LLM（通过tools schema）
```

### 为什么LLM不列出所有工具？
- 工具数量太多（41个），完整列表会占用大量tokens
- LLM通常只"知道"它需要的工具
- 所有工具都在schema中，LLM可以选择调用任何一个

### 验证工具可用性
```bash
>>> /tools                    # 查看工具列表
>>> run 使用 create_repository 创建测试仓库  # 测试MCP工具
```

---

## 总结

| 问题 | 状态 | 解决方案 |
|------|------|---------|
| 代码无法自动写入 | ✅ 已知 | 使用 `write_file` 工具 |
| MCP工具不显示 | ✅ 已修复 | 使用 `/tools` 命令 |
| Spinner缺失 | ⚠️ 限制 | Token使用情况可提示状态 |
| /tools命令TypeError | ✅ 已修复 | v1.1.1+ |

---

**最近修复**: `v1.1.1` - 修复 `/tools` 命令 TypeError 和快速命令集成

**最新改进** (2026-02-07):
- **Memory Flush阈值百分比化**: 软硬阈值改为百分比配置（70%/90%），自动适配任意context window
  - 40K模型：软阈值28K，硬阈值36K
  - 128K模型：软阈值90K，硬阈值115K
  - 无需手动计算，自动适配
- **ContextMonitor计数修复**: 显示当前实际context大小，而非累加值（之前bug：显示所有请求的token累加和，导致误报50K+）
- **ContextMonitor显示改进**: 进度条显示token数而非百分比（如"2.8K / 40K"）
- **会话存储逻辑修复**: 每次对话更新同一JSON文件，而非创建新文件（之前bug：每次查询创建新文件）
- **历史消息截断**: 每条历史消息限制2000字符，防止context膨胀
- **早期回应机制**:
  - 简单问候/帮助问题直接回答，跳过复杂度评估
  - 执行任务前显示 "正在读取文件..." 等提示

**下次会话建议**:
1. 优先改进任务评估逻辑（代码生成 → 推荐REACT）
2. 考虑添加更明显的状态提示
3. 改进write_file工具的使用提示
