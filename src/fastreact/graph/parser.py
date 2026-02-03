"""
Plan Parser - 解析 LLM 输出为执行计划

支持从 LLM 的结构化输出（JSON/Markdown）中提取执行步骤，
并将这些步骤转换为 ToolGraph DAG 结构。
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ParseFormat(Enum):
    """解析格式"""
    JSON = "json"
    MARKDOWN = "markdown"
    AUTO = "auto"


@dataclass
class ExecutionStep:
    """
    执行步骤定义

    Attributes:
        step_id: 步骤 ID
        tool_name: 工具名称
        inputs: 输入参数
        dependencies: 依赖的步骤 ID 列表
        condition: 执行条件（可选）
        description: 步骤描述
    """
    step_id: str
    tool_name: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "step_id": self.step_id,
            "tool_name": self.tool_name,
            "inputs": self.inputs,
            "dependencies": self.dependencies,
            "condition": self.condition,
            "description": self.description,
        }


@dataclass
class ExecutionPlan:
    """
    执行计划

    Attributes:
        steps: 执行步骤列表
        goal: 计划目标
        description: 计划描述
        metadata: 额外元数据
    """
    steps: List[ExecutionStep]
    goal: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "goal": self.goal,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
            "metadata": self.metadata,
        }

    def validate(self) -> tuple[bool, List[str]]:
        """
        验证计划

        Returns:
            (is_valid, errors): 是否有效和错误列表
        """
        errors = []
        step_ids = set()

        # 检查步骤 ID 唯一性
        for step in self.steps:
            if step.step_id in step_ids:
                errors.append(f"Duplicate step_id: {step.step_id}")
            step_ids.add(step.step_id)

        # 检查依赖是否存在（必须在环检测之前）
        for step in self.steps:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    errors.append(f"Step {step.step_id} depends on non-existent step: {dep_id}")

        # 只有在所有依赖都存在时才检查环
        if not any("non-existent" in err for err in errors):
            has_cycle = self._detect_cycle()
            if has_cycle:
                errors.append("Plan contains circular dependencies")

        is_valid = len(errors) == 0
        return is_valid, errors

    def _detect_cycle(self) -> bool:
        """检测计划中是否有环"""
        # 构建依赖图（只包含存在的步骤）
        graph = {step.step_id: step.dependencies for step in self.steps}

        # DFS 检测环
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {step_id: WHITE for step_id in graph}

        def dfs(step_id: str) -> bool:
            color[step_id] = GRAY
            for dep_id in graph.get(step_id, []):
                # 跳过不存在的依赖（已在验证阶段检查）
                if dep_id not in color:
                    continue
                if color[dep_id] == GRAY:
                    return True
                if color[dep_id] == WHITE:
                    if dfs(dep_id):
                        return True
            color[step_id] = BLACK
            return False

        for step_id in graph:
            if color[step_id] == WHITE:
                if dfs(step_id):
                    return True

        return False


class ParseError(Exception):
    """解析错误"""
    pass


class PlanParser:
    """
    计划解析器

    从 LLM 输出中解析执行计划，支持多种格式。

    支持的输入格式：
    1. JSON 格式：结构化的步骤定义
    2. Markdown 格式：使用标题和代码块定义步骤
    3. 自动检测：根据内容自动选择格式
    """

    def __init__(
        self,
        format: ParseFormat = ParseFormat.AUTO,
        tool_registry: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化解析器

        Args:
            format: 解析格式
            tool_registry: 工具注册表（用于验证工具名）
        """
        self.format = format
        self.tool_registry = tool_registry or {}

    def parse(self, llm_output: str) -> ExecutionPlan:
        """
        解析 LLM 输出

        Args:
            llm_output: LLM 的原始输出

        Returns:
            ExecutionPlan: 解析后的执行计划

        Raises:
            ParseError: 解析失败
        """
        logger.debug(f"Parsing LLM output (format={self.format})")

        # 清理输出
        cleaned_output = self._clean_output(llm_output)

        # 尝试不同格式
        if self.format == ParseFormat.AUTO:
            # 自动检测格式
            plan = self._parse_auto(cleaned_output)
        elif self.format == ParseFormat.JSON:
            plan = self._parse_json(cleaned_output)
        elif self.format == ParseFormat.MARKDOWN:
            plan = self._parse_markdown(cleaned_output)
        else:
            raise ParseError(f"Unsupported format: {self.format}")

        # 验证计划
        is_valid, errors = plan.validate()
        if not is_valid:
            raise ParseError(f"Invalid plan: {errors}")

        logger.info(f"Parsed {len(plan.steps)} steps from LLM output")
        return plan

    def _clean_output(self, output: str) -> str:
        """清理输出内容"""
        # 移除多余的空白行
        lines = output.strip().split("\n")
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped:
                cleaned_lines.append(stripped)

        return "\n".join(cleaned_lines)

    def _parse_auto(self, output: str) -> ExecutionPlan:
        """自动检测格式并解析"""
        # 首先尝试 JSON
        try:
            return self._parse_json(output)
        except (json.JSONDecodeError, ParseError):
            pass

        # 尝试 Markdown
        try:
            return self._parse_markdown(output)
        except ParseError:
            pass

        raise ParseError("Unable to parse output in any supported format")

    def _parse_json(self, output: str) -> ExecutionPlan:
        """解析 JSON 格式"""
        try:
            # 尝试提取 JSON 块
            json_match = re.search(r'\{[\s\S]*\}', output)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = output

            data = json.loads(json_str)

            # 提取步骤
            steps_data = data.get("steps", [])

            if not steps_data:
                raise ParseError("No steps found in JSON output")

            steps = []
            for step_data in steps_data:
                step = ExecutionStep(
                    step_id=step_data.get("step_id", f"step_{len(steps)}"),
                    tool_name=step_data.get("tool", step_data.get("tool_name", "")),
                    inputs=step_data.get("inputs", {}),
                    dependencies=step_data.get("dependencies", []),
                    condition=step_data.get("condition"),
                    description=step_data.get("description", ""),
                )
                steps.append(step)

            return ExecutionPlan(
                steps=steps,
                goal=data.get("goal", ""),
                description=data.get("description", ""),
                metadata=data.get("metadata", {}),
            )

        except json.JSONDecodeError as e:
            raise ParseError(f"Invalid JSON: {e}")

    def _parse_markdown(self, output: str) -> ExecutionPlan:
        """解析 Markdown 格式"""
        steps = []
        goal = ""
        description = ""

        lines = output.split("\n")
        current_step = None
        in_code_block = False

        for line in lines:
            # 检测代码块
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue

            # 在代码块内跳过
            if in_code_block:
                continue

            # 提取目标
            if line.startswith("# ") or line.startswith("## Goal:"):
                goal = line.lstrip("#").strip().replace("Goal:", "").strip()

            # 提取描述
            if line.lower().startswith("description:"):
                description = line.split(":", 1)[1].strip()

            # 提取步骤标题
            step_match = re.match(r'^#+\s*(\d+\.?\s*)?Step\s*(\d+):?\s*(.+)', line, re.IGNORECASE)
            if step_match:
                step_num = step_match.group(2) if step_match.group(2) else str(len(steps) + 1)
                step_name = step_match.group(3).strip()

                current_step = ExecutionStep(
                    step_id=f"step_{step_num}",
                    tool_name=step_name,
                    description=step_name,
                )
                steps.append(current_step)

            # 提取工具信息
            elif current_step and line.lower().startswith("tool:"):
                tool_name = line.split(":", 1)[1].strip()
                current_step.tool_name = tool_name

            # 提取依赖
            elif current_step and line.lower().startswith("depends on:") or line.lower().startswith("dependencies:"):
                deps_str = line.split(":", 1)[1].strip()
                # 解析依赖列表（支持逗号、分号、空格分隔）
                deps = re.split(r'[,;\s]+', deps_str)
                current_step.dependencies = [d.strip() for d in deps if d.strip()]

            # 提取条件
            elif current_step and line.lower().startswith("condition:"):
                condition = line.split(":", 1)[1].strip()
                current_step.condition = condition

        if not steps:
            raise ParseError("No steps found in Markdown output")

        return ExecutionPlan(
            steps=steps,
            goal=goal,
            description=description,
        )

    def validate_tool_names(self, plan: ExecutionPlan) -> tuple[bool, List[str]]:
        """
        验证工具名称

        Args:
            plan: 执行计划

        Returns:
            (all_valid, invalid_tools): 是否全部有效和无效工具列表
        """
        invalid_tools = []

        for step in plan.steps:
            if step.tool_name and step.tool_name not in self.tool_registry:
                invalid_tools.append(step.tool_name)

        all_valid = len(invalid_tools) == 0
        return all_valid, invalid_tools


