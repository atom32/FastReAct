"""
Tool Graph - 工具图系统

提供基于 DAG 的工具组合和执行框架。
"""

from .node import (
    ToolNode,
    NodeStatus,
    NodeConfig,
    NodePort,
    NodeResult,
    create_tool_node,
    create_input_port,
)

from .parser import (
    PlanParser,
    ParseFormat,
    ExecutionStep,
    ExecutionPlan,
    ParseError,
    create_plan_parser,
    parse_llm_plan,
    generate_planning_prompt,
    DEFAULT_PLANNING_PROMPT,
)
from .state import (
    NodeOutput,
    ExecutionContext,
    ReferenceResolver,
    GraphState,
    create_graph_state,
    create_execution_context,
)
from .runtime import (
    ExecutionStrategy,
    ExecutionConfig,
    ExecutionReport,
    ToolRuntime,
    create_runtime,
    execute_graph,
)
from .agent import (
    GraphAgent,
    AgentConfig,
    create_graph_agent,
)
from .conditional import (
    ConditionalNode,
    Branch,
    ConditionType,
    create_conditional_node,
    if_then_else,
    switch_case,
)
from .loop import (
    LoopNode,
    LoopType,
    LoopResult,
    create_loop_node,
    repeat,
    while_true,
    for_each,
)
from .subgraph import (
    SubGraph,
    SubGraphConfig,
    SubGraphNode,
    SubGraphTemplates,
    create_subgraph,
    compose_subgraph,
    inline_subgraph,
)
from .graph import (
    ToolGraph,
    ToolEdge,
    ParallelGroup,
    GraphMetrics,
    create_graph,
    create_pipeline,
    create_parallel_workflow,
)

__all__ = [
    # Node
    "ToolNode",
    "NodeStatus",
    "NodeConfig",
    "NodePort",
    "NodeResult",
    "create_tool_node",
    "create_input_port",
    # Graph
    "ToolGraph",
    "ToolEdge",
    "ParallelGroup",
    "GraphMetrics",
    "create_graph",
    "create_pipeline",
    "create_parallel_workflow",
    # Parser
    "PlanParser",
    "ParseFormat",
    "ExecutionStep",
    "ExecutionPlan",
    "ParseError",
    "create_plan_parser",
    "parse_llm_plan",
    "generate_planning_prompt",
    "DEFAULT_PLANNING_PROMPT",
    # State
    "NodeOutput",
    "ExecutionContext",
    "ReferenceResolver",
    "GraphState",
    "create_graph_state",
    "create_execution_context",
    # Runtime
    "ExecutionStrategy",
    "ExecutionConfig",
    "ExecutionReport",
    "ToolRuntime",
    "create_runtime",
    "execute_graph",
    # Agent
    "GraphAgent",
    "AgentConfig",
    "create_graph_agent",
    # Conditional
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
    # SubGraph
    "SubGraph",
    "SubGraphConfig",
    "SubGraphNode",
    "SubGraphTemplates",
    "create_subgraph",
    "compose_subgraph",
    "inline_subgraph",
]
