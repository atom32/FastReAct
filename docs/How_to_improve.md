## 先看核心架构
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - 系统架构和设计原理

## 然后是如何改进

你的 **FastReAct v1.0.0** 架构在 **Token 管理**、**记忆检索** 和 **对话压缩** 方面已经做得非常扎实（甚至可以说是企业级的）。

但如果要复现 **Claude Code** (或类似的 Agentic Coding 工具) 的核心体验，目前的架构主要缺口在于：**v1.0 的设计是针对“通用对话”的，而 Coding Agent 需要针对“代码上下文”和“副作用（Side Effects）”的深度优化。**

基于你现有的 `ARCHITECTURE.md`，以下是复现 Claude Code 效果所需的关键架构改动建议：

### 1. 上下文层：从“对话流”转向“项目全貌” (Project Context)

目前的 `ContextBuilder` 和 `MemoryRetrieval` 专注于**历史对话**。但 Claude Code 的核心在于它“看见”了整个代码库。

* **现状**：`ContextBuilder` 只是从 Token 预算中切分历史记录。
* **改动方向**：引入 **Repository Map (代码库地图)**。
* **原理**：Coding Agent 不需要（也不应该）把所有文件内容塞进 Context。它需要一个高层级的目录树结构、核心类/函数的签名摘要。
* **具体实现**：
1. 新增 `src/fastreact/context/repo_mapper.py`。
2. 在 `ContextBuilder` 中，**永久保留**一部分 Token 预算（例如 2k-4k）给 Repo Map，这部分内容必须放在 System Prompt 之后、History 之前。
3. **动态更新**：当 Tool 修改了文件结构时，Repo Map 必须实时刷新。





### 2. 执行层：工具输出的智能截断 (Tool Result Pruning)

你在文档的 "Future Roadmap" 中提到了 `Tool Result Pruning`，这对于 Coding Agent 是 **P0 级** 需求，而非仅仅是优化。

* **痛点**：如果 Agent 执行 `cat package-lock.json` 或 `grep` 输出了 5000 行日志，你的 `ContextBuilder` 会瞬间爆表，或者把宝贵的 Reasoning 历史挤出去。
* **改动方向**：**Smart Truncation Strategy**。
* 在 `src/fastreact/core/engine.py` 的 `Execution` 阶段后、`Observation` 阶段前加入拦截层。
* **策略**：
* **Head/Tail 模式**：保留前 50 行和后 50 行，中间用 `<...omitted 4000 lines...>` 替换。
* **引导性提示**：如果截断发生，自动在 Observation 中追加系统提示：“*Output was truncated. Use `grep` or read specific line ranges to see missing parts.*”


* 这比通用的 `MemoryFlush` 更紧迫，因为它是单次交互内的防御。



### 3. ReACT 循环：引入 "Bash State" 和 "Editor State"

目前的架构中，Tool 是无状态的函数调用。但 Claude Code 的体验建立在**持久化环境**上。

* **现状**：`tavily_search` 用完即走。
* **改动方向**：
* **Persistent Shell Session**：Agent 不应只是运行 `os.system`，而是应该持有一个持久的 `subprocess` (如 `/bin/bash`)。这样它能维持 `cd` 后的目录状态，环境变量等。
* **Strudel / Editor Pattern**：Claude Code 不只是覆盖文件，它使用 `sed` 或自定义的 `edit_file(path, search_block, replace_block)`。
* 你需要扩展 `Layer 3 ReACT Engine`，支持 **Stateful Tools**。



### 4. 决策层：从 "ReACT" 升级为 "Plan-Act-Verify"

标准的 ReACT (Thought -> Action -> Obs) 在处理复杂编程任务时容易陷入“死胡同”。

* **现状**：线性的 ReACT Loop。
* **改动方向**：**双层循环架构**。
* **外层 (Planner)**：负责生成待办清单（Task List）。
* **内层 (Executor)**：负责执行具体的代码修改。
* **改动点**：在 `engine.py` 中，System Prompt 需要维护一个动态的 `<task_list>` 状态。每完成一个步骤，Agent 必须显式更新这个列表的状态（Pending -> Done）。



### 5. 安全与交互：Human-in-the-loop (HITL)

Claude Code 的一大特点是它在做危险操作（删除文件、Push 代码）时会询问用户。