# ============================================================================
# 工厂函数
# ============================================================================

def create_plan_parser(
    format: ParseFormat = ParseFormat.AUTO,
    tool_registry: Optional[Dict[str, Any]] = None,
) -> PlanParser:
    """
    创建计划解析器

    Args:
        format: 解析格式
        tool_registry: 工具注册表

    Returns:
        PlanParser 实例
    """
    return PlanParser(format=format, tool_registry=tool_registry)


def parse_llm_plan(
    llm_output: str,
    format: ParseFormat = ParseFormat.AUTO,
    tool_registry: Optional[Dict[str, Any]] = None,
) -> ExecutionPlan:
    """
    快捷函数：解析 LLM 计划

    Args:
        llm_output: LLM 输出
        format: 解析格式
        tool_registry: 工具注册表

    Returns:
        ExecutionPlan: 执行计划
    """
    parser = create_plan_parser(format=format, tool_registry=tool_registry)
    return parser.parse(llm_output)


# ============================================================================
# LLM Prompt 模板
# ============================================================================

DEFAULT_PLANNING_PROMPT = """You are an expert at planning multi-step workflows.

Given a user request, create a structured execution plan using available tools.

Available tools:
{tool_list}

Output format (JSON):
```json
{{
  "goal": "Brief description of the overall goal",
  "description": "Detailed explanation of the approach",
  "steps": [
    {{
      "step_id": "step_1",
      "tool": "tool_name",
      "description": "What this step accomplishes",
      "inputs": {{
        "param1": "value1",
        "param2": "value2"
      }},
      "dependencies": [],
      "condition": null
    }},
    {{
      "step_id": "step_2",
      "tool": "another_tool",
      "description": "What this step does",
      "inputs": {{
        "param": "@step_1.result"  // Reference output from previous step
      }},
      "dependencies": ["step_1"],
      "condition": null
    }}
  ]
}}
```

Rules:
1. Each step must have a unique step_id
2. Use dependencies to define execution order
3. Reference previous step outputs with @step_id.output_name
4. Only use tools from the available list
5. Keep the plan focused and efficient

User request: {user_request}"""


def generate_planning_prompt(
    user_request: str,
    tool_list: List[str],
    template: str = DEFAULT_PLANNING_PROMPT,
) -> str:
    """
    生成规划提示词

    Args:
        user_request: 用户请求
        tool_list: 可用工具列表
        template: 提示词模板

    Returns:
        完整的提示词
    """
    tools_text = "\n".join(f"- {tool}" for tool in tool_list)
    return template.format(
        tool_list=tools_text,
        user_request=user_request,
    )
