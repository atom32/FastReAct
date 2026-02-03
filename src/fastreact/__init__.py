"""
FastReAct - 企业级 Agent 基础设施框架

核心特性：
- 企业级上下文管理：Token-aware + 智能压缩 + 混合检索
- 完整的 Coding Agent 工具链：Shell + Repo Map + Edit + Pruning
- 异步并发：工具调用可并发执行（最多 3 个）
- 内置缓存：LRU 缓存减少重复计算
- 流式响应：支持流式输出
- 跨平台：Windows (APSW) + Linux (sqlite-vec)
- MCP 协议：完整的 Model Context Protocol 支持

战略定位："Bring Your Own Model & Data" - 让企业用 1/10 成本获得 80% Claude Code 体验
"""

__version__ = "1.0.0"
__author__ = "FastReAct Team"

from fastreact.core.engine import FastReAct
from fastreact.core.tool import Tool, ToolCall, ToolResult
from fastreact.core.cache import LRUCache
from fastreact.core.callbacks import (
    StreamingCallbacks,
    ConsoleCallbacks,
    CallbackRecorder,
    Phase,
    StepEvent
)
from fastreact.core.streaming import (
    StreamChunk,
    StreamChunkType,
    StreamingContext,
    create_streaming_context,
)
# V2: 工具分组系统
from fastreact.core.tool_group import (
    ToolGroup,
    GroupPolicy,
    get_predefined_group,
    list_predefined_groups,
)
from fastreact.core.tool_manager import (
    ToolManager,
    get_global_manager,
)
# Tool Graph V2
from fastreact.graph import (
    ToolNode,
    NodeStatus,
    NodeConfig,
    NodePort,
    NodeResult,
    ToolGraph,
    ToolEdge,
    ParallelGroup,
    GraphMetrics,
    PlanParser,
    ParseFormat,
    ExecutionStep,
    ExecutionPlan,
    create_tool_node,
    create_graph,
    create_pipeline,
    create_parallel_workflow,
    create_plan_parser,
    parse_llm_plan,
    generate_planning_prompt,
)
# Graph State
from fastreact.graph import (
    NodeOutput,
    ExecutionContext,
    ReferenceResolver,
    GraphState,
    create_graph_state,
    create_execution_context,
)
# Tool Runtime
from fastreact.graph import (
    ExecutionStrategy,
    ExecutionConfig,
    ExecutionReport,
    ToolRuntime,
    create_runtime,
    execute_graph,
)
# Graph Agent
from fastreact.graph import (
    GraphAgent,
    AgentConfig,
    create_graph_agent,
)
# Conditional Execution
from fastreact.graph import (
    ConditionalNode,
    Branch,
    ConditionType,
    create_conditional_node,
    if_then_else,
    switch_case,
)
# Loop
from fastreact.graph import (
    LoopNode,
    LoopType,
    LoopResult,
    create_loop_node,
    repeat,
    while_true,
    for_each,
)


__all__ = [
    "FastReAct",
    "Tool",
    "ToolCall",
    "ToolResult",
    "LRUCache",
    # Streaming callbacks
    "StreamingCallbacks",
    "ConsoleCallbacks",
    "CallbackRecorder",
    "Phase",
    "StepEvent",
    # Streaming V2
    "StreamChunk",
    "StreamChunkType",
    "StreamingContext",
    "create_streaming_context",
    # Tool Groups V2
    "ToolGroup",
    "GroupPolicy",
    "get_predefined_group",
    "list_predefined_groups",
    "ToolManager",
    "get_global_manager",
    # Tool Graph V2
    "ToolNode",
    "NodeStatus",
    "NodeConfig",
    "NodePort",
    "NodeResult",
    "ToolGraph",
    "ToolEdge",
    "ParallelGroup",
    "GraphMetrics",
    "create_tool_node",
    "create_graph",
    "create_pipeline",
    "create_parallel_workflow",
    # Plan Parser
    "PlanParser",
    "ParseFormat",
    "ExecutionStep",
    "ExecutionPlan",
    "create_plan_parser",
    "parse_llm_plan",
    "generate_planning_prompt",
    # Graph State
    "NodeOutput",
    "ExecutionContext",
    "ReferenceResolver",
    "GraphState",
    "create_graph_state",
    "create_execution_context",
    # Tool Runtime
    "ExecutionStrategy",
    "ExecutionConfig",
    "ExecutionReport",
    "ToolRuntime",
    "create_runtime",
    "execute_graph",
    # Graph Agent
    "GraphAgent",
    "AgentConfig",
    "create_graph_agent",
    # Conditional Execution
    "ConditionalNode",
    "Branch",
    "ConditionType",
    "create_conditional_node",
    "if_then_else",
    "switch_case",
    # Loop
    "LoopNode",
    "LoopType",
    "LoopResult",
    "create_loop_node",
    "repeat",
    "while_true",
    "for_each",
]
