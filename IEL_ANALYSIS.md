# IEL Refactoring Analysis

## Executive Summary

This document analyzes the current FastReAct architecture and compares it with the IEL (Interactive Execution Loop) requirements specified in IEL.md.

**Key Finding**: The current architecture follows a "Plan-Once, Execute-Once" pattern, while IEL requires a "Plan-Execute-Reflect-Replan" continuous loop.

---

## 1. Current Architecture Overview

### 1.1 Core Components

| Component | File | Purpose | Key Characteristics |
|-----------|------|---------|---------------------|
| **ToolGraph** | `graph/graph.py` | DAG structure | Static but mutable (add_node, add_edge) |
| **ToolNode** | `graph/node.py` | Execution unit | Has execute() returning NodeResult |
| **GraphState** | `graph/state.py` | State management | Manages node outputs, completed nodes |
| **ToolRuntime** | `graph/runtime.py` | Graph executor | Executes entire graph in one run |
| **GraphAgent** | `graph/agent.py` | Planning agent | LLM-based planner, one-shot execution |
| **Tool** | `tools/fn_registry.py` | Tool definition | Simple dataclass with execute function |

### 1.2 Current Execution Flow

```
User Query
    -> GraphAgent.run()
        -> _generate_plan()  [LLM call]
        -> _plan_to_graph()   [Parse plan to DAG]
        -> ToolRuntime.execute()  [Run entire graph]
            -> _execute_topological() / _execute_level_based()
            -> Returns ExecutionReport
        -> _generate_response()  [LLM call]
    -> Final Response
```

**Key Characteristics**:
- No step-by-step execution
- No interrupts
- No replanning
- No human-in-the-loop
- No rollback capability

---

## 2. Gap Analysis: Current vs IEL Requirements

### 2.1 ExecutionContext

**IEL Requirement**:
```python
class ExecutionContext(BaseModel):
    graph: 'ToolGraph'           # Mutable graph
    history: List[StepResult]    # Structured history
    shared_memory: Dict[str, Any]  # Shared state
    snapshots: Dict[str, Any]    # Rollback checkpoints
```

**Current Reality** (`graph/state.py:191-218`):
```python
class ExecutionContext:
    variables: Dict[str, Any]
    metadata: Dict[str, Any]
```

**Gap**:
- [ ] No `graph` attribute (current context is detached from graph)
- [ ] No `history` tracking (GraphState tracks completed nodes, but not StepResult)
- [ ] No `snapshots` for rollback
- [ ] Missing: `pending` nodes queue

**Migration Strategy**: Extend existing ExecutionContext or create new IELExecutionContext

---

### 2.2 Step-based Execution

**IEL Requirement**:
```python
executor.step(context) -> StepResult
```

**Current Reality** (`graph/runtime.py:66-96`):
```python
async def execute(self, graph, initial_inputs=None) -> ExecutionReport:
    # Executes entire graph in one call
```

**Gap**:
- [ ] No `step()` method
- [ ] Current `_execute_node()` exists but is private
- [ ] No ability to pause/resume execution
- [ ] No interrupt handling

**Migration Strategy**:
1. Create new `StepExecutor` class
2. Extract node execution logic from `ToolRuntime._execute_node()`
3. Add interrupt queue checking before each step
4. Make `step()` return structured `StepResult`

---

### 2.3 Structured Tool Results

**IEL Requirement**:
```python
class Status(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NEEDS_INPUT = "NEEDS_INPUT"

class StepResult(BaseModel):
    status: Status
    payload: Any
    error: Optional[str] = None
    meta: Dict[str, Any]
```

**Current Reality**:

Tools return `str` (from `fn_registry.py:709-728`):
```python
async def execute_tool(tool: Tool, arguments: Dict[str, Any]) -> str:
    result = await tool.execute(**arguments)
    return result  # Always string
```

Node execution returns `NodeResult` (from `node.py:62-95`):
```python
@dataclass
class NodeResult:
    node_id: str
    status: NodeStatus  # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
    outputs: Dict[str, Any]
    error: Optional[str]
    execution_time: float
```

**Gap**:
- [ ] Tools return unstructured strings, not StepResult
- [ ] No `NEEDS_INPUT` status (only NodeStatus enum)
- [ ] No failure_type (ACTION vs LOGIC)
- [ ] Missing metadata field for contextual info

