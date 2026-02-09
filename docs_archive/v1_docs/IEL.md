
> **Role:** You are a Senior Backend Architect specializing in Agentic Frameworks.
> **Task:** Refactor the core runtime of `FastReAct`.
> **Context:** The current implementation is too rigid (static graph, run-to-completion). We need to upgrade it to a dynamic, interruptible, state-aware system similar to how "Claude Code" operates.
> **Action:** Read the following **"Unified Refactoring Spec"** carefully. Then, plan your code changes.
> **Note:** Do not start coding immediately. First, analyze which files in `FastReAct` need to be modified (e.g., `executor.py`, `graph.py`, `planner.py`) and propose a modification plan.
> ---

> **重构目标：**
> 将 FastReAct 从「静态计划 + 一次性执行」升级为
> **「状态驱动的、可中断、可反思、可再规划的执行循环（Interactive Execution Loop）」**，
> 适用于 Coding 场景的高副作用任务（文件、依赖、编译、测试）。

---

### 1️⃣ 强制引入 `ExecutionContext`（唯一真实状态源）

**必须新增一个显式的 ExecutionContext，对象生命周期贯穿整个执行过程。**

`ExecutionContext` 至少包含：

* `graph`：当前 Tool Graph（**执行期可变**）
* `state`：共享数据（memory / artifacts / user_input）
* `history`：已执行步骤的结构化记录（含 SUCCESS / FAILED）
* `pending`：尚未执行或被插队的节点
* `checkpoints`：可回滚的状态快照引用

> ❗ 禁止 Executor / Tool 依赖隐式全局状态
> ❗ 所有重规划必须基于 ExecutionContext

---

### 2️⃣ Executor 必须是 Step-based，而非一次性 run

**禁止：**

```python
executor.run(graph)
```

**必须：**

```python
executor.step(context) -> StepResult
```

每一步执行规则：

* 只执行 **一个** Tool Node
* 执行后更新 `ExecutionContext.history`
* 执行点前后必须允许中断 / 重规划

---

### 3️⃣ 工具失败不是异常，而是 Observation

**所有 Tool 必须返回结构化结果：**

```text
status: SUCCESS | FAILED | NEEDS_INPUT
payload
error / hint
failure_type: ACTION | LOGIC   (如适用)
```

**硬约束：**

* 禁止因 Tool 失败抛出 Runtime Exception
* 当 `status != SUCCESS`：

  * Executor **必须**进入 Reflect / Replan 分支
  * 控制权交回 Planner

> 失败是信号，不是终止条件

---

### 4️⃣ Tool Graph 在执行期必须允许 Patch（动态修改）

**Planner 在以下情况必须允许修改 Graph：**

* Tool 返回 FAILED
* Tool 返回 NEEDS_INPUT
* 检测到用户中断输入

**允许的 Graph Patch 行为：**

* 插入新节点（如环境修复、依赖安装）
* 替换失败节点的实现策略
* 重排尚未执行的子图

> 计划是草稿，不是不可变真理

---

### 5️⃣ 支持 Human-in-the-loop（最高优先级 Observation）

Executor 在每个 `step()` 前：

* 检查 `InterruptQueue`
* 若存在用户输入：

  * 转换为 `ExternalObservation`
  * 写入 ExecutionContext
  * **立即触发 Replan**
  * 用户输入对应的任务节点优先入栈

---

### 6️⃣ Coding 场景必须支持原子快照与回滚

**在高副作用节点前（写文件 / 安装依赖 / 运行测试）：**

* 自动创建轻量级快照（如 workspace diff / git stash）

**当满足以下任一条件：**

* 同一目标连续失败超过阈值
* Planner 判定当前路径无解

**必须：**

* 回滚至最近“干净状态”
* 基于该状态重新规划 Graph

---

### 一句话执行原则（给 Agent 兜底）

> **步进执行、状态显式、失败即信号、计划可修改、永远可回退。**


#### 2. (可选但强烈推荐) 附带核心数据结构

如果你想让 Coding Agent 的代码质量直接达到 Production 级别，在指令最后补上这段 Python 代码暗示：

> **Technical Hint (Python Type Definitions):**
> Use Pydantic or Dataclasses to enforce the state. Here is the recommended schema for the new core structures:

```python
from enum import Enum
from typing import Any, List, Optional, Dict
from pydantic import BaseModel, Field

class Status(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NEEDS_INPUT = "NEEDS_INPUT"

class StepResult(BaseModel):
    status: Status
    payload: Any
    error: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

class ExecutionContext(BaseModel):
    """The single source of truth for the agent's lifecycle."""
    graph: 'ToolGraph'  # Mutable graph
    history: List[StepResult] = Field(default_factory=list)
    shared_memory: Dict[str, Any] = Field(default_factory=dict)
    # Checkpoints for rollback capabilities
    snapshots: Dict[str, Any] = Field(default_factory=dict) 

```