* **现状**：`engine.py` 自动执行工具。
* **改动方向**：**Tool Policy & Interruption**。
* 在 `config.json` 中定义工具的 `risk_level`（例如 `read_file` 是 low，`write_file` 是 medium，`rm` 是 high）。
* 在 `Layer 3` 的 `3. Execution` 阶段之前，加入 **Approval Gate**。
* 如果 `risk_level > threshold`，挂起 Loop，通过 `Gateway/WebSocket` 向用户发送确认请求，收到 `approved` 事件后再继续。



### 架构演进路线图 (Roadmap for Claude Code-like behavior)

为了实现上述目标，建议对架构图进行如下调整：

#### 修改后的 System Thinking Flow

```
┌───────────────────────────────────────────────────────────────────────┐
│                    FastReAct Coding Flow (v2.0 Plan)                   │
└───────────────────────────────────────────────────────────────────────┘
                                   │
┌───────────────────┐    ┌─────────▼─────────┐
│  Repo Map/Index   │───▶│ 1. Context Build  │ 
│ (File Tree View)  │    │ (+ Task Status)   │
└───────────────────┘    └─────────┬─────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────────┐
│                          2. Execution Loop                            │
│                                                                       │
│  ┌─────────┐   ┌────────────┐   ┌──────────┐   ┌──────────────────┐   │
│  │ Thought │──▶│ Risk Check │──▶│ Execute  │──▶│ Output Pruning   │   │
│  │ (Plan)  │   │ (HITL)     │   │ (Stateful│   │ (Smart Truncate) │   │
│  └─────────┘   └────────────┘   │  Shell)  │   └────────┬─────────┘   │
│                                 └──────────┘            │             │
└─────────────────────────────────────────────────────────┼─────────────┘
                                                          ▼
                                                  ┌──────────────┐
                                                  │  Verify /    │
                                                  │  Test Run    │
                                                  └──────────────┘

```

### 总结：你需要补全的“拼图”

1. **Repo Mapper**：让 LLM 拥有上帝视角，而不仅仅是对话记忆。
2. **Stateful Shell**：从 API 调用者变成 Linux 操作员。
3. **Output Pruning**：这是防止 Token 爆炸的关键防御机制。
4. **Risk Gate**：从 `auto_execute` 变为 `conditional_execute`。

你的基础架构非常优秀（特别是 TokenCounter 重用和混合检索），这些都是 Claude Code 也需要的底层能力。只要加上上述针对 **Coding Domain** 的特化层，就能非常接近目标效果。

**下一步建议**：优先实现 **Output Pruning (Tool Result Truncation)**，因为这是 Coding Agent 最容易遇到的第一个崩溃点。


如果要复现 Claude Code 的核心体验，你需要从“通用工具（搜索/计算器）”转向一套深度优化的**工程化工具链**。

这套工具链的核心逻辑是：**“像人类开发者一样操作环境”**。这意味着工具必须支持持久化状态、大文件处理和精确修改。

以下是按照优先级排序的必须实现的工具清单（定义在 `src/fastreact/tools/`）：

---

### 第一梯队：核心交互层 (MVP 必须实现)

这四个工具构成了 Coding Agent 的最小闭环。

#### 1. `bash` (Stateful Shell Executor)

**最关键的工具**。不同于 `os.system`，它必须是一个持久化的 Shell 会话。

* **功能**：执行 Shell 命令。
* **关键特性**：
* **状态保持**：如果上一步执行了 `cd frontend` 或 `export NODE_ENV=test`，下一步必须生效。你需要用 `subprocess.Popen` 维护一个后台进程。
* **超时控制**：防止 `npm install` 卡死（例如设置 120s 超时）。
* **输出截断**：如果输出超过 200 行，自动截取 Head + Tail，并提示 Agent。


* **工具定义示例**：
```python
{
  "name": "bash",
  "description": "Run commands in a persistent shell session. Use this for navigation, running tests, or git operations.",
  "parameters": {
    "command": {"type": "string", "description": "The command to run"}
  }
}

```



#### 2. `view_file` (Smart File Reader)

LLM 不能一次读取 5MB 的日志文件。这个工具需要支持“切片读取”。

* **功能**：读取文件内容。
* **关键参数**：
* `path`: 文件路径。
* `start_line`: 起始行（可选，默认 1）。
* `end_line`: 结束行（可选，默认 100）。
* `view_window`: 比如 "lines 100-200"。


