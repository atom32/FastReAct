"""
Graph Agent - 基于 Tool Graph 的 Agent

使用 LLM 作为 Planner，Runtime 作为 Executor 的实现模式。
"""

import logging
from typing import Dict, List, Any, Optional, AsyncIterator
from dataclasses import dataclass

from .parser import PlanParser, ExecutionPlan, generate_planning_prompt, ParseFormat
from .graph import ToolGraph, create_graph
from .node import ToolNode, create_tool_node
from .runtime import ToolRuntime, ExecutionConfig, ExecutionStrategy, ExecutionReport
from .state import GraphState, create_graph_state

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Agent 配置"""
    execution_strategy: ExecutionStrategy = ExecutionStrategy.LEVEL_BASED
    max_parallel: int = 3
    timeout: float = 300.0
    continue_on_error: bool = False
    enable_visualization: bool = True


class GraphAgent:
    """
    基于 Tool Graph 的 Agent

    工作流程：
    1. LLM 生成执行计划（Plan）
    2. PlanParser 解析计划为 ToolGraph
    3. ToolRuntime 执行图
    4. 返回结果

    Attributes:
        llm_driver: LLMDriver 实例（统一 LLM 调用中间层）
        tools: 工具列表
        config: Agent 配置
    """

    def __init__(
        self,
        llm_client=None,  # Deprecated: Use llm_driver instead
        llm_driver=None,
        tools: Optional[Dict[str, Any]] = None,
        config: Optional[AgentConfig] = None,
    ):
        """
        初始化 GraphAgent

        Args:
            llm_client: [DEPRECATED] LLM 客户端，请使用 llm_driver 代替
            llm_driver: LLMDriver 实例
            tools: 工具字典 {name: tool_function}
            config: Agent 配置
        """
        # 兼容旧代码：优先使用 llm_driver
        if llm_driver is not None:
            self.llm_driver = llm_driver
            self._use_driver = True
        elif llm_client is not None:
            # 兼容旧方式：包装为 driver（简单包装，不处理重试）
            from fastreact.llm import LLMDriver, LLMDriverConfig
            self.llm_driver = LLMDriver(
                api_key=getattr(llm_client, 'api_key', None),
                base_url=getattr(llm_client, 'base_url', None),
                config=LLMDriverConfig(
                    model=getattr(llm_client, 'model', None) or "gpt-4",
                    log_requests=False,  # 旧代码不期望日志
                    enable_cache=False,  # 旧代码不期望缓存
                    max_retries=0,  # 旧代码自己处理重试
                )
            )
            self._use_driver = True
        else:
            raise ValueError("必须提供 llm_driver 或 llm_client（已废弃）")

        self.tools = tools or {}
        self.config = config or AgentConfig()

        # 创建计划解析器
        self.parser = PlanParser(
            format=ParseFormat.AUTO,
            tool_registry=list(tools.keys()),
        )

    async def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        运行 Agent

        Args:
            query: 用户查询
            context: 初始上下文（可选）

        Returns:
            执行结果
        """
        logger.info(f"GraphAgent: Processing query - {query[:100]}...")

        # Step 1: 生成执行计划
        plan = await self._generate_plan(query)

        logger.info(f"GraphAgent: Generated plan with {len(plan.steps)} steps")

        # Step 2: 将计划转换为 ToolGraph
        graph = self._plan_to_graph(plan)

        # Step 3: 执行图
        runtime = ToolRuntime(
            config=ExecutionConfig(
                strategy=self.config.execution_strategy,
                max_parallel=self.config.max_parallel,
                timeout=self.config.timeout,
                continue_on_error=self.config.continue_on_error,
            ),
            state=create_graph_state(),
        )

        report = await runtime.execute(graph, initial_inputs=context)

        # Step 4: 生成最终响应
        response = await self._generate_response(query, plan, report)

        # 可视化（如果启用）
        visualization = None
        if self.config.enable_visualization:
            visualization = graph.visualize()

        return {
            "response": response,
            "plan": plan.to_dict(),
            "report": report.to_dict(),
            "visualization": visualization,
            "success": report.success,
        }

    async def _generate_plan(self, query: str) -> ExecutionPlan:
        """
        生成执行计划

        Args:
            query: 用户查询

        Returns:
            ExecutionPlan
        """
        # 生成提示词
        tool_list = list(self.tools.keys())
        prompt = generate_planning_prompt(
            user_request=query,
            tool_list=tool_list,
        )

        # 调用 LLM（使用 LLMDriver）
        try:
            messages = [
                {"role": "system", "content": "You are an expert at planning multi-step workflows."},
                {"role": "user", "content": prompt},
            ]

            response = await self.llm_driver.chat(
                messages=messages,
                temperature=0.5,
                max_tokens=2000,
            )

            llm_output = response.content

            # 解析计划
            plan = self.parser.parse(llm_output)

            return plan

        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            raise

    def _plan_to_graph(self, plan: ExecutionPlan) -> ToolGraph:
        """
        将计划转换为 ToolGraph

        Args:
            plan: 执行计划

        Returns:
            ToolGraph
        """
        graph = create_graph(name=plan.goal or "agent_plan")

        # 为每个步骤创建节点
        for step in plan.steps:
            if step.tool_name not in self.tools:
                logger.warning(f"Tool {step.tool_name} not found, skipping step {step.step_id}")
                continue

            tool_func = self.tools[step.tool_name]

            node = create_tool_node(
                id=step.step_id,
                tool=tool_func,
                inputs=step.inputs,
            )

            graph.add_node(node)

        # 添加依赖边
        for step in plan.steps:
            for dep_id in step.dependencies:
                if dep_id in graph.nodes and step.step_id in graph.nodes:
                    graph.connect(dep_id, step.step_id)

        logger.info(f"Created graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges")

        return graph

    async def _generate_response(
        self,
        query: str,
        plan: ExecutionPlan,
        report: ExecutionReport,
    ) -> str:
        """
        生成最终响应

        Args:
            query: 用户查询
            plan: 执行计划
            report: 执行报告

        Returns:
            最终响应文本
        """
        # 构建结果摘要
        results_summary = []
        for node_id, result in report.node_results.items():
            if result.status.name == "COMPLETED":
                results_summary.append(f"- {node_id}: {result.outputs}")
            else:
                results_summary.append(f"- {node_id}: FAILED - {result.error}")

        # 生成提示词
        prompt = f"""Based on the execution results, provide a helpful response to the user's query.

User Query: {query}

Plan Goal: {plan.goal}

Execution Results:
{chr(10).join(results_summary)}

Statistics:
- Total nodes: {report.total_nodes}
- Completed: {report.completed_nodes}
- Failed: {report.failed_nodes}
- Execution time: {report.execution_time:.2f}s

Provide a clear, helpful response that:
1. Summarizes what was accomplished
2. Highlights key results
3. Mentions any failures or issues
4. Provides next steps if applicable
"""

        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant that summarizes task execution results."},
                {"role": "user", "content": prompt},
            ]

            response = await self.llm_driver.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
            )

            return response.content or "Execution completed."

        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return f"Execution completed with {report.completed_nodes}/{report.total_nodes} nodes successful."

    async def stream(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        流式运行 Agent

        Args:
            query: 用户查询
            context: 初始上下文

        Yields:
            执行事件
        """
        yield {"type": "start", "query": query}

        try:
            # 生成计划
            yield {"type": "planning"}
            plan = await self._generate_plan(query)
            yield {"type": "plan_generated", "plan": plan.to_dict()}

            # 转换为图
            graph = self._plan_to_graph(plan)
            yield {
                "type": "graph_ready",
                "node_count": len(graph.nodes),
                "visualization": graph.visualize() if self.config.enable_visualization else None,
            }

            # 执行图（这里可以改为流式执行）
            runtime = ToolRuntime(
                config=ExecutionConfig(
                    strategy=self.config.execution_strategy,
                    max_parallel=self.config.max_parallel,
                ),
            )

            report = await runtime.execute(graph, initial_inputs=context)

            yield {
                "type": "execution_complete",
                "report": report.to_dict(),
            }

            # 生成响应
            response = await self._generate_response(query, plan, report)

            yield {
                "type": "done",
                "response": response,
                "success": report.success,
            }

        except Exception as e:
            logger.error(f"Error in stream: {e}")
            yield {"type": "error", "error": str(e)}


def create_graph_agent(
    llm_client=None,  # Deprecated
    llm_driver=None,
    tools: Optional[Dict[str, Any]] = None,
    config: Optional[AgentConfig] = None,
) -> GraphAgent:
    """
    创建 GraphAgent

    Args:
        llm_client: [DEPRECATED] LLM 客户端，请使用 llm_driver
        llm_driver: LLMDriver 实例
        tools: 工具字典
        config: Agent 配置

    Returns:
        GraphAgent 实例
    """
    return GraphAgent(llm_client=llm_client, llm_driver=llm_driver, tools=tools, config=config)