**Migration Strategy**:
1. Create `StepResult` adapter wrapping `NodeResult`
2. Add `NEEDS_INPUT` to NodeStatus enum
3. Modify tool execution to detect and signal input needs
4. Add failure classification logic

---

### 2.4 Dynamic Replanning

**IEL Requirement**:
- On tool failure: Enter Reflect/Replan branch
- On user interrupt: Immediate replan
- Graph must be mutable during execution

**Current Reality** (`graph/agent.py:70-122`):
```python
async def run(self, query, context=None) -> Dict[str, Any]:
    plan = await self._generate_plan(query)  # Plan once
    graph = self._plan_to_graph(plan)
    report = await runtime.execute(graph)     # Execute once
    response = await self._generate_response(query, plan, report)
    return {"response": response, ...}        # Done
```

**Gap**:
- [ ] No replanning loop
- [ ] No reflection phase
- [ ] No dynamic graph modification
- [ ] Plan is static after generation

**Migration Strategy**:
1. Extract planning logic into reusable method
2. Add reflection logic (analyze failure, decide next action)
3. Add graph patching API (insert nodes, replace nodes, reorder)
4. Create execution loop: `Plan -> Execute -> Reflect -> (Replan | Continue)`

---

### 2.5 Human-in-the-Loop

**IEL Requirement**:
```python
# Before each step():
if interrupt_queue:
    observation = ExternalObservation.from(user_input)
    context.history.append(observation)
    trigger_replan()
```

**Current Reality**:
- No interrupt queue
- No user input handling during execution
- No way to inject observations mid-execution

**Gap**:
- [ ] No InterruptQueue mechanism
- [ ] No ExternalObservation type
- [ ] No integration with user input channels

**Migration Strategy**:
1. Create `InterruptQueue` (asyncio.Queue)
2. Add input hooks to REPL, Gateway, Web UI
3. Add interrupt check in StepExecutor.step()
4. Create replan trigger mechanism

---

### 2.6 Checkpoints & Rollback

**IEL Requirement**:
- Auto-create lightweight snapshots before high-side-effect nodes
- Rollback when same target fails N times
- Rollback when planner determines path is unsolvable

**Current Reality** (`graph/state.py:67-189`):
```python
class GraphState:
    _snapshot_history: List[Dict[str, Any]] = field(default_factory=list)

    def snapshot(self) -> str:
        # Creates snapshot but minimal implementation
        snapshot_id = f"snapshot_{len(self._snapshot_history)}"
        self._snapshot_history.append({snapshot_id: self.to_dict()})
        return snapshot_id

    def restore(self, snapshot_id: str) -> bool:
        # Basic restore, not comprehensive
```

**Gap**:
- [ ] No automatic snapshot creation
- [ ] No git/workspace diff integration
- [ ] No failure counting per target
- [ ] No rollback trigger logic

**Migration Strategy**:
1. Define "high-side-effect" nodes (write_file, bash, etc.)
2. Auto-create snapshots before these nodes
3. Add failure counter to ExecutionContext
4. Implement rollback with git stash / file restore

---

## 3. Compatibility Assessment

### 3.1 What Can Be Reused

| Component | Reusability | Notes |
|-----------|-------------|-------|
| **ToolGraph** | High | Already mutable, has add_node/add_edge |
| **ToolNode** | High | Has execute() and NodeResult, just need wrapper |
| **GraphState** | Medium | Has base state, needs extension |
| **ToolRuntime** | Low | Execute-once pattern, need new StepExecutor |
| **GraphAgent** | Low | One-shot planning, need replanning loop |
| **Tool dataclass** | High | Just need StepResult adapter |

### 3.2 What Needs New Implementation

1. **StepExecutor** - New step-based executor
2. **IELExecutionContext** - Enhanced execution context
3. **StepResult** - Structured result type
4. **InterruptQueue** - User input handling
5. **Replanner** - Dynamic planning logic
6. **CheckpointManager** - Snapshot/rollback system
7. **ReflectAgent** - Failure analysis

---

## 4. Recommended Refactoring Approach

### Phase 1: Core Data Structures (Low Risk)
1. Create `Status` enum (SUCCESS, FAILED, NEEDS_INPUT)
2. Create `StepResult` dataclass
3. Extend `ExecutionContext` or create new `IELExecutionContext`
4. Add `NEEDS_INPUT` to `NodeStatus` enum