* **增强逻辑**：并在输出中带上行号（Line Numbers），这对后续的“修改”至关重要。

#### 3. `edit_file` (Search & Replace Block)

**这是最难做好的工具**。不要让 LLM 每次都重写整个文件（浪费 Token 且慢），也不要让它用 `sed`（转义字符噩梦）。

* **功能**：精准修改代码。
* **推荐模式**：**Strudel Pattern / Search-Replace**
* `path`: 文件路径。
* `search_block`: 原始内容（Unique Context）。
* `replace_block`: 新内容。


* **实现难点**：
* **Fuzzy Match**：LLM 经常记错空格或缩进。你可能需要实现一个稍微宽松的匹配算法（忽略多余空白字符），或者在匹配失败时报错提示它“Did you mean...?”。



#### 4. `ls` / `list_files`

* **功能**：探索目录结构。
* **关键特性**：
* 不要只返回文件名，要返回类似 `tree` 的结构。
* **递归限制**：默认只看当前层级，防止 token 爆炸。



---

### 第二梯队：智能检索与感知 (大幅提升智商)

当代码库很大时，Agent 不能靠 `ls` 和 `cat` 瞎找，它需要“雷达”。

#### 5. `grep` / `project_search`

* **功能**：全局搜索代码字符串或正则。
* **实现建议**：底层直接调用 `ripgrep (rg)`，速度极快。
* **用途**：Agent 思考“Where is the `AuthService` defined?” -> 调用 `grep "class AuthService"`.

#### 6. `file_tree` (Repository Map Generator)

* **功能**：生成项目的高层级地图。
* **差异**：与 `ls` 不同，这个工具应该被设计为生成并注入到 `System Prompt` 中，或者作为工具随时查看。
* **策略**：对于重要文件列出，对于 `node_modules` 或 `.git` 自动折叠。

---

### 第三梯队：高阶能力 (Claude Code 的魔法)

#### 7. `report_issue` / `ask_human`

* **功能**：当 Agent 遇到模棱两可的情况（比如“要删库吗？”），主动暂停并询问用户。
* **实现**：这不仅仅是一个 Tool，而是触发 FastReAct 引擎进入 `AWAITING_INPUT` 状态的特殊信号。

#### 8. `lint_file` / `check_syntax`

* **功能**：Agent 修改完代码后，自己运行一下语法检查。
* **实现**：根据文件扩展名自动调用 `eslint`、`pylint` 或 `go vet`。这能让 Agent 实现“自我修复”。

---

### 架构层面的改动清单

为了支持上述工具，你需要修改 `src/fastreact/core/engine.py` 和 `tools` 目录：

1. **Stateful Session Manager**:
你需要创建一个 `Session` 类，它不仅保存 Message History，还持有一个 `ShellProcess` 对象。
```python
# 伪代码概念
class CodingSession:
    def __init__(self):
        self.shell = Popen(['/bin/bash'], stdin=PIPE, stdout=PIPE, ...)
        self.cwd = "/workspace"
        self.env = os.environ.copy()

```


2. **Tool Output Processor (Middleware)**:
在工具返回结果给 LLM 之前，必须经过一层处理：
* 如果输出是 XML/JSON，保持原样。
* 如果输出是 10000 行文本，**必须** 压缩成：
> Output (truncated):
> [Lines 1-50] ...
> ... <9000 lines hidden> ...
> [Lines 9950-10000]




3. **Diff View**:
当 `edit_file` 成功时，Observation 不应该只返回 "Success"，而应该返回 Unified Diff（类似 Git 的 diff），这样 LLM 能够确认它修改的内容是否符合预期。

### 总结：你的 `v1.1` 工具箱

| Tool Name | Type | Priority | Implementation Core |
| --- | --- | --- | --- |
| `bash` | Execution | **P0** | `subprocess` with state & timeout |
| `view_file` | Read | **P0** | Line range slicing |
| `edit_file` | Write | **P0** | Search/Replace block matching |
| `ls_dir` | Navigation | **P1** | Depth-limited tree listing |
| `grep_search` | Discovery | **P1** | `ripgrep` wrapper |
| `ask_user` | Interaction | **P2** | Interrupt mechanism |

先把 **P0** 的三个工具做出来，你的 FastReAct 就能通过简单的 Coding Agent 测试了。