### Phase 2: Step Executor (Medium Risk)
1. Create `StepExecutor` class
2. Implement `step(context) -> StepResult`
3. Add interrupt checking
4. Add progress tracking to context.history

### Phase 3: Replanning Loop (High Risk)
1. Extract planning logic from `GraphAgent`
2. Create `Replanner` class
3. Add reflection logic
4. Implement graph patching API
5. Create execution loop

### Phase 4: Human-in-the-Loop (Medium Risk)
1. Create `InterruptQueue`
2. Add input hooks to REPL, Gateway, Web UI
3. Integrate with StepExecutor
4. Add replan triggers

### Phase 5: Checkpoints & Rollback (Medium Risk)
1. Create `CheckpointManager`
2. Define high-side-effect nodes
3. Add auto-snapshot logic
4. Implement rollback mechanism

---

## 5. Key Design Decisions Needed

### 5.1 ExecutionContext: Extend or Replace?

**Option A**: Extend existing `ExecutionContext` in `state.py`
- Pros: Reuse existing code, minimal changes
- Cons: May break existing code using ExecutionContext

**Option B**: Create new `IELExecutionContext` extending base
- Pros: Clean separation, backward compatible
- Cons: Code duplication

**Recommendation**: Option B - Create new class for backward compatibility

### 5.2 StepExecutor: Modify ToolRuntime or New Class?

**Option A**: Add `step()` to `ToolRuntime`, keep `execute()` for backward compat
- Pros: Single executor class
- Cons: Mixed responsibilities

**Option B**: Create new `StepExecutor` class
- Pros: Clean separation, can coexist with ToolRuntime
- Cons: Code duplication

**Recommendation**: Option B - Keep ToolRuntime for batch execution, use StepExecutor for IEL

### 5.3 Tool Results: Modify Tool.execute() or Adapter?

**Option A**: Change all Tool.execute() to return StepResult
- Pros: Clean, structured
- Cons: Breaks all existing tools

**Option B**: Create adapter wrapping tool results
- Pros: Backward compatible
- Cons: Adds abstraction layer

**Recommendation**: Option B - Use adapter pattern for migration

---

## 6. File Modification List

### New Files to Create
1. `src/fastreact/graph/iel_executor.py` - StepExecutor
2. `src/fastreact/graph/iel_context.py` - IELExecutionContext
3. `src/fastreact/graph/iel_types.py` - Status, StepResult, ExternalObservation
4. `src/fastreact/graph/replanner.py` - Replanning logic
5. `src/fastreact/graph/interrupt.py` - InterruptQueue
6. `src/fastreact/graph/checkpoint.py` - CheckpointManager

### Files to Modify
1. `src/fastreact/graph/node.py` - Add NEEDS_INPUT to NodeStatus
2. `src/fastreact/graph/graph.py` - Add graph patching methods
3. `src/fastreact/graph/agent.py` - Add replanning loop
4. `src/fastreact/tools/fn_registry.py` - Add StepResult adapter
5. `src/fastreact/core/engine.py` - Integrate with IEL system

### Files to Keep Unchanged
- `src/fastreact/graph/state.py` - Keep for backward compatibility
- `src/fastreact/graph/runtime.py` - Keep for batch execution
- `src/fastreact/graph/parser.py` - Keep for plan parsing

---

## 7. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing code | High | Create new classes, keep old ones |
| Tool ecosystem incompatibility | Medium | Use adapter pattern |
| Performance degradation | Medium | Add optional optimizations |
| Complex state management | High | Use Pydantic for validation |
| Replanning loop instability | High | Add max replan depth, timeout |

---

## 8. Next Steps

1. **Review this analysis** with team/stakeholders
2. **Confirm design decisions** (ExecutionContext, StepExecutor, Tool results)
3. **Create detailed implementation plan** for each phase
4. **Start with Phase 1** (Core Data Structures) - lowest risk
5. **Implement Phase 2** (StepExecutor) - core functionality
6. **Test incrementally** after each phase

---

## 9. Questions for User

1. Should we maintain full backward compatibility with existing ToolRuntime?
2. Do you want to keep both execution modes (batch and step-based) long-term?
3. What should be the failure threshold for triggering rollback?
4. Should human interrupts be blocking or non-blocking?
5. Do we need visualization of the replanning process?
